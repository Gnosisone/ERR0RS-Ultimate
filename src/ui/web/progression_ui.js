
// ══ ERR0RS SKILL PANEL + ONBOARDING + PROGRESSION ═══════════════════════════
// Injected from: src/ui/web/progression_ui.js (loaded inline)

// ── Skill Panel ──────────────────────────────────────────────────────────────
let _skillPanelOpen = false;

function toggleSkillPanel() {
  _skillPanelOpen = !_skillPanelOpen;
  document.getElementById('skill-panel').classList.toggle('open', _skillPanelOpen);
  if (_skillPanelOpen) loadSkillPanel();
}

async function loadSkillPanel() {
  try {
    const r = await fetch('/api/progression');
    const d = await r.json();

    // Level badge
    document.getElementById('sp-badge').textContent = d.level_badge || '🔰';
    document.getElementById('sp-level-name').textContent = d.level_name || 'SCRIPT KIDDIE';

    const xpToNext = d.xp_to_next || 0;
    const nextLvl  = d.next_level || 'MAX';
    document.getElementById('sp-xp-line').textContent = `${d.xp} XP • ${xpToNext} to ${nextLvl}`;

    // XP bar (progress to next level)
    const levels = [0, 100, 500, 1500, 4000, 10000];
    const lvlIdx = d.level || 0;
    const lvlXPStart = levels[lvlIdx] || 0;
    const lvlXPEnd   = levels[lvlIdx + 1] || lvlXPStart + 1;
    const pct = Math.min(100, ((d.xp - lvlXPStart) / (lvlXPEnd - lvlXPStart)) * 100);
    document.getElementById('sp-xp-bar').style.width = pct + '%';

    // Domains
    const domsEl = document.getElementById('sp-domains');
    domsEl.innerHTML = (d.domains || []).map(dom => `
      <div class="sp-domain-row">
        <div class="sp-domain-icon">${dom.icon}</div>
        <div class="sp-domain-name">${dom.name}</div>
        <div class="sp-domain-bar-wrap">
          <div class="sp-domain-bar" style="width:${dom.pct}%"></div>
        </div>
        <div class="sp-domain-pct">${dom.pct}%</div>
      </div>
    `).join('');

    // Stats
    const statsEl = document.getElementById('sp-stats');
    statsEl.innerHTML = [
      ['Tools Used',    d.tools_used],
      ['Findings',      d.findings],
      ['Achievements',  d.achievements],
      ['Day Streak',    d.streak + ' days'],
    ].map(([k, v]) => `
      <div class="sp-stat-row">
        <span>${k}</span>
        <span class="sp-stat-val">${v}</span>
      </div>
    `).join('');

  } catch(e) {
    document.getElementById('sp-level-name').textContent = 'ERR0RS offline';
  }
}

// Auto-refresh skill panel every 30s if open
setInterval(() => { if (_skillPanelOpen) loadSkillPanel(); }, 30000);

// ── XP Toast Notification ────────────────────────────────────────────────────
function showXPToast(xpGained, levelUp, newLevelName) {
  const toast = document.createElement('div');
  toast.style.cssText = `
    position:fixed; bottom:80px; right:${_skillPanelOpen ? '296px' : '16px'};
    background:#0a0012; border:1px solid #7b2fbe; border-radius:8px;
    padding:10px 14px; z-index:500; font-size:12px; color:#d8b4fe;
    box-shadow:0 4px 20px #7b2fbe44; transition:opacity 0.4s;
    display:flex; align-items:center; gap:8px;
  `;

  if (levelUp) {
    toast.innerHTML = `<span style="font-size:20px">🎉</span>
      <div>
        <div style="color:#a855f7;font-weight:700;font-size:13px">LEVEL UP!</div>
        <div>${newLevelName}</div>
      </div>`;
  } else {
    toast.innerHTML = `<span style="color:#a855f7;font-size:16px;font-weight:700">+${xpGained}</span>
      <div>XP earned</div>`;
  }

  document.body.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 400); }, 2500);

  // Refresh panel if open
  if (_skillPanelOpen) setTimeout(loadSkillPanel, 500);
}

