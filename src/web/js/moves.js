// Moves tab shell (REQ-16). Rows, filtering and decisions arrive with Part B (Track 3 moves).

import { el } from "./dom.js";

const COLUMNS = 8;

function renderEmpty() {
  const cell = el("td", { colspan: String(COLUMNS), class: "moves-empty" }, [
    el("strong", { text: "No moves available yet" }),
    document.createTextNode("Move generation (Track 3) is not built, so there is nothing to review."),
  ]);
  document.getElementById("moves-body").replaceChildren(el("tr", {}, [cell]));
}

/** Fill the Store filter from the network overview (flattened state -> city -> store). */
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

export function initMoves() {
  renderEmpty();
}
