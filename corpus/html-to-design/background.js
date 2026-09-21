// html.to.design - Background Service Worker
// Handles capture orchestration and Figma integration

const CAPTURE_STATES = {
  IDLE: 'idle',
  CAPTURING: 'capturing',
  PROCESSING: 'processing',
  COMPLETE: 'complete',
  ERROR: 'error'
};

let currentCapture = null;

// Listen for extension install
chrome.runtime.onInstalled.addListener(() => {
  console.log('html.to.design installed');
  chrome.storage.local.set({ captureState: CAPTURE_STATES.IDLE });
});

// Listen for messages from popup and content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  switch (request.type) {
    case 'START_CAPTURE':
      handleStartCapture(request, sender, sendResponse);
      return true;
    
    case 'STOP_CAPTURE':
      handleStopCapture(sendResponse);
      return true;
    
    case 'CAPTURE_COMPLETE':
      handleCaptureComplete(request, sender, sendResponse);
      return true;
    
    case 'GET_CAPTURE_STATE':
      sendResponse({ state: currentCapture?.state || CAPTURE_STATES.IDLE });
      return false;
    
    case 'EXPORT_FIGMA':
      handleExportFigma(request, sendResponse);
      return true;
    
    case 'EXPORT_CLIPBOARD':
      handleExportClipboard(request, sendResponse);
      return true;
  }
});

async function handleStartCapture(request, sender, sendResponse) {
  try {
    const { tabId } = request;
    
    // Get the active tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
      sendResponse({ error: 'No active tab' });
      return;
    }
    
    // Check if debugger is already attached
    const targets = await chrome.debugger.getTargets();
    const attached = targets.some(t => t.tabId === tab.id && t.attached);
    
    if (!attached) {
      // Attach debugger
      await chrome.debugger.attach({ tabId: tab.id }, '1.3');
      console.log('Debugger attached to tab', tab.id);
    }
    
    // Initialize capture
    currentCapture = {
      tabId: tab.id,
      state: CAPTURE_STATES.CAPTURING,
      startTime: Date.now(),
      elements: [],
      styles: {},
      layout: {}
    };
    
    await chrome.storage.local.set({ 
      captureState: CAPTURE_STATES.CAPTURING,
      captureTabId: tab.id 
    });
    
    // Enable necessary domains
    await chrome.debugger.sendCommand({ tabId: tab.id }, 'DOM.enable');
    await chrome.debugger.sendCommand({ tabId: tab.id }, 'CSS.enable');
    await chrome.debugger.sendCommand({ tabId: tab.id }, 'Runtime.enable');
    
    // Start capturing DOM and styles
    await capturePage(tab.id);
    
    sendResponse({ success: true, tabId: tab.id });
  } catch (error) {
    console.error('Capture error:', error);
    currentCapture = { ...currentCapture, state: CAPTURE_STATES.ERROR, error: error.message };
    await chrome.storage.local.set({ captureState: CAPTURE_STATES.ERROR });
    sendResponse({ error: error.message });
  }
}

async function capturePage(tabId) {
  try {
    // Get document root
    const { root } = await chrome.debugger.sendCommand({ tabId }, 'DOM.getDocument', { depth: -1 });
    
    // Capture full page layout
    const { model } = await chrome.debugger.sendCommand({ tabId }, 'Page.getLayoutMetrics');
    
    // Get all computed styles
    const styleSheetTexts = await chrome.debugger.sendCommand({ tabId }, 'CSS.getAllStyleSheetTexts');
    
    // Process elements
    const elements = await processNode(tabId, root, 0);
    
    currentCapture = {
      ...currentCapture,
      state: CAPTURE_STATES.PROCESSING,
      elements,
      layout: {
        width: model.cssContentSize.width,
        height: model.cssContentSize.height
      },
      styles: styleSheetTexts
    };
    
    // Process and complete
    await processCapture(tabId);
    
  } catch (error) {
    console.error('Page capture error:', error);
    throw error;
  }
}

