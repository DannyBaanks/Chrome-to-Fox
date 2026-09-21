document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('actionBtn');
  
  btn.addEventListener('click', () => {
    browser.storage.local.set({ lastClick: Date.now() }, () => {
      console.log('Click timestamp saved');
    });
    
    browser.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      browser.tabs.sendMessage(tabs[0].id, { type: 'highlight' });
    });
  });
});
