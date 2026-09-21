/**
 * Chrome-to-Fox Polyfill: chrome.tts
 * 
 * Chrome's tts API allows text-to-speech.
 * Firefox supports Web Speech API which provides similar functionality.
 * 
 * This polyfill maps Chrome's tts API to Web Speech API.
 */

if (typeof chrome !== 'undefined' && chrome.tts) {
  console.log('chrome.tts polyfill: native API available');
} else if (typeof chrome !== 'undefined') {
  // State tracking
  let _speaking = false;
  let _paused = false;
  let _currentUtterance = null;
  let _eventListeners = new Map();
  let _nextEventId = 1;
  
  chrome.tts = {
    /**
     * Speak text
     * Maps to SpeechSynthesisUtterance
     */
    speak: function(text, options, callback) {
      if (!('speechSynthesis' in window)) {
        console.warn('chrome.tts.speak: Web Speech API not available');
        if (callback) callback();
        return;
      }
      
      // Stop any current speech
      window.speechSynthesis.cancel();
      
      // Create utterance
      const utterance = new SpeechSynthesisUtterance(text);
      
      // Apply options
      if (options) {
        if (options.rate !== undefined) utterance.rate = options.rate;
        if (options.pitch !== undefined) utterance.pitch = options.pitch;
        if (options.volume !== undefined) utterance.volume = options.volume;
        if (options.lang !== undefined) utterance.lang = options.lang;
        
        // Find voice by name
        if (options.voiceName) {
          const voices = window.speechSynthesis.getVoices();
          const voice = voices.find(v => v.name === options.voiceName);
          if (voice) utterance.voice = voice;
        }
      }
      
      // Event handlers
      utterance.onstart = () => {
        _speaking = true;
        _paused = false;
        _currentUtterance = utterance;
        _emitTtsEvent('start', { charIndex: 0 });
      };
      
      utterance.onend = () => {
        _speaking = false;
        _paused = false;
        _currentUtterance = null;
        _emitTtsEvent('end', { charIndex: text.length });
      };
      
      utterance.onerror = (event) => {
        _speaking = false;
        _paused = false;
        _currentUtterance = null;
        _emitTtsEvent('error', { errorMessage: event.error });
      };
      
      utterance.onboundary = (event) => {
        _emitTtsEvent('boundary', {
          charIndex: event.charIndex,
          charLength: event.charLength || 1
        });
      };
      
      utterance.onmark = (event) => {
        _emitTtsEvent('mark', {
          name: event.name
        });
      };
      
      // Speak
      window.speechSynthesis.speak(utterance);
      
      if (callback) callback();
    },
    
    /**
     * Stop speaking
     */
    stop: function() {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
      _speaking = false;
      _paused = false;
      _currentUtterance = null;
    },
    
    /**
     * Pause speaking
     */
    pause: function() {
      if ('speechSynthesis' in window && _speaking && !_paused) {
        window.speechSynthesis.pause();
        _paused = true;
        _emitTtsEvent('pause', { charIndex: 0 });
      }
    },
    
    /**
     * Resume speaking
     */
    resume: function() {
      if ('speechSynthesis' in window && _paused) {
        window.speechSynthesis.resume();
        _paused = false;
        _emitTtsEvent('resume', { charIndex: 0 });
      }
    },
    
    /**
     * Check if speaking
     */
    isSpeaking: function(callback) {
      callback(_speaking);
    },
    
    /**
     * Get available voices
     */
    getVoices: function(callback) {
      if (!('speechSynthesis' in window)) {
        callback([]);
        return;
      }
      
      const voices = window.speechSynthesis.getVoices();
      const mappedVoices = voices.map(v => ({
        voiceName: v.name,
        lang: v.lang,
        voiceId: v.name,
        remote: v.localService === false,
        extensionId: '',
        eventTypes: ['start', 'end', 'error', 'word', 'sentence', 'mark', 'boundary']
      }));
      
      callback(mappedVoices);
    },
    
    /**
     * Send TTS event (for testing)
     */
    sendTtsEvent: function(eventType, callback) {
      _emitTtsEvent(eventType, {});
      if (callback) callback();
    },
    
    /**
     * Event: onPause
     */
    onPause: {
      addListener: function(callback) {
        const id = _nextEventId++;
        _eventListeners.set(`pause_${id}`, callback);
      },
      removeListener: function(callback) {
        for (const [key, cb] of _eventListeners.entries()) {
          if (key.startsWith('pause_') && cb === callback) {
            _eventListeners.delete(key);
            break;
          }
        }
      },
      hasListener: function(callback) {
        for (const [key, cb] of _eventListeners.entries()) {
          if (key.startsWith('pause_') && cb === callback) return true;
        }
        return false;
      }
    },
    
    /**
     * Event: onResume
     */
    onResume: {
      addListener: function(callback) {
        const id = _nextEventId++;
        _eventListeners.set(`resume_${id}`, callback);
      },
      removeListener: function(callback) {
        for (const [key, cb] of _eventListeners.entries()) {
          if (key.startsWith('resume_') && cb === callback) {
            _eventListeners.delete(key);
            break;
          }
        }
      },
      hasListener: function(callback) {
        for (const [key, cb] of _eventListeners.entries()) {
          if (key.startsWith('resume_') && cb === callback) return true;
        }
        return false;
      }
    },
    
    /**
     * Event: onStart
     */
    onStart: {
      addListener: function(callback) {
        const id = _nextEventId++;
        _eventListeners.set(`start_${id}`, callback);
      },
      removeListener: function(callback) {
        for (const [key, cb] of _eventListeners.entries()) {
          if (key.startsWith('start_') && cb === callback) {
            _eventListeners.delete(key);
            break;
          }
        }
      },
      hasListener: function(callback) {
        for (const [key, cb] of _eventListeners.entries()) {
          if (key.startsWith('start_') && cb === callback) return true;
        }
        return false;
      }
    },
    
    /**
     * Event: onEnd
     */
    onEnd: {
      addListener: function(callback) {
        const id = _nextEventId++;
        _eventListeners.set(`end_${id}`, callback);
      },
      removeListener: function(callback) {
        for (const [key, cb] of _eventListeners.entries()) {
          if (key.startsWith('end_') && cb === callback) {
            _eventListeners.delete(key);
            break;
          }
        }
      },
      hasListener: function(callback) {
        for (const [key, cb] of _eventListeners.entries()) {
          if (key.startsWith('end_') && cb === callback) return true;
        }
        return false;
      }
    },
    
    /**
     * Event: onError
     */
    onError: {
      addListener: function(callback) {
        const id = _nextEventId++;
        _eventListeners.set(`error_${id}`, callback);
      },
      removeListener: function(callback) {
        for (const [key, cb] of _eventListeners.entries()) {
          if (key.startsWith('error_') && cb === callback) {
            _eventListeners.delete(key);
            break;
          }
        }
      },
      hasListener: function(callback) {
        for (const [key, cb] of _eventListeners.entries()) {
          if (key.startsWith('error_') && cb === callback) return true;
        }
        return false;
      }
    },
    
    /**
     * Event: onVoiceUpdate
     */
    onVoiceUpdate: {
      addListener: function(callback) {
        const id = _nextEventId++;
        _eventListeners.set(`voiceUpdate_${id}`, callback);
      },
      removeListener: function(callback) {
        for (const [key, cb] of _eventListeners.entries()) {
          if (key.startsWith('voiceUpdate_') && cb === callback) {
            _eventListeners.delete(key);
            break;
          }
        }
      },
      hasListener: function(callback) {
        for (const [key, cb] of _eventListeners.entries()) {
          if (key.startsWith('voiceUpdate_') && cb === callback) return true;
        }
        return false;
      }
    }
  };
  
  /**
   * Emit TTS event to listeners
   */
  function _emitTtsEvent(type, data) {
    const event = {
      type,
      charIndex: data.charIndex || 0,
      charLength: data.charLength || 0,
      errorMessage: data.errorMessage || '',
      name: data.name || ''
    };
    
    // Emit to specific event listeners
    for (const [key, callback] of _eventListeners.entries()) {
      if (key.startsWith(type + '_')) {
        try {
          callback(event);
        } catch (e) {
          console.error(`chrome.tts.${type} listener error:`, e);
        }
      }
    }
    
    // Emit to generic onEvent if exists
    if (_eventListeners.has('onEvent')) {
      try {
        _eventListeners.get('onEvent')(event);
      } catch (e) {
        console.error('chrome.tts.onEvent listener error:', e);
      }
    }
  }
  
  // Wait for voices to load
  if ('speechSynthesis' in window) {
    // Some browsers need this to populate voices
    window.speechSynthesis.onvoiceschanged = () => {
      const voices = window.speechSynthesis.getVoices();
      console.log(`chrome.tts polyfill: ${voices.length} voices loaded`);
      
      // Notify voice update listeners
      for (const [key, callback] of _eventListeners.entries()) {
        if (key.startsWith('voiceUpdate_')) {
          try {
            callback({ voices: voices.map(v => v.name) });
          } catch (e) {
            console.error('chrome.tts.onVoiceUpdate listener error:', e);
          }
        }
      }
    };
  }
  
  console.log('chrome.tts polyfill: installed (Web Speech API bridge)');
}
