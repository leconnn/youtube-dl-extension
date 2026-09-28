// Owns the native messaging Port to the local host, tracks in-flight
// download jobs, and pushes progress/notifications independently of
// whether the popup is open (a Port opened from the popup would die the
// instant the popup closes, so the popup only ever talks to us).

const HOST_NAME = 'com.leconnn.youtube_dl_extension';

let port = null;

// requestId -> { resolve, reject }, for one-shot request/response calls (ping, formats)
const pendingRequests = {};

// requestId -> tabUrl, so a pushed jobUpdate can find its job
const requestIdToTabUrl = {};

// tabUrl -> { requestId, title, mode, status, percent, filename, error }
const jobs = {};

// notificationId -> file path, so clicking a finished-download notification
// can ask the host to reveal it
const notificationPaths = {};

function newRequestId() {
  return crypto.randomUUID();
}

function ensurePort() {
  if (port) return port;
  port = browser.runtime.connectNative(HOST_NAME);
  port.onMessage.addListener(onPortMessage);
  port.onDisconnect.addListener(onPortDisconnect);
  return port;
}

function sendRequest(message) {
  return new Promise((resolve, reject) => {
    pendingRequests[message.requestId] = { resolve, reject };
    try {
      ensurePort().postMessage(message);
    } catch (e) {
      delete pendingRequests[message.requestId];
      reject(e);
    }
  });
}

function notify(job) {
  const isError = job.status === 'error';
  browser.notifications.create({
    type: 'basic',
    title: isError ? 'Download failed' : 'Download finished',
    message: isError ? job.error : (job.title || job.filename || 'Saved') + (job.path ? '\nClick to show in folder' : ''),
  }).then((notificationId) => {
    if (!isError && job.path) {
      notificationPaths[notificationId] = job.path;
    }
  });
}

browser.notifications.onClicked.addListener((notificationId) => {
  const path = notificationPaths[notificationId];
  if (!path) return;
  ensurePort().postMessage({ type: 'revealFile', requestId: newRequestId(), path });
});

browser.notifications.onClosed.addListener((notificationId) => {
  delete notificationPaths[notificationId];
});

function broadcast(tabUrl) {
  browser.runtime.sendMessage({ type: 'jobUpdate', tabUrl, job: jobs[tabUrl] }).catch(() => {
    // No popup listening; that's fine.
  });
}

function onPortMessage(msg) {
  if (msg.type === 'pong' || msg.type === 'formatsResult' || msg.type === 'configResult' || msg.type === 'browseFolderResult') {
    const pending = pendingRequests[msg.requestId];
    if (!pending) return;
    delete pendingRequests[msg.requestId];
    if (msg.ok === false) {
      pending.reject(new Error(msg.error));
    } else {
      pending.resolve(msg);
    }
    return;
  }

  if (msg.type === 'jobUpdate') {
    const tabUrl = requestIdToTabUrl[msg.requestId];
    if (!tabUrl || !jobs[tabUrl]) return;
    Object.assign(jobs[tabUrl], msg);
    broadcast(tabUrl);
    if (msg.status === 'finished' || msg.status === 'error') {
      notify(jobs[tabUrl]);
      delete requestIdToTabUrl[msg.requestId];
    }
  }
}

function onPortDisconnect() {
  const err = browser.runtime.lastError;
  const message = 'Native host disconnected' + (err && err.message ? ': ' + err.message : '');
  port = null;

  Object.values(pendingRequests).forEach((p) => p.reject(new Error(message)));
  for (const id in pendingRequests) delete pendingRequests[id];

  for (const tabUrl in jobs) {
    if (jobs[tabUrl].status !== 'finished' && jobs[tabUrl].status !== 'error') {
      jobs[tabUrl].status = 'error';
      jobs[tabUrl].error = message;
      broadcast(tabUrl);
      notify(jobs[tabUrl]);
    }
  }
}

browser.runtime.onMessage.addListener((message) => {
  if (message.type === 'getFormats') {
    return sendRequest({ type: 'formats', requestId: newRequestId(), url: message.url });
  }

  if (message.type === 'startDownload') {
    const requestId = newRequestId();
    requestIdToTabUrl[requestId] = message.tabUrl;
    jobs[message.tabUrl] = {
      requestId,
      title: message.title,
      mode: message.mode,
      status: 'starting',
      percent: 0,
    };
    try {
      ensurePort().postMessage({
        type: 'download',
        requestId,
        url: message.url,
        mode: message.mode,
        quality: message.quality,
        title: message.title,
        downloadDir: message.downloadDir,
      });
    } catch (e) {
      jobs[message.tabUrl].status = 'error';
      jobs[message.tabUrl].error = e.message;
    }
    broadcast(message.tabUrl);
    return;
  }

  if (message.type === 'getJob') {
    return Promise.resolve(jobs[message.tabUrl] || null);
  }

  if (message.type === 'getConfig') {
    return sendRequest({ type: 'getConfig', requestId: newRequestId() });
  }

  if (message.type === 'setConfig') {
    return sendRequest({ type: 'setConfig', requestId: newRequestId(), config: message.config });
  }

  if (message.type === 'browseFolder') {
    return sendRequest({ type: 'browseFolder', requestId: newRequestId() });
  }
});
