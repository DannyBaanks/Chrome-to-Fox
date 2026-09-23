// FoxBlock background (service_worker MV3) — usa chrome.* para que chrome2fox lo parachee a browser.*.
const RULESET_ID = "ads";

async function refreshBadge() {
  try {
    const data = await chrome.storage.local.get(["enabled", "blockedCount"]);
    const enabled = data.enabled !== false;
    const count = data.blockedCount || 0;
    if (chrome.action && chrome.action.setBadgeText) {
      await chrome.action.setBadgeText({ text: enabled ? String(Math.min(count, 99)) : "OFF" });
      if (chrome.action.setBadgeBackgroundColor) {
        await chrome.action.setBadgeBackgroundColor({ color: enabled ? "#228B22" : "#808080" });
      }
    }
  } catch (e) {
    console.warn("FoxBlock badge failed:", e);
  }
}

async function applyNetworkState(enabled) {
  try {
    if (chrome.declarativeNetRequest && chrome.declarativeNetRequest.updateEnabledRulesets) {
      await chrome.declarativeNetRequest.updateEnabledRulesets(
        enabled ? { enableRulesetIds: [RULESET_ID] } : { disableRulesetIds: [RULESET_ID] }
      );
    }
  } catch (e) {
    console.warn("FoxBlock DNR toggle failed (sigo con cosmetico):", e);
  }
}

chrome.runtime.onInstalled.addListener(async () => {
  const cur = await chrome.storage.local.get(["enabled", "blockedCount"]);
  if (cur.enabled === undefined) await chrome.storage.local.set({ enabled: true });
  if (cur.blockedCount === undefined) await chrome.storage.local.set({ blockedCount: 0 });
  await applyNetworkState(true);
  await refreshBadge();
  console.log("FoxBlock installed");
});

chrome.runtime.onStartup.addListener(async () => {
  const { enabled } = await chrome.storage.local.get(["enabled"]);
  await applyNetworkState(enabled !== false);
  await refreshBadge();
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    if (msg && msg.type === "cosmetic-blocked" && typeof msg.count === "number") {
      const { blockedCount = 0 } = await chrome.storage.local.get(["blockedCount"]);
      await chrome.storage.local.set({ blockedCount: blockedCount + msg.count });
      await refreshBadge();
      sendResponse({ ok: true });
    } else if (msg && msg.type === "set-enabled") {
      await chrome.storage.local.set({ enabled: !!msg.enabled });
      await applyNetworkState(!!msg.enabled);
      await refreshBadge();
      sendResponse({ ok: true, enabled: !!msg.enabled });
    } else if (msg && msg.type === "get-state") {
      const s = await chrome.storage.local.get(["enabled", "blockedCount"]);
      sendResponse({ enabled: s.enabled !== false, blockedCount: s.blockedCount || 0 });
    } else {
      sendResponse({ ok: false });
    }
  })();
  return true;
});

chrome.storage.onChanged.addListener(() => { refreshBadge(); });
