// html.to.design - Popup Script

document.addEventListener('DOMContentLoaded', async () => {
  const captureBtn = document.getElementById('captureBtn');
  const status = document.getElementById('status');
  const exportFigma = document.getElementById('exportFigma');
  const exportClipboard = document.getElementById('exportClipboard');
  const exportMake = document.getElementById('exportMake');
  
  let currentDesign = null;
  
  // Check current state
  const state = await chrome.runtime.sendMessage({ type: 'GET_CAPTURE_STATE' });
  updateUI(state.state);
  
  // Load last capture if exists
  const { lastDesign } = await chrome.storage.local.get('lastDesign');
  if (lastDesign) {
    currentDesign = lastDesign;
    enableExportButtons();
  }
  
  // Capture button click
  captureBtn.addEventListener('click', async () => {
    captureBtn.disabled = true;
    captureBtn.textContent = 'Capturing...';
    captureBtn.classList.add('capturing');
    showStatus('Starting capture...', 'info');
    
    try {
      const response = await chrome.runtime.sendMessage({ 
        type: 'START_CAPTURE',
        tabId: null // Will use active tab
      });
      
      if (response.error) {
        showStatus(`Error: ${response.error}`, 'error');
        resetCaptureButton();
        return;
      }
      
      showStatus('Capture in progress...', 'info');
      
      // Wait for capture to complete
      const result = await waitForCapture();
      
      if (result.success) {
        currentDesign = result.data;
        showStatus('Capture complete!', 'success');
        enableExportButtons();
      } else {
        showStatus(`Capture failed: ${result.error}`, 'error');
      }
      
    } catch (error) {
      showStatus(`Error: ${error.message}`, 'error');
    } finally {
      resetCaptureButton();
    }
  });
  
  // Export to Figma
  exportFigma.addEventListener('click', async () => {
    if (!currentDesign) return;
    
    try {
      await chrome.runtime.sendMessage({
        type: 'EXPORT_FIGMA',
        designData: currentDesign
      });
      showStatus('Exported to .h2d file', 'success');
    } catch (error) {
      showStatus(`Export error: ${error.message}`, 'error');
    }
  });
  
  // Copy to clipboard
  exportClipboard.addEventListener('click', async () => {
    if (!currentDesign) return;
    
    try {
      const response = await chrome.runtime.sendMessage({
        type: 'EXPORT_CLIPBOARD',
        designData: currentDesign
      });
      
      if (response.success) {
        // Copy HTML to clipboard
        await navigator.clipboard.writeText(response.data.html);
        showStatus('Copied to clipboard! Paste in Figma.', 'success');
      }
    } catch (error) {
      showStatus(`Clipboard error: ${error.message}`, 'error');
    }
  });
  
  // Export to Figma Make
  exportMake.addEventListener('click', async () => {
    if (!currentDesign) return;
    
    try {
      const makeFormat = {
        type: 'figma_make',
        version: '1.0',
        data: currentDesign
      };
      
      const blob = new Blob([JSON.stringify(makeFormat)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      
      await chrome.downloads.download({
        url,
        filename: `capture-${Date.now()}.make`,
        saveAs: true
      });
      
      showStatus('Exported to .make file', 'success');
    } catch (error) {
      showStatus(`Export error: ${error.message}`, 'error');
    }
  });
  
  function waitForCapture() {
    return new Promise((resolve) => {
      const listener = (request) => {
        if (request.type === 'CAPTURE_COMPLETE') {
          chrome.runtime.onMessage.removeListener(listener);
          resolve({ success: true, data: request.designData });
        }
      };
      
      chrome.runtime.onMessage.addListener(listener);
      
      // Timeout after 30 seconds
      setTimeout(() => {
        chrome.runtime.onMessage.removeListener(listener);
        resolve({ success: false, error: 'Capture timed out' });
      }, 30000);
    });
  }
  
  function updateUI(state) {
    switch (state) {
      case 'capturing':
        captureBtn.disabled = true;
        captureBtn.textContent = 'Capturing...';
        captureBtn.classList.add('capturing');
        break;
      case 'complete':
        captureBtn.disabled = false;
        captureBtn.textContent = 'Capture Again';
        captureBtn.classList.remove('capturing');
        enableExportButtons();
        break;
      default:
        resetCaptureButton();
    }
  }
  
  function resetCaptureButton() {
    captureBtn.disabled = false;
    captureBtn.textContent = 'Capture Page';
    captureBtn.classList.remove('capturing');
  }
  
  function showStatus(message, type) {
    status.textContent = message;
    status.className = `status visible ${type}`;
  }
  
  function enableExportButtons() {
    exportFigma.disabled = false;
    exportClipboard.disabled = false;
    exportMake.disabled = false;
  }
});
