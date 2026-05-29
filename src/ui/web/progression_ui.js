
// ══ ERR0RS SKILL PANEL + ONBOARDING + PROGRESSION ═══════════════════════════
// Injected from: src/ui/web/progression_ui.js (loaded inline)

// ── Skill Panel ──────────────────────────────────────────────────────────────
let _skillPanelOpen = false;

function toggleSkillPanel() {
  _skillPanelOpen = !_skillPanelOpen;
  document.getElementById('skill-panel').classList.toggle('open', _skillPanelOpen);
  if (_skillPanelOpen) {
    loadSkillPanel();
    // Dismiss the welcome-back card if it's still onscreen — it physically
    // overlaps the skill panel's content area (top:60px right:14px width:300px
    // vs. panel right:0 width:280px) and would silently intercept clicks on
    // the buttons in the OPERATOR / MODES / ACTIONS sections. Either of
    // these wants the user's attention, not both at once.
    const wb = document.getElementById('welcome-back');
    if (wb) wb.classList.add('hidden');
  }
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
  // Always pull the new operator profile section too (separate fetch so
  // a /api/progression failure doesn't block /api/profile and vice versa).
  try {
    if (typeof loadOperatorProfileSection === 'function') {
      await loadOperatorProfileSection();
    }
  } catch(e) {}
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

  // ── Mission opt-in instead of auto-start ──────────────────────────────────
  // Per the agreed UX: onboarding completion does NOT auto-start a mission.
  // The user sees a "Start Mission 01" card on the dashboard and clicks it
  // when ready. This respects user agency and lets them explore the UI
  // before committing to a guided flow.
  showMissionInvite();

  // Award XP for completing onboarding
  showXPToast(10, false, '');
}

// ── Mission Coach — server-authoritative ─────────────────────────────────────
// The frontend is a thin renderer. All mission state lives in the backend
// (src/core/mission_state.py + ~/.err0rs/mission_state.json) and survives
// reboots, browser refreshes, and multiple tabs. The JS module-level state
// here is purely a cache of the last server response.
let _missionState = null;  // last response from /api/mission/state

// Extract the tool name from a command string ("nmap -sV foo" → "nmap").
// Used to render step previews; advancement logic lives server-side.
function _missionToolFromCommand(cmd) {
  if (!cmd) return '';
  const first = cmd.trim().split(/\s+/)[0] || '';
  return first.split('/').pop().toLowerCase();
}

// Pull current mission state from the server. Called on page load and after
// every advancement. Updates the Mission Coach UI to reflect what the server
// says is the truth.
async function refreshMissionState() {
  try {
    const r = await fetch('/api/mission/state');
    const state = await r.json();
    _missionState = state;
    window.MISSION_STATE  = state;             // expose for debug
    window.MISSION_ACTIVE = !!state.active_mission && !state.is_complete;
    renderMissionCoach(state);
    return state;
  } catch(e) {
    window.MISSION_ACTIVE = false;
    return null;
  }
}

// Decide what to render based on current server state.
//   1. just_completed set → show celebration ONCE, then dismiss
//   2. No active mission → no Mission Coach (the invite is shown from
//      completeOnboarding only, not auto on every load)
//   3. Active mission, not complete → show current step
//   4. Active mission, complete → show celebration (legacy path; cleared
//      state migration will handle this on next mission completion)
function renderMissionCoach(state) {
  if (!state) return;

  // Just-completed celebration (one-shot)
  if (state.just_completed) {
    showMissionComplete({
      mission_def: { title: state.just_completed.mission_id.replace(/_/g, ' ') }
    });
    // Don't bug the user every reload — fire-and-forget clear of the flag
    fetch('/api/mission/clear-celebration', { method: 'POST' }).catch(() => {});
    return;
  }

  if (!state.active_mission) return;
  if (state.is_complete) {
    showMissionComplete(state);
    return;
  }
  showCurrentMissionStep(state);
}

