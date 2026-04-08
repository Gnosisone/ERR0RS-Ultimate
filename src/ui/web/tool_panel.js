/**
 * ERR0RS ULTIMATE — Tool Panel v1.0
 * =====================================
 * Renders the interactive tool anatomy panel:
 *   - Explanation dialog (what this tool does, teach mode)
 *   - Clickable flag buttons with tooltips
 *   - Live command preview bar
 *   - Preset profile selector
 *   - FIRE button → spawns OS terminal
 *
 * Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
 */

const ToolPanel = (() => {

  // ── State ──────────────────────────────────────────────────────────────────
  let _state = {
    tool:         "",
    target:       "",
    panelData:    null,
    activeFlags:  new Set(),
    flagValues:   {},   // flag → value for flags that take args
    builtCommand: "",
  };

  // ── DOM refs (injected panel element) ─────────────────────────────────────
  let _container = null;

  // ── Risk badge colours ─────────────────────────────────────────────────────
  const RISK_STYLE = {
    safe:             { bg: "#0a2200", color: "#39ff14", label: "SAFE"     },
    quiet:            { bg: "#0a1a00", color: "#7fff00", label: "QUIET"    },
    noisy:            { bg: "#1a0a00", color: "#ffaa00", label: "NOISY"    },
    slow:             { bg: "#0a001a", color: "#c084fc", label: "SLOW"     },
    very_noisy:       { bg: "#2a0000", color: "#ff2255", label: "LOUD"     },
    requires_root:    { bg: "#1a1000", color: "#ffd700", label: "ROOT"     },
    depends_on_script:{ bg: "#0a0a1a", color: "#00f5ff", label: "VARIES"  },
  };

  // ── Fetch panel data from backend ──────────────────────────────────────────
  async function loadPanel(tool, target) {
    _state.tool   = tool;
    _state.target = target;
    _state.activeFlags  = new Set();
    _state.flagValues   = {};

    try {
      const r = await fetch(`/api/tool/panel/${tool}?target=${encodeURIComponent(target)}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      _state.panelData = await r.json();
      // Auto-select default flags
      if (_state.panelData.default_command) {
        _state.builtCommand = _state.panelData.default_command;
      }
      render();
      show();
    } catch(e) {
      console.error("[ToolPanel] load error:", e);
      _showError(`Could not load panel for ${tool}: ${e.message}`);
    }
  }

  // ── Build command from active flags ───────────────────────────────────────
  function rebuildCommand() {
    const pd = _state.panelData;
    if (!pd) return;
    const binary  = pd.tool;
    const flags   = [..._state.activeFlags];
    const parts   = [binary];
    flags.forEach(f => {
      parts.push(f);
      if (_state.flagValues[f]) parts.push(_state.flagValues[f]);
    });
    parts.push(_state.target || "TARGET");
    _state.builtCommand = parts.join(" ");
    // Update preview bar
    const bar = document.getElementById("errz-cmd-preview");
    if (bar) bar.textContent = _state.builtCommand;
  }

  // ── Apply preset profile ──────────────────────────────────────────────────
  async function applyPreset(presetName) {
    try {
      const r = await fetch(`/api/tool/preset?tool=${_state.tool}&preset=${encodeURIComponent(presetName)}&target=${encodeURIComponent(_state.target)}`);
      const d = await r.json();
      if (d.command) {
        _state.builtCommand = d.command;
        const bar = document.getElementById("errz-cmd-preview");
        if (bar) bar.textContent = d.command;
        // Flash the preview
        bar.style.color = "var(--green)";
        setTimeout(() => { bar.style.color = ""; }, 800);
      }
    } catch(e) { console.error("[ToolPanel] preset error:", e); }
  }

  // ── FIRE — launch OS terminal ─────────────────────────────────────────────
  async function fire() {
    const cmd  = _state.builtCommand || document.getElementById("errz-cmd-preview")?.textContent;
    const btn  = document.getElementById("errz-fire-btn");
    if (!cmd || !_state.tool) return;

    if (btn) { btn.textContent = "LAUNCHING..."; btn.disabled = true; }

    try {
      const r = await fetch("/api/terminal/fire", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: cmd, tool: _state.tool, target: _state.target }),
      });
      const d = await r.json();
      if (d.status === "fired") {
        if (btn) { btn.textContent = "✔ TERMINAL OPEN"; btn.style.background = "#0a2200"; }
        _appendFeedLog(`[ERR0RS] Terminal launched → ${cmd}`);
      } else {
        if (btn) { btn.textContent = "ERROR — retry"; btn.disabled = false; }
        _appendFeedLog(`[ERR0RS] Launch failed: ${JSON.stringify(d)}`);
      }
    } catch(e) {
      if (btn) { btn.textContent = "NET ERROR"; btn.disabled = false; }
    }

    setTimeout(() => {
      if (btn) { btn.textContent = "⚡ FIRE"; btn.disabled = false; btn.style.background = ""; }
    }, 3000);
  }

  function _appendFeedLog(msg) {
    // Push into the main ERR0RS feed if it exists
    const feed = document.getElementById("feed") || document.getElementById("terminal-output");
    if (feed) {
      const line = document.createElement("div");
      line.style.cssText = "color:var(--green);font-size:12px;padding:2px 0;";
      line.textContent = msg;
      feed.appendChild(line);
      feed.scrollTop = feed.scrollHeight;
    }
  }

  // ── Render the full panel HTML ────────────────────────────────────────────
  function render() {
    if (!_container || !_state.panelData) return;
    const pd = _state.panelData;

    _container.innerHTML = `
      <div id="errz-tool-panel" style="
        background: #0c0020;
        border: 1px solid #2d0a60;
        border-radius: 8px;
        padding: 16px;
        font-family: 'Share Tech Mono', monospace;
        color: #d4b8ff;
        position: relative;
      ">
        <!-- Header -->
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
          <div>
            <span style="font-family:Orbitron,monospace;font-size:1rem;color:#bf6fff;letter-spacing:2px;">
              ${pd.name.toUpperCase()}
            </span>
            <span style="margin-left:10px;font-size:11px;color:#4a2870;text-transform:uppercase;">
              ${pd.category}
            </span>
          </div>
          <button onclick="ToolPanel.hide()" style="background:none;border:none;color:#4a2870;cursor:pointer;font-size:18px;">✕</button>
        </div>

        <!-- Description dialog -->
        <div style="
          background:#08001a;border-left:3px solid #7b2fbe;
          padding:10px 14px;border-radius:4px;margin-bottom:14px;font-size:13px;line-height:1.6;
        ">
          <div style="color:#c084fc;font-size:11px;margin-bottom:4px;">WHAT IS THIS TOOL?</div>
          ${pd.description}
        </div>

        <!-- Teach intro -->
        ${pd.teach_intro ? `
        <div style="
          background:#040010;border:1px dashed #2d0a60;
          padding:10px 14px;border-radius:4px;margin-bottom:14px;font-size:12px;
          color:#9d7ecc;line-height:1.7;
        ">
          <div style="color:#39ff14;font-size:11px;margin-bottom:4px;">[ERR0RS] HOW IT WORKS</div>
          ${pd.teach_intro}
        </div>` : ""}

        <!-- Preset profiles -->
        ${_renderPresets(pd.preset_profiles)}

        <!-- Flag anatomy section -->
        <div style="color:#c084fc;font-size:11px;margin-bottom:8px;letter-spacing:1px;">
          COMMAND FLAGS — click to toggle, hover for explanation
        </div>
        <div id="errz-flag-grid" style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px;">
          ${_renderFlags(pd.flags)}
        </div>

        <!-- Command preview bar -->
        <div style="margin-bottom:12px;">
          <div style="color:#4a2870;font-size:11px;margin-bottom:4px;">BUILT COMMAND</div>
          <div style="
            background:#04000a;border:1px solid #1e0040;border-radius:4px;
            padding:10px 14px;font-size:13px;color:#39ff14;
            word-break:break-all;line-height:1.5;
          " id="errz-cmd-preview" contenteditable="true"
             oninput="ToolPanel._onPreviewEdit(this.textContent)">
            ${pd.default_command || pd.tool + ' TARGET'}
          </div>
          <div style="font-size:10px;color:#2d0a60;margin-top:4px;">
            Editable — click flags above to build, or type directly
          </div>
        </div>

        <!-- DEFEND / Blue Team note -->
        ${pd.defend_notes ? `
        <details style="margin-bottom:12px;">
          <summary style="cursor:pointer;color:#00f5ff;font-size:11px;letter-spacing:1px;user-select:none;">
            🛡 DEFEND — Blue team detection notes
          </summary>
          <div style="padding:10px;background:#00050a;border-left:2px solid #00f5ff;margin-top:6px;font-size:12px;color:#7ecfff;line-height:1.7;">
            ${pd.defend_notes}
          </div>
        </details>` : ""}

        <!-- MITRE techniques -->
        ${pd.mitre && pd.mitre.length ? `
        <div style="margin-bottom:12px;font-size:11px;color:#4a2870;">
          MITRE ATT&CK: ${pd.mitre.map(m => `<span style="color:#ffaa00">${m}</span>`).join(" | ")}
        </div>` : ""}

        <!-- FIRE button -->
        <button id="errz-fire-btn" onclick="ToolPanel.fire()" style="
          width:100%;padding:12px;
          background:linear-gradient(135deg,#1a0040,#3d0a80);
          border:1px solid #bf6fff;border-radius:6px;
          color:#fff;font-family:Orbitron,monospace;font-size:0.95rem;
          letter-spacing:3px;cursor:pointer;
          transition:all 0.2s;
        " onmouseover="this.style.background='linear-gradient(135deg,#2d0060,#5a14b0)'"
           onmouseout="this.style.background='linear-gradient(135deg,#1a0040,#3d0a80)'">
          ⚡ FIRE — LAUNCH TERMINAL
        </button>
      </div>
    `;

    // Re-init flag listeners after render
    _bindFlagEvents();
    rebuildCommand();
  }

  // ── Render preset profile buttons ─────────────────────────────────────────
  function _renderPresets(presets) {
    if (!presets || !Object.keys(presets).length) return "";
    const btns = Object.entries(presets).map(([name, p]) => `
      <button onclick="ToolPanel._applyPreset('${name.replace(/'/g,"\\'")}')"
        title="${p.desc}"
        style="
          padding:5px 10px;background:#0a0020;border:1px solid #2d0a60;
          border-radius:4px;color:#c084fc;font-size:11px;cursor:pointer;
          transition:border-color 0.15s;font-family:'Share Tech Mono',monospace;
        "
        onmouseover="this.style.borderColor='#7b2fbe'"
        onmouseout="this.style.borderColor='#2d0a60'">
        ${name}
      </button>
    `).join("");
    return `
      <div style="margin-bottom:14px;">
        <div style="color:#4a2870;font-size:11px;margin-bottom:6px;letter-spacing:1px;">PRESET PROFILES</div>
        <div style="display:flex;flex-wrap:wrap;gap:6px;">${btns}</div>
      </div>
    `;
  }

  // ── Render individual flag buttons ─────────────────────────────────────────
  function _renderFlags(flags) {
    if (!flags) return "";
    return Object.entries(flags).map(([flag, info]) => {
      const risk = RISK_STYLE[info.risk] || RISK_STYLE.safe;
      return `
        <div class="errz-flag-btn" data-flag="${flag}"
          title="${info.teach || info.desc}"
          style="
            background:#08001a;border:1px solid #1e0040;border-radius:6px;
            padding:8px 12px;cursor:pointer;min-width:120px;max-width:200px;
            transition:border-color 0.15s,background 0.15s;
            position:relative;
          "
          onmouseover="this.style.borderColor='#7b2fbe'"
          onmouseout="if(!this.classList.contains('active'))this.style.borderColor='#1e0040'">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
            <code style="color:#c084fc;font-size:12px;">${flag}</code>
            <span style="
              background:${risk.bg};color:${risk.color};
              font-size:9px;padding:1px 5px;border-radius:3px;
            ">${risk.label}</span>
          </div>
          <div style="font-size:11px;color:#9d7ecc;line-height:1.4;">${info.label}</div>
          <!-- Tooltip on hover -->
          <div class="errz-tooltip" style="
            display:none;position:absolute;bottom:calc(100% + 6px);left:0;
            background:#0c0020;border:1px solid #7b2fbe;border-radius:6px;
            padding:10px 14px;font-size:11px;color:#d4b8ff;z-index:9999;
            min-width:260px;max-width:340px;line-height:1.6;white-space:normal;
          ">
            <div style="color:#39ff14;margin-bottom:4px;">[ERR0RS] ${info.label}</div>
            ${info.teach || info.desc}
            <div style="margin-top:6px;color:#4a2870;">Example: <code style="color:#bf6fff">${info.example || flag}</code></div>
          </div>
        </div>
      `;
    }).join("");
  }

  // ── Bind click/hover events to flag buttons after render ──────────────────
  function _bindFlagEvents() {
    document.querySelectorAll(".errz-flag-btn").forEach(btn => {
      const flag    = btn.dataset.flag;
      const tooltip = btn.querySelector(".errz-tooltip");

      btn.addEventListener("click", () => {
        if (_state.activeFlags.has(flag)) {
          _state.activeFlags.delete(flag);
          btn.style.background  = "#08001a";
          btn.style.borderColor = "#1e0040";
        } else {
          _state.activeFlags.add(flag);
          btn.style.background  = "#1a0040";
          btn.style.borderColor = "#bf6fff";
        }
        btn.classList.toggle("active", _state.activeFlags.has(flag));
        rebuildCommand();
      });

      btn.addEventListener("mouseenter", () => { if (tooltip) tooltip.style.display = "block"; });
      btn.addEventListener("mouseleave", () => { if (tooltip) tooltip.style.display = "none"; });
    });
  }

  // ── Public: direct preview edits ──────────────────────────────────────────
  function _onPreviewEdit(txt) {
    _state.builtCommand = txt.trim();
  }

  // ── Show / hide ────────────────────────────────────────────────────────────
  function show() {
    if (_container) _container.style.display = "block";
  }

  function hide() {
    if (_container) _container.style.display = "none";
  }

  function _showError(msg) {
    if (_container) {
      _container.innerHTML = `<div style="color:#ff2255;padding:16px;">${msg}</div>`;
      _container.style.display = "block";
    }
  }

  // ── Init — create the panel container in the DOM ──────────────────────────
  function init(containerId) {
    _container = document.getElementById(containerId);
    if (!_container) {
      // Create it if not present
      _container = document.createElement("div");
      _container.id = containerId || "errz-tool-panel-wrap";
      _container.style.cssText = "display:none;";
      document.body.appendChild(_container);
    }
  }

  // ── Public API ─────────────────────────────────────────────────────────────
  return {
    init,
    loadPanel,
    show,
    hide,
    fire,
    rebuildCommand,
    _applyPreset: applyPreset,
    _onPreviewEdit,
  };

})();
