// Overview / Moves tabs driven by the URL hash (REQ-13). No page reload; reload keeps the tab.

const TABS = ["overview", "moves"];

function show(name) {
  for (const tab of TABS) {
    const active = tab === name;
    document.getElementById("view-" + tab).hidden = !active;
    document.getElementById("tab-" + tab).setAttribute("aria-selected", String(active));
  }
}

function fromHash() {
  const name = location.hash.replace("#", "");
  return TABS.includes(name) ? name : "overview";
}

export function initTabs() {
  window.addEventListener("hashchange", () => show(fromHash()));
  show(fromHash());
}
