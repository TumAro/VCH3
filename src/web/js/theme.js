// Light / dark theme (REQ-14). Follows the OS until the user picks one; the pick is remembered.

import { read, write } from "./storage.js";

const KEY = "stockMover.theme";
const media = window.matchMedia("(prefers-color-scheme: dark)");

function current() {
  return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
}

function apply(theme, button, onChange) {
  document.documentElement.setAttribute("data-theme", theme);
  button.setAttribute("aria-label", theme === "dark" ? "Switch to light mode" : "Switch to dark mode");
  if (onChange) onChange(theme);
}

export function initTheme(onChange) {
  const button = document.getElementById("theme-toggle");
  const stored = read(KEY);
  apply(stored === "dark" || stored === "light" ? stored : media.matches ? "dark" : "light", button, null);

  button.addEventListener("click", () => {
    const next = current() === "dark" ? "light" : "dark";
    write(KEY, next);
    apply(next, button, onChange);
  });

  // Follow live OS changes only while the user has not chosen a theme.
  media.addEventListener("change", (event) => {
    const choice = read(KEY);
    if (choice !== "dark" && choice !== "light") apply(event.matches ? "dark" : "light", button, onChange);
  });
}