// Render the current step using server-provided data. Pulls rich coaching
// fields (instruction, what_it_does, what_to_look_for) directly from the
// state.current_step_data the backend joined in from FIRST_MISSIONS.
function showCurrentMissionStep(state) {
  const step    = state.current_step_data;
  if (!step) return;
  const stepNum = state.current_step + 1;
  const total   = state.total_steps;
  const mtitle  = (state.mission_def && state.mission_def.title) || 'MISSION';

  const html = `
    <div style="font-size:11px;color:#7b2fbe;font-weight:700;margin-bottom:6px">
      STEP ${stepNum} / ${total} &nbsp;•&nbsp; +${step.xp_reward} XP
    </div>
    <div style="font-size:13px;color:#e8d5ff;margin-bottom:8px;line-height:1.5">
      ${step.instruction}
    </div>
    <div style="background:#0d001a;border:1px solid #7b2fbe66;border-radius:6px;
                padding:8px 10px;margin:6px 0;
                font-family:'Share Tech Mono',monospace;font-size:12px;
                color:#a855f7;word-break:break-all;cursor:pointer"
         onclick="navigator.clipboard&&navigator.clipboard.writeText(this.textContent.trim());this.style.borderColor='#22d3ee';setTimeout(()=>this.style.borderColor='#7b2fbe66',600)"
         title="Click to copy">
      ${step.command}
    </div>
    <div style="display:flex;gap:6px;margin:8px 0 4px 0">
      <button onclick="runCurrentMissionStep()"
              style="flex:1;background:#7b2fbe;border:none;color:#fff;
                     padding:8px 12px;border-radius:6px;cursor:pointer;
                     font-family:'Share Tech Mono',monospace;font-size:11px;
                     font-weight:700;letter-spacing:0.05em">
        ▶ RUN STEP
      </button>
      <button onclick="document.getElementById('mission-coach').classList.remove('visible')"
              style="background:#0d001a;border:1px solid #7b2fbe66;color:#888;
                     padding:8px 12px;border-radius:6px;cursor:pointer;
                     font-family:'Share Tech Mono',monospace;font-size:11px"
              title="Close \u2014 reopen via the skill panel">
        ✕
      </button>
    </div>
    <div style="font-size:11px;color:#888;margin-top:8px;line-height:1.5">
      <strong style="color:#22d3ee">What it does:</strong> ${step.what_it_does}
    </div>
    <div style="font-size:11px;color:#888;margin-top:6px;line-height:1.5">
      <strong style="color:#f59e0b">What to look for:</strong> ${step.what_to_look_for}
    </div>
    <div style="margin-top:10px;font-size:10px;color:#7b2fbe;letter-spacing:.08em">
      ▶ Click RUN STEP \u2014 ERR0RS fires the command with the mission's exact args.
    </div>
  `;
  const shortTitle = step.instruction.split('.')[0].slice(0, 60);
  showMissionCoach(`${mtitle} — STEP ${stepNum}: ${shortTitle}`, html);
}

// Mission completed — celebration card with accurate "what's next" pointers
// based on what actually exists in the lesson DB and the future mission list.
function showMissionComplete(state) {
  const mtitle = (state.mission_def && state.mission_def.title) || 'Mission';
  showMissionCoach(
    `✅ ${mtitle.toUpperCase()} COMPLETE`,
    `<div style="font-size:13px;color:#22d3ee;line-height:1.5">
      Nice work, operator. You've completed your first recon.
      You now know the target's attack surface — every path you found is a
      potential entry point.
    </div>
    <div style="margin-top:10px;font-size:11px;color:#888;line-height:1.6">
      Ready for more? Try one of these:
    </div>
    <div style="margin-top:8px;display:flex;flex-direction:column;gap:6px">
      <button onclick="continueLessons()"
              style="background:#0d001a;border:1px solid #7b2fbe66;color:#e8d5ff;
                     padding:6px 10px;border-radius:5px;cursor:pointer;
                     font-family:'Share Tech Mono',monospace;font-size:11px;
                     text-align:left">
        📚 Continue learning — open the next lesson
      </button>
      <button onclick="document.getElementById('mission-coach').classList.remove('visible')"
              style="background:#0d001a;border:1px solid #22d3ee66;color:#22d3ee;
                     padding:6px 10px;border-radius:5px;cursor:pointer;
                     font-family:'Share Tech Mono',monospace;font-size:11px;
                     text-align:left">
        🎯 Explore on your own — close this card
      </button>
    </div>`
  );
}

