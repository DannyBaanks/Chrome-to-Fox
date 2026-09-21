/**
 * Chrome-to-Fox Polyfill: chrome.offscreen
 * 
 * Chrome's offscreen API allows creating offscreen documents for
 * background processing. Firefox doesn't support this API, so we
 * provide a minimal polyfill that logs warnings.
 */

if (typeof chrome !== 'undefined' && chrome.offscreen) {
  // Already exists (unlikely in Firefox)
  console.log('chrome.offscreen polyfill: native API available');
} else if (typeof chrome !== 'undefined') {
  // Create polyfill
  chrome.offscreen = {
    _documents: new Map(),
    
    createDocument: async function(options) {
      console.warn('chrome.offscreen.createDocument polyfill: ' +
        'Offscreen documents not supported in Firefox. ' +
        'Reason:', options.reason, 
        'Justification:', options.justification);
      
      // Store the request for reference
      this._documents.set(options.url, {
        url: options.url,
        reasons: options.reasons,
        justification: options.justification,
        created: Date.now()
      });
      
      return true;
    },
    
    closeDocument: async function(url) {
      console.warn('chrome.offscreen.closeDocument polyfill: ' +
        'Offscreen documents not supported in Firefox');
      this._documents.delete(url);
      return true;
    },
    
    hasDocument: function(url) {
      return this._documents.has(url);
    },
    
    getDocument: function(url) {
      return this._documents.get(url) || null;
    }
  };
  
  console.log('chrome.offscreen polyfill: installed (mock implementation)');
}
