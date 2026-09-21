// html.to.design - Side Panel Script

document.getElementById('openPopup').addEventListener('click', () => {
  chrome.action.openPopup();
});

// Listen for capture updates
chrome.runtime.onMessage.addListener((request) => {
  if (request.type === 'CAPTURE_UPDATE') {
    updatePreview(request.data);
  }
});

function updatePreview(data) {
  const preview = document.querySelector('.preview');
  if (data) {
    preview.innerHTML = `
      <p><strong>URL:</strong> ${data.url || 'Unknown'}</p>
      <p><strong>Elements:</strong> ${data.elements?.length || 0}</p>
      <p><strong>Size:</strong> ${data.layout?.width || 0} x ${data.layout?.height || 0}</p>
    `;
  }
}
