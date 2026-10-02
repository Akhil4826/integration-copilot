/**
 * Integration Copilot Frontend Application Logic
 * Corporate Minimalist AI Design System & Dynamic Engine Management
 */

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const messagesContainer = document.getElementById("messages-container");
  const chatForm = document.getElementById("chat-form");
  const promptInput = document.getElementById("prompt-input");
  const sendBtn = document.getElementById("send-btn");
  const resetBtn = document.getElementById("reset-chat-btn");
  const authTokenInput = document.getElementById("auth-token-input");
  const toggleTokenBtn = document.getElementById("toggle-token-btn");
  
  // Segmented Tabs
  const tabBtnChat = document.getElementById("tab-btn-chat");
  const tabBtnTools = document.getElementById("tab-btn-tools");
  const paneChatControls = document.getElementById("pane-chat-controls");
  const paneToolsCatalog = document.getElementById("pane-tools-catalog");

  // Engine Configuration
  const engineRadios = document.querySelectorAll('input[name="engine-select"]');
  const engineRadioCards = document.querySelectorAll(".engine-radio-card");
  const engineConfigFields = document.getElementById("engine-config-fields");
  const toggleEngineBtn = document.getElementById("toggle-engine-btn");
  const groqKeyInput = document.getElementById("groq-api-key-input");
  const groqModelSelect = document.getElementById("groq-model-select");
  const customUrlInput = document.getElementById("custom-url-input");
  const customModelInput = document.getElementById("custom-model-input");
  const statusEngineVal = document.getElementById("status-engine-val");

  // Confirmation Elements
  const confirmationBanner = document.getElementById("confirmation-banner");
  const confToolName = document.getElementById("conf-tool-name");
  const confPromptText = document.getElementById("conf-prompt-text");
  const confApproveBtn = document.getElementById("conf-approve-btn");
  const confRejectBtn = document.getElementById("conf-reject-btn");

  let activeConfirmationId = null;

  // =========================================================================
  // 1. Settings Persistence (localStorage)
  // =========================================================================
  const STORAGE_KEY_TOKEN = "copilot_auth_token";
  const STORAGE_KEY_ENGINE = "copilot_engine";
  const STORAGE_KEY_GROQ_KEY = "copilot_groq_key";
  const STORAGE_KEY_GROQ_MODEL = "copilot_groq_model";
  const STORAGE_KEY_CUSTOM_URL = "copilot_custom_url";
  const STORAGE_KEY_CUSTOM_MODEL = "copilot_custom_model";

  // Restore saved token
  const savedToken = localStorage.getItem(STORAGE_KEY_TOKEN);
  if (savedToken) {
    authTokenInput.value = savedToken;
  }
  authTokenInput.addEventListener("input", () => {
    localStorage.setItem(STORAGE_KEY_TOKEN, authTokenInput.value.trim());
  });

  // Restore engine selections
  const savedEngine = localStorage.getItem(STORAGE_KEY_ENGINE) || "mock";
  const savedGroqKey = localStorage.getItem(STORAGE_KEY_GROQ_KEY) || "";
  const savedGroqModel = localStorage.getItem(STORAGE_KEY_GROQ_MODEL) || "llama-3.3-70b-versatile";
  const savedCustomUrl = localStorage.getItem(STORAGE_KEY_CUSTOM_URL) || "http://localhost:11434/v1";
  const savedCustomModel = localStorage.getItem(STORAGE_KEY_CUSTOM_MODEL) || "qwen3:4b";

  groqKeyInput.value = savedGroqKey;
  groqModelSelect.value = savedGroqModel;
  customUrlInput.value = savedCustomUrl;
  customModelInput.value = savedCustomModel;

  function applyEngineSelection(val) {
    engineRadios.forEach((r) => {
      r.checked = (r.value === val);
    });
    engineRadioCards.forEach((c) => {
      const radio = c.querySelector('input[type="radio"]');
      if (radio && radio.value === val) {
        c.classList.add("active");
      } else {
        c.classList.remove("active");
      }
    });

    // Update status text
    if (val === "mock") {
      statusEngineVal.textContent = "Built-in Resilient";
      engineConfigFields.style.display = "none";
    } else if (val === "groq") {
      statusEngineVal.textContent = `Groq (${groqModelSelect.value})`;
      engineConfigFields.style.display = "flex";
      document.getElementById("field-groq-key").style.display = "block";
      document.getElementById("field-groq-model").style.display = "block";
      document.getElementById("field-custom-url").style.display = "none";
      document.getElementById("field-custom-model").style.display = "none";
    } else if (val === "custom") {
      statusEngineVal.textContent = `Custom (${customModelInput.value || "local"})`;
      engineConfigFields.style.display = "flex";
      document.getElementById("field-groq-key").style.display = "none";
      document.getElementById("field-groq-model").style.display = "none";
      document.getElementById("field-custom-url").style.display = "block";
      document.getElementById("field-custom-model").style.display = "block";
    }
    localStorage.setItem(STORAGE_KEY_ENGINE, val);
  }

  applyEngineSelection(savedEngine);

  engineRadios.forEach((r) => {
    r.addEventListener("change", (e) => {
      applyEngineSelection(e.target.value);
    });
  });

  toggleEngineBtn.addEventListener("click", () => {
    if (engineConfigFields.style.display === "none") {
      engineConfigFields.style.display = "flex";
    } else {
      engineConfigFields.style.display = "none";
    }
  });

  groqKeyInput.addEventListener("input", () => {
    localStorage.setItem(STORAGE_KEY_GROQ_KEY, groqKeyInput.value.trim());
  });
  groqModelSelect.addEventListener("change", () => {
    localStorage.setItem(STORAGE_KEY_GROQ_MODEL, groqModelSelect.value);
    applyEngineSelection("groq");
  });
  customUrlInput.addEventListener("input", () => {
    localStorage.setItem(STORAGE_KEY_CUSTOM_URL, customUrlInput.value.trim());
  });
  customModelInput.addEventListener("input", () => {
    localStorage.setItem(STORAGE_KEY_CUSTOM_MODEL, customModelInput.value.trim());
  });

  // =========================================================================
  // 2. Navigation Tabs (Console vs MCP Tools Catalog)
  // =========================================================================
  tabBtnChat.addEventListener("click", () => {
    tabBtnChat.classList.add("active");
    tabBtnTools.classList.remove("active");
    paneChatControls.classList.add("active");
    paneToolsCatalog.classList.remove("active");
  });

  tabBtnTools.addEventListener("click", () => {
    tabBtnTools.classList.add("active");
    tabBtnChat.classList.remove("active");
    paneToolsCatalog.classList.add("active");
    paneChatControls.classList.remove("active");
  });

  // Quick Chips & Catalog Cards Auto-Fill
  document.querySelectorAll(".chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      const q = btn.getAttribute("data-query");
      if (q) {
        promptInput.value = q;
        promptInput.focus();
      }
    });
  });

  document.querySelectorAll(".tool-card").forEach((card) => {
    card.addEventListener("click", () => {
      const sample = card.getAttribute("data-sample");
      if (sample) {
        promptInput.value = sample;
        // switch back to chat tab
        tabBtnChat.click();
        promptInput.focus();
      }
    });
  });

  // =========================================================================
  // 3. System Readiness Probe
  // =========================================================================
  async function checkSystemReadiness() {
    try {
      const res = await fetch("/ready");
      const data = await res.json();
      
      const dbVal = document.getElementById("status-db-val");
      if (data.database === "connected") {
        dbVal.textContent = "SQLite Connected";
      } else {
        dbVal.textContent = "DB Degraded";
      }
    } catch (e) {
      console.warn("Readiness probe check failed:", e);
      document.getElementById("status-db-val").textContent = "Offline";
    }
  }
  checkSystemReadiness();

  // Auth token toggle visibility
  toggleTokenBtn.addEventListener("click", () => {
    if (authTokenInput.type === "password") {
      authTokenInput.type = "text";
    } else {
      authTokenInput.type = "password";
    }
  });

  // Reset Chat
  resetBtn.addEventListener("click", () => {
    const welcome = document.querySelector(".welcome-card");
    messagesContainer.innerHTML = "";
    if (welcome) messagesContainer.appendChild(welcome);
    hideConfirmation();
  });

  // =========================================================================
  // 4. Message Rendering Helpers (Bespoke SVGs)
  // =========================================================================
  function getAssistantAvatarSVG() {
    return `
      <div class="avatar-box">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
          <polyline points="2 17 12 22 22 17"></polyline>
          <polyline points="2 12 12 17 22 12"></polyline>
        </svg>
      </div>
    `;
  }

  function getUserAvatarSVG() {
    return `
      <div class="avatar-box">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
          <circle cx="12" cy="7" r="4"></circle>
        </svg>
      </div>
    `;
  }

  function appendUserMessage(text) {
    const row = document.createElement("div");
    row.className = "message-row user";
    row.innerHTML = `
      ${getUserAvatarSVG()}
      <div class="bubble-content">${escapeHTML(text)}</div>
    `;
    messagesContainer.appendChild(row);
    scrollToBottom();
  }

  function appendLoadingMessage() {
    const row = document.createElement("div");
    row.className = "message-row assistant";
    row.id = "active-loading-row";
    row.innerHTML = `
      ${getAssistantAvatarSVG()}
      <div class="bubble-content">
        <div class="typing-dots">
          <span></span><span></span><span></span>
        </div>
      </div>
    `;
    messagesContainer.appendChild(row);
    scrollToBottom();
    return row;
  }

  function removeLoadingMessage() {
    const el = document.getElementById("active-loading-row");
    if (el) el.remove();
  }

  function appendAssistantResponse(data) {
    removeLoadingMessage();
    const row = document.createElement("div");
    row.className = "message-row assistant";

    let traceHTML = "";
    if (data.tool_trace && data.tool_trace.length > 0) {
      const traces = data.tool_trace.map(t => `
        <div class="trace-line">
          <span class="trace-key">Tool:</span>
          <strong>${escapeHTML(t.tool)}</strong> (${t.duration_ms}ms)
        </div>
        <div class="trace-line">
          <span class="trace-key">Status:</span>
          <span>${escapeHTML(t.status)}</span>
        </div>
        <div class="trace-line">
          <span class="trace-key">Summary:</span>
          <span>${escapeHTML(t.result_summary || 'Done')}</span>
        </div>
      `).join("<hr style='border:0; border-top:1px solid rgba(255,255,255,0.06); margin:4px 0;'>");

      traceHTML = `
        <div class="trace-accordion">
          <div class="trace-summary" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'flex' : 'none'">
            <span>⚡ Execution Details (${data.tool_trace.length} tool${data.tool_trace.length > 1 ? 's' : ''})</span>
            <span class="trace-badge">${data.total_duration_ms || data.tool_trace[0].duration_ms}ms</span>
          </div>
          <div class="trace-details" style="display: none;">
            <div class="trace-line">
              <span class="trace-key">Execution ID:</span>
              <span>${data.execution_id || 'n/a'}</span>
            </div>
            ${traces}
          </div>
        </div>
      `;
    }

    let confirmationCardHTML = "";
    if (data.confirmation_request) {
      const conf = data.confirmation_request;
      const paramsList = Object.entries(conf.parameters || {})
        .map(([k, v]) => `<div><strong>${escapeHTML(k)}:</strong> ${escapeHTML(JSON.stringify(v))}</div>`)
        .join("");

      confirmationCardHTML = `
        <div style="margin-top:0.75rem; background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.3); border-radius:8px; padding:0.85rem;">
          <div style="display:flex; align-items:center; gap:6px; color:#fbbf24; font-size:0.74rem; font-weight:700; margin-bottom:4px;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
            AUTHORIZATION REQUIRED
          </div>
          <div style="font-size:0.78rem; font-family:var(--font-mono); color:#cbd5e1; margin-bottom:8px;">
            Action: <code>${escapeHTML(conf.tool_name)}</code>
            <div style="margin-top:4px;">${paramsList}</div>
          </div>
          <div style="display:flex; gap:6px;">
            <button class="btn btn-success" onclick="window.confirmAction('${conf.confirmation_id}', true)">Confirm & Execute</button>
            <button class="btn btn-secondary" onclick="window.confirmAction('${conf.confirmation_id}', false)">Cancel</button>
          </div>
        </div>
      `;
    }

    row.innerHTML = `
      ${getAssistantAvatarSVG()}
      <div class="bubble-content">
        <div>${formatMarkdown(data.message || "")}</div>
        ${confirmationCardHTML}
        ${traceHTML}
      </div>
    `;

    messagesContainer.appendChild(row);
    scrollToBottom();
  }

  function appendErrorMessage(msg) {
    removeLoadingMessage();
    const row = document.createElement("div");
    row.className = "message-row assistant";
    row.innerHTML = `
      ${getAssistantAvatarSVG()}
      <div class="bubble-content" style="border-color: rgba(239, 68, 68, 0.4); background: rgba(239, 68, 68, 0.08);">
        <strong style="color: #f87171;">⚠️ Notice:</strong> ${escapeHTML(msg)}
      </div>
    `;
    messagesContainer.appendChild(row);
    scrollToBottom();
  }

  function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function escapeHTML(str) {
    if (!str) return "";
    return str.replace(/[&<>'"]/g, 
      tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
  }

  function formatMarkdown(text) {
    if (!text) return "";
    let html = escapeHTML(text);
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italics
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Inline code
    html = html.replace(/`(.*?)`/g, '<code style="background:rgba(0,0,0,0.3); padding:1px 5px; border-radius:4px; font-family:var(--font-mono); font-size:0.8em;">$1</code>');
    // Line breaks
    html = html.replace(/\n/g, '<br>');
    return html;
  }

  // =========================================================================
  // 5. Chat Interaction Execution
  // =========================================================================
  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = promptInput.value.trim();
    if (!message) return;

    appendUserMessage(message);
    promptInput.value = "";
    sendBtn.disabled = true;
    appendLoadingMessage();

    // Determine current engine
    const selectedEngine = document.querySelector('input[name="engine-select"]:checked')?.value || "mock";
    
    // Construct payload with dynamic client overrides
    const payload = {
      message: message,
      llm_provider: selectedEngine,
    };

    if (selectedEngine === "groq") {
      payload.llm_model = groqModelSelect.value;
      if (groqKeyInput.value.trim()) {
        payload.api_key = groqKeyInput.value.trim();
      }
    } else if (selectedEngine === "custom") {
      payload.api_base = customUrlInput.value.trim() || undefined;
      payload.llm_model = customModelInput.value.trim() || undefined;
    }

    try {
      const token = authTokenInput.value.trim() || "dev-secret-token-12345";
      const res = await fetch("/api/v1/agent/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        const errMsg = errData.error?.message || errData.detail || `Server returned HTTP ${res.status}`;
        appendErrorMessage(errMsg);
        return;
      }

      const data = await res.json();
      appendAssistantResponse(data);

      if (data.confirmation_request) {
        showConfirmation(data.confirmation_request);
      } else {
        hideConfirmation();
      }

    } catch (err) {
      appendErrorMessage(`Network error: ${err.message}`);
    } finally {
      sendBtn.disabled = false;
    }
  });

  // Confirmation banner handlers
  function showConfirmation(conf) {
    activeConfirmationId = conf.confirmation_id;
    confToolName.textContent = conf.tool_name;
    confPromptText.textContent = conf.prompt_message || "Authorize execution of this write action?";
    confirmationBanner.style.display = "block";
  }

  function hideConfirmation() {
    activeConfirmationId = null;
    confirmationBanner.style.display = "none";
  }

  window.confirmAction = async function(confId, approved) {
    hideConfirmation();
    appendLoadingMessage();

    try {
      const token = authTokenInput.value.trim() || "dev-secret-token-12345";
      const res = await fetch("/api/v1/agent/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          confirmation_id: confId,
          confirmed: approved
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        appendErrorMessage(errData.detail || errData.error?.message || "Confirmation failed");
        return;
      }

      const data = await res.json();
      appendAssistantResponse(data);
    } catch (e) {
      appendErrorMessage(`Confirmation network error: ${e.message}`);
    }
  };

  confApproveBtn.addEventListener("click", () => {
    if (activeConfirmationId) window.confirmAction(activeConfirmationId, true);
  });
  confRejectBtn.addEventListener("click", () => {
    if (activeConfirmationId) window.confirmAction(activeConfirmationId, false);
  });
});