// ── Onboarding Wizard ────────────────────────────────────────────────────────
let _obCurrentScreen = 0;
let _obSkillLevel    = -1;
let _obAgreed        = false;
let _obPayload       = null;

async function checkOnboarding() {
  try {
    const r = await fetch('/api/onboarding');
    const d = await r.json();
    if (d.first_run && d.payload) {
      _obPayload = d.payload;
      document.getElementById('onboarding-overlay').classList.remove('hidden');
      renderOnboardingScreen(0);
    }
  } catch(e) { /* Onboarding check failed silently */ }
}

function renderOnboardingScreen(idx) {
  _obCurrentScreen = idx;
  const screens = _obPayload.screens;
  const screen  = screens[idx];

  // Update step dots
  for (let i = 0; i < screens.length; i++) {
    const dot = document.getElementById(`ob-step-${i}`);
    if (!dot) continue;
    dot.className = 'ob-step' + (i === idx ? ' active' : i < idx ? ' done' : '');
  }

  const el = document.getElementById('ob-screen-content');

  if (screen.id === 'welcome') {
    el.innerHTML = `
      <div class="ob-title">${screen.title}</div>
      <div class="ob-sub">${screen.subtitle}</div>
      <div class="ob-content">
        ${screen.content.map(p => `<p>${p}</p>`).join('')}
      </div>
      <button class="ob-btn" onclick="renderOnboardingScreen(${idx + 1})">
        ${screen.action_label}
      </button>
    `;

  } else if (screen.id === 'ethics') {
    el.innerHTML = `
      <div class="ob-title" style="color:#ef4444">⚠️ ${screen.title}</div>
      <div class="ob-sub">${screen.subtitle}</div>
      <div class="ob-content">
        ${screen.content.map(p => `<p>${p}</p>`).join('')}
      </div>
      <div class="ob-checkbox-row">
        <input type="checkbox" id="ob-agree-check" onchange="
          _obAgreed = this.checked;
          document.getElementById('ob-agree-btn').disabled = !this.checked;
        ">
        <label for="ob-agree-check">${screen.checkbox}</label>
      </div>
      <button class="ob-btn" id="ob-agree-btn" disabled
        onclick="renderOnboardingScreen(${idx + 1})">
        ${screen.action_label}
      </button>
    `;

  } else if (screen.id === 'skill_assessment') {
    el.innerHTML = `
      <div class="ob-title">${screen.title}</div>
      <div class="ob-sub">${screen.subtitle}</div>
      ${screen.options.map(opt => `
        <div class="ob-skill-option" id="ob-opt-${opt.id}"
          onclick="selectSkill(${opt.id})">
          <div class="ob-skill-badge">${opt.badge}</div>
          <div>
            <div class="ob-skill-label">${opt.label}</div>
            <div class="ob-skill-desc">${opt.description}</div>
          </div>
        </div>
      `).join('')}
      <button class="ob-btn" id="ob-skill-btn" disabled
        onclick="renderOnboardingScreen(${idx + 1})">
        Continue →
      </button>
    `;

  } else if (screen.id === 'first_mission') {
    el.innerHTML = `
      <div class="ob-title">🎯 ${screen.title}</div>
      <div class="ob-sub">${screen.subtitle}</div>
      <div class="ob-content">
        ${screen.content.map(p => `<p>${p}</p>`).join('')}
      </div>
      <div style="background:#0d001a;border:1px solid #7b2fbe44;border-radius:8px;padding:12px;margin:12px 0">
        <div style="font-size:11px;color:#7b2fbe;font-weight:700;margin-bottom:6px">MISSION 01</div>
        <div style="font-size:14px;font-weight:700;color:#c084fc">${screen.mission.title}</div>
        <div style="font-size:12px;color:#888;margin-top:4px">${screen.mission.description}</div>
        <div style="font-size:11px;color:#7b2fbe;margin-top:8px">${screen.mission.steps.length} guided steps • XP rewards throughout</div>
      </div>
      <button class="ob-btn" onclick="completeOnboarding()">
        ${screen.action_label}
      </button>
    `;
  }
}

