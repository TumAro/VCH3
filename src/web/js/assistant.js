import { getJson } from "./api.js";

function appendLine(container, text) {
  const p = document.createElement("p");
  p.textContent = text;
  container.appendChild(p);
}

function renderCitations(container, citations) {
  container.replaceChildren();
  for (const citation of citations) {
    const item = document.createElement("span");
    item.className = "assistant-citation";
    item.textContent = `${citation.source_label}: ${citation.metric} = ${citation.value} ${citation.unit}`;
    container.appendChild(item);
  }
}

export function initAssistant() {
  const form = document.getElementById("assistant-form");
  const input = document.getElementById("assistant-query");
  const messages = document.getElementById("assistant-messages");
  const citations = document.getElementById("assistant-citations");
  const status = document.getElementById("assistant-status");
  const dailyButton = document.getElementById("assistant-daily");
  const dailyOutput = document.getElementById("assistant-daily-output");

  getJson("/api/assistant/status")
    .then((state) => {
      status.textContent = state.configured
        ? "Generated answers use verified evidence."
        : state.message || "Provider not configured; verified-only mode.";
    })
    .catch(() => {
      status.textContent = "Assistant status unavailable.";
    });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const query = input.value.trim();
    if (!query) return;
    messages.replaceChildren();
    appendLine(messages, "Thinking...");
    citations.replaceChildren();
    try {
      const answer = await getJson("/api/assistant/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      messages.replaceChildren();
      appendLine(messages, answer.text);
      renderCitations(citations, answer.citations);
    } catch (error) {
      messages.replaceChildren();
      appendLine(messages, "The assistant is unavailable. " + error.message);
    }
  });

  dailyButton.addEventListener("click", async () => {
    dailyButton.disabled = true;
    dailyButton.textContent = "Loading...";
    dailyOutput.hidden = false;
    dailyOutput.replaceChildren();
    appendLine(dailyOutput, "Loading verified tasks...");
    try {
      const answer = await getJson("/api/assistant/daily");
      dailyOutput.replaceChildren();
      appendLine(dailyOutput, answer.text);
      renderCitations(citations, answer.citations);
    } catch (error) {
      dailyOutput.replaceChildren();
      appendLine(dailyOutput, "Could not load daily tasks. " + error.message);
    } finally {
      dailyButton.disabled = false;
      dailyButton.textContent = "Show daily tasks";
    }
  });
}
