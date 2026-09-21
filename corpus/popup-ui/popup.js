document.addEventListener('DOMContentLoaded', () => {
  // Load saved settings
  chrome.storage.local.get(['apiKey', 'interval', 'lastCheck', 'count'], (result) => {
    document.getElementById('apiKey').value = result.apiKey || '';
    document.getElementById('interval').value = result.interval || 5;
    document.getElementById('lastCheck').textContent = result.lastCheck 
      ? new Date(result.lastCheck).toLocaleString() 
      : 'Never';
    document.getElementById('count').textContent = result.count || 0;
  });

  // Save settings
  document.getElementById('saveBtn').addEventListener('click', () => {
    const apiKey = document.getElementById('apiKey').value;
    const interval = parseInt(document.getElementById('interval').value) || 5;

    chrome.storage.local.set({ apiKey, interval }, () => {
      chrome.notifications.create('saved', {
        type: 'basic',
        iconUrl: 'icons/icon128.png',
        title: 'Settings Saved',
        message: `Check interval set to ${interval} minutes`
      });
    });
  });
});