function selectSkill(id) {
  _obSkillLevel = id;
  document.querySelectorAll('.ob-skill-option').forEach(el => el.classList.remove('selected'));
  document.getElementById(`ob-opt-${id}`).classList.add('selected');
  const btn = document.getElementById('ob-skill-btn');
  if (btn) btn.disabled = false;
}

async function completeOnboarding() {
  try {
    await fetch('/api/onboarding/complete', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        agreed: _obAgreed,
        skill_level: _obSkillLevel >= 0 ? _obSkillLevel : 0,
      }),
    });
  } catch(e) {}

  document.getElementById('onboarding-overlay').classList.add('hidden');

  // Show first mission coach
  showMissionCoach(
    'MISSION 01: YOUR FIRST RECON',
    "Let's run nmap against the Juice Shop. Type in the terminal: <code style='color:#a855f7'>nmap -sV -p 80,443,3000,8080 localhost</code>"
  );

  // Award XP
  showXPToast(10, false, '');
}

function showMissionCoach(title, text) {
  document.getElementById('mc-title').textContent = title;
  document.getElementById('mc-text').innerHTML = text;
  document.getElementById('mission-coach').classList.add('visible');
}

// ── Boot sequence ────────────────────────────────────────────────────────────
window.addEventListener('load', () => {
  // Load skill panel data in background
  loadSkillPanel();
  // Check onboarding after 1s (let WS connect first)
  setTimeout(checkOnboarding, 1200);
});

// ════════════════════════════════════════════════════════════════════════════

// ══ BEGINNER MODE TOGGLE ═════════════════════════════════════════════════════
let _beginnerMode = false;
const _beginnerPlaceholders = [
  "try: 'explain sql injection' or 'walk me through kerberoasting'",
  "try: 'what is CIS Control 6' or 'nmap 192.168.1.1'",
  "ask anything — ERR0RS explains what it does and why",
  "try: 'scan 10.0.0.1' or 'what tools should I use for web testing'",
];
let _phIdx = 0;

function toggleBeginner() {
  _beginnerMode = !_beginnerMode;
  const badge = document.getElementById('ltp-mode-badge');
  const input = document.getElementById('ltp-input');
  const grid  = document.getElementById('tool-grid');

  if (_beginnerMode) {
    badge.textContent = '🎓 GUIDED';
    badge.style.color = '#22d3ee';
    badge.style.borderColor = '#22d3ee';
    if (input) input.placeholder = _beginnerPlaceholders[0];
    // Show mission coach if available
    const coach = document.getElementById('mission-coach');
    if (coach && !coach.classList.contains('visible')) {
      if (typeof showMissionCoach !== 'undefined') {
        showMissionCoach(
          'GUIDED MODE ACTIVE',
          'ERR0RS will explain every tool and finding. Ask me anything — I adapt to your level. Try: <code style="color:#a855f7">explain what nmap does</code>'
        );
      }
    }
    // Auto-enable teach mode
    if (!_teachMode) toggleTeachMode();
    // Rotate placeholder
    setInterval(() => {
      if (!_beginnerMode) return;
      _phIdx = (_phIdx + 1) % _beginnerPlaceholders.length;
      if (input) input.placeholder = _beginnerPlaceholders[_phIdx];
    }, 5000);
  } else {
    badge.textContent = '⚡ EXPERT';
    badge.style.color = '#f59e0b';
    badge.style.borderColor = '#f59e0b';
    if (input) input.placeholder = 'type command... add --teach for inline education... Ctrl+C to stop tool';
    const coach = document.getElementById('mission-coach');
    if (coach) coach.classList.remove('visible');
  }
}

// Load beginner mode from preferences on boot
async function loadModeFromPrefs() {
  try {
    const r = await fetch('/api/onboarding');
    const d = await r.json();
    if (!d.first_run) {
      // Not first run — check saved prefs
      const pr = await fetch('/api/progression');
      const pd = await pr.json();
      if (pd.is_beginner && !_beginnerMode) {
        // Auto-enable guided mode for beginners (level 0 or 1)
        // Don't auto-toggle — let user choose after onboarding
      }
    }
  } catch(e) {}
}

