// Moves tab: real moves rendering, interactive filtering, and decision actions (REQ-4, REQ-5, REQ-16).
import { el, inr, int } from "./dom.js";
import { getJson } from "./api.js";

const COLUMNS = 8;
let allMoves = [];
let currentFilter = {
  type: "",
  store: "",
  category: "",
  value: "All",      // "All" | "Over" | "Under"
  decision: "Any",   // "Any" | "Waiting" | "Approved" | "Rejected"
  find: "",
};

function renderEmpty(message = "No moves match the current filters.") {
  const cell = el("td", { colspan: String(COLUMNS), class: "moves-empty" }, [
    el("strong", { text: "No moves found" }),
    document.createTextNode(message),
  ]);
  document.getElementById("moves-body").replaceChildren(el("tr", {}, [cell]));
}

export function setStores(network) {
  const select = document.getElementById("f-store");
  const previous = select.value;
  const stores = network.states
    .flatMap((s) => s.cities.flatMap((c) => c.stores.map((st) => ({ id: st.store_id, city: c.city }))))
    .sort((a, b) => a.id.localeCompare(b.id));

  select.replaceChildren(
    el("option", { value: "", text: "All stores" }),
    ...stores.map((s) => el("option", { value: s.id, text: `${s.id} - ${s.city}` })),
  );
  if (stores.some((s) => s.id === previous)) select.value = previous;
}

function updateSummary(filtered) {
  const totalUnits = filtered.reduce((sum, m) => sum + m.qty, 0);
  const totalMrp = filtered.reduce((sum, m) => sum + m.value_mrp, 0);
  const summaryEl = document.getElementById("moves-summary");
  summaryEl.textContent = `Showing ${int.format(filtered.length)} of ${int.format(allMoves.length)} moves: ${int.format(totalUnits)} units, ${inr.format(totalMrp)} MRP.`;
}

function renderMovesTable(movesToRender) {
  const tbody = document.getElementById("moves-body");
  if (!movesToRender.length) {
    renderEmpty();
    return;
  }

  const rows = movesToRender.map((m) => {
    const isSignoff = m.requires_human_approval;
    const trClass = isSignoff ? "needs-signoff" : "";

    // Move column
    const moveSub = m.move_type === "W2S" ? "Warehouse to store" : "Store to store";
    const moveTd = el("td", {}, [
      el("strong", { text: m.move_type }),
      el("div", { class: "hint", text: moveSub }),
    ]);

    // Route column
    const routeTd = el("td", {}, [
      el("div", { text: `${m.from_city || m.from_location} → ${m.to_city || m.to_location}` }),
      el("div", { class: "hint", text: `${m.from_location} → ${m.to_location}` }),
    ]);

    // Style & Reason column
    const styleTd = el("td", {}, [
      el("strong", { text: m.style_name || m.style_id }),
      el("div", { class: "hint", text: m.sku_id }),
      el("div", { style: "margin-top: 4px; font-size: 13px;", text: m.reason }),
    ]);

    // Qty
    const qtyTd = el("td", { class: "num" }, [el("strong", { text: int.format(m.qty) })]);

    // MRP Value & Badge
    const mrpChildren = [document.createTextNode(inr.format(m.value_mrp))];
    if (isSignoff) {
      mrpChildren.push(el("div", { class: "signoff-badge", text: "Needs sign-off" }));
    }
    const mrpTd = el("td", { class: "num" }, mrpChildren);

    // Dispatch & Arrival
    const dateTd = el("td", {}, [
      el("div", { text: `${m.dispatch_date} → ${m.arrival_date}` }),
      el("div", { class: "hint", text: `${m.route_days} days transit` }),
    ]);

    // Decision actions
    const approveBtn = el("button", {
      type: "button",
      class: `btn-sm btn-approve ${m.decision === "Approved" ? "is-active" : ""}`,
      style: "padding: 4px 8px; font-size: 12px; margin-right: 4px; cursor: pointer; border-radius: 4px; border: 1px solid var(--border); background: " + (m.decision === "Approved" ? "var(--accent)" : "var(--surface)") + "; color: " + (m.decision === "Approved" ? "#fff" : "var(--text)"),
      text: "Approve",
    });

    const rejectBtn = el("button", {
      type: "button",
      class: `btn-sm btn-reject ${m.decision === "Rejected" ? "is-active" : ""}`,
      style: "padding: 4px 8px; font-size: 12px; cursor: pointer; border-radius: 4px; border: 1px solid var(--border); background: " + (m.decision === "Rejected" ? "var(--error, #ef4444)" : "var(--surface)") + "; color: " + (m.decision === "Rejected" ? "#fff" : "var(--text)"),
      text: "Reject",
    });

    approveBtn.addEventListener("click", async () => {
      const nextDec = m.decision === "Approved" ? "Waiting" : "Approved";
      await saveDecision(m.id, nextDec);
    });

    rejectBtn.addEventListener("click", async () => {
      const nextDec = m.decision === "Rejected" ? "Waiting" : "Rejected";
      await saveDecision(m.id, nextDec);
    });

    const decisionTd = el("td", {}, [
      el("div", { style: "display: flex; align-items: center; gap: 4px;" }, [approveBtn, rejectBtn]),
      el("div", { class: "hint", style: "margin-top: 4px;", text: `Status: ${m.decision}` }),
    ]);

    return el("tr", { class: trClass }, [
      el("td", { class: "num", text: String(m.rank) }),
      moveTd,
      routeTd,
      styleTd,
      qtyTd,
      mrpTd,
      dateTd,
      decisionTd,
    ]);
  });

  tbody.replaceChildren(...rows);
}

