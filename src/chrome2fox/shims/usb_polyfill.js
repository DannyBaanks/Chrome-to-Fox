/**
 * Chrome-to-Fox Polyfill: chrome.usb
 * 
 * Chrome's usb API allows USB device access.
 * Firefox supports WebUSB API which provides similar functionality.
 * 
 * This polyfill maps Chrome's usb API to WebUSB API.
 */

if (typeof chrome !== 'undefined' && chrome.usb) {
  console.log('chrome.usb polyfill: native API available');
} else if (typeof chrome !== 'undefined') {
  // WebUSB device handle mapping
  const _usbDeviceHandles = new Map();
  let _nextHandle = 1;
  
  chrome.usb = {
    /**
     * Get list of USB devices
     * Maps to navigator.usb.getDevices()
     */
    getDevices: async function(options) {
      if (!navigator.usb) {
        console.warn('chrome.usb.getDevices: WebUSB not supported in this context');
        return [];
      }
      
      try {
        const devices = await navigator.usb.getDevices();
        
        // Filter by vendorId/productId if specified
        let filtered = devices;
        if (options && options.vendorId !== undefined) {
          filtered = filtered.filter(d => d.vendorId === options.vendorId);
        }
        if (options && options.productId !== undefined) {
          filtered = filtered.filter(d => d.productId === options.productId);
        }
        
        // Map WebUSB devices to Chrome format
        return filtered.map(device => ({
          handle: _nextHandle++,
          vendorId: device.vendorId,
          productId: device.productId,
          version: device.version,
          manufacturerName: device.manufacturerName || '',
          productName: device.productName || '',
          serialNumber: device.serialNumber || '',
          configurations: device.configurations.map(config => ({
            configurationValue: config.configurationValue,
            configurationName: config.configurationName || '',
            interfaces: config.interfaces.map(iface => ({
              interfaceNumber: iface.interfaceNumber,
              alternateSetting: iface.alternateSetting,
              interfaceClass: iface.interfaceClass,
              interfaceSubclass: iface.interfaceSubclass,
              interfaceProtocol: iface.interfaceProtocol,
              interfaceName: iface.interfaceName || ''
            }))
          }))
        }));
      } catch (e) {
        console.error('chrome.usb.getDevices error:', e);
        return [];
      }
    },
    
    /**
     * Get USB device configurations
     */
    getConfigurations: async function(device) {
      // device is the device object from getDevices
      if (!device || !device.configurations) {
        return [];
      }
      return device.configurations;
    },
    
    /**
     * Open USB device
     * Maps to USBDevice.open()
     */
    openDevice: async function(device) {
      if (!navigator.usb) {
        console.warn('chrome.usb.openDevice: WebUSB not supported');
        return null;
      }
      
      try {
        const devices = await navigator.usb.getDevices();
        const usbDevice = devices.find(d => 
          d.vendorId === device.vendorId && 
          d.productId === device.productId
        );
        
        if (!usbDevice) {
          console.error('chrome.usb.openDevice: Device not found');
          return null;
        }
        
        await usbDevice.open();
        
        // Store handle mapping
        const handle = _nextHandle++;
        _usbDeviceHandles.set(handle, usbDevice);
        
        return handle;
      } catch (e) {
        console.error('chrome.usb.openDevice error:', e);
        return null;
      }
    },
    
    /**
     * Close USB device
     * Maps to USBDevice.close()
     */
    closeDevice: async function(handle) {
      const device = _usbDeviceHandles.get(handle);
      if (!device) {
        console.warn('chrome.usb.closeDevice: Invalid handle');
        return true;
      }
      
      try {
        await device.close();
        _usbDeviceHandles.delete(handle);
        return true;
      } catch (e) {
        console.error('chrome.usb.closeDevice error:', e);
        _usbDeviceHandles.delete(handle);
        return true;
      }
    },
    
    /**
     * Claim USB interface
     * Maps to USBDevice.selectConfiguration() + USBDevice.claimInterface()
     */
    claimInterface: async function(handle, interfaceNumber) {
      const device = _usbDeviceHandles.get(handle);
      if (!device) {
        console.warn('chrome.usb.claimInterface: Invalid handle');
        return false;
      }
      
      try {
        // Select configuration first (use first configuration)
        if (device.configuration === null) {
          await device.selectConfiguration(1);
        }
        
        await device.claimInterface(interfaceNumber);
        return true;
      } catch (e) {
        console.error('chrome.usb.claimInterface error:', e);
        return false;
      }
    },
    
    /**
     * Release USB interface
     * Maps to USBDevice.releaseInterface()
     */
    releaseInterface: async function(handle, interfaceNumber) {
      const device = _usbDeviceHandles.get(handle);
      if (!device) {
        console.warn('chrome.usb.releaseInterface: Invalid handle');
        return false;
      }
      
      try {
        await device.releaseInterface(interfaceNumber);
        return true;
      } catch (e) {
        console.error('chrome.usb.releaseInterface error:', e);
        return false;
      }
    },
    
    /**
     * Control transfer
     * Maps to USBDevice.controlTransferIn()
     */
    controlTransfer: async function(handle, transferInfo) {
      const device = _usbDeviceHandles.get(handle);
      if (!device) {
        console.warn('chrome.usb.controlTransfer: Invalid handle');
        return { resultCode: -1 };
      }
      
      try {
        const setup = {
          requestType: transferInfo.requestType || 'standard',
          recipient: transferInfo.recipient || 'device',
          request: transferInfo.request,
          value: transferInfo.value || 0,
          index: transferInfo.index || 0
        };
        
        const length = transferInfo.length || 0;
        const result = await device.controlTransferIn(setup, length);
        
        if (result.status === 'ok') {
          return {
            resultCode: 0,
            data: result.data ? new Uint8Array(result.data.buffer) : null
          };
        } else {
          return { resultCode: -1 };
        }
      } catch (e) {
        console.error('chrome.usb.controlTransfer error:', e);
        return { resultCode: -1 };
      }
    },
    
    /**
     * Bulk transfer
     * Maps to USBDevice.transferIn()
     */
    bulkTransfer: async function(handle, transferInfo) {
      const device = _usbDeviceHandles.get(handle);
      if (!device) {
        console.warn('chrome.usb.bulkTransfer: Invalid handle');
        return { resultCode: -1 };
      }
      
      try {
        const endpoint = transferInfo.endpoint || 1;
        const length = transferInfo.length || 64;
        
        const result = await device.transferIn(endpoint, length);
        
        if (result.status === 'ok') {
          return {
            resultCode: 0,
            data: result.data ? new Uint8Array(result.data.buffer) : null
          };
        } else {
          return { resultCode: -1 };
        }
      } catch (e) {
        console.error('chrome.usb.bulkTransfer error:', e);
        return { resultCode: -1 };
      }
    },
    
    /**
     * Interrupt transfer
     * Maps to USBDevice.transferIn()
     */
    interruptTransfer: async function(handle, transferInfo) {
      const device = _usbDeviceHandles.get(handle);
      if (!device) {
        console.warn('chrome.usb.interruptTransfer: Invalid handle');
        return { resultCode: -1 };
      }
      
      try {
        const endpoint = transferInfo.endpoint || 1;
        const length = transferInfo.length || 64;
        
        const result = await device.transferIn(endpoint, length);
        
        if (result.status === 'ok') {
          return {
            resultCode: 0,
            data: result.data ? new Uint8Array(result.data.buffer) : null
          };
        } else {
          return { resultCode: -1 };
        }
      } catch (e) {
        console.error('chrome.usb.interruptTransfer error:', e);
        return { resultCode: -1 };
      }
    },
    
    /**
     * Isochronous transfer
     * Maps to USBDevice.isochronousTransferIn()
     */
    isochronousTransfer: async function(handle, transferInfo) {
      const device = _usbDeviceHandles.get(handle);
      if (!device) {
        console.warn('chrome.usb.isochronousTransfer: Invalid handle');
        return { resultCode: -1 };
      }
      
      try {
        const endpoint = transferInfo.endpoint || 1;
        const packetLengths = transferInfo.packetLengths || [64];
        
        const result = await device.isochronousTransferIn(endpoint, packetLengths);
        
        if (result.status === 'ok') {
          return {
            resultCode: 0,
            packets: result.packets.map(p => ({
              data: p.data ? new Uint8Array(p.data.buffer) : null,
              status: p.status
            }))
          };
        } else {
          return { resultCode: -1 };
        }
      } catch (e) {
        console.error('chrome.usb.isochronousTransfer error:', e);
        return { resultCode: -1 };
      }
    },
    
    /**
     * Reset USB device
     * Maps to USBDevice.reset()
     */
    resetDevice: async function(handle) {
      const device = _usbDeviceHandles.get(handle);
      if (!device) {
        console.warn('chrome.usb.resetDevice: Invalid handle');
        return false;
      }
      
      try {
        await device.reset();
        return true;
      } catch (e) {
        console.error('chrome.usb.resetDevice error:', e);
        return false;
      }
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
  
  // Listen for WebUSB connect/disconnect events
  if (navigator.usb) {
    navigator.usb.addEventListener('connect', (event) => {
      console.log('WebUSB device connected:', event.device.productName);
      // Notify listeners
      for (const callback of chrome.usb.onConnect._listeners.values()) {
        try {
          callback({ device: event.device });
        } catch (e) {
          console.error('onConnect listener error:', e);
        }
      }
    });
    
    navigator.usb.addEventListener('disconnect', (event) => {
      console.log('WebUSB device disconnected:', event.device.productName);
      // Remove from handles
      for (const [handle, device] of _usbDeviceHandles.entries()) {
        if (device === event.device) {
          _usbDeviceHandles.delete(handle);
          break;
        }
      }
      // Notify listeners
      for (const callback of chrome.usb.onDisconnect._listeners.values()) {
        try {
          callback({ device: event.device });
        } catch (e) {
          console.error('onDisconnect listener error:', e);
        }
      }
    });
  }
  
  console.log('chrome.usb polyfill: installed (WebUSB bridge)');
}
