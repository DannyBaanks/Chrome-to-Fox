/**
 * Chrome-to-Fox Polyfill: chrome.tabCapture
 * 
 * Chrome's tabCapture API allows capturing tab content (video/audio).
 * Firefox has limited support for tab capture via browser.tabCapture.
 * 
 * This polyfill provides:
 * 1. Uses Firefox's browser.tabCapture if available
 * 2. Falls back to getUserMedia for screen capture
 * 3. Provides stream-based API similar to Chrome
 */

if (typeof chrome !== 'undefined' && chrome.tabCapture) {
  console.log('chrome.tabCapture polyfill: native API available');
} else if (typeof chrome !== 'undefined') {
  // Captured streams tracking
  const _capturedStreams = new Map();
  let _nextStreamId = 1;
  
  chrome.tabCapture = {
    /**
     * Capture tab content
     * Maps to browser.tabCapture or getUserMedia fallback
     */
    capture: async function(options, callback) {
      console.log('chrome.tabCapture.capture: Attempting tab capture');
      
      // Try Firefox's browser.tabCapture first
      if (typeof browser !== 'undefined' && browser.tabCapture) {
        try {
          const streamId = await browser.tabCapture.capture(options);
          if (streamId) {
            console.log('chrome.tabCapture.capture: Using Firefox tabCapture');
            if (callback) callback(streamId);
            return streamId;
          }
        } catch (e) {
          console.warn('chrome.tabCapture.capture: Firefox tabCapture failed:', e);
        }
      }
      
      // Fallback: Use getUserMedia for screen capture
      console.log('chrome.tabCapture.capture: Using getUserMedia fallback');
      
      try {
        // Request screen capture
        const constraints = {
          video: {
            displaySurface: 'browser',
            logicalSurface: true,
            cursor: 'never'
          },
          audio: options?.audio !== false ? {
            echoCancellation: false,
            noiseSuppression: false,
            autoGainControl: false
          } : false
        };
        
        const stream = await navigator.mediaDevices.getDisplayMedia(constraints);
        
        // Store stream
        const streamId = _nextStreamId++;
        _capturedStreams.set(streamId, {
          stream,
          options,
          active: true
        });
        
        // Handle stream end
        stream.getVideoTracks()[0].addEventListener('ended', () => {
          console.log('chrome.tabCapture.capture: Stream ended');
          _capturedStreams.get(streamId).active = false;
          _capturedStreams.delete(streamId);
        });
        
        console.log('chrome.tabCapture.capture: Stream captured, ID:', streamId);
        
        if (callback) callback(streamId);
        return streamId;
      } catch (e) {
        console.error('chrome.tabCapture.capture: getUserMedia failed:', e);
        
        if (callback) callback(null);
        return null;
      }
    },
    
    /**
     * Get captured tabs
     */
    getCapturedTabs: async function() {
      const tabs = [];
      
      // Try Firefox's browser.tabCapture first
      if (typeof browser !== 'undefined' && browser.tabCapture) {
        try {
          const capturedTabs = await browser.tabCapture.getCapturedTabs();
          return capturedTabs;
        } catch (e) {
          console.warn('chrome.tabCapture.getCapturedTabs: Firefox tabCapture failed:', e);
        }
      }
      
      // Return our tracked streams
      for (const [streamId, data] of _capturedStreams) {
        if (data.active) {
          tabs.push({
            streamId,
            active: true,
            options: data.options
          });
        }
      }
      
      return tabs;
    },
    
    /**
     * Get stream by ID (extension method)
     */
    getStream: function(streamId) {
      const data = _capturedStreams.get(streamId);
      return data ? data.stream : null;
    },
    
    /**
     * Stop capture (extension method)
     */
    stopCapture: function(streamId) {
      const data = _capturedStreams.get(streamId);
      if (data) {
        data.stream.getTracks().forEach(track => track.stop());
        _capturedStreams.delete(streamId);
        return true;
      }
      return false;
    },
    
    /**
     * Event: onStatusChanged
     */
    onStatusChanged: {
      _listeners: new Map(),
      
      addListener: function(callback) {
        const id = Symbol('onStatusChanged');
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
      },
      
      _emit: function(status) {
        for (const callback of this._listeners.values()) {
          try {
            callback(status);
          } catch (e) {
            console.error('onStatusChanged listener error:', e);
          }
        }
      }
    }
  };
  
  console.log('chrome.tabCapture polyfill: installed (Firefox tabCapture + getUserMedia fallback)');
}
