/**
 * Chrome-to-Fox Polyfill: chrome.tabCapture
 * 
 * Chrome's tabCapture API allows capturing tab content.
 * Firefox doesn't support this API.
 */

if (typeof chrome !== 'undefined' && chrome.tabCapture) {
  console.log('chrome.tabCapture polyfill: native API available');
} else if (typeof chrome !== 'undefined') {
  chrome.tabCapture = {
    capture: async function(options, callback) {
      console.warn('chrome.tabCapture.capture polyfill: ' +
        'Tab capture not supported in Firefox. ' +
        'Use getUserMedia or screen capture APIs instead.');
      
      if (callback) {
        callback(null, { error: 'Not supported in Firefox' });
      }
      return null;
    },
    
    getCapturedTabs: async function() {
      console.warn('chrome.tabCapture.getCapturedTabs polyfill: ' +
        'Tab capture not supported in Firefox');
      return [];
    }
  };
  
  console.log('chrome.tabCapture polyfill: installed (no-op implementation)');
}
