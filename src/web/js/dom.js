// DOM and number-formatting helpers. All text goes through textContent (never innerHTML).

export const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
export const int = new Intl.NumberFormat("en-IN");

export function el(tag, attrs, children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "text") node.textContent = v;
    else if (k === "class") node.className = v;
    else node.setAttribute(k, v);
  }
  for (const child of children || []) node.append(child);
  return node;
}

export function svgEl(tag, attrs) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, v);
  return node;
}

export function compactInr(value) {
  if (value >= 1e7) return "₹" + (value / 1e7).toFixed(1) + " Cr";
  if (value >= 1e5) return "₹" + (value / 1e5).toFixed(1) + " L";
  return inr.format(value);
}

export function pct(value) {
  return value.toFixed(1) + "%";
}

export function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
