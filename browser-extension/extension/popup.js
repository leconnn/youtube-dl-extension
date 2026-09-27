const YOUTUBE_URL_RE = /^https?:\/\/(www\.|m\.)?(youtube\.com\/(watch\?|shorts\/)|youtu\.be\/)/i;

const messageEl = document.getElementById('message');
const videoInfoEl = document.getElementById('video-info');
const thumbEl = document.getElementById('thumb');
const titleEl = document.getElementById('title');
const mp4QualityEl = document.getElementById('mp4-quality');
const mp3QualityEl = document.getElementById('mp3-quality');
const downloadBtn = document.getElementById('download');
const progressWrap = document.getElementById('progress-wrap');
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');

let currentTabUrlValue = null;

function setMessage(text) {
  messageEl.textContent = text;
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

function renderJob(job) {
  if (!job) {
    progressWrap.classList.add('hidden');
    downloadBtn.disabled = false;
    return;
  }
  progressWrap.classList.remove('hidden');
  const percent = job.percent || 0;
  progressBar.style.width = percent + '%';
  if (job.status === 'starting') {
    progressText.textContent = 'Starting…';
  } else if (job.status === 'downloading') {
    progressText.textContent = 'Downloading… ' + percent + '%';
  } else if (job.status === 'converting') {
    progressText.textContent = 'Converting…';
  } else if (job.status === 'finished') {
    progressText.textContent = 'Saved as ' + job.filename;
  } else if (job.status === 'error') {
    progressText.textContent = 'Error: ' + job.error;
  }
  downloadBtn.disabled = !(job.status === 'finished' || job.status === 'error');
}

browser.runtime.onMessage.addListener((message) => {
  if (message.type === 'jobUpdate' && message.tabUrl === currentTabUrlValue) {
    renderJob(message.job);
  }
});

function startDownload(url, title) {
  const mode = selectedMode();
  const quality = selectedQuality(mode);
  downloadBtn.disabled = true;
  renderJob({ status: 'starting', percent: 0 });

  browser.runtime.sendMessage({
    type: 'startDownload',
    tabUrl: url,
    url,
    mode,
    quality,
    title,
  }).catch((err) => {
    renderJob({ status: 'error', error: err.message });
  });
}

function populateFormats(info) {
  titleEl.textContent = info.title || '';

  if (info.thumbnail) {
    thumbEl.src = info.thumbnail;
    thumbEl.classList.remove('hidden');
  } else {
    thumbEl.classList.add('hidden');
  }

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
  currentTabUrl().then((url) => {
    currentTabUrlValue = url;

    if (!YOUTUBE_URL_RE.test(url)) {
      setMessage('Open a YouTube video to download it (only YouTube is supported so far).');
      return;
    }

    setMessage('Loading video info…');

    browser.runtime.sendMessage({ type: 'getFormats', url })
      .then((res) => {
        setMessage('');
        populateFormats(res);

        downloadBtn.addEventListener('click', () => startDownload(url, res.title));

        browser.runtime.sendMessage({ type: 'getJob', tabUrl: url }).then((job) => {
          if (job) renderJob(job);
        });
      })
      .catch((err) => {
        setMessage(
          'Could not reach the youtube-dl Downloader native host (' + err.message + '). ' +
          'Try reinstalling it.'
        );
      });
  });
}

init();
