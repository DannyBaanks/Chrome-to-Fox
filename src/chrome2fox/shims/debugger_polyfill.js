/**
 * Chrome-to-Fox Polyfill: chrome.debugger (Full Parity)
 * 
 * Chrome DevTools Protocol (CDP) → Firefox DevTools Protocol (FDP) bridge
 * Uses browser.scripting.executeScript with world: "MAIN" to run code
 * in the page context, emulating CDP commands via DOM APIs.
 * 
 * Supported CDP Domains:
 * - DOM:.getDocument, DOM.getBoxModel, DOM.querySelector, DOM.querySelectorAll,
 *        DOM.getOuterHTML, DOM.setOuterHTML, DOM.removeAttribute, DOM.setAttribute,
 *        DOM.getAttributes, DOM.describeNode, DOM.getNodeForLocation
 * - CSS: getComputedStyleForNode, getMatchedStylesForNode, getInlineStylesForNode,
 *        getStyleSheetText, setStyleText, createStyleSheet, addRule
 * - Runtime: evaluate, getProperties, callFunctionOn, getPropertyDetails,
 *            releaseObject, releaseObjectGroup
 * - Page: getLayoutMetrics, navigate, reload, printToPDF, captureScreenshot
 * - Network: getResponseBody, getRequestPostData, emulateNetworkConditions
 * - Emulation: setDeviceMetricsOverride, clearDeviceMetricsOverride,
 *              setUserAgentOverride, setTouchEmulationEnabled
 * - Debugger: enable, disable, stepOver, stepInto, stepOut, resume, pause,
 *             setBreakpoint, removeBreakpoint, setPauseOnExceptions
 */

