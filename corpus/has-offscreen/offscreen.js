// Offscreen document script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.target === 'offscreen') {
    console.log('Processing in offscreen document:', request.data);
    
    // Simulate DOM processing
    const result = processInOffscreen(request.data);
    
    // Send result back
    chrome.runtime.sendMessage({
      type: 'offscreenResult',
      result: result
    });
  }
});

function processInOffscreen(data) {
  // Simulate some processing
  return {
    processed: true,
    timestamp: Date.now(),
    data: data
  };
}
