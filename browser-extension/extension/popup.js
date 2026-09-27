const YOUTUBE_URL_RE = /^https?:\/\/(www\.|m\.)?(youtube\.com\/(watch\?|shorts\/)|youtu\.be\/)/i;

const messageEl = document.getElementById('message');
const videoInfoEl = document.getElementById('video-info');
const thumbEl = document.getElementById('thumb');
const titleEl = document.getElementById('title');
const mp4QualityEl = document.getElementById('mp4-quality');
const mp3QualityEl = document.getElementById('mp3-quality');
const wavHintEl = document.getElementById('wav-hint');
const downloadBtn = document.getElementById('download');
const progressWrap = document.getElementById('progress-wrap');
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');

const settingsToggleBtn = document.getElementById('settings-toggle');
const settingsPanel = document.getElementById('settings-panel');
const downloadDirInput = document.getElementById('download-dir');
const saveSettingsBtn = document.getElementById('save-settings');
const settingsStatusEl = document.getElementById('settings-status');

const themeToggleBtn = document.getElementById('theme-toggle');
const iconSun = document.getElementById('icon-sun');
const iconMoon = document.getElementById('icon-moon');

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

function formatBytes(bytes) {
  if (bytes == null) return null;
  const units = ['B', 'KB', 'MB', 'GB'];
  let n = bytes;
  let i = 0;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i++;
  }
  return n.toFixed(i === 0 ? 0 : (n < 10 ? 1 : 0)) + ' ' + units[i];
}

function estimateMp3Bytes(duration, quality, bestAudioKbps) {
  if (!duration) return null;
  const kbps = quality === 'best' ? (bestAudioKbps || 192) : Number(quality);
  return duration * kbps * 125; // kbps * 1000 / 8
}

function estimateWavBytes(duration) {
  if (!duration) return null;
  return duration * 176400; // ~CD quality: 44.1kHz, 16-bit, stereo
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

function startDownload(url) {
  const mode = selectedMode();
  const quality = selectedQuality(mode);
  const title = titleEl.value.trim() || titleEl.placeholder;
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
  titleEl.value = '';
  titleEl.placeholder = info.title || '';

  if (info.thumbnail) {
    thumbEl.src = info.thumbnail;
    thumbEl.classList.remove('hidden');
  } else {
    thumbEl.classList.add('hidden');
  }

  mp4QualityEl.innerHTML = '';
  (info.video_qualities || []).forEach((q) => {
    const opt = document.createElement('option');
    opt.value = q.height;
    const size = formatBytes(q.estimated_bytes);
    opt.textContent = q.height + 'p' + (size ? ' · ' + size : '');
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
    const size = formatBytes(estimateMp3Bytes(info.duration, q, info.best_audio_kbps));
    const label = q === 'best' ? 'Best' : q + ' kbps';
    opt.textContent = label + (size ? ' · ~' + size : '');
    mp3QualityEl.appendChild(opt);
  });

  const wavSize = formatBytes(estimateWavBytes(info.duration));
  wavHintEl.textContent = 'lossless' + (wavSize ? ' · ~' + wavSize : '');

  videoInfoEl.classList.remove('hidden');
}

function setSettingsStatus(text) {
  settingsStatusEl.textContent = text;
}

function loadSettings() {
  setSettingsStatus('Loading…');
  browser.runtime.sendMessage({ type: 'getConfig' })
    .then((res) => {
      downloadDirInput.value = res.downloadDir || '';
      setSettingsStatus('');
    })
    .catch((err) => {
      setSettingsStatus('Error: ' + err.message);
    });
}

function saveSettings() {
  setSettingsStatus('Saving…');
  browser.runtime.sendMessage({
    type: 'setConfig',
    config: { downloadDir: downloadDirInput.value.trim() },
  })
    .then((res) => {
      downloadDirInput.value = res.downloadDir || '';
      setSettingsStatus('Saved');
      setTimeout(() => setSettingsStatus(''), 1500);
    })
    .catch((err) => {
      setSettingsStatus('Error: ' + err.message);
    });
}

settingsToggleBtn.addEventListener('click', () => {
  const opening = settingsPanel.classList.contains('hidden');
  settingsPanel.classList.toggle('hidden');
  if (opening) loadSettings();
});

saveSettingsBtn.addEventListener('click', saveSettings);

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  const isDark = theme === 'dark';
  iconMoon.classList.toggle('hidden', isDark);
  iconSun.classList.toggle('hidden', !isDark);
  themeToggleBtn.title = isDark ? 'Switch to light mode' : 'Switch to dark mode';
}

function initTheme() {
  browser.storage.local.get('theme').then((stored) => {
    const theme = stored.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    applyTheme(theme);
  });
}

themeToggleBtn.addEventListener('click', () => {
  const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  browser.storage.local.set({ theme: next });
});

initTheme();

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

        downloadBtn.addEventListener('click', () => startDownload(url));

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
