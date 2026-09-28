// Minimal shim so the shared popup.js (which calls browser.*) runs
// unmodified under Chromium. Chrome/Edge/Brave's chrome.* APIs already
// return native Promises when no callback is passed (tabs.query,
// storage.local.get/set), so this is mostly just a name alias. The one real
// piece of behavior is wrapping runtime.sendMessage: raw chrome.runtime
// gives the receiving end no way to reject the caller's promise --
// sendResponse() only ever resolves it -- so background.js replies with
// { ok: false, error } on failure, and this shim turns that into an actual
// rejection, matching what Firefox's browser.runtime.sendMessage does when
// a listener returns a rejected promise. popup.js's existing
// `.catch(err => ...)` calls rely on that.
(function () {
  if (self.browser) return; // real Firefox `browser`, nothing to do

  self.browser = {
    tabs: chrome.tabs,
    storage: chrome.storage,
    notifications: chrome.notifications,
    runtime: Object.assign({}, chrome.runtime, {
      sendMessage: function (message) {
        return chrome.runtime.sendMessage(message).then((response) => {
          if (response && response.ok === false) {
            throw new Error(response.error);
          }
          return response;
        });
      },
    }),
  };
})();
