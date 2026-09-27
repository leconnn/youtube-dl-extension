const DEFAULT_BACKEND_URL = 'http://127.0.0.1:4325';

const backendUrlInput = document.getElementById('backendUrl');
const tokenInput = document.getElementById('token');
const statusEl = document.getElementById('status');

function load() {
  browser.storage.local.get(['backendUrl', 'token']).then((stored) => {
    backendUrlInput.value = stored.backendUrl || DEFAULT_BACKEND_URL;
    tokenInput.value = stored.token || '';
  });
}

function save() {
  const backendUrl = (backendUrlInput.value || DEFAULT_BACKEND_URL).replace(/\/+$/, '');
  const token = tokenInput.value.trim();
  browser.storage.local.set({ backendUrl, token }).then(() => {
    statusEl.textContent = 'Saved.';
    setTimeout(() => { statusEl.textContent = ''; }, 1500);
  });
}

document.getElementById('save').addEventListener('click', save);
load();
