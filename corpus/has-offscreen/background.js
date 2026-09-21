// Extension using Chrome-only offscreen API
chrome.runtime.onInstalled.addListener(async () => {
  console.log('Offscreen extension installed');

  // Check if offscreen API is available
  if (chrome.offscreen) {
    console.log('Offscreen API available');
    
    // Create offscreen document
    await chrome.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: ['DOM_SCRAPING'],
      justification: 'Need to process DOM in background'
    });
    
    console.log('Offscreen document created');
  } else {
    console.warn('Offscreen API not available - this is Chrome-only');
  }
});

// Listen for messages
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'processData') {
    // Send to offscreen document
    chrome.runtime.sendMessage({
      target: 'offscreen',
      data: request.data
    });
    sendResponse({ status: 'sent' });
  }
});
