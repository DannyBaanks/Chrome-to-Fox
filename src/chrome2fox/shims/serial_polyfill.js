/**
 * Chrome-to-Fox Polyfill: chrome.serial
 * 
 * Chrome's serial API allows serial port access.
 * Firefox supports Web Serial API which provides similar functionality.
 * 
 * This polyfill maps Chrome's serial API to Web Serial API.
 */

if (typeof chrome !== 'undefined' && chrome.serial) {
  console.log('chrome.serial polyfill: native API available');
} else if (typeof chrome !== 'undefined') {
  // Serial port handle mapping
  const _serialPorts = new Map();
  let _nextConnectionId = 1;
  
  chrome.serial = {
    /**
     * Get list of serial devices
     * Maps to navigator.serial.getPorts()
     */
    getDevices: async function() {
      if (!navigator.serial) {
        console.warn('chrome.serial.getDevices: Web Serial not supported in this context');
        return [];
      }
      
      try {
        const ports = await navigator.serial.getPorts();
        
        // Map Web Serial ports to Chrome format
        return ports.map((port, index) => ({
          path: port.getInfo().usbVendorId ? 
            `usb-${port.getInfo().usbVendorId}-${port.getInfo().usbProductId}` : 
            `serial-${index}`,
          vendorId: port.getInfo().usbVendorId || 0,
          productId: port.getInfo().usbProductId || 0
        }));
      } catch (e) {
        console.error('chrome.serial.getDevices error:', e);
        return [];
      }
    },
    
    /**
     * Connect to serial port
     * Maps to navigator.serial.requestPort() + port.open()
     */
    connect: async function(path, options, callback) {
      if (!navigator.serial) {
        console.warn('chrome.serial.connect: Web Serial not supported');
        if (callback) callback(null);
        return null;
      }
      
      try {
        // Request port if not already selected
        let port;
        const ports = await navigator.serial.getPorts();
        
        // Try to find existing port by path
        port = ports.find(p => {
          const info = p.getInfo();
          const portPath = info.usbVendorId ? 
            `usb-${info.usbVendorId}-${info.usbProductId}` : 
            `serial-${ports.indexOf(p)}`;
          return portPath === path;
        });
        
        // If not found, request new port
        if (!port) {
          port = await navigator.serial.requestPort();
        }
        
        // Open port with options
        const baudRate = options?.bitrate || options?.baudRate || 9600;
        await port.open({ baudRate });
        
        // Store connection
        const connectionId = _nextConnectionId++;
        _serialPorts.set(connectionId, {
          port,
          reader: null,
          writer: null
        });
        
        if (callback) callback({ connectionId });
        return connectionId;
      } catch (e) {
        console.error('chrome.serial.connect error:', e);
        if (callback) callback(null);
        return null;
      }
    },
    
    /**
     * Disconnect from serial port
     * Maps to port.close()
     */
    disconnect: async function(connectionId, callback) {
      const connection = _serialPorts.get(connectionId);
      if (!connection) {
        console.warn('chrome.serial.disconnect: Invalid connectionId');
        if (callback) callback(false);
        return false;
      }
      
      try {
        if (connection.reader) {
          await connection.reader.cancel();
        }
        if (connection.writer) {
          await connection.writer.releaseLock();
        }
        await connection.port.close();
        _serialPorts.delete(connectionId);
        
        if (callback) callback(true);
        return true;
      } catch (e) {
        console.error('chrome.serial.disconnect error:', e);
        _serialPorts.delete(connectionId);
        if (callback) callback(true);
        return true;
      }
    },
    
    /**
     * Set paused state
     */
    setPaused: async function(connectionId, paused, callback) {
      const connection = _serialPorts.get(connectionId);
      if (!connection) {
        if (callback) callback(false);
        return false;
      }
      
      // Web Serial doesn't have direct pause, but we can cancel reader
      if (paused && connection.reader) {
        await connection.reader.cancel();
        connection.reader = null;
      }
      
      if (callback) callback(true);
      return true;
    },
    
    /**
     * Get connection info
     */
    getInfo: async function() {
      const info = [];
      for (const [connectionId, connection] of _serialPorts) {
        const portInfo = connection.port.getInfo();
        info.push({
          connectionId,
          path: portInfo.usbVendorId ? 
            `usb-${portInfo.usbVendorId}-${portInfo.usbProductId}` : 
            `serial-${connectionId}`,
          vendorId: portInfo.usbVendorId || 0,
          productId: portInfo.usbProductId || 0
        });
      }
      return info;
    },
    
    /**
     * Update connection options
     * Maps to port.reconfigure()
     */
    update: async function(connectionId, options, callback) {
      const connection = _serialPorts.get(connectionId);
      if (!connection) {
        if (callback) callback(false);
        return false;
      }
      
      try {
        await connection.port.reconfigure({
          baudRate: options.bitrate || options.baudRate
        });
        if (callback) callback(true);
        return true;
      } catch (e) {
        console.error('chrome.serial.update error:', e);
        if (callback) callback(false);
        return false;
      }
    },
    
    /**
     * Get control signals (DTR, RTS, etc.)
     */
    getControlSignals: async function(connectionId) {
      const connection = _serialPorts.get(connectionId);
      if (!connection) {
        return {};
      }
      
      // Web Serial doesn't expose control signals directly
      // Return defaults
      return {
        dtr: true,
        rts: true,
        cts: false,
        dsr: false,
        dcd: false,
        ring: false
      };
    },
    
    /**
     * Set control signals
     */
    setControlSignals: async function(connectionId, signals) {
      const connection = _serialPorts.get(connectionId);
      if (!connection) {
        return false;
      }
      
      // Web Serial doesn't expose control signals directly
      console.warn('chrome.serial.setControlSignals: Not fully supported in Web Serial');
      return true;
    },
    
    /**
     * Send data
     * Maps to port.writable.getWriter().write()
     */
    send: async function(connectionId, data, callback) {
      const connection = _serialPorts.get(connectionId);
      if (!connection) {
        if (callback) callback({ bytesSent: 0 });
        return { bytesSent: 0 };
      }
      
      try {
        if (!connection.writer) {
          connection.writer = connection.port.writable.getWriter();
        }
        
        // Convert data to Uint8Array
        let buffer;
        if (data instanceof ArrayBuffer) {
          buffer = new Uint8Array(data);
        } else if (Array.isArray(data)) {
          buffer = new Uint8Array(data);
        } else if (typeof data === 'string') {
          buffer = new TextEncoder().encode(data);
        } else {
          buffer = new Uint8Array(data);
        }
        
        await connection.writer.write(buffer);
        
        if (callback) callback({ bytesSent: buffer.length });
        return { bytesSent: buffer.length };
      } catch (e) {
        console.error('chrome.serial.send error:', e);
        if (callback) callback({ bytesSent: 0 });
        return { bytesSent: 0 };
      }
    },
    
    /**
     * Flush serial port
     */
    flush: async function(connectionId, callback) {
      const connection = _serialPorts.get(connectionId);
      if (!connection) {
        if (callback) callback(false);
        return false;
      }
      
      // Web Serial doesn't have explicit flush
      // But we can release and re-acquire writer
      if (connection.writer) {
        await connection.writer.releaseLock();
        connection.writer = null;
      }
      
      if (callback) callback(true);
      return true;
    },
    
    /**
     * Get native baud rate
     */
    getNativeRate: async function(connectionId) {
      const connection = _serialPorts.get(connectionId);
      if (!connection) {
        return 9600;
      }
      
      // Web Serial doesn't expose current baud rate directly
      return 9600;
    },
    
    /**
     * Set break condition
     */
    setBreak: async function(connectionId, callback) {
      const connection = _serialPorts.get(connectionId);
      if (!connection) {
        if (callback) callback(false);
        return false;
      }
      
      // Web Serial doesn't expose break control directly
      console.warn('chrome.serial.setBreak: Not supported in Web Serial');
      if (callback) callback(true);
      return true;
    },
    
    /**
     * Clear break condition
     */
    clearBreak: async function(connectionId, callback) {
      const connection = _serialPorts.get(connectionId);
      if (!connection) {
        if (callback) callback(false);
        return false;
      }
      
      // Web Serial doesn't expose break control directly
      console.warn('chrome.serial.clearBreak: Not supported in Web Serial');
      if (callback) callback(true);
      return true;
    },
    
    /**
     * Event: onReceive
     */
    onReceive: {
      _listeners: new Map(),
      
      addListener: function(callback) {
        const id = Symbol('onReceive');
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
     * Event: onReceiveError
     */
    onReceiveError: {
      _listeners: new Map(),
      
      addListener: function(callback) {
        const id = Symbol('onReceiveError');
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
  
  // Start reading from port and emit events
  async function _startReading(connectionId) {
    const connection = _serialPorts.get(connectionId);
    if (!connection || !connection.port.readable) {
      return;
    }
    
    try {
      connection.reader = connection.port.readable.getReader();
      
      while (true) {
        const { value, done } = await connection.reader.read();
        if (done) break;
        
        // Emit onReceive event
        for (const callback of chrome.serial.onReceive._listeners.values()) {
          try {
            callback({
              connectionId,
              data: value.buffer
            });
          } catch (e) {
            console.error('onReceive listener error:', e);
          }
        }
      }
    } catch (e) {
      if (e.name !== 'NetworkError') {
        console.error('Serial read error:', e);
        
        // Emit onReceiveError event
        for (const callback of chrome.serial.onReceiveError._listeners.values()) {
          try {
            callback({
              connectionId,
              error: e.message
            });
          } catch (e2) {
            console.error('onReceiveError listener error:', e2);
          }
        }
      }
    }
  }
  
  console.log('chrome.serial polyfill: installed (Web Serial bridge)');
}
