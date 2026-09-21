browser.runtime.onInstalled.addListener(() => {
  console.log('Simple Popup extension installed');
});

browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'getData') {
    browser.storage.local.get('userSettings', (result) => {
      sendResponse(result.userSettings);
    });
    return true; // Keep message channel open
  }
});
