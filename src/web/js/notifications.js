// Notification bell (REQ-15). Unseen = ids not yet seen in this browser.

import { getJson } from "./api.js";
import { el } from "./dom.js";
import { readJson, writeJson } from "./storage.js";
import { bindPopover } from "./popover.js";

const SEEN_KEY = "stockMover.seenNotifications";
let items = [];
let loadFailed = false;

function seenIds() {
  return new Set(readJson(SEEN_KEY, []));
}

function renderBadge() {
  const badge = document.getElementById("bell-count");
  const seen = seenIds();
  const unseen = loadFailed ? 0 : items.filter((n) => !seen.has(n.id)).length;
  badge.hidden = unseen === 0;
  badge.textContent = unseen > 99 ? "99+" : String(unseen);
  document.getElementById("bell-btn").setAttribute(
    "aria-label", unseen ? `Notifications, ${unseen} unseen` : "Notifications"
  );
}

function renderList() {
  const list = document.getElementById("bell-list");
  if (loadFailed) {
    list.replaceChildren(el("li", { class: "notice-empty", text: "Notifications could not be loaded." }));
    return;
  }
  if (!items.length) {
    list.replaceChildren(el("li", { class: "notice-empty", text: "No notifications." }));
    return;
  }
  list.replaceChildren(...items.map((n) => el("li", {}, [
    el("p", { class: "notice-title", text: n.title }),
    el("p", { class: "notice-detail", text: n.detail }),
  ])));
}

function markAllSeen() {
  // Replace (not append) so the stored list stays bounded to the current items.
  writeJson(SEEN_KEY, items.map((n) => n.id));
  renderBadge();
}

export async function refreshNotifications() {
  try {
    items = (await getJson("/api/notifications")).items;
    loadFailed = false;
  } catch (e) {
    items = [];
    loadFailed = true;
  }
  renderList();
  renderBadge();
}

export function initNotifications() {
  bindPopover(document.getElementById("bell-btn"), document.getElementById("bell-panel"), markAllSeen);
  return refreshNotifications();
}
