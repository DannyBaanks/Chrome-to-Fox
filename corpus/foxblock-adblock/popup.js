// FoxBlock popup — chrome.storage / chrome.runtime (parcheables a browser.*).
document.addEventListener("DOMContentLoaded", async () => {
  const box = document.getElementById("enabled");
  const count = document.getElementById("count");
  async function load() {
    const s = await chrome.storage.local.get(["enabled", "blockedCount"]);
    box.checked = s.enabled !== false;
    count.textContent = s.blockedCount || 0;
  }
  box.addEventListener("change", () => {
    chrome.runtime.sendMessage({ type: "set-enabled", enabled: box.checked }, load);
  });
  document.getElementById("reset").addEventListener("click", async () => {
    await chrome.storage.local.set({ blockedCount: 0 });
    load();
  });
  chrome.storage.onChanged.addListener(load);
  load();
});