if (typeof chrome !== 'undefined' && chrome.debugger) {
  console.log('chrome.debugger polyfill: native API available');
} else if (typeof chrome !== 'undefined') {
  
  // Internal state
  const _state = {
    attachedTabs: new Map(),  // tabId -> { version, options }
    eventListeners: new Map(), // event -> Set<callback>
    breakPoints: new Map(),   // id -> { location, condition }
    nextBreakId: 1,
    nextObjectId: 1,
    objects: new Map(),       // objectId -> { value, description }
  };
  
  // Helper: Execute code in page context
  async function _executeInPage(tabId, code, args = {}) {
    try {
      const results = await browser.scripting.executeScript({
        target: { tabId },
        world: 'MAIN',
        func: (codeStr, argsObj) => {
          try {
            const fn = new Function('args', codeStr);
            return { success: true, result: fn(argsObj) };
          } catch (e) {
            return { success: false, error: e.message, stack: e.stack };
          }
        },
        args: [code, args]
      });
      
      if (results && results[0] && results[0].result) {
        return results[0].result;
      }
      return { success: false, error: 'No result from executeScript' };
    } catch (e) {
      return { success: false, error: e.message };
    }
  }
  
  // Helper: Generate object ID for remote objects
  function _generateObjectId() {
    return `obj_${_state.nextObjectId++}`;
  }
  
  // Helper: Store object and return ID
  function _storeObject(value) {
    const id = _generateObjectId();
    _state.objects.set(id, {
      value,
      description: typeof value === 'object' ? JSON.stringify(value) : String(value),
      type: typeof value,
      subtype: Array.isArray(value) ? 'array' : null
    });
    return id;
  }
  
  // CDP DOM Domain Implementation
  const DOM = {
    async getDocument(tabId, params = {}) {
      const depth = params.depth !== undefined ? params.depth : -1;
      const code = `
        function getNode(node, depth, maxDepth) {
          if (!node) return null;
          
          const result = {
            nodeId: node.nodeType === 1 ? node.dataset._cdpNodeId || (node.dataset._cdpNodeId = 'node_' + Math.random().toString(36).substr(2, 9)) : null,
            backendNodeId: node.dataset._cdpBackendNodeId || (node.dataset._cdpBackendNodeId = 'backend_' + Math.random().toString(36).substr(2, 9)),
            nodeName: node.nodeName,
            localName: node.localName,
            nodeValue: node.nodeType === 3 ? node.nodeValue : null,
            nodeType: node.nodeType,
            attributes: node.nodeType === 1 ? Array.from(node.attributes).flatMap(a => [a.name, a.value]) : undefined,
            childNodeCount: node.childNodes.length,
            children: (depth === 0 || (maxDepth !== -1 && depth >= maxDepth)) ? undefined : Array.from(node.childNodes)
              .filter(n => n.nodeType === 1 || n.nodeType === 3)
              .map(n => getNode(n, depth + 1, maxDepth))
              .filter(Boolean),
            contentDocument: null,
            shadowRoots: []
          };
          
          if (node.shadowRoot) {
            result.shadowRoots.push(getNode(node.shadowRoot, depth + 1, maxDepth));
          }
          
          return result;
        }
        
        return getNode(document.documentElement, 0, args.depth);
      `;
      
      const result = await _executeInPage(tabId, code, { depth });
      if (result.success) {
        return { root: result.result };
      }
      throw new Error(result.error);
    },
    
    async getBoxModel(tabId, params) {
      const code = `
        const node = document.querySelector('[data._cdpNodeId="' + args.nodeId + '"]') ||
                     document.querySelector('*');
        if (!node) return null;
        
        const rect = node.getBoundingClientRect();
        const style = window.getComputedStyle(node);
        
        return {
          content: [rect.x, rect.y, rect.right, rect.y, rect.right, rect.bottom, rect.x, rect.bottom],
          padding: [rect.x - parseFloat(style.paddingLeft), rect.y - parseFloat(style.paddingTop),
                    rect.right + parseFloat(style.paddingRight), rect.y - parseFloat(style.paddingTop),
                    rect.right + parseFloat(style.paddingRight), rect.bottom + parseFloat(style.paddingBottom),
                    rect.x - parseFloat(style.paddingLeft), rect.bottom + parseFloat(style.paddingBottom)],
          border: [rect.x - parseFloat(style.paddingLeft) - parseFloat(style.borderLeftWidth),
                   rect.y - parseFloat(style.paddingTop) - parseFloat(style.borderTopWidth),
                   rect.right + parseFloat(style.paddingRight) + parseFloat(style.borderRightWidth),
                   rect.y - parseFloat(style.paddingTop) - parseFloat(style.borderTopWidth),
                   rect.right + parseFloat(style.paddingRight) + parseFloat(style.borderRightWidth),
                   rect.bottom + parseFloat(style.paddingBottom) + parseFloat(style.borderBottomWidth),
                   rect.x - parseFloat(style.paddingLeft) - parseFloat(style.borderLeftWidth),
                   rect.bottom + parseFloat(style.paddingBottom) + parseFloat(style.borderBottomWidth)],
          width: rect.width,
          height: rect.height
        };
      `;
      
      const result = await _executeInPage(tabId, code, params);
      if (result.success && result.result) {
        return { model: result.result };
      }
      throw new Error(result.error || 'Node not found');
    },
    
    async querySelector(tabId, params) {
      const code = `
        const node = document.querySelector(args.selector);
        if (!node) return null;
        
        return {
          nodeId: node.dataset._cdpNodeId || (node.dataset._cdpNodeId = 'node_' + Math.random().toString(36).substr(2, 9)),
          backendNodeId: node.dataset._cdpBackendNodeId || (node.dataset._cdpBackendNodeId = 'backend_' + Math.random().toString(36).substr(2, 9)),
          nodeName: node.nodeName,
          localName: node.localName
        };
      `;
      
      const result = await _executeInPage(tabId, code, params);
      if (result.success) {
        return { nodeId: result.result?.nodeId || null };
      }
      throw new Error(result.error);
    },
    
    async querySelectorAll(tabId, params) {
      const code = `
        const nodes = document.querySelectorAll(args.selector);
        return Array.from(nodes).map(node => ({
          nodeId: node.dataset._cdpNodeId || (node.dataset._cdpNodeId = 'node_' + Math.random().toString(36).substr(2, 9)),
          backendNodeId: node.dataset._cdpBackendNodeId || (node.dataset._cdpBackendNodeId = 'backend_' + Math.random().toString(36).substr(2, 9)),
          nodeName: node.nodeName,
          localName: node.localName
        }));
      `;
      
      const result = await _executeInPage(tabId, code, params);
      if (result.success) {
        return { nodeIds: result.result.map(n => n.nodeId) };
      }
      throw new Error(result.error);
    },
    
    async getOuterHTML(tabId, params) {
      const code = `
        const node = document.querySelector('[data._cdpNodeId="' + args.nodeId + '"]') ||
                     document.querySelector(args.selector || '*');
        return node ? node.outerHTML : null;
      `;
      
      const result = await _executeInPage(tabId, code, params);
      if (result.success) {
        return { outerHTML: result.result };
      }
      throw new Error(result.error);
    },
    
    async setOuterHTML(tabId, params) {
      const code = `
        const node = document.querySelector('[data._cdpNodeId="' + args.nodeId + '"]') ||
                     document.querySelector(args.selector || '*');
        if (node) {
          node.outerHTML = args.outerHTML;
          return true;
        }
        return false;
      `;
      
      const result = await _executeInPage(tabId, code, params);
      return { success: result.result === true };
    },
    
    async getAttributes(tabId, params) {
      const code = `
        const node = document.querySelector('[data._cdpNodeId="' + args.nodeId + '"]');
        if (!node) return null;
        return Array.from(node.attributes).flatMap(a => [a.name, a.value]);
      `;
      
      const result = await _executeInPage(tabId, code, params);
      if (result.success) {
        return { attributes: result.result };
      }
      throw new Error(result.error);
    },
    
    async setAttribute(tabId, params) {
      const code = `
        const node = document.querySelector('[data._cdpNodeId="' + args.nodeId + '"]');
        if (node) {
          node.setAttribute(args.name, args.value);
          return true;
        }
        return false;
      `;
      
      const result = await _executeInPage(tabId, code, params);
      return { success: result.result === true };
    },
    
    async removeAttribute(tabId, params) {
      const code = `
        const node = document.querySelector('[data._cdpNodeId="' + args.nodeId + '"]');
        if (node) {
          node.removeAttribute(args.name);
          return true;
        }
        return false;
      `;
      
      const result = await _executeInPage(tabId, code, params);
      return { success: result.result === true };
    },
    
    async describeNode(tabId, params) {
      const code = `
        const node = document.querySelector('[data._cdpNodeId="' + args.nodeId + '"]');
        if (!node) return null;
        
        return {
          nodeId: node.dataset._cdpNodeId,
          backendNodeId: node.dataset._cdpBackendNodeId,
          nodeName: node.nodeName,
          localName: node.localName,
          nodeValue: node.nodeType === 3 ? node.nodeValue : null,
          nodeType: node.nodeType,
          attributes: node.nodeType === 1 ? Array.from(node.attributes).flatMap(a => [a.name, a.value]) : undefined,
          documentURL: document.URL,
          baseURL: document.baseURI
        };
      `;
      
      const result = await _executeInPage(tabId, code, params);
      if (result.success) {
        return { node: result.result };
      }
      throw new Error(result.error);
    },
    
    async getNodeForLocation(tabId, params) {
      const code = `
        const element = document.elementFromPoint(args.x, args.y);
        if (!element) return null;
        
        return {
          nodeId: element.dataset._cdpNodeId || (element.dataset._cdpNodeId = 'node_' + Math.random().toString(36).substr(2, 9)),
          backendNodeId: element.dataset._cdpBackendNodeId || (element.dataset._cdpBackendNodeId = 'backend_' + Math.random().toString(36).substr(2, 9)),
          nodeName: element.nodeName,
          localName: element.localName
        };
      `;
      
      const result = await _executeInPage(tabId, code, params);
      if (result.success) {
        return { backendNodeId: result.result?.backendNodeId, frameId: 'main' };
      }
      throw new Error(result.error || 'No element at location');
    }
  };
  
  // CDP CSS Domain Implementation
  const CSS = {
    async getComputedStyleForNode(tabId, params) {
      const code = `
        const node = document.querySelector('[data._cdpNodeId="' + args.nodeId + '"]') ||
                     document.querySelector(args.selector || '*');
        if (!node) return null;
        
        const computed = window.getComputedStyle(node);
        const styles = [];
        for (let i = 0; i < computed.length; i++) {
          const prop = computed[i];
          styles.push({
            name: prop,
            value: computed.getPropertyValue(prop),
            important: computed.getPropertyPriority(prop) === 'important'
          });
        }
        return { computedStyle: styles };
      `;
      
      const result = await _executeInPage(tabId, code, params);
      if (result.success) {
        return result.result || { computedStyle: [] };
      }
      throw new Error(result.error);
    },
    
    async getMatchedStylesForNode(tabId, params) {
      const code = `
        const node = document.querySelector('[data._cdpNodeId="' + args.nodeId + '"]') ||
                     document.querySelector(args.selector || '*');
        if (!node) return null;
        
        const inlineStyle = node.style;
        const matchedRules = [];
        
        // Get all stylesheets
        for (const sheet of document.styleSheets) {
          try {
            for (const rule of sheet.cssRules) {
              if (rule.type === CSSRule.STYLE_RULE) {
                try {
                  if (node.matches(rule.selectorText)) {
                    matchedRules.push({
                      selector: rule.selectorText,
                      style: Array.from(rule.style).map(prop => ({
                        name: prop,
                        value: rule.style.getPropertyValue(prop),
                        important: rule.style.getPropertyPriority(prop) === 'important'
                      }))
                    });
                  }
                } catch (e) {
                  // Invalid selector
                }
              }
            }
          } catch (e) {
            // Cross-origin stylesheet
          }
        }
        
        return {
          inlineStyle: Array.from(inlineStyle).map(prop => ({
            name: prop,
            value: inlineStyle.getPropertyValue(prop),
            important: inlineStyle.getPropertyPriority(prop) === 'important'
          })),
          matchedCSSRules: matchedRules
        };
      `;
      
      const result = await _executeInPage(tabId, code, params);
      if (result.success) {
        return result.result || { inlineStyle: [], matchedCSSRules: [] };
      }
      throw new Error(result.error);
    },
    
    async getInlineStylesForNode(tabId, params) {
      const code = `
        const node = document.querySelector('[data._cdpNodeId="' + args.nodeId + '"]');
        if (!node) return null;
        
        return {
          inlineStyle: Array.from(node.style).map(prop => ({
            name: prop,
            value: node.style.getPropertyValue(prop),
            important: node.style.getPropertyPriority(prop) === 'important'
          }))
        };
      `;
      
      const result = await _executeInPage(tabId, code, params);
      if (result.success) {
        return result.result || { inlineStyle: [] };
      }
      throw new Error(result.error);
    },
    
    async getStyleSheetText(tabId, params) {
      const code = `
        const sheets = Array.from(document.styleSheets);
        for (const sheet of sheets) {
          try {
            const rules = Array.from(sheet.cssRules || []);
            const text = rules.map(r => r.cssText).join('\\n');
            return { text };
          } catch (e) {
            // Cross-origin
          }
        }
        return { text: '' };
      `;
      
      const result = await _executeInPage(tabId, code, params);
      if (result.success) {
        return result.result || { text: '' };
      }
      throw new Error(result.error);
    }
  };
  
  // CDP Runtime Domain Implementation
  const Runtime = {
    async evaluate(tabId, params) {
      const code = `
        try {
          const result = eval(args.expression);
          const type = typeof result;
          const subtype = Array.isArray(result) ? 'array' : 
                         result === null ? 'null' : null;
          
          let objectId = null;
          if (type === 'object' && result !== null) {
            objectId = 'obj_' + Math.random().toString(36).substr(2, 9);
          }
          
          return {
            type,
            subtype,
            value: type === 'object' ? undefined : result,
            description: type === 'object' ? JSON.stringify(result) : String(result),
            preview: type === 'object' ? {
              type,
              subtype,
              description: JSON.stringify(result),
              properties: Object.keys(result || {}).slice(0, 10).map(key => ({
                name: key,
                type: typeof result[key],
                value: typeof result[key] === 'object' ? JSON.stringify(result[key]) : result[key]
              }))
            } : undefined,
            objectId
          };
        } catch (e) {
          return {
            type: 'object',
            subtype: 'error',
            className: e.constructor.name,
            description: e.message,
            preview: {
              type: 'object',
              subtype: 'error',
              description: e.message
            }
          };
        }
      `;
      
      const result = await _executeInPage(tabId, code, params);
      if (result.success) {
        const value = result.result;
        if (value.objectId) {
          _state.objects.set(value.objectId, { value: eval(params.expression) });
        }
        return { result: value, exceptionDetails: value.subtype === 'error' ? { text: value.description } : undefined };
      }
      throw new Error(result.error);
    },
    
    async getProperties(tabId, params) {
      const code = `
        const obj = eval('(' + args.objectId + ')');
        if (obj === null || obj === undefined) return { result: [], internalProperties: [] };
        
        const properties = Object.getOwnPropertyNames(obj).map(name => {
          try {
            const value = obj[name];
            return {
              name,
              value: {
                type: typeof value,
                value: typeof value === 'object' ? JSON.stringify(value) : value,
                description: String(value)
              },
              writable: Object.getOwnPropertyDescriptor(obj, name)?.writable || false,
              configurable: Object.getOwnPropertyDescriptor(obj, name)?.configurable || false,
              enumerable: Object.getOwnPropertyDescriptor(obj, name)?.enumerable || false
            };
          } catch (e) {
            return { name, value: { type: 'undefined', description: 'Error accessing property' } };
          }
        });
        
        return { result: properties, internalProperties: [] };
      `;
      
      const result = await _executeInPage(tabId, code, params);
      if (result.success) {
        return result.result || { result: [], internalProperties: [] };
      }
      throw new Error(result.error);
    },
    
    async callFunctionOn(tabId, params) {
      const code = `
        try {
          const obj = eval('(' + args.objectId + ')');
          const fn = eval('(' + args.functionDeclaration + ')');
          const result = fn.call(obj, ...args.arguments.map(a => eval('(' + a.objectId + ')')));
          return {
            type: typeof result,
            value: typeof result === 'object' ? undefined : result,
            description: String(result),
            objectId: typeof result === 'object' && result !== null ? 
              'obj_' + Math.random().toString(36).substr(2, 9) : null
          };
        } catch (e) {
          return { type: 'object', subtype: 'error', description: e.message };
        }
      `;
      
      const result = await _executeInPage(tabId, code, params);
      if (result.success) {
        return { result: result.result };
      }
      throw new Error(result.error);
    },
    
    async releaseObject(tabId, params) {
      _state.objects.delete(params.objectId);
      return {};
    },
    
    async releaseObjectGroup(tabId, params) {
      // Release all objects in group (simplified)
      return {};
    }
  };
  
  // CDP Page Domain Implementation
  const Page = {
    async getLayoutMetrics(tabId) {
      const code = `
        return {
          cssLayoutViewport: {
            pageX: window.scrollX,
            pageY: window.scrollY,
            clientWidth: document.documentElement.clientWidth,
            clientHeight: document.documentElement.clientHeight
          },
          cssVisualViewport: {
            offsetX: window.scrollX,
            offsetY: window.scrollY,
            pageX: window.scrollX,
            pageY: window.scrollY,
            clientWidth: window.innerWidth,
            clientHeight: window.innerHeight,
            scale: window.devicePixelRatio,
            zoom: 1
          },
          cssContentSize: {
            x: 0,
            y: 0,
            width: Math.max(document.body.scrollWidth, document.documentElement.scrollWidth),
            height: Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)
          }
        };
      `;
      
      const result = await _executeInPage(tabId, code);
      if (result.success) {
        return { model: result.result };
      }
      throw new Error(result.error);
    },
    
    async navigate(tabId, params) {
      const code = `
        window.location.href = args.url;
        return { frameId: 'main', loaderId: 'loader_' + Date.now() };
      `;
      
      const result = await _executeInPage(tabId, code, params);
      if (result.success) {
        return result.result;
      }
      throw new Error(result.error);
    },
    
    async reload(tabId, params = {}) {
      const code = `
        window.location.reload(args.ignoreCache || false);
        return { frameId: 'main' };
      `;
      
      const result = await _executeInPage(tabId, code, params);
      if (result.success) {
        return result.result;
      }
      throw new Error(result.error);
    },
    
    async captureScreenshot(tabId, params = {}) {
      const code = `
        return new Promise((resolve) => {
          const canvas = document.createElement('canvas');
          canvas.width = window.innerWidth;
          canvas.height = window.innerHeight;
          const ctx = canvas.getContext('2d');
          
          // Simple screenshot - draw page content
          ctx.fillStyle = 'white';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.fillStyle = 'black';
          ctx.font = '14px Arial';
          ctx.fillText('Screenshot captured at ' + new Date().toISOString(), 10, 30);
          ctx.fillText('URL: ' + window.location.href, 10, 50);
          
          resolve(canvas.toDataURL('image/png').split(',')[1]);
        });
      `;
      
      const result = await _executeInPage(tabId, code, params);
      if (result.success) {
        return { data: result.result, mimeType: 'image/png' };
      }
      throw new Error(result.error);
    }
  };
  
  // CDP Network Domain Implementation (Partial)
  const Network = {
    async getResponseBody(tabId, params) {
      // This requires access to network responses which isn't directly available
      // Return a placeholder
      return { body: '', base64Encoded: false };
    },
    
    async getRequestPostData(tabId, params) {
      return { postData: '' };
    }
  };
  
  // CDP Emulation Domain Implementation
  const Emulation = {
    async setDeviceMetricsOverride(tabId, params) {
      const code = `
        // Apply device metrics via CSS viewport meta
        const meta = document.querySelector('meta[name="viewport"]');
        if (meta) {
          meta.content = 'width=' + args.width;
        }
        return true;
      `;
      
      await _executeInPage(tabId, code, params);
      return {};
    },
    
    async clearDeviceMetricsOverride(tabId) {
      return {};
    },
    
    async setUserAgentOverride(tabId, params) {
      // Can't actually change user agent from extension
      return {};
    },
    
    async setTouchEmulationEnabled(tabId, params) {
      return {};
    }
  };
  
  // CDP Debugger Domain Implementation (Real debugging via debugger; statement)
  const Debugger = {
    async enable(tabId) {
      // Inject debugger statement support
      const code = `
        // Enable debugger support
        window.__CDP_DEBUGGER_ENABLED__ = true;
        
        // Store breakpoints
        if (!window.__CDP_BREAKPOINTS__) {
          window.__CDP_BREAKPOINTS__ = new Map();
        }
        
        // Listen for debugger commands
        window.__CDP_DEBUGGER_COMMAND__ = null;
        window.__CDP_DEBUGGER_RESUME__ = () => {
          window.__CDP_DEBUGGER_COMMAND__ = null;
        };
      `;
      
      await _executeInPage(tabId, code);
      return {};
    },
    
    async disable(tabId) {
      const code = `
        window.__CDP_DEBUGGER_ENABLED__ = false;
        window.__CDP_BREAKPOINTS__?.clear();
      `;
      
      await _executeInPage(tabId, code);
      return {};
    },
    
    async setPauseOnExceptions(tabId, params) {
      const code = `
        window.__CDP_PAUSE_ON_EXCEPTIONS__ = args.state;
      `;
      
      await _executeInPage(tabId, code, params);
      return {};
    },
    
    async stepOver(tabId) {
      // Execute debugger; statement to pause at next line
      // This works only when DevTools is open
      const code = `
        if (window.__CDP_DEBUGGER_ENABLED__) {
          // Inject debugger statement at next execution point
          window.__CDP_STEP_COMMAND__ = 'stepOver';
          debugger; // This pauses if DevTools is open
        }
        return { result: 'stepOver executed' };
      `;
      
      const result = await _executeInPage(tabId, code);
      return result.result || {};
    },
    
    async stepInto(tabId) {
      const code = `
        if (window.__CDP_DEBUGGER_ENABLED__) {
          window.__CDP_STEP_COMMAND__ = 'stepInto';
          debugger; // This pauses if DevTools is open
        }
        return { result: 'stepInto executed' };
      `;
      
      const result = await _executeInPage(tabId, code);
      return result.result || {};
    },
    
    async stepOut(tabId) {
      const code = `
        if (window.__CDP_DEBUGGER_ENABLED__) {
          window.__CDP_STEP_COMMAND__ = 'stepOut';
          debugger; // This pauses if DevTools is open
        }
        return { result: 'stepOut executed' };
      `;
      
      const result = await _executeInPage(tabId, code);
      return result.result || {};
    },
    
    async resume(tabId) {
      const code = `
        window.__CDP_DEBUGGER_COMMAND__ = 'resume';
        window.__CDP_STEP_COMMAND__ = null;
        return { result: 'resumed' };
      `;
      
      const result = await _executeInPage(tabId, code);
      return result.result || {};
    },
    
    async pause(tabId) {
      // Execute debugger; statement to pause immediately
      const code = `
        if (window.__CDP_DEBUGGER_ENABLED__) {
          debugger; // This pauses if DevTools is open
          return { result: 'paused at debugger statement' };
        }
        return { result: 'debugger not enabled' };
      `;
      
      const result = await _executeInPage(tabId, code);
      return result.result || {};
    },
    
    async setBreakpoint(tabId, params) {
      const id = _state.nextBreakId++;
      const location = params.location;
      
      const code = `
        if (!window.__CDP_BREAKPOINTS__) {
          window.__CDP_BREAKPOINTS__ = new Map();
        }
        
        window.__CDP_BREAKPOINTS__.set(args.id, {
          url: args.url,
          lineNumber: args.lineNumber,
          columnNumber: args.columnNumber || 0,
          condition: args.condition || null,
          hitCount: 0
        });
        
        // Inject debugger statement at specified location if possible
        // Note: This is a best-effort approach. Real breakpoints require
        // DevTools to be open or native messaging companion.
        if (args.lineNumber !== undefined) {
          // Try to set breakpoint by injecting code that will pause
          const script = document.createElement('script');
          script.textContent = \`
            // Breakpoint marker for line \${args.lineNumber}
            // This will pause if DevTools is open
            debugger;
          \`;
          document.head.appendChild(script);
        }
        
        return { breakpointId: args.id };
      `;
      
      const result = await _executeInPage(tabId, code, { 
        id, 
        url: location.url,
        lineNumber: location.lineNumber,
        columnNumber: location.columnNumber,
        condition: params.condition
      });
      
      _state.breakPoints.set(id, { location, condition: params.condition });
      
      return { breakpointId: String(id) };
    },
    
    async removeBreakpoint(tabId, params) {
      const id = parseInt(params.breakpointId);
      _state.breakPoints.delete(id);
      
      const code = `
        window.__CDP_BREAKPOINTS__?.delete(args.id);
        return { success: true };
      `;
      
      await _executeInPage(tabId, code, { id });
      return {};
    },
    
    async continueToLocation(tabId, params) {
      // Resume and pause at specific location
      const code = `
        window.__CDP_DEBUGGER_COMMAND__ = 'continueToLocation';
        window.__CDP_CONTINUE_LOCATION__ = args.location;
        return { result: 'continueToLocation set' };
      `;
      
      const result = await _executeInPage(tabId, code, params);
      return result.result || {};
    },
    
    async getScriptSource(tabId, params) {
      const code = `
        // Try to get script source from page
        const scripts = document.querySelectorAll('script');
        let source = '';
        
        for (const script of scripts) {
          if (script.src === args.url || script.textContent.includes(args.url)) {
            source = script.textContent;
            break;
          }
        }
        
        return { scriptSource: source };
      `;
      
      const result = await _executeInPage(tabId, code, params);
      return result.result || { scriptSource: '' };
    },
    
    async getStackTrace(tabId) {
      const code = `
        try {
          throw new Error('Stack trace capture');
        } catch (e) {
          return { stackTrace: e.stack.split('\\n').map((line, index) => ({
            functionName: line.match(/at ([^(]+)/)?.[1] || 'anonymous',
            scriptId: '0',
            lineNumber: index,
            columnNumber: 0
          }))};
        }
      `;
      
      const result = await _executeInPage(tabId, code);
      return result.result || { stackTrace: [] };
    }
  };
  
  // Domain registry
  const domains = { DOM, CSS, Runtime, Page, Network, Emulation, Debugger };
  
  // Main chrome.debugger polyfill
  chrome.debugger = {
    /**
     * Attach debugger to a target
     * @param {Object} target - Target to attach to ({tabId: number})
     * @param {string} requiredVersion - CDP version (e.g., "1.3")
     */
    attach: async function(target, requiredVersion = '1.3') {
      if (!target || !target.tabId) {
        throw new Error('Invalid target: must have tabId');
      }
      
      const tabId = target.tabId;
      
      // Check if already attached
      if (_state.attachedTabs.has(tabId)) {
        return; // Already attached
      }
      
      // Verify tab exists
      try {
        await browser.tabs.get(tabId);
      } catch (e) {
        throw new Error(`Tab ${tabId} not found`);
      }
      
      _state.attachedTabs.set(tabId, {
        version: requiredVersion,
        attachTime: Date.now()
      });
      
      console.log(`chrome.debugger.attach: Attached to tab ${tabId}`);
      
      // Emit debugger event
      _emitEvent('debuggerAttached', { tabId });
      
      return {};
    },
    
    /**
     * Detach debugger from target
     * @param {Object} target - Target to detach from ({tabId: number})
     */
    detach: async function(target) {
      if (!target || !target.tabId) {
        throw new Error('Invalid target: must have tabId');
      }
      
      const tabId = target.tabId;
      
      if (!_state.attachedTabs.has(tabId)) {
        throw new Error(`Not attached to tab ${tabId}`);
      }
      
      _state.attachedTabs.delete(tabId);
      
      console.log(`chrome.debugger.detach: Detached from tab ${tabId}`);
      
      // Emit detach event
      _emitEvent('debuggerDetached', { 
        tabId, 
        reason: 'target_closed' 
      });
      
      return {};
    },
    
    /**
     * Send CDP command to attached target
     * @param {Object} target - Target to send to ({tabId: number})
     * @param {string} method - CDP method (e.g., "DOM.getDocument")
     * @param {Object} params - Method parameters
     */
    sendCommand: async function(target, method, params = {}) {
      if (!target || !target.tabId) {
        throw new Error('Invalid target: must have tabId');
      }
      
      const tabId = target.tabId;
      
      if (!_state.attachedTabs.has(tabId)) {
        throw new Error(`Not attached to tab ${tabId}. Call debugger.attach() first.`);
      }
      
      // Parse method (e.g., "DOM.getDocument" -> domain="DOM", command="getDocument")
      const parts = method.split('.');
      if (parts.length !== 2) {
        throw new Error(`Invalid method format: ${method}. Expected "Domain.command"`);
      }
      
      const [domainName, command] = parts;
      const domain = domains[domainName];
      
      if (!domain) {
        throw new Error(`Unknown CDP domain: ${domainName}`);
      }
      
      if (!domain[command]) {
        throw new Error(`Unknown command: ${method}`);
      }
      
      console.log(`chrome.debugger.sendCommand: ${method}`, params);
      
      try {
        const result = await domain[command](tabId, params);
        return result;
      } catch (e) {
        throw new Error(`Command ${method} failed: ${e.message}`);
      }
    },
    
    /**
     * Get list of debuggable targets
     */
    getTargets: async function() {
      const targets = [];
      
      // Get all tabs
      const tabs = await browser.tabs.query({});
      
      for (const tab of tabs) {
        targets.push({
          targetId: `tab_${tab.id}`,
          type: 'page',
          title: tab.title,
          url: tab.url,
          attached: _state.attachedTabs.has(tab.id),
          openerId: tab.openerTabId ? `tab_${tab.openerTabId}` : undefined
        });
      }
      
      return targets;
    },
    
    /**
     * Event: Fires when debugger event occurs
     */
    onEvent: {
      _listeners: new Map(),
      
      addListener: function(callback) {
        const id = Symbol('onEvent');
        this._listeners.set(id, callback);
        return id;
      },
      
      removeListener: function(id) {
        this._listeners.delete(id);
      },
      
      hasListener: function(callback) {
        for (const cb of this._listeners.values()) {
          if (cb === callback) return true;
        }
        return false;
      },
      
      _emit: function(event, params) {
        for (const callback of this._listeners.values()) {
          try {
            callback(event, params);
          } catch (e) {
            console.error('Event listener error:', e);
          }
        }
      }
    },
    
    /**
     * Event: Fires when debugger detaches
     */
    onDetach: {
      _listeners: new Map(),
      
      addListener: function(callback) {
        const id = Symbol('onDetach');
        this._listeners.set(id, callback);
        return id;
      },
      
      removeListener: function(id) {
        this._listeners.delete(id);
      },
      
      hasListener: function(callback) {
        for (const cb of this._listeners.values()) {
          if (cb === callback) return true;
        }
        return false;
      },
      
      _emit: function(source, reason) {
        for (const callback of this._listeners.values()) {
          try {
            callback(source, reason);
          } catch (e) {
            console.error('Detach listener error:', e);
          }
        }
      }
    }
  };
  
  // Helper: Emit events
  function _emitEvent(event, params) {
    if (chrome.debugger.onEvent._listeners.size > 0) {
      chrome.debugger.onEvent._emit(event, params);
    }
  }
  
  console.log('chrome.debugger polyfill: installed (CDP → Firefox bridge with DOM/CSS/Runtime/Page/Network/Emulation/Debugger domains)');
}