// Invite card — shown after onboarding when no mission is active.
// Single button "Start Mission 01" calls the backend to begin web_recon.
function showMissionInvite() {
  const html = `
    <div style="font-size:13px;color:#e8d5ff;line-height:1.5;margin-bottom:10px">
      Welcome aboard, operator. You're ready for your first guided mission —
      a 3-step web recon against a local target.
    </div>
    <div style="font-size:11px;color:#888;margin-bottom:12px">
      Or close this card and explore the platform on your own. You can start
      the mission anytime from the dashboard.
    </div>
    <button onclick="startMission('web_recon')"
            style="background:#7b2fbe;border:none;color:#fff;padding:8px 16px;
                   border-radius:6px;font-family:'Share Tech Mono',monospace;
                   font-size:12px;font-weight:700;letter-spacing:.08em;cursor:pointer">
      START MISSION 01 →
    </button>
  `;
  showMissionCoach('🎯 MISSION 01 AVAILABLE', html);
}

// Called from the "Start Mission" button. Hits the backend, then refreshes
// the local view from the server's authoritative response.
async function startMission(missionId) {
  try {
    await fetch('/api/mission/start', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({mission_id: missionId}),
    });
    await refreshMissionState();
  } catch(e) {
    console.error('startMission failed:', e);
  }
}

// Called from the WS handler in index.html when a tool completes. Hits the
// backend — server decides whether to advance, returns new state, we re-render.
// Wrong-tool runs return the state unchanged (silent no-op by design).
async function advanceMission(completedCommand) {
  const tool = _missionToolFromCommand(completedCommand);
  if (!tool) return null;
  try {
    const r = await fetch('/api/mission/advance', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({tool: tool}),
    });
    const newState = await r.json();
    // Did we actually advance? Compare to cached state.
    const advanced = _missionState
      && newState.current_step > (_missionState.current_step || 0);
    _missionState = newState;
    window.MISSION_STATE  = newState;
    window.MISSION_ACTIVE = !!newState.active_mission && !newState.is_complete;
    if (advanced) {
      // Award XP for the completed step (XP toast is FE-only flash)
      const completedIdx = newState.current_step - 1;
      try {
        // Find xp_reward of the just-completed step from completion_history
        // or fall back to the step object we just left
        showXPToast(30, false, '');  // Conservative default; real XP lives server-side
      } catch(e) {}
      renderMissionCoach(newState);
    }
    return newState;
  } catch(e) {
    console.error('advanceMission failed:', e);
    return null;
  }
}

// Expose mission API to the inline handler in index.html and to dashboard buttons
window.startMission           = startMission;
window.advanceMission         = advanceMission;
window.refreshMissionState    = refreshMissionState;
window.showMissionInvite      = showMissionInvite;

// Run the current mission step VERBATIM via the new backend route. Bypasses
// the intent parser — guarantees the mission's exact args reach the tool
// without the Brain replacing them with its own defaults. Triggered by the
// "▶ RUN STEP" button on the Mission Coach card.
async function runCurrentMissionStep() {
  try {
    const r = await fetch('/api/mission/run-current-step', {method: 'POST'});
    const d = await r.json();
    if (d.error) {
      console.error('runCurrentMissionStep:', d.error);
      return;
    }
    // The operator._run_tool call already broadcasts narration + findings
    // via the WS, so the Live Term and xterm will show progress in real
    // time. We just need to refresh mission state to advance the Coach
    // card if the step completed successfully.
    setTimeout(refreshMissionState, 1500);
  } catch(e) {
    console.error('runCurrentMissionStep failed:', e);
  }
}
window.runCurrentMissionStep  = runCurrentMissionStep;

