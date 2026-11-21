// Admin display name (REQ-7, REQ-13): first-visit dialog, profile menu editing, greeting.

import { read, write } from "./storage.js";
import { bindPopover, closeAll } from "./popover.js";

const KEY = "stockMover.adminName";

function display(name) {
  const clean = (name || "").trim() || "Admin";
  document.getElementById("admin-name").textContent = clean;
  document.getElementById("profile-name").textContent = clean;
  document.getElementById("avatar").textContent = clean.charAt(0).toUpperCase();
}

function save(name) {
  const clean = (name || "").trim();
  write(KEY, clean);
  display(clean);
}

function initDialog() {
  const dialog = document.getElementById("name-dialog");
  const input = document.getElementById("name-dialog-input");

  // Shown only when the name was never written. Unavailable storage (undefined) never prompts.
  if (read(KEY) !== null || typeof dialog.showModal !== "function") return;

  // Enter in the field submits with the first button ("Skip"); treat Enter as Save instead.
  document.getElementById("name-dialog-form").addEventListener("submit", (event) => {
    event.preventDefault();
    dialog.close(event.submitter && event.submitter.value === "skip" ? "skip" : "save");
  });

  dialog.addEventListener("close", () => {
    // Save stores the typed name; Skip or Escape stores "" so the dialog does not return.
    save(dialog.returnValue === "save" ? input.value : "");
  });
  dialog.showModal();
  input.focus();
}

function initMenu() {
  const button = document.getElementById("profile-btn");
  const panel = document.getElementById("profile-panel");
  const form = document.getElementById("profile-form");
  const input = document.getElementById("profile-input");

  bindPopover(button, panel, () => {
    input.value = (read(KEY) || "").trim();
    input.focus();
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    save(input.value);
    closeAll();
  });
}

export function initProfile() {
  display(read(KEY));
  initMenu();
  initDialog();
}
