// Background service worker
chrome.runtime.onInstalled.addListener(() => {
  console.log('Background Worker extension installed');
  
  // Set up alarm
  chrome.alarms.create('periodicCheck', { periodInMinutes: 5 });
  
  // Show welcome notification
  chrome.notifications.create('welcome', {
    type: 'basic',
    iconUrl: 'icon.png',
    title: 'Extension Installed',
    message: 'Background worker is now active!'
  });
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'periodicCheck') {
    performPeriodicCheck();
  }
});

function performPeriodicCheck() {
  chrome.storage.local.get('lastCheck', (result) => {
    const lastCheck = result.lastCheck || 0;
    const now = Date.now();
    
    if (now - lastCheck > 300000) { // 5 minutes
      chrome.storage.local.set({ lastCheck: now });
      console.log('Periodic check performed');
    }
  });
}

// Listen for messages
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'getAlarmStatus') {
    chrome.alarms.get('periodicCheck', (alarm) => {
      sendResponse({ active: !!alarm });
    });
    return true;
  }
});