function showMissionCoach(title, text) {
  document.getElementById('mc-title').textContent = title;
  document.getElementById('mc-text').innerHTML = text;
  document.getElementById('mission-coach').classList.add('visible');
}

// ── Boot sequence ────────────────────────────────────────────────────────────
window.addEventListener('load', () => {
  // Load skill panel data in background
  loadSkillPanel();
  // Per-launch ethics gate fires first. If acknowledged, runPostGateBoot
  // runs onboarding/mission/welcome-back. If not, the gate blocks the UI
  // and the user clicking I AGREE will call runPostGateBoot itself.
  setTimeout(async () => {
    const gatePassed = await checkEthicsGate();
    if (gatePassed) {
      await runPostGateBoot();
    }
    // If gate not passed, acceptEthics() will call runPostGateBoot when ready.
  }, 1000);
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


// ════════════════════════════════════════════════════════════════════════════
// ══ ETHICS GATE — per-launch agreement, blocks UI until acknowledged
// ════════════════════════════════════════════════════════════════════════════
// Architecture: on every page load, fetch /api/ethics/status. If not
// acknowledged for THIS launcher PID, show the gate modal blocking the UI
// until the user checks the box and clicks I AGREE. On agreement, POST to
// /api/ethics/agree and hide the modal. Once agreed, proceeds to onboarding
// (if first run) or welcome-back card (if returning).

async function checkEthicsGate() {
  try {
    const r = await fetch('/api/ethics/status');
    const d = await r.json();
    if (d.acknowledged) return true;   // gate not needed, fall through

    // Populate the agreement text from server (FE doesn't hardcode legal copy)
    const a = d.agreement || {};
    document.getElementById('ethics-gate-title').textContent    = a.title || 'ETHICS AGREEMENT';
    document.getElementById('ethics-gate-preamble').textContent = a.preamble || '';
    document.getElementById('ethics-gate-footer').textContent   = a.footer || '';
    const clauses = document.getElementById('ethics-gate-clauses');
    clauses.innerHTML = (a.clauses || []).map(c => `<li>${c}</li>`).join('');

    // Wire the checkbox → button enable/disable.
    // Use BOTH onchange and onclick to maximize reliability across browsers
    // (Firefox sometimes fires only one, depending on input scaling and
    // event ordering with click-on-label).
    const cb  = document.getElementById('ethics-gate-check');
    const btn = document.getElementById('ethics-gate-agree-btn');
    cb.checked = false;
    btn.disabled = true;
    btn.style.opacity = 0.4;
    const syncBtnState = () => {
      btn.disabled = !cb.checked;
      btn.style.opacity = cb.checked ? 1.0 : 0.4;
    };
    cb.onchange = syncBtnState;
    cb.onclick  = syncBtnState;   // belt + suspenders
    // Also sync on any keyboard interaction with the label (space toggles)
    cb.parentElement.onclick = () => setTimeout(syncBtnState, 0);

    document.getElementById('ethics-gate').classList.remove('hidden');
    return false;   // gate is now shown; resolved via acceptEthics()
  } catch(e) {
    // Network/server unreachable — fail SAFE by showing the gate, not by
    // letting the user bypass it. Better to deny on error than allow on error.
    document.getElementById('ethics-gate').classList.remove('hidden');
    return false;
  }
}

async function acceptEthics() {
  const cb = document.getElementById('ethics-gate-check');
  if (!cb || !cb.checked) return;
  try {
    await fetch('/api/ethics/agree', {method: 'POST'});
  } catch(e) {}
  document.getElementById('ethics-gate').classList.add('hidden');
  // After agreeing, run the post-gate sequence (onboarding or welcome-back)
  await runPostGateBoot();
}

window.acceptEthics = acceptEthics;


// ════════════════════════════════════════════════════════════════════════════
// ══ WELCOME-BACK CARD — returning users see this after ethics gate
// ════════════════════════════════════════════════════════════════════════════
// Tone calibration: friendly for beginners (skill_level 0-1), terse for
// advanced (2-3). Voice matches the user's wizard-declared skill level so
// onboarding nuance carries through the whole experience.

async function showWelcomeBack(profile) {
  if (!profile) return;
  const tone = (profile.skill_level || 0) <= 1 ? 'guided' : 'pro';

  // Determine the right "next action" for this user. We have to check the
  // ACTUAL mission state — profile.active_mission could be a leftover from
  // before mission_state cleared it on completion. Fetching /api/mission/state
  // gives us the authoritative truth.
  const continueBits = [];
  let missionState = null;
  try {
    const mr = await fetch('/api/mission/state');
    missionState = await mr.json();
  } catch(e) {}

  const hasActive = missionState && missionState.active_mission
                    && !missionState.is_complete;

  if (hasActive) {
    // Real in-progress mission — show Continue button
    continueBits.push(`<div style="margin-top:8px">
      <button onclick="document.getElementById('welcome-back').classList.add('hidden');
                       window.refreshMissionState && window.refreshMissionState()"
              style="background:#7b2fbe;border:none;color:#fff;padding:6px 12px;
                     border-radius:5px;font-family:'Share Tech Mono',monospace;
                     font-size:11px;font-weight:700;letter-spacing:0.08em;cursor:pointer">
        ▶ CONTINUE MISSION
      </button>
    </div>`);
  } else if (profile.next_lesson) {
    // No active mission — point to next unread lesson
    continueBits.push(`<div style="margin-top:8px">
      <button onclick="continueLessons();document.getElementById('welcome-back').classList.add('hidden')"
              style="background:#0d001a;border:1px solid #7b2fbe66;color:#e8d5ff;
                     padding:6px 12px;border-radius:5px;
                     font-family:'Share Tech Mono',monospace;font-size:11px;cursor:pointer">
        📚 NEXT LESSON: ${profile.next_lesson}
      </button>
    </div>`);
  }
  // If neither active mission nor next lesson, no button — user is done with
  // available guided content and the card stays as a pure greeting.

  const greeting = tone === 'guided'
    ? `Welcome back, <strong style="color:#a855f7">${profile.name}</strong>.`
    : `${profile.name}.`;

  const body = `
    <div>${greeting}</div>
    <div style="margin-top:6px;color:#888;font-size:11px">
      ${profile.skill_name} &nbsp;•&nbsp; Level ${profile.level} &nbsp;•&nbsp; ${profile.xp} XP
    </div>
    <div style="margin-top:6px;color:#666;font-size:10px">
      Missions: ${profile.missions_completed}
      &nbsp;•&nbsp;
      Lessons: ${profile.lessons_completed_count}/${profile.lessons_total}
      &nbsp;•&nbsp;
      Sessions: ${profile.sessions || 0}
    </div>
    ${continueBits.join('')}
  `;
  document.getElementById('welcome-back-content').innerHTML = body;
  document.getElementById('welcome-back').classList.remove('hidden');

  // Auto-dismiss after 15s if the user doesn't interact
  setTimeout(() => {
    document.getElementById('welcome-back').classList.add('hidden');
  }, 15000);
}

// ── Post-gate boot orchestrator ─────────────────────────────────────────────
// Called once the ethics gate passes. Decides between:
//   - First-time user → fire onboarding wizard
//   - Returning user → show welcome-back card + refresh mission state
async function runPostGateBoot() {
  try {
    // Check onboarding (will fire the wizard if first_run)
    await checkOnboarding();
    // Refresh mission state (will render Mission Coach if active)
    if (window.refreshMissionState) await window.refreshMissionState();
    // Show welcome-back card for returning users
    const r = await fetch('/api/profile');
    const profile = await r.json();
    if (profile && profile.agreed_to_tos) {
      // Only show welcome-back if user has previously onboarded
      showWelcomeBack(profile);
    }
  } catch(e) {
    console.error('Post-gate boot failed:', e);
  }
}

window.runPostGateBoot = runPostGateBoot;


// ════════════════════════════════════════════════════════════════════════════
// ══ OPERATOR PROFILE PANEL — populates the new sections of the skill panel
// ════════════════════════════════════════════════════════════════════════════

async function loadOperatorProfileSection() {
  try {
    const r = await fetch('/api/profile');
    const p = await r.json();
    if (p.error) return;
    window._opProfile = p;   // cache for other functions

    // ── OPERATOR stats ───────────────────────────────────────────────────
    const stats = document.getElementById('sp-profile-stats');
    if (stats) {
      stats.innerHTML = `
        <div><strong style="color:#a855f7">${p.name}</strong></div>
        <div style="color:#888;font-size:10px;margin-top:2px">${p.skill_name}</div>
        <div style="margin-top:8px;display:flex;justify-content:space-between;font-size:10px;color:#888">
          <span>Missions:</span><span style="color:#22d3ee">${p.missions_completed}</span>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:10px;color:#888">
          <span>Sessions:</span><span style="color:#22d3ee">${p.sessions || 0}</span>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:10px;color:#888">
          <span>Achievements:</span><span style="color:#22d3ee">${(p.achievements || []).length}</span>
        </div>
      `;
    }

    // ── MODES toggles ────────────────────────────────────────────────────
    const tog = document.getElementById('sp-toggles');
    if (tog) {
      tog.innerHTML = _renderToggle('teach_mode',     p.teach_mode,     '🎓 Teach Mode',         'Explain every tool as it runs')
                    + _renderToggle('auto_coach',     p.auto_coach,     '🤝 Auto-Coach',         'Proactive tips during scans')
                    + _renderToggle('mentor_context', p.mentor_context, '👁️ Mentor Context',     'Lessons reference your current engagement');
    }

    // ── LESSON badge on Continue Lessons button ──────────────────────────
    const badge = document.getElementById('sp-lesson-badge');
    if (badge) {
      badge.textContent = `${p.lessons_completed_count}/${p.lessons_total}`;
    }

    // ── Show/hide Restart Mission button based on whether one is active ──
    const restartBtn = document.getElementById('sp-act-restart-mission');
    if (restartBtn) {
      restartBtn.style.display = p.active_mission ? 'block' : 'none';
    }
  } catch(e) {
    console.error('loadOperatorProfileSection:', e);
  }
}

// Helper — renders a styled toggle row
function _renderToggle(key, value, label, sublabel) {
  return `
    <label style="display:flex;align-items:center;gap:8px;cursor:pointer;
                  padding:6px 8px;border:1px solid #7b2fbe33;border-radius:5px;
                  background:#0d001a">
      <input type="checkbox" ${value ? 'checked' : ''}
             onchange="setProfileToggle('${key}', this.checked)"
             style="accent-color:#7b2fbe;cursor:pointer">
      <div style="flex:1">
        <div style="font-size:11px;color:#e8d5ff">${label}</div>
        <div style="font-size:9px;color:#666">${sublabel}</div>
      </div>
    </label>
  `;
}

async function setProfileToggle(key, value) {
  try {
    await fetch('/api/profile/toggle', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({key: key, value: !!value}),
    });
    // No re-fetch needed — the checkbox state IS the new state. But we DO
    // want to sync the in-memory teachMode var if that's what toggled, so
    // commands sent through the terminal use the new value.
    if (key === 'teach_mode' && typeof teachMode !== 'undefined') {
      window.teachMode = !!value;
    }
  } catch(e) {
    console.error('toggle failed:', e);
  }
}

window.setProfileToggle = setProfileToggle;
window.loadOperatorProfileSection = loadOperatorProfileSection;


// ════════════════════════════════════════════════════════════════════════════
// ══ ACTION BUTTON HANDLERS — Continue Lessons / Restart Mission / Reset
// ════════════════════════════════════════════════════════════════════════════

// Continue Lessons: opens the next unread topic via the existing teach
// command path. Marks the topic as "started" so the next press picks the
// one after that.
async function continueLessons() {
  try {
    const r = await fetch('/api/lessons/state');
    const ls = await r.json();
    const topic = ls.next_unread;
    if (!topic) {
      // All lessons done — celebrate
      if (typeof addIntel === 'function') {
        addIntel('🎓 LESSONS', 'All 23 topics complete. You\'re a verified ERR0RS scholar.', 'win');
      }
      return;
    }
    // Mark as started so next press picks a different topic
    await fetch('/api/lessons/mark', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({topic: topic, status: 'started'}),
    });
    // Refresh the badge in the skill panel
    await loadOperatorProfileSection();

    // ── Send the teach command via the operator chat path ────────────────
    // Earlier version called sendToLive() which doesn't exist anywhere —
    // both buttons (skill panel + welcome-back card) fired but the lesson
    // never appeared. sendToOperator(msg) is the actual public function
    // at index.html:2459: it opens the Live Term panel and POSTs to
    // /api/operator/receive, which routes 'teach <topic>' to teach_engine.
    if (typeof window.sendToOperator === 'function') {
      window.sendToOperator(`teach ${topic}`);
    } else {
      // Fallback: hit the API directly so the lesson still loads even if
      // the chat UI helper isn't available (e.g. embedded mode).
      await fetch('/api/operator/receive', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({msg: `teach ${topic}`}),
      });
      // And try to open the Live Term so the user actually SEES the lesson
      if (typeof window.openLiveTerm === 'function') window.openLiveTerm();
    }
  } catch(e) {
    console.error('continueLessons:', e);
  }
}

