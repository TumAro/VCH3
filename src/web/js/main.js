// Start-up wiring and re-run (REQ-6, REQ-12).

import { getJson } from "./api.js";
import { initTabs } from "./tabs.js";
import { initTheme } from "./theme.js";
import { initProfile } from "./profile.js";
import { initNotifications, refreshNotifications } from "./notifications.js";
import { renderOverview, repaintChart } from "./overview.js";
import { initMoves, loadMoves, setStores } from "./moves.js";
import { initAssistant } from "./assistant.js";

function showError(message) {
  const error = document.getElementById("rerun-error");
  error.textContent = message;
  error.hidden = !message;
}

async function loadAll() {
  const [status, monthly, network] = await Promise.all([
    getJson("/api/status"),
    getJson("/api/revenue/monthly"),
    getJson("/api/network"),
  ]);
  renderOverview({ status, monthly, network });
  setStores(network);
}

function initRerun() {
  const btn = document.getElementById("rerun-btn");
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    btn.textContent = "Running...";
    showError("");
    try {
      await getJson("/api/sync", { method: "POST" });
      await Promise.all([loadAll(), refreshNotifications(), loadMoves()]);
    } catch (e) {
      showError("Re-run failed, showing last good data. " + e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "Re-run";
    }
  });
}

initTheme(repaintChart);
initTabs();
initProfile();
initMoves();
initAssistant();
initRerun();
initNotifications();
loadAll().catch((e) => showError("Could not load data. " + e.message));
