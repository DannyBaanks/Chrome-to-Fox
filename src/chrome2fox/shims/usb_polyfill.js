/**
 * Chrome-to-Fox Polyfill: chrome.usb
 * 
 * Chrome's usb API allows USB device access.
 * Firefox doesn't support this API.
 */

if (typeof chrome !== 'undefined' && chrome.usb) {
  console.log('chrome.usb polyfill: native API available');
} else if (typeof chrome !== 'undefined') {
  chrome.usb = {
    getDevices: async function(options) {
      console.warn('chrome.usb.getDevices polyfill: ' +
        'USB API not supported in Firefox');
      return [];
    },
    
    getConfigurations: async function(device) {
      console.warn('chrome.usb.getConfigurations polyfill: ' +
        'USB API not supported in Firefox');
      return [];
    },
    
    openDevice: async function(device) {
      console.warn('chrome.usb.openDevice polyfill: ' +
        'USB API not supported in Firefox');
      return null;
    },
    
    closeDevice: async function(handle) {
      console.warn('chrome.usb.closeDevice polyfill: ' +
        'USB API not supported in Firefox');
      return true;
    },
    
    claimInterface: async function(handle, interfaceNumber) {
      console.warn('chrome.usb.claimInterface polyfill: ' +
        'USB API not supported in Firefox');
      return true;
    },
    
    releaseInterface: async function(handle, interfaceNumber) {
      console.warn('chrome.usb.releaseInterface polyfill: ' +
        'USB API not supported in Firefox');
      return true;
    },
    
    controlTransfer: async function(handle, transferInfo) {
      console.warn('chrome.usb.controlTransfer polyfill: ' +
        'USB API not supported in Firefox');
      return { resultCode: -1 };
    },
    
    bulkTransfer: async function(handle, transferInfo) {
      console.warn('chrome.usb.bulkTransfer polyfill: ' +
        'USB API not supported in Firefox');
      return { resultCode: -1 };
    },
    
    interruptTransfer: async function(handle, transferInfo) {
      console.warn('chrome.usb.interruptTransfer polyfill: ' +
        'USB API not supported in Firefox');
      return { resultCode: -1 };
    },
    
    isochronousTransfer: async function(handle, transferInfo) {
      console.warn('chrome.usb.isochronousTransfer polyfill: ' +
        'USB API not supported in Firefox');
      return { resultCode: -1 };
    },
    
    resetDevice: async function(handle) {
      console.warn('chrome.usb.resetDevice polyfill: ' +
        'USB API not supported in Firefox');
      return true;
    }
  };
  
  console.log('chrome.usb polyfill: installed (no-op implementation)');
}
