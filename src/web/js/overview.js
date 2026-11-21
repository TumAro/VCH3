// Overview tab: revenue chart with state filter (REQ-9) and state table drill-down (REQ-10, REQ-11).
// Moved unchanged from the former app.js, except colours are re-read on theme change.

import { compactInr, cssVar, el, inr, int, pct, svgEl } from "./dom.js";

const STATE_COLORS = ["--s1", "--s2", "--s3", "--s4", "--s5", "--s6"];

// ---------------------------------------------------------------- chart

const chartState = { data: null, selected: null, known: new Set(), order: [] };

function colorOf(state) {
  const i = chartState.order.indexOf(state);
  return cssVar(STATE_COLORS[(i < 0 ? 0 : i) % STATE_COLORS.length]);
}

function renderFilter() {
  const fieldset = document.getElementById("state-filter");
  fieldset.querySelectorAll("label").forEach((n) => n.remove());
  for (const { state } of chartState.data.series) {
    const box = el("input", { type: "checkbox", value: state });
    box.checked = chartState.selected.has(state);
    box.addEventListener("change", () => {
      if (box.checked) chartState.selected.add(state);
      else chartState.selected.delete(state);
      renderChart();
    });
    const swatch = el("span", { class: "swatch" });
    swatch.style.background = colorOf(state);
    fieldset.append(el("label", {}, [box, swatch, document.createTextNode(state)]));
  }
}

// Round tick step (1, 2, 2.5, 5 x 10^n) giving about four gridlines above zero.
function niceStep(maxValue) {
  if (maxValue <= 0) return 1;
  const raw = maxValue / 4;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  for (const m of [1, 2, 2.5, 5, 10]) if (m * mag >= raw) return m * mag;
  return 10 * mag;
}

function monthLabel(ym) {
  const [y, m] = ym.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleString("en-IN", { month: "short" }) + " " + String(y).slice(2);
}

function renderChart() {
  const host = document.getElementById("chart");
  host.replaceChildren();
  const { months, series } = chartState.data;
  const shown = series.filter((s) => chartState.selected.has(s.state));

  if (!months.length) {
    host.append(el("p", { class: "chart-empty", text: "No sales data loaded." }));
    return;
  }
  if (!shown.length) {
    host.append(el("p", { class: "chart-empty", text: "Select at least one state to show the chart." }));
    return;
  }

  const W = 800, H = 320, L = 70, R = 16, T = 16, B = 36;
  const peak = Math.max(...shown.flatMap((s) => s.values));
  const step = niceStep(peak);
  const ticks = Math.max(1, Math.ceil(peak / step));
  const maxY = step * ticks;
  const x = (i) => L + (months.length === 1 ? 0 : (i * (W - L - R)) / (months.length - 1));
  const y = (v) => T + (H - T - B) * (1 - v / maxY);

  const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Monthly revenue by state" });

  for (let k = 0; k <= ticks; k++) {
    const v = step * k;
    svg.append(svgEl("line", { class: "grid", x1: L, x2: W - R, y1: y(v), y2: y(v) }));
    const label = svgEl("text", { class: "axis-label", x: L - 8, y: y(v) + 4, "text-anchor": "end" });
    label.textContent = compactInr(v);
    svg.append(label);
  }

  const every = Math.max(1, Math.ceil(months.length / 8));
  months.forEach((m, i) => {
    if (i % every !== 0 && i !== months.length - 1) return;
    const label = svgEl("text", { class: "axis-label", x: x(i), y: H - 12, "text-anchor": "middle" });
    label.textContent = monthLabel(m);
    svg.append(label);
  });

  for (const s of shown) {
    const color = colorOf(s.state);
    const d = s.values.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
    svg.append(svgEl("path", { class: "line", d, stroke: color }));
    s.values.forEach((v, i) => {
      const dot = svgEl("circle", { cx: x(i), cy: y(v), r: 3, fill: color });
      const tip = svgEl("title");
      tip.textContent = `${s.state}, ${monthLabel(months[i])}: ${inr.format(v)}`;
      dot.append(tip);
      svg.append(dot);
    });
  }
  host.append(svg);
}