// ════════════════════════════════════════════════════════════════════════════

// ══ AUTONOMOUS AGENT PANEL ═══════════════════════════════════════════════════
let _agentPanelOpen = false;
let _agentRunning   = false;
let _agentStatusInterval = null;

function toggleAgentPanel() {
  _agentPanelOpen = !_agentPanelOpen;
  document.getElementById('agent-panel').classList.toggle('visible', _agentPanelOpen);
  if (_agentPanelOpen) refreshAgentStatus();
}

function launchAgent() {
  const target = document.getElementById('ag-target').value.trim();
  const goal   = document.getElementById('ag-goal').value;
  if (!target) { alert('Enter a target first'); return; }

  // Send command via terminal WS
  const cmd = `agent ${target} ${goal}`;
  const input = document.getElementById('ltp-input');
  if (input) {
    input.value = cmd;
    // Trigger send — dispatch Enter key event
    input.dispatchEvent(new KeyboardEvent('keydown', {key:'Enter',keyCode:13,bubbles:true}));
  }
  // Also call wsSend directly if available
  if (typeof wsSend !== 'undefined') wsSend(cmd);

  _agentRunning = true;
  updateAgentUI(true);
  startAgentPolling();
}

function stopAgent() {
  const input = document.getElementById('ltp-input');
  if (input) { input.value = 'stop agent'; input.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',keyCode:13,bubbles:true})); }
  if (typeof wsSend !== 'undefined') wsSend('stop agent');
  _agentRunning = false;
  updateAgentUI(false);
  stopAgentPolling();
}

function updateAgentUI(running) {
  const dot   = document.getElementById('ag-dot');
  const txt   = document.getElementById('ag-status-text');
  const launch= document.getElementById('ag-launch-btn');
  const stop  = document.getElementById('ag-stop-btn');
  if (running) {
    dot.className   = 'ag-dot running';
    txt.textContent = 'RUNNING — ReAct loop active';
    launch.style.display = 'none';
    stop.style.display   = '';
  } else {
    dot.className   = 'ag-dot done';
    txt.textContent = 'IDLE — Ready to engage';
    launch.style.display = '';
    stop.style.display   = 'none';
  }
}

async function refreshAgentStatus() {
  try {
    const r = await fetch('/api/agent/status');
    const d = await r.json();
    if (d.running) {
      updateAgentUI(true);
      _agentRunning = true;
    } else if (_agentRunning) {
      updateAgentUI(false);
      _agentRunning = false;
      stopAgentPolling();
    }
    // Update stats
    const set = (id, val) => { const el = document.getElementById(id); if(el) el.textContent = val; };
    set('ag-phase',    d.phase   || '—');
    set('ag-steps',    d.steps   || 0);
    set('ag-findings', d.findings|| 0);
    set('ag-ports',    (d.open_ports||[]).slice(0,6).join(', ') || '—');
    set('ag-vulns',    (d.vulns||[]).length);
    set('ag-creds',    d.creds   || 0);
  } catch(e) {}
}

function startAgentPolling() {
  if (_agentStatusInterval) return;
  _agentStatusInterval = setInterval(refreshAgentStatus, 3000);
}

function stopAgentPolling() {
  if (_agentStatusInterval) {
    clearInterval(_agentStatusInterval);
    _agentStatusInterval = null;
  }
}

// Pre-fill target from current terminal state
function syncAgentTarget() {
  try {
    const statusEl = document.querySelector('#rp-engagement-target');
    if (statusEl && statusEl.textContent.trim()) {
      document.getElementById('ag-target').value = statusEl.textContent.trim();
    }
  } catch(e) {}
}

// Poll every 3s when panel is open
setInterval(() => { if (_agentPanelOpen && _agentRunning) refreshAgentStatus(); }, 3000);
// ════════════════════════════════════════════════════════════════════════════
