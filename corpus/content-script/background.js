chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'pageInfo') {
    console.log('Page info:', request.url, request.title);
    chrome.storage.local.set({
      [`page_${request.url}`]: {
        title: request.title,
        timestamp: Date.now()
      }
    });
  }
});
