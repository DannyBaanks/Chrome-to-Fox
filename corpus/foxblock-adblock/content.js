// FoxBlock cosmetic filter — DOM puro, sin chrome.* salvo un sendMessage final (parcheable).
(function () {
  const SELECTORS = [
    ".ad", ".ads", ".advert", ".advertisement", ".sponsored",
    "[id^='div-gpt-ad']", "[id*='-ad-']", "[class*='taboola']",
    "[class*='outbrain']", "iframe[src*='doubleclick']",
    "iframe[src*='googlesyndication']", "[data-ad-slot]"
  ];
  let total = 0;
  function sweep(root) {
    let n = 0;
    for (const sel of SELECTORS) {
      for (const el of root.querySelectorAll(sel)) {
        if (!el.dataset.foxblockHidden) { el.style.setProperty("display", "none", "important"); el.dataset.foxblockHidden = "1"; n++; }
      }
    }
    return n;
  }
  function report(n) {
    total += n;
    try {
      if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.sendMessage) {
        chrome.runtime.sendMessage({ type: "cosmetic-blocked", count: n });
      }
    } catch (e) { /* pagina sin contexto extension, ignoro */ }
  }
  const first = sweep(document);
  if (first) report(first);
  const obs = new MutationObserver((muts) => {
    let n = 0;
    for (const m of muts) for (const node of m.addedNodes) {
      if (node.nodeType === 1) { n += sweep(node); if (node.matches && SELECTORS.some((s) => { try { return node.matches(s); } catch (e) { return false; } })) { node.style.setProperty("display", "none", "important"); n++; } }
    }
    if (n) report(n);
  });
  obs.observe(document.documentElement, { childList: true, subtree: true });
})();
