/**
 * Chrome-to-Fox Polyfill: chrome.hid
 * 
 * Chrome's hid API allows HID device access.
 * Firefox supports WebHID API which provides similar functionality.
 * 
 * This polyfill maps Chrome's hid API to WebHID API.
 */

if (typeof chrome !== 'undefined' && chrome.hid) {
  console.log('chrome.hid polyfill: native API available');
} else if (typeof chrome !== 'undefined') {
  // HID device handle mapping
  const _hidDevices = new Map();
  let _nextConnectionId = 1;
  
  chrome.hid = {
    /**
     * Get list of HID devices
     * Maps to navigator.hid.getDevices()
     */
    getDevices: async function(options) {
      if (!navigator.hid) {
        console.warn('chrome.hid.getDevices: WebHID not supported in this context');
        return [];
      }
      
      try {
        const devices = await navigator.hid.getDevices();
        
        // Filter by vendorId/productId if specified
        let filtered = devices;
        if (options && options.vendorId !== undefined) {
          filtered = filtered.filter(d => d.vendorId === options.vendorId);
        }
        if (options && options.productId !== undefined) {
          filtered = filtered.filter(d => d.productId === options.productId);
        }
        
        // Map WebHID devices to Chrome format
        return filtered.map(device => ({
          deviceId: _nextConnectionId++,
          vendorId: device.vendorId,
          productId: device.productId,
          productName: device.productName || '',
          serialNumber: device.serialNumber || '',
          manufacturerName: device.manufacturerName || '',
          collections: device.collections || []
        }));
      } catch (e) {
        console.error('chrome.hid.getDevices error:', e);
        return [];
      }
    },
    
    /**
     * Get devices ignoring permission check
     */
    getDevicesIgnoringPermissionCheck: async function(options) {
      // WebHID doesn't have this, just use regular getDevices
      return chrome.hid.getDevices(options);
    },
    
    /**
     * Connect to HID device
     * Maps to navigator.hid.requestDevice() + device.open()
     */
    connect: async function(vendorId, productId) {
      if (!navigator.hid) {
        console.warn('chrome.hid.connect: WebHID not supported');
        return null;
      }
      
      try {
        // Request device with filters
        const device = await navigator.hid.requestDevice({
          filters: [{
            vendorId: vendorId,
            productId: productId
          }]
        });
        
        if (!device) {
          return null;
        }
        
        // Open device
        await device.open();
        
        // Store device
        const connectionId = _nextConnectionId++;
        _hidDevices.set(connectionId, device);
        
        return connectionId;
      } catch (e) {
        console.error('chrome.hid.connect error:', e);
        return null;
      }
    },
    
    /**
     * Disconnect from HID device
     * Maps to device.close()
     */
    disconnect: async function(connectionId) {
      const device = _hidDevices.get(connectionId);
      if (!device) {
        console.warn('chrome.hid.disconnect: Invalid connectionId');
        return false;
      }
      
      try {
        await device.close();
        _hidDevices.delete(connectionId);
        return true;
      } catch (e) {
        console.error('chrome.hid.disconnect error:', e);
        _hidDevices.delete(connectionId);
        return true;
      }
    },
    
    /**
     * Send HID report
     * Maps to device.sendReport()
     */
    send: async function(connectionId, reportId, data) {
      const device = _hidDevices.get(connectionId);
      if (!device) {
        console.warn('chrome.hid.send: Invalid connectionId');
        return false;
      }
      
      try {
        // Convert data to Uint8Array
        let buffer;
        if (data instanceof ArrayBuffer) {
          buffer = new Uint8Array(data);
        } else if (Array.isArray(data)) {
          buffer = new Uint8Array(data);
        } else {
          buffer = new Uint8Array(data);
        }
        
        await device.sendReport(reportId, buffer);
        return true;
      } catch (e) {
        console.error('chrome.hid.send error:', e);
        return false;
      }
    },
    
    /**
     * Receive HID report
     * Maps to device.receiveReport()
     */
    receive: async function(connectionId) {
      const device = _hidDevices.get(connectionId);
      if (!device) {
        console.warn('chrome.hid.receive: Invalid connectionId');
        return { reportId: 0, data: new ArrayBuffer(0) };
      }
      
      try {
        const report = await device.receiveReport(0);
        return {
          reportId: report.reportId,
          data: report.data.buffer
        };
      } catch (e) {
        console.error('chrome.hid.receive error:', e);
        return { reportId: 0, data: new ArrayBuffer(0) };
      }
    },
    
    /**
     * Receive feature report
     * Maps to device.receiveFeatureReport()
     */
    receiveFeatureReport: async function(connectionId, reportId) {
      const device = _hidDevices.get(connectionId);
      if (!device) {
        console.warn('chrome.hid.receiveFeatureReport: Invalid connectionId');
        return new ArrayBuffer(0);
      }
      
      try {
        const report = await device.receiveFeatureReport(reportId);
        return report.data.buffer;
      } catch (e) {
        console.error('chrome.hid.receiveFeatureReport error:', e);
        return new ArrayBuffer(0);
      }
    },
    
    /**
     * Send feature report
     * Maps to device.sendFeatureReport()
     */
    sendFeatureReport: async function(connectionId, reportId, data) {
      const device = _hidDevices.get(connectionId);
      if (!device) {
        console.warn('chrome.hid.sendFeatureReport: Invalid connectionId');
        return false;
      }
      
      try {
        // Convert data to Uint8Array
        let buffer;
        if (data instanceof ArrayBuffer) {
          buffer = new Uint8Array(data);
        } else if (Array.isArray(data)) {
          buffer = new Uint8Array(data);
        } else {
          buffer = new Uint8Array(data);
        }
        
        await device.sendFeatureReport(reportId, buffer);
        return true;
      } catch (e) {
        console.error('chrome.hid.sendFeatureReport error:', e);
        return false;
      }
    },
    
    /**
     * Enable protection (not supported in WebHID)
     */
    enableProtection: async function(connectionId, reportIds) {
      console.warn('chrome.hid.enableProtection: Not supported in WebHID');
      return true;
    },
    
    /**
     * Event: onConnect
     */
    onConnect: {
      _listeners: new Map(),
      
      addListener: function(callback) {
        const id = Symbol('onConnect');
        this._listeners.set(id, callback);
        return id;
      },
      
      removeListener: function(id) {
        this._listeners.delete(id);
      },
      
      hasListener: function(callback) {
        for (const cb of this._listeners.values()) {
          if (cb === callback) return true;
        }
        return false;
      }
    },
    
    /**
     * Event: onDisconnect
     */
    onDisconnect: {
      _listeners: new Map(),
      
      addListener: function(callback) {
        const id = Symbol('onDisconnect');
        this._listeners.set(id, callback);
        return id;
      },
      
      removeListener: function(id) {
        this._listeners.delete(id);
      },
      
      hasListener: function(callback) {
        for (const cb of this._listeners.values()) {
          if (cb === callback) return true;
        }
        return false;
      }
    }
  };
  
  // Listen for WebHID connect/disconnect events
  if (navigator.hid) {
    navigator.hid.addEventListener('connect', (event) => {
      console.log('WebHID device connected:', event.device.productName);
      // Notify listeners
      for (const callback of chrome.hid.onConnect._listeners.values()) {
        try {
          callback({ device: event.device });
        } catch (e) {
          console.error('onConnect listener error:', e);
        }
      }
    });
    
    navigator.hid.addEventListener('disconnect', (event) => {
      console.log('WebHID device disconnected:', event.device.productName);
      // Remove from handles
      for (const [connectionId, device] of _hidDevices.entries()) {
        if (device === event.device) {
          _hidDevices.delete(connectionId);
          break;
        }
      }
      // Notify listeners
      for (const callback of chrome.hid.onDisconnect._listeners.values()) {
        try {
          callback({ device: event.device });
        } catch (e) {
          console.error('onDisconnect listener error:', e);
        }
      }
    });
  }
  
  console.log('chrome.hid polyfill: installed (WebHID bridge)');
}
