/**
 * Integration Copilot Frontend Application Logic
 */

document.addEventListener("DOMContentLoaded", () => {
  const messagesContainer = document.getElementById("messages-container");
  const chatForm = document.getElementById("chat-form");
  const promptInput = document.getElementById("prompt-input");
  const sendBtn = document.getElementById("send-btn");
  const resetBtn = document.getElementById("reset-chat-btn");
  const authTokenInput = document.getElementById("auth-token-input");
  const toggleTokenBtn = document.getElementById("toggle-token-btn");
  const confirmationBanner = document.getElementById("confirmation-banner");
  const confToolName = document.getElementById("conf-tool-name");
  const confPromptText = document.getElementById("conf-prompt-text");
  const confApproveBtn = document.getElementById("conf-approve-btn");
  const confRejectBtn = document.getElementById("conf-reject-btn");

  let activeConfirmationId = null;

  // 1. Initial System Readiness Check
  async function checkSystemReadiness() {
    try {
      const res = await fetch("/ready");
      const data = await res.json();
      
      const dbVal = document.getElementById("status-db-val");
      const dbDot = document.getElementById("status-db-dot");
      if (data.database === "connected") {
        dbVal.textContent = "Connected";
        dbDot.className = "status-dot online";
      } else {
        dbVal.textContent = "Degraded";
        dbDot.className = "status-dot offline";
      }

      const llmVal = document.getElementById("status-llm-val");
      const llmDot = document.getElementById("status-llm-dot");
      llmVal.textContent = `${data.llm_provider} (${data.llm_model})`;
      llmDot.className = "status-dot online";
    } catch (e) {
      console.warn("Readiness probe check failed:", e);
      document.getElementById("status-db-val").textContent = "Offline";
      document.getElementById("status-db-dot").className = "status-dot offline";
    }
  }

  checkSystemReadiness();

  // 2. Token Visibility Toggle
  toggleTokenBtn.addEventListener("click", () => {
    authTokenInput.type = authTokenInput.type === "password" ? "text" : "password";
  });

  // 3. Auto-expanding Textarea
  promptInput.addEventListener("input", () => {
    promptInput.style.height = "auto";
    promptInput.style.height = Math.min(promptInput.scrollHeight, 120) + "px";
  });

  promptInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event("submit"));
    }
  });

  // 4. Reset Chat
  resetBtn.addEventListener("click", () => {
    messagesContainer.innerHTML = `
      <div class="message assistant welcome-card">
        <div class="avatar">🤖</div>
        <div class="content">
          <h3>Welcome to Integration Copilot</h3>
          <p>I am your business integration assistant. I interact directly with your database, order management, and customer support systems via <strong>MCP tools</strong>.</p>
          <p class="hint">Type an instruction below or click any example query from the sidebar to get started.</p>
        </div>
      </div>
    `;
    hideConfirmationBanner();
    promptInput.value = "";
    promptInput.focus();
  });

  // 5. Example Query Chips
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      promptInput.value = chip.dataset.query;
      promptInput.style.height = "auto";
      chatForm.dispatchEvent(new Event("submit"));
    });
  });

  // 6. Confirmation Banner Handling
  function showConfirmationBanner(conf) {
    activeConfirmationId = conf.confirmation_id;
    confToolName.textContent = conf.tool_name;
    confPromptText.textContent = conf.prompt_message;
    confirmationBanner.classList.remove("hidden");
  }

  function hideConfirmationBanner() {
    activeConfirmationId = null;
    confirmationBanner.classList.add("hidden");
  }

  confApproveBtn.addEventListener("click", () => {
    if (activeConfirmationId) {
      resolveConfirmation(activeConfirmationId, true);
    }
  });

  confRejectBtn.addEventListener("click", () => {
    if (activeConfirmationId) {
      resolveConfirmation(activeConfirmationId, false);
    }
  });

  async function resolveConfirmation(confId, approved) {
    hideConfirmationBanner();
    appendUserMessage(approved ? "✓ Approved operation." : "✕ Cancelled operation.");
    
    const loadingId = appendLoadingMessage();
    try {
      const response = await fetch("/api/v1/agent/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${authTokenInput.value.trim()}`,
        },
        body: JSON.stringify({
          message: approved ? "Confirmed" : "Cancelled",
          confirmation_id: confId,
          confirmed: approved,
        }),
      });

      removeLoadingMessage(loadingId);
      const data = await response.json();

      if (!response.ok) {
        appendErrorMessage(data.error?.message || "Failed to process confirmation");
        return;
      }

      appendAssistantMessage(data);
    } catch (err) {
      removeLoadingMessage(loadingId);
      appendErrorMessage(err.message || "Network error occurred");
    }
  }

  // 7. Message Rendering
  function appendUserMessage(text) {
    const msg = document.createElement("div");
    msg.className = "message user";
    msg.innerHTML = `
      <div class="avatar">👤</div>
      <div class="content">${escapeHtml(text)}</div>
    `;
    messagesContainer.appendChild(msg);
    scrollToBottom();
  }

  function appendLoadingMessage() {
    const id = "loading-" + Date.now();
    const msg = document.createElement("div");
    msg.className = "message assistant";
    msg.id = id;
    msg.innerHTML = `
      <div class="avatar">🤖</div>
      <div class="content loading-bubble">
        <div class="dot"></div>
        <div class="dot"></div>
        <div class="dot"></div>
      </div>
    `;
    messagesContainer.appendChild(msg);
    scrollToBottom();
    return id;
  }

  function removeLoadingMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function appendAssistantMessage(data) {
    const msg = document.createElement("div");
    msg.className = "message assistant";

    let traceHtml = "";
    if (data.tool_trace && data.tool_trace.length > 0) {
      const traceId = "trace-" + Math.random().toString(36).substring(2, 9);
      const traceItems = data.tool_trace.map((t) => `
        <div class="tool-step-item">
          <div>
            <span class="step-badge">Step ${t.step}</span>
            <span class="tool-name-badge">→ ${escapeHtml(t.tool)}</span>
            <span class="tool-duration">${t.duration_ms}ms</span>
          </div>
          <div class="tool-summary-line">${escapeHtml(t.result_summary)}</div>
        </div>
      `).join("");

      traceHtml = `
        <div class="tool-trace-card">
          <button class="tool-trace-toggle" onclick="document.getElementById('${traceId}').toggleAttribute('hidden')">
            ⚙ Execution Details (${data.tool_trace.length} tool ${data.tool_trace.length === 1 ? 'call' : 'calls'}) ▾
          </button>
          <div id="${traceId}" class="tool-trace-details" hidden>
            ${traceItems}
            <div class="execution-meta-bar">
              <span>Exec ID: ${data.execution_id.substring(0, 8)}</span>
              <span>Model: ${escapeHtml(data.model)}</span>
              <span>Latency: ${data.total_duration_ms}ms</span>
            </div>
          </div>
        </div>
      `;
    }

    // Format Markdown-like line breaks and bold tags
    let formattedText = escapeHtml(data.message)
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');

    msg.innerHTML = `
      <div class="avatar">🤖</div>
      <div class="content">
        <div>${formattedText}</div>
        ${traceHtml}
      </div>
    `;
    messagesContainer.appendChild(msg);

    // If confirmation is needed, activate confirmation banner
    if (data.status === "AWAITING_CONFIRMATION" && data.confirmation_request) {
      showConfirmationBanner(data.confirmation_request);
    }

    scrollToBottom();
  }

  function appendErrorMessage(errorMsg) {
    const msg = document.createElement("div");
    msg.className = "message assistant";
    msg.innerHTML = `
      <div class="avatar" style="background:#881337; color:#fecdd3;">⚠️</div>
      <div class="content" style="border-color:#f43f5e; color:#fecdd3;">
        <strong>Error:</strong> ${escapeHtml(errorMsg)}
      </div>
    `;
    messagesContainer.appendChild(msg);
    scrollToBottom();
  }

  function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // 8. Chat Form Submit Handler
  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = promptInput.value.trim();
    if (!query) return;

    promptInput.value = "";
    promptInput.style.height = "auto";
    sendBtn.disabled = true;

    appendUserMessage(query);
    const loadingId = appendLoadingMessage();

    try {
      const response = await fetch("/api/v1/agent/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${authTokenInput.value.trim()}`,
        },
        body: JSON.stringify({ message: query }),
      });

      removeLoadingMessage(loadingId);
      const data = await response.json();

      if (!response.ok) {
        appendErrorMessage(data.error?.message || `HTTP ${response.status}: Failed to process request.`);
        return;
      }

      appendAssistantMessage(data);
    } catch (err) {
      removeLoadingMessage(loadingId);
      appendErrorMessage("Network error: Could not reach the Integration Copilot server.");
    } finally {
      sendBtn.disabled = false;
      promptInput.focus();
    }
  });
});