// Restart Active Mission: resets to step 0 of whichever mission is active.
async function restartActiveMission() {
  if (!window._opProfile || !window._opProfile.active_mission) return;
  if (!confirm('Restart the current mission from step 1? (Your XP from completed steps stays.)')) return;
  try {
    const missionId = window._opProfile.active_mission;
    await fetch('/api/mission/start', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({mission_id: missionId}),
    });
    if (window.refreshMissionState) await window.refreshMissionState();
    await loadOperatorProfileSection();
  } catch(e) {
    console.error('restartActiveMission:', e);
  }
}

// ── Reset Profile — two-click confirmation flow ─────────────────────────────
// First click: button swaps to red "ARE YOU SURE?" with a 5-second timeout
// that reverts if the user doesn't click again. Second click: actually fires.
let _resetConfirmTimeout = null;

function confirmResetProfile() {
  const btn = document.getElementById('sp-act-reset-profile');
  if (!btn) return;

  if (btn.dataset.armed === '1') {
    // Second click — execute the reset
    doResetProfile();
    return;
  }

  // First click — arm the button
  btn.dataset.armed = '1';
  btn.style.background = '#330000';
  btn.style.borderColor = '#ff3366';
  btn.style.color = '#ff3366';
  btn.innerHTML = '⚠️ ARE YOU SURE? Click again to wipe (backup saved)';

  // Auto-disarm after 5 seconds
  _resetConfirmTimeout = setTimeout(() => {
    btn.dataset.armed = '';
    btn.style.background = '#0d001a';
    btn.style.borderColor = '#ff336699';
    btn.style.color = '#ffaaaa';
    btn.innerHTML = '⚠️ Reset Profile';
  }, 5000);
}

async function doResetProfile() {
  if (_resetConfirmTimeout) clearTimeout(_resetConfirmTimeout);
  try {
    const r = await fetch('/api/profile/reset', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({confirm: true}),
    });
    const d = await r.json();
    if (d.success) {
      // Brief confirmation, then reload the page so the user re-onboards
      alert(`Profile reset.\n\nBackup saved to:\n${d.backup_path}\n\nThe page will reload to start fresh.`);
      location.reload();
    } else {
      alert('Reset failed: ' + (d.error || 'unknown error'));
    }
  } catch(e) {
    alert('Reset request failed: ' + e.message);
  }
}

window.continueLessons      = continueLessons;
window.restartActiveMission = restartActiveMission;
window.confirmResetProfile  = confirmResetProfile;
window.doResetProfile       = doResetProfile;
