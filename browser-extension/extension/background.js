// Tracks in-flight download jobs and polls the backend independently of
// whether the popup is open, so completion notifications still fire after
// the popup closes.

const POLL_INTERVAL_MS = 1000;

// Keyed by tabUrl. Value: { jobId, backendUrl, token, title, mode, status, percent, filename, error }
const jobs = {};

function apiFetch(backendUrl, token, path, options) {
  options = options || {};
  options.headers = Object.assign({}, options.headers, { 'X-Auth-Token': token });
  return fetch(backendUrl + path, options).then((res) =>
    res.json().then((body) => {
      if (!res.ok) throw new Error(body.error || ('Request failed: ' + res.status));
      return body;
    })
  );
}

function notify(job) {
  const isError = job.status === 'error';
  browser.notifications.create({
    type: 'basic',
    title: isError ? 'Download failed' : 'Download finished',
    message: isError ? job.error : (job.title || job.filename || 'Saved'),
  });
}

function broadcast(tabUrl) {
  browser.runtime.sendMessage({ type: 'jobUpdate', tabUrl, job: jobs[tabUrl] }).catch(() => {
    // No popup listening; that's fine.
  });
}

function poll(tabUrl) {
  const job = jobs[tabUrl];
  if (!job || job.status === 'finished' || job.status === 'error') return;

  apiFetch(job.backendUrl, job.token, '/status?id=' + encodeURIComponent(job.jobId))
    .then((status) => {
      Object.assign(job, status);
      broadcast(tabUrl);
      if (job.status === 'finished' || job.status === 'error') {
        notify(job);
      } else {
        setTimeout(() => poll(tabUrl), POLL_INTERVAL_MS);
      }
    })
    .catch((err) => {
      job.status = 'error';
      job.error = err.message;
      broadcast(tabUrl);
      notify(job);
    });
}

browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'startTracking') {
    jobs[message.tabUrl] = {
      jobId: message.jobId,
      backendUrl: message.backendUrl,
      token: message.token,
      title: message.title,
      mode: message.mode,
      status: 'starting',
      percent: 0,
    };
    poll(message.tabUrl);
    return;
  }
  if (message.type === 'getJob') {
    sendResponse(jobs[message.tabUrl] || null);
    return true;
  }
});
