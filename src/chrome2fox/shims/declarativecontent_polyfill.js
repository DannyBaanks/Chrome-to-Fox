/**
 * Chrome-to-Fox Polyfill: chrome.declarativeContent
 * 
 * Chrome's declarativeContent API allows declarative content matching.
 * Firefox supports declarativeNetRequest instead.
 */

if (typeof chrome !== 'undefined' && chrome.declarativeContent) {
  console.log('chrome.declarativeContent polyfill: native API available');
} else if (typeof chrome !== 'undefined') {
  chrome.declarativeContent = {
    _rules: new Map(),
    _nextRuleId: 1,
    
    PageStateMatcher: function(options) {
      this.options = options;
      this._type = 'PageStateMatcher';
    },
    
    ShowAction: function(options) {
      this.options = options;
      this._type = 'ShowAction';
    },
    
    SetIcon: function(options) {
      this.options = options;
      this._type = 'SetIcon';
    },
    
    RequestContentScript: function(options) {
      this.options = options;
      this._type = 'RequestContentScript';
    },
    
    AddRules: function(rules) {
      rules.forEach(rule => {
        const ruleId = rule.priority || this._nextRuleId++;
        this._rules.set(ruleId, rule);
      });
      console.warn('chrome.declarativeContent.AddRules polyfill: ' +
        'Rules stored but not applied. Use declarativeNetRequest for Firefox.');
    },
    
    removeRules: function(ruleIds, callback) {
      ruleIds.forEach(id => this._rules.delete(id));
      if (callback) callback();
    },
    
    getRules: function(ruleIds, callback) {
      if (ruleIds && ruleIds.length > 0) {
        const rules = ruleIds.map(id => this._rules.get(id)).filter(Boolean);
        callback(rules);
      } else {
        callback(Array.from(this._rules.values()));
      }
    }
  };
  
  console.log('chrome.declarativeContent polyfill: installed (rule storage only)');
}
