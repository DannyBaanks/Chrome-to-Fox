document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('actionBtn');
  
  btn.addEventListener('click', () => {
    chrome.storage.local.set({ lastClick: Date.now() }, () => {
      console.log('Click timestamp saved');
    });
    
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      chrome.tabs.sendMessage(tabs[0].id, { type: 'highlight' });
    });
  });
});
