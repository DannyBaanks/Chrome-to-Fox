/**
 * Chrome-to-Fox Polyfill: chrome.serial
 * 
 * Chrome's serial API allows serial port access.
 * Firefox doesn't support this API.
 */

if (typeof chrome !== 'undefined' && chrome.serial) {
  console.log('chrome.serial polyfill: native API available');
} else if (typeof chrome !== 'undefined') {
  chrome.serial = {
    getDevices: async function() {
      console.warn('chrome.serial.getDevices polyfill: ' +
        'Serial API not supported in Firefox');
      return [];
    },
    
    connect: async function(path, options, callback) {
      console.warn('chrome.serial.connect polyfill: ' +
        'Serial API not supported in Firefox');
      if (callback) callback(null);
      return null;
    },
    
    disconnect: async function(connectionId, callback) {
      console.warn('chrome.serial.disconnect polyfill: ' +
        'Serial API not supported in Firefox');
      if (callback) callback(true);
      return true;
    },
    
    setPaused: async function(connectionId, paused, callback) {
      console.warn('chrome.serial.setPaused polyfill: ' +
        'Serial API not supported in Firefox');
      if (callback) callback(true);
      return true;
    },
    
    getInfo: async function() {
      console.warn('chrome.serial.getInfo polyfill: ' +
        'Serial API not supported in Firefox');
      return [];
    },
    
    update: async function(connectionId, options, callback) {
      console.warn('chrome.serial.update polyfill: ' +
        'Serial API not supported in Firefox');
      if (callback) callback(true);
      return true;
    },
    
    getControlSignals: async function(connectionId) {
      console.warn('chrome.serial.getControlSignals polyfill: ' +
        'Serial API not supported in Firefox');
      return {};
    },
    
    setControlSignals: async function(connectionId, signals) {
      console.warn('chrome.serial.setControlSignals polyfill: ' +
        'Serial API not supported in Firefox');
      return true;
    },
    
    send: async function(connectionId, data, callback) {
      console.warn('chrome.serial.send polyfill: ' +
        'Serial API not supported in Firefox');
      if (callback) callback({ bytesSent: 0 });
      return { bytesSent: 0 };
    },
    
    flush: async function(connectionId, callback) {
      console.warn('chrome.serial.flush polyfill: ' +
        'Serial API not supported in Firefox');
      if (callback) callback(true);
      return true;
    },
    
    getNativeRate: async function(connectionId) {
      console.warn('chrome.serial.getNativeRate polyfill: ' +
        'Serial API not supported in Firefox');
      return 9600;
    },
    
    setBreak: async function(connectionId, callback) {
      console.warn('chrome.serial.setBreak polyfill: ' +
        'Serial API not supported in Firefox');
      if (callback) callback(true);
      return true;
    },
    
    clearBreak: async function(connectionId, callback) {
      console.warn('chrome.serial.clearBreak polyfill: ' +
        'Serial API not supported in Firefox');
      if (callback) callback(true);
      return true;
    }
  };
  
  console.log('chrome.serial polyfill: installed (no-op implementation)');
}
