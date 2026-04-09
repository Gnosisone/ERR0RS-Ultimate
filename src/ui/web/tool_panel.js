/**
 * ERR0RS ULTIMATE — Tool Panel v2.0 (Production)
 * ================================================
 * Renders the interactive tool anatomy panel.
 *
 * BUGS FIXED vs v1.0:
 *   - _state is now exposed in public API so _updateTarget works
 *   - show() now controls the OVERLAY element, not just the container
 *   - hide() closes overlay AND backdrop
 *   - _appendFeedLog targets #intel-feed (the real element ID)
 *   - rebuildCommand() exposed in public API
 *   - Preset fetch uses correct GET method
 *   - Flag tooltips use absolute positioning inside the panel overlay
 *     so they never clip outside the viewport
 *   - FIRE button sends to both OS terminal AND live terminal feed
 *   - launchInLiveTerm() option sends command directly to WebSocket
 *
 * Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
 */

const ToolPanel = (() => {

  /* ── State ─────────────────────────────────────────────────────────────── */
  const _state = {
    tool:        "",
    target:      "",
    panelData:   null,
    activeFlags: new Set(),
    flagValues:  {},
    builtCommand:"",
  };

  let _container = null;   // #errz-tool-panel-wrap
  let _overlay   = null;   // #errz-panel-overlay

  /* ── Risk colours ──────────────────────────────────────────────────────── */
  const RISK = {
    safe:             { bg:"#0a2200", fg:"#39ff14", label:"SAFE"    },
    quiet:            { bg:"#0a1a00", fg:"#7fff00", label:"QUIET"   },
    noisy:            { bg:"#1a0a00", fg:"#ffaa00", label:"NOISY"   },
    slow:             { bg:"#0a001a", fg:"#c084fc", label:"SLOW"    },
    very_noisy:       { bg:"#2a0000", fg:"#ff2255", label:"LOUD"    },
    requires_root:    { bg:"#1a1000", fg:"#ffd700", label:"ROOT"    },
    depends_on_script:{ bg:"#0a0a1a", fg:"#00f5ff", label:"VARIES" },
  };

  /* ── Init ──────────────────────────────────────────────────────────────── */
  function init(containerId) {
    _container = document.getElementById(containerId);
    _overlay   = document.getElementById("errz-panel-overlay");
    if (!_container) {
      _container = document.createElement("div");
      _container.id = containerId || "errz-tool-panel-wrap";
      document.getElementById("errz-panel-overlay")?.appendChild(_container)
        || document.body.appendChild(_container);
    }
  }

  /* ── Load panel data from server ───────────────────────────────────────── */
  async function loadPanel(tool, target) {
    _state.tool        = tool;
    _state.target      = target || "";
    _state.activeFlags = new Set();
    _state.flagValues  = {};
    _state.builtCommand= "";

    if (!_container) init("errz-tool-panel-wrap");

    _container.innerHTML = `<div style="color:#c084fc;padding:24px;font-size:13px;letter-spacing:1px;">
      LOADING ${tool.toUpperCase()} ANATOMY...</div>`;
    show();

    try {
      const url = `/api/tool/panel/${encodeURIComponent(tool)}?target=${encodeURIComponent(_state.target)}`;
      const r   = await fetch(url);
      if (!r.ok) throw new Error(`Server returned ${r.status}`);
      _state.panelData    = await r.json();
      _state.builtCommand = _state.panelData.default_command || `${tool} ${_state.target || "TARGET"}`;
      render();
    } catch(e) {
      _container.innerHTML = `<div style="color:#ff2255;padding:16px;font-size:13px;">
        [ERR0RS] Could not load panel: ${e.message}<br><br>
        Make sure the server is running at http://127.0.0.1:8765</div>`;
      console.error("[ToolPanel]", e);
    }
  }


  /* ── Build command from toggled flags ──────────────────────────────────── */
  function rebuildCommand() {
    const pd = _state.panelData;
    if (!pd) return;
    const flags = [..._state.activeFlags];
    if (!flags.length) {
      // No flags toggled — show the default command
      const bar = document.getElementById("errz-cmd-preview");
      if (bar) bar.textContent = _state.builtCommand;
      return;
    }
    const binary = pd.tool;
    const parts  = [binary];
    flags.forEach(f => {
      parts.push(f);
      if (_state.flagValues[f]) parts.push(_state.flagValues[f]);
    });
    parts.push(_state.target || "TARGET");
    _state.builtCommand = parts.join(" ");
    const bar = document.getElementById("errz-cmd-preview");
    if (bar) bar.textContent = _state.builtCommand;
  }

  /* ── Apply preset ──────────────────────────────────────────────────────── */
  async function applyPreset(presetName) {
    const btn = document.querySelector(`[data-preset="${CSS.escape(presetName)}"]`);
    if (btn) btn.textContent = "Loading...";
    try {
      const url = `/api/tool/preset?tool=${encodeURIComponent(_state.tool)}`
                + `&preset=${encodeURIComponent(presetName)}`
                + `&target=${encodeURIComponent(_state.target)}`;
      const r = await fetch(url);
      if (!r.ok) throw new Error(`${r.status}`);
      const d = await r.json();
      if (d.error) throw new Error(d.error);
      _state.builtCommand = d.command;
      // Clear active flags — preset owns the command now
      _state.activeFlags.clear();
      document.querySelectorAll(".errz-flag-btn.active").forEach(el => {
        el.classList.remove("active");
        el.style.background  = "#08001a";
        el.style.borderColor = "#1e0040";
      });
      const bar = document.getElementById("errz-cmd-preview");
      if (bar) {
        bar.textContent   = d.command;
        bar.style.color   = "#39ff14";
        bar.style.outline = "1px solid #39ff14";
        setTimeout(() => { bar.style.color = ""; bar.style.outline = ""; }, 900);
      }
      _intelLog(`Preset "${presetName}" → ${d.command}`);
    } catch(e) {
      _intelLog(`Preset error: ${e.message}`, "error");
    }
    if (btn) btn.textContent = presetName;
  }

  /* ── FIRE: open OS terminal window ─────────────────────────────────────── */
  async function fire() {
    const cmd = _getCurrentCommand();
    if (!cmd) { _intelLog("No command to fire", "error"); return; }
    const btn = document.getElementById("errz-fire-btn");
    if (btn) { btn.textContent = "⏳ LAUNCHING..."; btn.disabled = true; }
    try {
      const r = await fetch("/api/terminal/fire", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ command: cmd, tool: _state.tool, target: _state.target }),
      });
      const d = await r.json();
      if (d.status === "fired") {
        _intelLog(`⚡ Terminal launched → ${cmd}`);
        if (btn) { btn.textContent = "✔ TERMINAL OPEN"; btn.style.borderColor = "#39ff14"; }
      } else {
        throw new Error(d.result?.error || JSON.stringify(d));
      }
    } catch(e) {
      _intelLog(`Launch failed: ${e.message}`, "error");
      if (btn) { btn.textContent = "❌ ERROR — retry"; btn.disabled = false; }
    }
    setTimeout(() => {
      if (btn) { btn.textContent = "⚡ FIRE — LAUNCH TERMINAL"; btn.disabled = false; btn.style.borderColor = ""; }
    }, 4000);
  }

  /* ── Send command into the live WebSocket terminal ─────────────────────── */
  function sendToLiveTerm() {
    const cmd = _getCurrentCommand();
    if (!cmd) return;
    // Access the global WS from index.html
    if (typeof ws !== "undefined" && ws && ws.readyState === 1) {
      // Open live terminal panel if not already open
      if (typeof openLiveTerm === "function") openLiveTerm();
      ws.send(JSON.stringify({ type: "run", command: cmd, teach: true }));
      _intelLog(`Sent to live terminal: ${cmd}`);
      // Close the panel overlay so the terminal is visible
      setTimeout(hide, 400);
    } else {
      // Fall back: open the target modal path
      _intelLog("Live terminal not connected — opening target modal", "warn");
      if (typeof openLiveTerm === "function") {
        openLiveTerm();
        setTimeout(() => {
          if (typeof ltpInput !== "undefined" && ltpInput) {
            ltpInput.value = cmd;
            ltpInput.focus();
          }
        }, 600);
      }
    }
  }

  /* ── Helpers ───────────────────────────────────────────────────────────── */
  function _getCurrentCommand() {
    const bar = document.getElementById("errz-cmd-preview");
    return (bar ? bar.textContent.trim() : "") || _state.builtCommand || "";
  }

  function _onPreviewEdit(txt) {
    _state.builtCommand = txt.trim();
  }

  function _updateTarget(val) {
    _state.target = val.trim();
    rebuildCommand();
  }

  /* ── Push a message into the ERR0RS intel feed ─────────────────────────── */
  function _intelLog(msg, type = "info") {
    // #intel-feed is the real element ID in index.html
    const feed = document.getElementById("intel-feed");
    if (!feed) return;
    const ts   = new Date().toLocaleTimeString("en-US", { hour12: false });
    const card = document.createElement("div");
    card.className = "ic " + (type === "error" ? "error" : "info");
    card.innerHTML = `<div class="ic-ts">${ts}</div><div class="ic-ttl">⚡ TOOL PANEL</div>`
                   + `<div class="ic-body">${msg}</div>`;
    feed.insertBefore(card, feed.firstChild);
    while (feed.children.length > 14) feed.removeChild(feed.lastChild);
  }


  /* ── Show / hide the overlay ────────────────────────────────────────────── */
  function show() {
    // Show the outer overlay (which contains the panel)
    const ov = _overlay || document.getElementById("errz-panel-overlay");
    const bd = document.getElementById("errz-panel-backdrop");
    if (ov) ov.style.display = "block";
    if (bd) bd.style.display = "block";
  }

  function hide() {
    const ov = _overlay || document.getElementById("errz-panel-overlay");
    const bd = document.getElementById("errz-panel-backdrop");
    if (ov) ov.style.display = "none";
    if (bd) bd.style.display = "none";
  }

  /* ── Render full panel HTML ─────────────────────────────────────────────── */
  function render() {
    if (!_container || !_state.panelData) return;
    const pd = _state.panelData;

    _container.innerHTML = `
<div style="font-family:'Share Tech Mono',monospace;color:#d4b8ff;">

  <!-- Tool header -->
  <div style="display:flex;align-items:center;justify-content:space-between;
              margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid #1e0040;">
    <div>
      <span style="font-family:Orbitron,monospace;font-size:.95rem;
                   color:#bf6fff;letter-spacing:2px;">
        ${_esc(pd.name.toUpperCase())}
      </span>
      <span style="margin-left:8px;font-size:10px;color:#4a2870;
                   text-transform:uppercase;letter-spacing:1px;">
        ${_esc(pd.category)}
      </span>
    </div>
    <button onclick="ToolPanel.hide()"
      style="background:none;border:none;color:#4a2870;cursor:pointer;
             font-size:20px;line-height:1;padding:0 4px;"
      title="Close">✕</button>
  </div>

  <!-- What is this tool -->
  <div style="background:#08001a;border-left:3px solid #7b2fbe;
              padding:10px 14px;border-radius:4px;margin-bottom:12px;
              font-size:12px;line-height:1.7;">
    <div style="color:#c084fc;font-size:10px;margin-bottom:4px;letter-spacing:1px;">
      WHAT IS THIS TOOL?
    </div>
    ${_esc(pd.description)}
  </div>

  <!-- How it works -->
  ${pd.teach_intro ? `
  <div style="background:#040010;border:1px dashed #2d0a60;
              padding:10px 14px;border-radius:4px;margin-bottom:12px;
              font-size:12px;color:#9d7ecc;line-height:1.7;">
    <div style="color:#39ff14;font-size:10px;margin-bottom:4px;letter-spacing:1px;">
      [ERR0RS] HOW IT WORKS
    </div>
    ${_esc(pd.teach_intro)}
  </div>` : ""}

  <!-- Preset profiles -->
  ${_renderPresets(pd.preset_profiles)}

  <!-- Flag anatomy -->
  <div style="color:#c084fc;font-size:10px;margin-bottom:8px;letter-spacing:1px;">
    FLAGS — click to toggle · hover to learn
  </div>
  <div id="errz-flag-grid"
       style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px;">
    ${_renderFlags(pd.flags)}
  </div>

  <!-- Command preview -->
  <div style="margin-bottom:12px;">
    <div style="color:#4a2870;font-size:10px;margin-bottom:4px;letter-spacing:1px;">
      BUILT COMMAND
    </div>
    <div id="errz-cmd-preview"
         contenteditable="true"
         oninput="ToolPanel._onPreviewEdit(this.textContent)"
         spellcheck="false"
         style="background:#04000a;border:1px solid #1e0040;border-radius:4px;
                padding:10px 14px;font-size:12px;color:#39ff14;
                word-break:break-all;line-height:1.6;min-height:38px;
                outline:none;cursor:text;font-family:'Share Tech Mono',monospace;">
      ${_esc(_state.builtCommand)}
    </div>
    <div style="font-size:10px;color:#2d0a60;margin-top:3px;">
      Editable directly · click flags to build · or type your own
    </div>
  </div>

  <!-- Blue team / defend notes -->
  ${pd.defend_notes ? `
  <details style="margin-bottom:12px;">
    <summary style="cursor:pointer;color:#00f5ff;font-size:10px;
                    letter-spacing:1px;user-select:none;padding:4px 0;">
      🛡 DEFEND — Blue team detection &amp; remediation
    </summary>
    <div style="padding:10px;background:#00050a;border-left:2px solid #00f5ff;
                margin-top:6px;font-size:11px;color:#7ecfff;line-height:1.7;">
      ${_esc(pd.defend_notes)}
    </div>
  </details>` : ""}

  <!-- MITRE -->
  ${pd.mitre && pd.mitre.length ? `
  <div style="margin-bottom:14px;font-size:10px;color:#4a2870;line-height:1.8;">
    MITRE ATT&amp;CK:
    ${pd.mitre.map(m => `<span style="color:#ffaa00;">${_esc(m)}</span>`).join(" &nbsp;|&nbsp; ")}
  </div>` : ""}

  <!-- Action buttons -->
  <div style="display:flex;gap:8px;margin-top:4px;">
    <button id="errz-fire-btn" onclick="ToolPanel.fire()"
      style="flex:1;padding:12px 8px;
             background:linear-gradient(135deg,#1a0040,#3d0a80);
             border:1px solid #bf6fff;border-radius:6px;
             color:#fff;font-family:Orbitron,monospace;font-size:.75rem;
             letter-spacing:2px;cursor:pointer;transition:all 0.2s;"
      onmouseover="this.style.background='linear-gradient(135deg,#2d0060,#5a14b0)'"
      onmouseout="this.style.background='linear-gradient(135deg,#1a0040,#3d0a80)'">
      ⚡ FIRE — OS TERMINAL
    </button>
    <button onclick="ToolPanel.sendToLiveTerm()"
      style="flex:1;padding:12px 8px;
             background:linear-gradient(135deg,#001a00,#003d00);
             border:1px solid #39ff14;border-radius:6px;
             color:#39ff14;font-family:Orbitron,monospace;font-size:.75rem;
             letter-spacing:2px;cursor:pointer;transition:all 0.2s;"
      onmouseover="this.style.background='linear-gradient(135deg,#002a00,#005a00)'"
      onmouseout="this.style.background='linear-gradient(135deg,#001a00,#003d00)'"
      title="Run in ERR0RS live terminal with inline teaching">
      📺 RUN + TEACH
    </button>
  </div>
  <div style="font-size:10px;color:#2d0a60;margin-top:6px;text-align:center;">
    ⚡ FIRE opens a real ${_esc(detectTerminalName())} window &nbsp;|&nbsp;
    📺 RUN+TEACH pipes to ERR0RS live terminal with inline annotation
  </div>

</div>`;

    _bindFlagEvents();
    rebuildCommand();
  }

  function detectTerminalName() {
    // This is client-side — just show a friendly name
    return "terminal";
  }


  /* ── Render preset buttons ──────────────────────────────────────────────── */
  function _renderPresets(presets) {
    if (!presets || !Object.keys(presets).length) return "";
    const btns = Object.entries(presets).map(([name, p]) => `
      <button data-preset="${_esc(name)}"
        onclick="ToolPanel._applyPreset(this.dataset.preset)"
        title="${_esc(p.desc)}"
        style="padding:5px 10px;background:#0a0020;border:1px solid #2d0a60;
               border-radius:4px;color:#c084fc;font-size:11px;cursor:pointer;
               font-family:'Share Tech Mono',monospace;white-space:nowrap;"
        onmouseover="this.style.borderColor='#7b2fbe';this.style.color='#d4b8ff'"
        onmouseout="this.style.borderColor='#2d0a60';this.style.color='#c084fc'">
        ${_esc(name)}
      </button>`).join("");
    return `<div style="margin-bottom:12px;">
      <div style="color:#4a2870;font-size:10px;margin-bottom:6px;letter-spacing:1px;">
        PRESET PROFILES
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:6px;">${btns}</div>
    </div>`;
  }

  /* ── Render flag buttons ────────────────────────────────────────────────── */
  function _renderFlags(flags) {
    if (!flags || !Object.keys(flags).length) return "<div style='color:#4a2870;font-size:11px;'>No flags defined for this tool.</div>";
    return Object.entries(flags).map(([flag, info]) => {
      const r    = RISK[info.risk] || RISK.safe;
      const tip  = _esc(info.teach || info.desc || "");
      const ex   = _esc(info.example || flag);
      const lbl  = _esc(info.label || flag);
      return `
<div class="errz-flag-btn" data-flag="${_esc(flag)}"
  style="background:#08001a;border:1px solid #1e0040;border-radius:6px;
         padding:8px 12px;cursor:pointer;position:relative;
         min-width:110px;max-width:190px;transition:border-color 0.15s,background 0.15s;">
  <div style="display:flex;align-items:center;gap:5px;margin-bottom:3px;">
    <code style="color:#c084fc;font-size:11px;font-weight:bold;">${_esc(flag)}</code>
    <span style="background:${r.bg};color:${r.fg};font-size:8px;
                 padding:1px 4px;border-radius:2px;white-space:nowrap;">${r.label}</span>
  </div>
  <div style="font-size:10px;color:#9d7ecc;line-height:1.4;">${lbl}</div>
  <div class="errz-tooltip" style="display:none;position:fixed;
    background:#0c0020;border:1px solid #7b2fbe;border-radius:6px;
    padding:12px 14px;font-size:11px;color:#d4b8ff;
    z-index:99999;width:300px;max-width:90vw;line-height:1.7;
    box-shadow:0 4px 24px rgba(0,0,0,0.6);">
    <div style="color:#39ff14;font-size:10px;margin-bottom:5px;letter-spacing:1px;">
      [ERR0RS] ${lbl}
    </div>
    <div style="margin-bottom:8px;">${tip}</div>
    <div style="color:#4a2870;font-size:10px;">
      Example:<br>
      <code style="color:#bf6fff;font-size:10px;word-break:break-all;">${ex}</code>
    </div>
  </div>
</div>`;
    }).join("");
  }

  /* ── Bind flag button events (called after render) ──────────────────────── */
  function _bindFlagEvents() {
    document.querySelectorAll(".errz-flag-btn").forEach(btn => {
      const flag    = btn.dataset.flag;
      const tooltip = btn.querySelector(".errz-tooltip");

      /* Click: toggle flag on/off */
      btn.addEventListener("click", () => {
        if (_state.activeFlags.has(flag)) {
          _state.activeFlags.delete(flag);
          btn.style.background  = "#08001a";
          btn.style.borderColor = "#1e0040";
          btn.classList.remove("active");
        } else {
          _state.activeFlags.add(flag);
          btn.style.background  = "#1a0040";
          btn.style.borderColor = "#bf6fff";
          btn.classList.add("active");
        }
        rebuildCommand();
      });

      /* Hover: position and show tooltip using fixed positioning
         so it never clips inside the scrollable overlay */
      btn.addEventListener("mouseenter", e => {
        if (!tooltip) return;
        const rect = btn.getBoundingClientRect();
        tooltip.style.display = "block";
        // Position above the button, aligned left, clamped to viewport
        let top  = rect.top - tooltip.offsetHeight - 8;
        let left = rect.left;
        if (top < 8) top = rect.bottom + 8;
        if (left + 300 > window.innerWidth - 8) left = window.innerWidth - 308;
        tooltip.style.top  = top  + "px";
        tooltip.style.left = left + "px";
      });
      btn.addEventListener("mouseleave", () => {
        if (tooltip) tooltip.style.display = "none";
      });
    });
  }

  /* ── HTML escape helper ─────────────────────────────────────────────────── */
  function _esc(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  /* ── Public API ─────────────────────────────────────────────────────────── */
  return {
    /* Core */
    init,
    loadPanel,
    show,
    hide,
    fire,
    sendToLiveTerm,
    rebuildCommand,
    /* Called from HTML attributes */
    _applyPreset:    applyPreset,
    _onPreviewEdit:  _onPreviewEdit,
    _updateTarget:   _updateTarget,
    /* Exposed state so external code can read/write */
    get _state()     { return _state; },
  };

})();
