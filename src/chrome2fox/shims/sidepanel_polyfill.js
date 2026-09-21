/**
 * Chrome-to-Fox Polyfill: chrome.sidePanel
 * 
 * Chrome's sidePanel API allows creating side panels.
 * Firefox supports sidebarAction instead.
 */

if (typeof chrome !== 'undefined' && chrome.sidePanel) {
  console.log('chrome.sidePanel polyfill: native API available');
} else if (typeof chrome !== 'undefined') {
  chrome.sidePanel = {
    _panels: new Map(),
    
    setOptions: async function(options) {
      console.warn('chrome.sidePanel.setOptions polyfill: ' +
        'Side panel not supported. Use browser.sidebarAction instead.');
      
      if (options.path) {
        this._panels.set('default', {
          path: options.path,
          enabled: options.enabled !== false
        });
      }
      return true;
    },
    
    getOptions: async function(options) {
      return this._panels.get('default') || { enabled: false };
    },
    
    open: async function(options) {
      console.warn('chrome.sidePanel.open polyfill: ' +
        'Side panel opening not supported in Firefox');
      return true;
    },
    
    close: async function(options) {
      console.warn('chrome.sidePanel.close polyfill: ' +
        'Side panel closing not supported in Firefox');
      return true;
    },
    
    getPanelBehavior: async function() {
      return { openPanelOnActionClick: false };
    },
    
    setPanelBehavior: async function(behavior) {
      console.warn('chrome.sidePanel.setPanelBehavior polyfill: ' +
        'Side panel behavior not configurable in Firefox');
      return true;
    }
  };
  
  console.log('chrome.sidePanel polyfill: installed (mock implementation)');
}
