/**
 * Chrome-to-Fox Polyfill: chrome.hid
 * 
 * Chrome's hid API allows HID device access.
 * Firefox doesn't support this API.
 */

if (typeof chrome !== 'undefined' && chrome.hid) {
  console.log('chrome.hid polyfill: native API available');
} else if (typeof chrome !== 'undefined') {
  chrome.hid = {
    getDevices: async function(options) {
      console.warn('chrome.hid.getDevices polyfill: ' +
        'HID API not supported in Firefox');
      return [];
    },
    
    getDevicesIgnoringPermissionCheck: async function(options) {
      console.warn('chrome.hid.getDevicesIgnoringPermissionCheck polyfill: ' +
        'HID API not supported in Firefox');
      return [];
    },
    
    connect: async function(vendorId, productId) {
      console.warn('chrome.hid.connect polyfill: ' +
        'HID API not supported in Firefox');
      return null;
    },
    
    disconnect: async function(connectionId) {
      console.warn('chrome.hid.disconnect polyfill: ' +
        'HID API not supported in Firefox');
      return true;
    },
    
    send: async function(connectionId, reportId, data) {
      console.warn('chrome.hid.send polyfill: ' +
        'HID API not supported in Firefox');
      return true;
    },
    
    receive: async function(connectionId) {
      console.warn('chrome.hid.receive polyfill: ' +
        'HID API not supported in Firefox');
      return { reportId: 0, data: new ArrayBuffer(0) };
    },
    
    receiveFeatureReport: async function(connectionId, reportId) {
      console.warn('chrome.hid.receiveFeatureReport polyfill: ' +
        'HID API not supported in Firefox');
      return new ArrayBuffer(0);
    },
    
    sendFeatureReport: async function(connectionId, reportId, data) {
      console.warn('chrome.hid.sendFeatureReport polyfill: ' +
        'HID API not supported in Firefox');
      return true;
    },
    
    enableProtection: async function(connectionId, reportIds) {
      console.warn('chrome.hid.enableProtection polyfill: ' +
        'HID API not supported in Firefox');
      return true;
    }
  };
  
  console.log('chrome.hid polyfill: installed (no-op implementation)');
}
