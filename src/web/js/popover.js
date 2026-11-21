// Shared open/close behaviour for nav-bar popovers: one open at a time,
// closes on outside click and Escape. Used by the bell and the profile menu.

const registry = [];

function close(entry) {
  entry.panel.hidden = true;
  entry.button.setAttribute("aria-expanded", "false");
}

export function closeAll() {
  registry.forEach(close);
}

export function bindPopover(button, panel, onOpen) {
  const entry = { button, panel };
  registry.push(entry);

  button.addEventListener("click", (event) => {
    event.stopPropagation();
    const opening = panel.hidden;
    closeAll();
    if (opening) {
      panel.hidden = false;
      button.setAttribute("aria-expanded", "true");
      if (onOpen) onOpen();
    }
  });
  panel.addEventListener("click", (event) => event.stopPropagation());
}

document.addEventListener("click", closeAll);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeAll();
});
