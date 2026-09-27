const YOUTUBE_URL_RE = /^https?:\/\/(www\.|m\.)?(youtube\.com\/(watch\?|shorts\/)|youtu\.be\/)/i;
const DEFAULT_BACKEND_URL = 'http://127.0.0.1:4325';

const messageEl = document.getElementById('message');
const videoInfoEl = document.getElementById('video-info');
const titleEl = document.getElementById('title');
const mp4QualityEl = document.getElementById('mp4-quality');
const mp3QualityEl = document.getElementById('mp3-quality');
const downloadBtn = document.getElementById('download');
const progressWrap = document.getElementById('progress-wrap');
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');

document.getElementById('open-options').addEventListener('click', (e) => {
  e.preventDefault();
  browser.runtime.openOptionsPage();
});

function setMessage(text) {
  messageEl.textContent = text;
}

function getSettings() {
  return browser.storage.local.get(['backendUrl', 'token']).then((stored) => ({
    backendUrl: (stored.backendUrl || DEFAULT_BACKEND_URL).replace(/\/+$/, ''),
    token: stored.token || '',
  }));
}

function apiFetch(backendUrl, token, path, options) {
  options = options || {};
  options.headers = Object.assign({}, options.headers, { 'X-Auth-Token': token });
  return fetch(backendUrl + path, options).then((res) => {
    return res.json().then((body) => {
      if (!res.ok) {
        throw new Error(body.error || ('Request failed: ' + res.status));
      }
      return body;
    });
  });
}

function currentTabUrl() {
  return browser.tabs.query({ active: true, currentWindow: true }).then((tabs) => tabs[0].url);
}

function selectedMode() {
  return document.querySelector('input[name="mode"]:checked').value;
}

function selectedQuality(mode) {
  if (mode === 'mp4') return mp4QualityEl.value;
  if (mode === 'mp3') return mp3QualityEl.value;
  return undefined;
}

function showProgress(status) {
  progressWrap.classList.remove('hidden');
  const percent = status.percent || 0;
  progressBar.style.width = percent + '%';
  if (status.status === 'starting') {
    progressText.textContent = 'Starting…';
  } else if (status.status === 'downloading') {
    progressText.textContent = 'Downloading… ' + percent + '%';
  } else if (status.status === 'converting') {
    progressText.textContent = 'Converting…';
  } else if (status.status === 'finished') {
    progressText.textContent = 'Saved as ' + status.filename;
  } else if (status.status === 'error') {
    progressText.textContent = 'Error: ' + status.error;
  }
}

function pollJob(backendUrl, token, jobId, tabUrl) {
  const tick = () => {
    apiFetch(backendUrl, token, '/status?id=' + encodeURIComponent(jobId))
      .then((status) => {
        showProgress(status);
        if (status.status === 'finished' || status.status === 'error') {
          browser.storage.local.remove('activeJob');
          downloadBtn.disabled = false;
          return;
        }
        setTimeout(tick, 1000);
      })
      .catch((err) => {
        progressText.textContent = 'Error: ' + err.message;
        downloadBtn.disabled = false;
      });
  };
  browser.storage.local.set({ activeJob: { jobId, tabUrl, backendUrl } });
  tick();
}

function startDownload(backendUrl, token, url) {
  const mode = selectedMode();
  const quality = selectedQuality(mode);
  downloadBtn.disabled = true;
  progressWrap.classList.remove('hidden');
  progressText.textContent = 'Starting…';
  progressBar.style.width = '0%';

  apiFetch(backendUrl, token, '/download', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, mode, quality }),
  })
    .then((res) => pollJob(backendUrl, token, res.job_id, url))
    .catch((err) => {
      progressText.textContent = 'Error: ' + err.message;
      downloadBtn.disabled = false;
    });
}

function populateFormats(info) {
  titleEl.textContent = info.title || '';

  mp4QualityEl.innerHTML = '';
  (info.video_qualities || []).forEach((h) => {
    const opt = document.createElement('option');
    opt.value = h;
    opt.textContent = h + 'p';
    mp4QualityEl.appendChild(opt);
  });
  if (mp4QualityEl.options.length === 0) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'no video streams found';
    mp4QualityEl.appendChild(opt);
  }

  mp3QualityEl.innerHTML = '';
  (info.mp3_qualities || ['best', '320', '256', '192', '128']).forEach((q) => {
    const opt = document.createElement('option');
    opt.value = q;
    opt.textContent = q === 'best' ? 'Best' : q + ' kbps';
    mp3QualityEl.appendChild(opt);
  });

  videoInfoEl.classList.remove('hidden');
}

function init() {
  getSettings().then(({ backendUrl, token }) => {
    if (!token) {
      setMessage('Set up the backend token in settings, then reopen this popup.');
      return;
    }

    currentTabUrl().then((url) => {
      if (!YOUTUBE_URL_RE.test(url)) {
        setMessage('Open a YouTube video to download it (only YouTube is supported so far).');
        return;
      }

      setMessage('Loading video info…');

      apiFetch(backendUrl, token, '/formats?url=' + encodeURIComponent(url))
        .then((info) => {
          setMessage('');
          populateFormats(info);

          downloadBtn.addEventListener('click', () => startDownload(backendUrl, token, url));

          browser.storage.local.get('activeJob').then((stored) => {
            const job = stored.activeJob;
            if (job && job.tabUrl === url) {
              downloadBtn.disabled = true;
              pollJob(backendUrl, token, job.jobId, url);
            }
          });
        })
        .catch((err) => {
          setMessage(
            'Could not reach the local backend (' + err.message + '). ' +
            'Is browser-extension/backend/server.py running?'
          );
        });
    });
  });
}

init();
