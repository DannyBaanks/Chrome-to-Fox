// Test various permissions
chrome.runtime.onInstalled.addListener(async () => {
  console.log('Permissions extension installed');

  // Test storage
  await chrome.storage.local.set({ initialized: true });

  // Test tabs
  const tabs = await chrome.tabs.query({});
  console.log(`Found ${tabs.length} tabs`);

  // Test bookmarks
  const bookmarks = await chrome.bookmarks.getTree();
  console.log(`Bookmarks loaded: ${bookmarks.length}`);

  // Test history
  const history = await chrome.history.search({ text: '', maxResults: 10 });
  console.log(`History items: ${history.length}`);

  // Test cookies
  const cookies = await chrome.cookies.getAll({ domain: 'example.com' });
  console.log(`Cookies found: ${cookies.length}`);

  // Test alarms
  await chrome.alarms.create('test', { delayInMinutes: 1 });
  console.log('Alarm created');

  // Test notifications
  await chrome.notifications.create('test', {
    type: 'basic',
    iconUrl: 'icon.png',
    title: 'Test',
    message: 'All permissions working!'
  });
});