function setChartData(data) {
  const isFirstLoad = chartState.selected === null;
  chartState.data = data;
  for (const s of data.series) if (!chartState.order.includes(s.state)) chartState.order.push(s.state);
  const states = data.series.map((s) => s.state);
  // Default: all states. On refresh, keep the user's selection and add any new state.
  chartState.selected = isFirstLoad
    ? new Set(states)
    : new Set(states.filter((s) => chartState.selected.has(s) || !chartState.known.has(s)));
  chartState.known = new Set(states);
  renderFilter();
  renderChart();
}

/** Re-draw with current theme colours (called on theme change). */
export function repaintChart() {
  if (!chartState.data) return;
  renderFilter();
  renderChart();
}

// ---------------------------------------------------------------- table

const expanded = new Set();  // keys of expanded state / city rows, kept across refreshes

function shareCell(value) {
  const bar = el("span");
  bar.style.width = Math.min(100, value) + "%";
  return el("td", {}, [
    el("div", { class: "share" }, [
      el("div", { class: "share-bar" }, [bar]),
      el("span", { class: "share-text", text: pct(value) }),
    ]),
  ]);
}

function toggleCell(label, key, rerender) {
  const btn = el("button", { type: "button", class: "toggle", "aria-expanded": String(expanded.has(key)), text: label });
  btn.addEventListener("click", () => {
    if (expanded.has(key)) expanded.delete(key);
    else expanded.add(key);
    rerender();
  });
  return el("td", {}, [btn]);
}

function storesTable(stores) {
  const head = el("tr", {}, [
    "Store", "Tier", "Revenue", "On hand", "In transit", "Capacity", "Utilisation", "Zero-stock SKUs",
  ].map((h, i) => el("th", { scope: "col", class: i > 1 ? "num" : "", text: h })));
  const rows = stores.map((s) => el("tr", {}, [
    el("td", { text: s.store_id }),
    el("td", { text: s.tier }),
    el("td", { class: "num", text: inr.format(s.revenue) }),
    el("td", { class: "num", text: int.format(s.on_hand) }),
    el("td", { class: "num", text: int.format(s.in_transit) }),
    el("td", { class: "num", text: int.format(s.capacity) }),
    el("td", { class: "num" + (s.utilisation_pct > 100 ? " warn" : ""), text: pct(s.utilisation_pct) }),
    el("td", { class: "num", text: int.format(s.zero_stock_skus) }),
  ]));
  return el("table", { class: "stores" }, [el("thead", {}, [head]), el("tbody", {}, rows)]);
}

function renderTable(network) {
  const body = document.getElementById("network-body");
  const rerender = () => renderTable(network);
  const rows = [];

  for (const state of network.states) {
    const stateKey = "s:" + state.state;
    rows.push(el("tr", { class: "state-row" }, [
      toggleCell(state.state, stateKey, rerender),
      el("td", { class: "num", text: int.format(state.store_count) }),
      el("td", { class: "num", text: inr.format(state.revenue) }),
      shareCell(state.share_pct),
    ]));
    if (!expanded.has(stateKey)) continue;

    for (const city of state.cities) {
      const cityKey = stateKey + "|c:" + city.city;
      rows.push(el("tr", { class: "city-row" }, [
        toggleCell(city.city, cityKey, rerender),
        el("td", { class: "num", text: int.format(city.store_count) }),
        el("td", { class: "num", text: inr.format(city.revenue) }),
        shareCell(city.share_of_state_pct),
      ]));
      if (expanded.has(cityKey)) {
        rows.push(el("tr", { class: "stores-row" }, [el("td", { colspan: "4" }, [storesTable(city.stores)])]));
      }
    }
  }
  body.replaceChildren(...rows);

  document.getElementById("network-foot").replaceChildren(el("tr", {}, [
    el("td", { text: "Total" }),
    el("td", { class: "num", text: int.format(network.store_count) }),
    el("td", { class: "num", text: inr.format(network.total_revenue) }),
    shareCell(network.total_revenue ? network.states.reduce((a, s) => a + s.share_pct, 0) : 0),
  ]));
}

// ---------------------------------------------------------------- public

export function renderOverview({ status, monthly, network }) {
  document.getElementById("last-run").textContent =
    new Date(status.last_run).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
  setChartData(monthly);
  renderTable(network);
}
