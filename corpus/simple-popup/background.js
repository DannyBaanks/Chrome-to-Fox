chrome.runtime.onInstalled.addListener(() => {
  console.log('Simple Popup extension installed');
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'getData') {
    chrome.storage.local.get('userSettings', (result) => {
      sendResponse(result.userSettings);
    });
    return true; // Keep message channel open
  }
});