async function processNode(tabId, node, depth) {
  const elements = [];
  
  if (node.nodeType === 1) { // Element node
    try {
      // Get computed styles
      const { computedStyle } = await chrome.debugger.sendCommand(
        { tabId }, 
        'CSS.getComputedStyleForNode', 
        { nodeId: node.nodeId }
      );
      
      // Get box model
      const { model } = await chrome.debugger.sendCommand(
        { tabId }, 
        'DOM.getBoxModel', 
        { nodeId: node.nodeId }
      ).catch(() => ({ model: null }));
      
      const element = {
        tagName: node.nodeName.toLowerCase(),
        attributes: node.attributes || [],
        styles: computedStyle,
        boxModel: model,
        depth,
        children: []
      };
      
      elements.push(element);
      
      // Process children
      if (node.children) {
        for (const child of node.children) {
          const childElements = await processNode(tabId, child, depth + 1);
          element.children.push(...childElements);
        }
      }
    } catch (e) {
      // Skip nodes that can't be processed
    }
  }
  
  return elements;
}

async function processCapture(tabId) {
  try {
    // Convert to design format
    const designData = {
      version: '2.0',
      timestamp: Date.now(),
      url: (await chrome.tabs.get(tabId)).url,
      layout: currentCapture.layout,
      elements: currentCapture.elements,
      styles: currentCapture.styles
    };
    
    // Store the capture
    await chrome.storage.local.set({
      lastCapture: designData,
      captureState: CAPTURE_STATES.COMPLETE
    });
    
    currentCapture = {
      ...currentCapture,
      state: CAPTURE_STATES.COMPLETE,
      designData
    };
    
    // Detach debugger
    await chrome.debugger.detach({ tabId });
    console.log('Capture complete, debugger detached');
    
  } catch (error) {
    console.error('Process error:', error);
    throw error;
  }
}

async function handleStopCapture(sendResponse) {
  if (currentCapture?.tabId) {
    try {
      await chrome.debugger.detach({ tabId: currentCapture.tabId });
    } catch (e) {
      // Debugger may already be detached
    }
  }
  
  currentCapture = null;
  await chrome.storage.local.set({ captureState: CAPTURE_STATES.IDLE });
  sendResponse({ success: true });
}

async function handleCaptureComplete(request, sender, sendResponse) {
  const { designData } = request;
  
  // Store for Figma export
  await chrome.storage.local.set({ 
    lastDesign: designData,
    captureState: CAPTURE_STATES.COMPLETE 
  });
  
  sendResponse({ success: true });
}

async function handleExportFigma(request, sendResponse) {
  try {
    const { designData } = request;
    
    // Format for Figma plugin
    const figmaFormat = {
      type: 'html_to_design',
      version: '2.0',
      data: designData
    };
    
    // Store as .h2d file data
    const blob = new Blob([JSON.stringify(figmaFormat)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    // Download
    await chrome.downloads.download({
      url,
      filename: `capture-${Date.now()}.h2d`,
      saveAs: true
    });
    
    sendResponse({ success: true });
  } catch (error) {
    sendResponse({ error: error.message });
  }
}

async function handleExportClipboard(request, sendResponse) {
  try {
    const { designData } = request;
    
    // Format for clipboard paste
    const clipboardData = {
      type: 'text/html',
      html: generateHTML(designData),
      json: designData
    };
    
    await chrome.storage.local.set({ clipboardData });
    sendResponse({ success: true, data: clipboardData });
  } catch (error) {
    sendResponse({ error: error.message });
  }
}

function generateHTML(designData) {
  // Generate clean HTML from design data
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Captured from ${designData.url}</title>
</head>
<body>
  <!-- Generated by html.to.design -->
  <!-- Original URL: ${designData.url} -->
  <!-- Capture time: ${new Date(designData.timestamp).toISOString()} -->
</body>
</html>`;
}
