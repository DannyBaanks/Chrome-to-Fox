// html.to.design - Content Script
// Injected into web pages to capture DOM structure and styles

(function() {
  'use strict';
  
  let isCapturing = false;
  let captureObserver = null;
  
  // Listen for messages from background
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === 'CAPTURE_DOM') {
      startCapture(sendResponse);
      return true;
    }
    
    if (request.type === 'STOP_CAPTURE') {
      stopCapture();
      sendResponse({ success: true });
      return false;
    }
  });
  
  function startCapture(sendResponse) {
    if (isCapturing) {
      sendResponse({ error: 'Already capturing' });
      return;
    }
    
    isCapturing = true;
    console.log('[html.to.design] Starting DOM capture');
    
    try {
      // Capture current DOM state
      const domData = captureDOM();
      
      // Capture computed styles
      const styleData = captureStyles();
      
      // Capture layout information
      const layoutData = captureLayout();
      
      const captureResult = {
        url: window.location.href,
        title: document.title,
        timestamp: Date.now(),
        dom: domData,
        styles: styleData,
        layout: layoutData
      };
      
      // Send to background for processing
      chrome.runtime.sendMessage({
        type: 'CAPTURE_COMPLETE',
        designData: captureResult
      });
      
      sendResponse({ success: true, data: captureResult });
      
    } catch (error) {
      console.error('[html.to.design] Capture error:', error);
      sendResponse({ error: error.message });
    } finally {
      isCapturing = false;
    }
  }
  
  function captureDOM() {
    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_ELEMENT,
      null,
      false
    );
    
    const elements = [];
    let node;
    
    while (node = walker.nextNode()) {
      const rect = node.getBoundingClientRect();
      const styles = window.getComputedStyle(node);
      
      elements.push({
        tagName: node.tagName.toLowerCase(),
        id: node.id || null,
        className: node.className || null,
        attributes: Array.from(node.attributes).map(attr => ({
          name: attr.name,
          value: attr.value
        })),
        boundingRect: {
          x: rect.x,
          y: rect.y,
          width: rect.width,
          height: rect.height
        },
        computedStyles: {
          display: styles.display,
          position: styles.position,
          width: styles.width,
          height: styles.height,
          backgroundColor: styles.backgroundColor,
          color: styles.color,
          fontSize: styles.fontSize,
          fontFamily: styles.fontFamily,
          padding: styles.padding,
          margin: styles.margin,
          border: styles.border,
          borderRadius: styles.borderRadius,
          boxShadow: styles.boxShadow
        },
        textContent: node.childNodes.length === 1 && 
                     node.childNodes[0].nodeType === 3 ? 
                     node.childNodes[0].textContent.trim() : null
      });
    }
    
    return elements;
  }
  
  function captureStyles() {
    const sheets = Array.from(document.styleSheets);
    const rules = [];
    
    sheets.forEach(sheet => {
      try {
        const sheetRules = Array.from(sheet.cssRules || []);
        sheetRules.forEach(rule => {
          if (rule.type === CSSRule.STYLE_RULE) {
            rules.push({
              selector: rule.selectorText,
              styles: Array.from(rule.style).map(prop => ({
                property: prop,
                value: rule.style.getPropertyValue(prop)
              }))
            });
          }
        });
      } catch (e) {
        // Cross-origin stylesheets can't be accessed
      }
    });
    
    return rules;
  }
  
  function captureLayout() {
    const body = document.body;
    const html = document.documentElement;
    
    return {
      scrollWidth: Math.max(body.scrollWidth, html.scrollWidth),
      scrollHeight: Math.max(body.scrollHeight, html.scrollHeight),
      clientWidth: html.clientWidth,
      clientHeight: html.clientHeight,
      devicePixelRatio: window.devicePixelRatio,
      viewportWidth: window.innerWidth,
      viewportHeight: window.innerHeight
    };
  }
  
  function stopCapture() {
    isCapturing = false;
    if (captureObserver) {
      captureObserver.disconnect();
      captureObserver = null;
    }
    console.log('[html.to.design] Capture stopped');
  }
  
  // Expose API for popup
  window.htmlToDesign = {
    startCapture,
    stopCapture,
    isCapturing: () => isCapturing
  };
  
})();
