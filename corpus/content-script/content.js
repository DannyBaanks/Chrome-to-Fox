// Content script - runs in web page context
(function() {
  'use strict';

  // Add visual indicator
  const indicator = document.createElement('div');
  indicator.id = 'extension-indicator';
  indicator.style.cssText = 'position:fixed;top:10px;right:10px;z-index:99999;background:#4CAF50;color:white;padding:5px 10px;border-radius:5px;font-size:12px;';
  indicator.textContent = 'Extension Active';
  document.body.appendChild(indicator);

  // Listen for messages from background
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === 'highlight') {
      document.body.style.border = '3px solid #4CAF50';
      setTimeout(() => {
        document.body.style.border = '';
      }, 2000);
    }
  });

  // Report page info to background
  chrome.runtime.sendMessage({
    type: 'pageInfo',
    url: window.location.href,
    title: document.title
  });
})();
