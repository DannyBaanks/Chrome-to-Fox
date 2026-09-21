chrome.runtime.onInstalled.addListener(() => {
  console.log('Popup UI extension installed');
  chrome.storage.local.set({ count: 0 });
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'incrementCount') {
    chrome.storage.local.get('count', (result) => {
      const newCount = (result.count || 0) + 1;
      chrome.storage.local.set({ count: newCount, lastCheck: Date.now() });
      sendResponse({ count: newCount });
    });
    return true;
  }
});
