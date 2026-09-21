/**
 * Chrome-to-Fox Polyfill: chrome.tts
 * 
 * Chrome's tts API allows text-to-speech.
 * Firefox doesn't support this API, but Web Speech API is available.
 */

if (typeof chrome !== 'undefined' && chrome.tts) {
  console.log('chrome.tts polyfill: native API available');
} else if (typeof chrome !== 'undefined') {
  chrome.tts = {
    _voices: [],
    _speaking: false,
    
    speak: function(text, options, callback) {
      console.warn('chrome.tts.speak polyfill: ' +
        'Using Web Speech API instead of chrome.tts');
      
      if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(text);
        if (options) {
          utterance.rate = options.rate || 1;
          utterance.pitch = options.pitch || 1;
          utterance.volume = options.volume || 1;
        }
        
        utterance.onstart = () => { this._speaking = true; };
        utterance.onend = () => { this._speaking = false; };
        
        window.speechSynthesis.speak(utterance);
      } else {
        console.warn('chrome.tts.speak polyfill: Web Speech API not available');
      }
      
      if (callback) callback();
    },
    
    stop: function() {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
      this._speaking = false;
    },
    
    pause: function() {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.pause();
      }
    },
    
    resume: function() {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.resume();
      }
    },
    
    isSpeaking: function(callback) {
      callback(this._speaking);
    },
    
    getVoices: function(callback) {
      if ('speechSynthesis' in window) {
        const voices = window.speechSynthesis.getVoices();
        callback(voices.map(v => ({
          voiceName: v.name,
          lang: v.lang,
          remote: false
        })));
      } else {
        callback([]);
      }
    },
    
    sendTtsEvent: function(eventType, callback) {
      console.warn('chrome.tts.sendTtsEvent polyfill: ' +
        'TTS events not supported in Firefox');
      if (callback) callback();
    }
  };
  
  console.log('chrome.tts polyfill: installed (Web Speech API fallback)');
}