async function saveDecision(moveId, decision) {
  try {
    await getJson(`/api/moves/${moveId}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision }),
    });
    const target = allMoves.find((m) => m.id === moveId);
    if (target) target.decision = decision;
    applyFilters();
  } catch (err) {
    alert("Failed to save decision: " + err.message);
  }
}

function applyFilters() {
  let filtered = allMoves;

  if (currentFilter.type) {
    filtered = filtered.filter((m) => m.move_type.toLowerCase() === currentFilter.type.toLowerCase());
  }

  if (currentFilter.store) {
    filtered = filtered.filter((m) => m.from_location === currentFilter.store || m.to_location === currentFilter.store);
  }

  if (currentFilter.category) {
    filtered = filtered.filter((m) => m.category.toLowerCase() === currentFilter.category.toLowerCase());
  }

  if (currentFilter.value === "Over") {
    filtered = filtered.filter((m) => m.value_mrp > 100000);
  } else if (currentFilter.value === "Under") {
    filtered = filtered.filter((m) => m.value_mrp <= 100000);
  }

  if (currentFilter.decision !== "Any") {
    filtered = filtered.filter((m) => m.decision.toLowerCase() === currentFilter.decision.toLowerCase());
  }

  if (currentFilter.find) {
    const q = currentFilter.find.toLowerCase();
    filtered = filtered.filter((m) =>
      `${m.sku_id} ${m.style_name} ${m.from_city} ${m.to_city} ${m.from_location} ${m.to_location} ${m.reason}`
        .toLowerCase()
        .includes(q)
    );
  }

  updateSummary(filtered);
  renderMovesTable(filtered);
}

function initFilterControls() {
  const typeSelect = document.getElementById("f-type");
  const storeSelect = document.getElementById("f-store");
  const catSelect = document.getElementById("f-category");
  const findInput = document.getElementById("f-find");

  typeSelect.disabled = false;
  catSelect.disabled = false;
  findInput.disabled = false;

  // Types
  typeSelect.replaceChildren(
    el("option", { value: "", text: "All types" }),
    el("option", { value: "W2S", text: "Warehouse to Store (W2S)" }),
    el("option", { value: "S2S", text: "Store to Store (S2S)" }),
  );
  typeSelect.addEventListener("change", (e) => {
    currentFilter.type = e.target.value;
    applyFilters();
  });

  // Stores
  storeSelect.addEventListener("change", (e) => {
    currentFilter.store = e.target.value;
    applyFilters();
  });

  // Categories
  const categories = Array.from(new Set(allMoves.map((m) => m.category).filter(Boolean))).sort();
  catSelect.replaceChildren(
    el("option", { value: "", text: "All categories" }),
    ...categories.map((c) => el("option", { value: c, text: c })),
  );
  catSelect.addEventListener("change", (e) => {
    currentFilter.category = e.target.value;
    applyFilters();
  });

  // Value segmented buttons
  const valueGroup = document.querySelector('[aria-labelledby="f-value-label"]');
  if (valueGroup) {
    const btns = valueGroup.querySelectorAll(".seg");
    btns.forEach((btn, idx) => {
      btn.disabled = false;
      btn.addEventListener("click", () => {
        btns.forEach((b) => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        currentFilter.value = idx === 0 ? "All" : idx === 1 ? "Over" : "Under";
        applyFilters();
      });
    });
  }

  // Decision segmented buttons
  const decGroup = document.querySelector('[aria-labelledby="f-decision-label"]');
  if (decGroup) {
    const btns = decGroup.querySelectorAll(".seg");
    btns.forEach((btn, idx) => {
      btn.disabled = false;
      btn.addEventListener("click", () => {
        btns.forEach((b) => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        const vals = ["Any", "Waiting", "Approved", "Rejected"];
        currentFilter.decision = vals[idx] || "Any";
        applyFilters();
      });
    });
  }

  // Search input
  findInput.addEventListener("input", (e) => {
    currentFilter.find = e.target.value.trim();
    applyFilters();
  });
}

export async function loadMoves() {
  try {
    const data = await getJson("/api/moves");
    allMoves = data.items || [];
    initFilterControls();
    applyFilters();
  } catch (err) {
    renderEmpty("Could not load moves: " + err.message);
  }
}

export function initMoves() {
  loadMoves();
}
