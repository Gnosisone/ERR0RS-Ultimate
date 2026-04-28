#!/usr/bin/env python3
"""
Build ERR0RS-Ultimate User Manual as a proper HTML document.
Styled with Kali/terminal aesthetics — dark theme, monospace, purple accents.
Readable in any browser on Kali. Can be opened with: xdg-open docs/USER_MANUAL.html
"""

MANUAL_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ERR0RS-Ultimate — User Manual v3.4.0</title>
<style>
  :root {
    --purple:      #7b2fbe;
    --purple-dark: #4c1d95;
    --purple-lo:   #c084fc;
    --cyan:        #22d3ee;
    --green:       #22c55e;
    --red:         #ef4444;
    --orange:      #f59e0b;
    --bg:          #0a0012;
    --bg2:         #0d001a;
    --bg3:         #120020;
    --text:        #e2d9f3;
    --text-dim:    #9ca3af;
    --border:      rgba(123,47,190,0.3);
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
    font-size: 14px;
    line-height: 1.7;
  }

  /* ── SIDEBAR NAV ─────────────────────────────────────────── */
  #sidebar {
    position: fixed;
    top: 0; left: 0;
    width: 260px;
    height: 100vh;
    background: var(--bg2);
    border-right: 1px solid var(--border);
    overflow-y: auto;
    padding: 16px 0;
    z-index: 100;
  }
  #sidebar .logo {
    padding: 12px 16px 20px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 12px;
  }
  #sidebar .logo .name {
    font-size: 18px;
    font-weight: 700;
    color: var(--purple-lo);
    letter-spacing: 0.05em;
  }
  #sidebar .logo .ver {
    font-size: 11px;
    color: var(--text-dim);
    margin-top: 2px;
  }
  #sidebar a {
    display: block;
    padding: 6px 16px;
    color: var(--text-dim);
    text-decoration: none;
    font-size: 12px;
    transition: all 0.15s;
    border-left: 2px solid transparent;
  }
  #sidebar a:hover, #sidebar a.active {
    color: var(--purple-lo);
    border-left-color: var(--purple);
    background: rgba(123,47,190,0.08);
    padding-left: 20px;
  }
  #sidebar .section-label {
    font-size: 9px;
    letter-spacing: 0.15em;
    color: var(--purple);
    padding: 10px 16px 2px;
    text-transform: uppercase;
    font-weight: 700;
  }

  /* ── MAIN CONTENT ────────────────────────────────────────── */
  #main {
    margin-left: 260px;
    padding: 40px 56px 80px;
    max-width: 1100px;
  }

  /* ── COVER ───────────────────────────────────────────────── */
  #cover {
    text-align: center;
    padding: 60px 0 80px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 60px;
  }
  #cover .ascii {
    font-size: 13px;
    color: var(--purple);
    line-height: 1.2;
    margin-bottom: 24px;
    white-space: pre;
    display: inline-block;
  }
  #cover h1 {
    font-size: 32px;
    color: var(--purple-lo);
    letter-spacing: 0.1em;
    margin-bottom: 8px;
  }
  #cover .subtitle {
    font-size: 14px;
    color: var(--text-dim);
    margin-bottom: 24px;
  }
  #cover .banner {
    display: inline-block;
    background: var(--purple-dark);
    color: #fff;
    padding: 10px 28px;
    font-size: 13px;
    border-radius: 4px;
    margin-bottom: 20px;
  }
  #cover .meta { font-size: 12px; color: var(--text-dim); }

  /* ── HEADINGS ────────────────────────────────────────────── */
  h1.section {
    font-size: 24px;
    color: var(--purple-lo);
    border-bottom: 2px solid var(--purple);
    padding-bottom: 10px;
    margin: 60px 0 24px;
    scroll-margin-top: 20px;
  }
  h2 {
    font-size: 17px;
    color: var(--cyan);
    margin: 32px 0 12px;
    scroll-margin-top: 20px;
  }
  h3 {
    font-size: 14px;
    color: var(--purple-lo);
    margin: 20px 0 8px;
  }

  /* ── PARAGRAPHS / TEXT ───────────────────────────────────── */
  p { margin: 8px 0 14px; color: var(--text); }
  .warn {
    border-left: 3px solid var(--red);
    background: rgba(239,68,68,0.08);
    padding: 10px 14px;
    margin: 14px 0;
    border-radius: 0 4px 4px 0;
    font-size: 13px;
    color: #fca5a5;
  }
  .note {
    border-left: 3px solid var(--purple);
    background: rgba(123,47,190,0.1);
    padding: 10px 14px;
    margin: 14px 0;
    border-radius: 0 4px 4px 0;
    font-size: 13px;
  }
  .tip {
    border-left: 3px solid var(--green);
    background: rgba(34,197,94,0.08);
    padding: 10px 14px;
    margin: 14px 0;
    border-radius: 0 4px 4px 0;
    font-size: 13px;
    color: #86efac;
  }

  /* ── CODE BLOCKS ─────────────────────────────────────────── */
  pre, code {
    font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
  }
  pre {
    background: var(--bg3);
    border: 1px solid var(--border);
    border-left: 3px solid var(--purple);
    padding: 12px 16px;
    margin: 10px 0;
    border-radius: 0 6px 6px 0;
    overflow-x: auto;
    font-size: 13px;
    color: var(--cyan);
    line-height: 1.5;
  }
  code {
    background: rgba(123,47,190,0.15);
    color: var(--purple-lo);
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 13px;
  }
  pre code {
    background: none;
    padding: 0;
    color: var(--cyan);
  }

  /* ── TABLES ──────────────────────────────────────────────── */
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0 24px;
    font-size: 13px;
  }
  th {
    background: var(--purple-dark);
    color: #fff;
    padding: 8px 12px;
    text-align: left;
    font-weight: 700;
    letter-spacing: 0.05em;
    font-size: 11px;
    text-transform: uppercase;
  }
  td {
    padding: 7px 12px;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
  }
  tr:nth-child(even) td { background: rgba(123,47,190,0.05); }
  tr:hover td { background: rgba(123,47,190,0.12); }
  td:first-child { color: var(--cyan); font-family: 'JetBrains Mono','Fira Code',monospace; }
  th:first-child { border-radius: 4px 0 0 0; }
  th:last-child  { border-radius: 0 4px 0 0; }

  /* ── BULLETS ─────────────────────────────────────────────── */
  ul { list-style: none; padding-left: 0; margin: 8px 0; }
  ul li { padding: 3px 0 3px 20px; position: relative; }
  ul li::before { content: '→'; color: var(--purple); position: absolute; left: 0; }
  ul li b { color: var(--purple-lo); }

  /* ── LEVEL BADGES ────────────────────────────────────────── */
  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 700;
  }
  .crit { background: rgba(239,68,68,0.2);  color: #fca5a5; }
  .high { background: rgba(245,158,11,0.2); color: #fcd34d; }
  .med  { background: rgba(192,132,252,0.2);color: #c084fc; }
  .info { background: rgba(107,114,128,0.2);color: #9ca3af; }

  /* ── SEARCH BAR ──────────────────────────────────────────── */
  #search-wrap {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 8px;
  }
  #search {
    width: 100%;
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 6px 10px;
    color: var(--text);
    font-family: inherit;
    font-size: 12px;
  }
  #search:focus { outline: none; border-color: var(--purple); }
  #search::placeholder { color: var(--text-dim); }

  /* ── SCROLLBAR ───────────────────────────────────────────── */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: var(--bg2); }
  ::-webkit-scrollbar-thumb { background: var(--purple); border-radius: 3px; }

  /* ── PRINT ───────────────────────────────────────────────── */
  @media print {
    #sidebar { display: none; }
    #main { margin-left: 0; }
  }
</style>
</head>
<body>

<!-- ══ SIDEBAR ══════════════════════════════════════════════════════════ -->
<nav id="sidebar">
  <div class="logo">
    <div class="name">ERR0RS-ULTIMATE</div>
    <div class="ver">User Manual v3.4.0  ·  April 2026</div>
  </div>
  <div id="search-wrap">
    <input id="search" type="text" placeholder="Search manual..." oninput="searchManual(this.value)">
  </div>

  <div class="section-label">Getting Started</div>
  <a href="#what">1. What Is ERR0RS?</a>
  <a href="#install">2. Installation</a>
  <a href="#firstrun">3. First Run</a>
  <a href="#ui">4. UI Layout</a>

  <div class="section-label">Core Features</div>
  <a href="#ai">5. AI Conversation</a>
  <a href="#commands">6. Command Reference</a>
  <a href="#coach">7. Auto Coach</a>
  <a href="#agent">8. Autonomous Agent</a>
  <a href="#threat">9. Threat Detection</a>
  <a href="#recon">10. Autonomous Recon</a>

  <div class="section-label">Education</div>
  <a href="#teach">11. Teach Engine</a>
  <a href="#zeroday">12. Zero-Day Training</a>
  <a href="#progression">13. Progression System</a>

  <div class="section-label">Platform</div>
  <a href="#hardware">14. Hardware</a>
  <a href="#api">15. API Reference</a>
  <a href="#modules">16. Module Map</a>
  <a href="#pi5">17. Pi 5 Cyberdeck</a>
  <a href="#troubleshoot">18. Troubleshooting</a>
  <a href="#quickref">19. Quick Reference</a>
  <a href="#ethics">20. Ethics & Legal</a>
  <a href="#citation">21. Citation</a>
</nav>

<!-- ══ MAIN ═════════════════════════════════════════════════════════════ -->
<main id="main">

<!-- COVER -->
<div id="cover">
<pre class="ascii">  ███████╗██████╗ ██████╗  ██████╗ ██████╗ ███████╗
  ██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗██╔════╝
  █████╗  ██████╔╝██████╔╝██║   ██║██████╔╝███████╗
  ██╔══╝  ██╔══██╗██╔══██╗██║   ██║██╔══██╗╚════██║
  ███████╗██║  ██║██║  ██║╚██████╔╝██║  ██║███████║
  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝</pre>
<h1>USER MANUAL</h1>
<p class="subtitle">Version 3.4.0  ·  April 2026  ·  Gary Holden Schneider (Eros)</p>
<div class="banner">100% Local · Zero Cloud · Open Source · 27 Modules · 28/28 Tests Passing</div>
<p class="meta">github.com/Gnosisone/ERR0RS-Ultimate  ·  MIT License</p>
</div>

<!-- ═══════════════════════════════════════════════════════════════════════
     1. WHAT IS ERR0RS
═══════════════════════════════════════════════════════════════════════ -->
<h1 class="section" id="what">1. What Is ERR0RS-Ultimate?</h1>
<p>ERR0RS-Ultimate is a fully local, AI-powered security platform that wraps 27 security modules in a conversational interface. It teaches offensive and defensive techniques inline, coaches operators through engagements, runs tools autonomously, and generates professional reports — without sending a single byte to the cloud.</p>
<p>Built for two audiences simultaneously: the security student who has never run a pentest and the professional operator who needs a faster, smarter workflow. Every tool run is explained. Every finding is analyzed. Every attack technique is paired with its defensive countermeasure.</p>

<h2>Core Design Principles</h2>
<ul>
  <li><b>Zero cloud dependency</b> — all LLM inference runs locally via Ollama. No API keys. No external calls.</li>
  <li><b>Offline first</b> — teach engine, auto-coach, agent, and threat detection all work without internet.</li>
  <li><b>Purple team</b> — every offensive technique paired with its MITRE ATT&amp;CK mapping and defensive countermeasure.</li>
  <li><b>Teach by default</b> — no command runs without an explanation of what it does and why it works.</li>
  <li><b>Progressive</b> — XP system tracks skill growth across 6 levels and 8 security domains.</li>
</ul>

<!-- ═══════════════════════════════════════════════════════════════════════
     2. INSTALLATION
═══════════════════════════════════════════════════════════════════════ -->
<h1 class="section" id="install">2. Installation</h1>

<h2>System Requirements</h2>
<table>
  <tr><th>Requirement</th><th>Notes</th></tr>
  <tr><td>Kali Linux / Parrot / Ubuntu</td><td>x86_64 or ARM64. Kali recommended — all security tools pre-installed.</td></tr>
  <tr><td>Python 3.10+</td><td>Check: <code>python3 --version</code></td></tr>
  <tr><td>git</td><td><code>sudo apt install git</code></td></tr>
  <tr><td>Ollama</td><td>Installed automatically by <code>install.sh</code></td></tr>
  <tr><td>4 GB free disk</td><td>For llama3.2:3b (2.0 GB) + Python dependencies</td></tr>
  <tr><td>Node 20–22 (optional)</td><td>Required for OWASP Juice Shop lab target only</td></tr>
</table>

<h2>Standard Install (Kali / Parrot)</h2>
<pre>git clone https://github.com/Gnosisone/ERR0RS-Ultimate.git
cd ERR0RS-Ultimate
sudo bash install.sh
bash start_err0rs.sh</pre>

<div class="warn">⚠ Do NOT run <code>cp configs/config.template.env .env</code> after install.sh — it overwrites the auto-generated secret key. The installer creates .env automatically.</div>

<h2>Full Lab (Juice Shop + Ollama + ERR0RS)</h2>
<pre>bash scripts/start_lab.sh</pre>
<p>Starts everything: Ollama, OWASP Juice Shop, wordlist extraction, then ERR0RS.</p>

<h2>Raspberry Pi 5</h2>
<pre>sudo bash scripts/pi5_first_boot.sh
sudo bash scripts/install_hailo_h10.sh   # If you have the AI HAT+
sudo bash install.sh</pre>

<h2>Access Points</h2>
<table>
  <tr><th>Service</th><th>URL</th></tr>
  <tr><td>Web UI</td><td><code>http://127.0.0.1:8765</code></td></tr>
  <tr><td>WebSocket</td><td><code>ws://127.0.0.1:8766</code></td></tr>
  <tr><td>REST API</td><td><code>http://127.0.0.1:8765/api/</code></td></tr>
</table>

<!-- ═══════════════════════════════════════════════════════════════════════
     3. FIRST RUN
═══════════════════════════════════════════════════════════════════════ -->
<h1 class="section" id="firstrun">3. First Run — Onboarding Wizard</h1>
<p>On first launch, ERR0RS presents a 4-screen guided wizard:</p>
<table>
  <tr><th>Screen</th><th>Title</th><th>What Happens</th></tr>
  <tr><td>1</td><td>Welcome</td><td>Introduction to ERR0RS philosophy and capabilities</td></tr>
  <tr><td>2</td><td>Ethics Agreement</td><td>Required agreement — must accept before accessing tools</td></tr>
  <tr><td>3</td><td>Skill Assessment</td><td>Sets GUIDED / STANDARD / EXPERT mode automatically</td></tr>
  <tr><td>4</td><td>First Mission</td><td>Guided nmap → nikto → gobuster walkthrough on Juice Shop</td></tr>
</table>

<h2>Mode Toggle</h2>
<p>Click the mode badge in the terminal header to switch at any time:</p>
<ul>
  <li><b>🔰 GUIDED</b> — rotating example placeholders, teach mode on, mission coach visible, coaching on every output</li>
  <li><b>⚡ EXPERT</b> — clean interface, coaching available on demand, full command access</li>
</ul>

<!-- ═══════════════════════════════════════════════════════════════════════
     4. UI LAYOUT
═══════════════════════════════════════════════════════════════════════ -->
<h1 class="section" id="ui">4. Web UI Layout</h1>
<table>
  <tr><th>Pane</th><th>Location</th><th>Contents</th></tr>
  <tr><td>Pentest Phases</td><td>Top-left sidebar</td><td>Kill chain tracker, engagement timeline, intel feed</td></tr>
  <tr><td>Live Terminal</td><td>Center main</td><td>Interactive terminal, streaming output, coaching blocks</td></tr>
  <tr><td>Intel Feed</td><td>Right sidebar</td><td>Real-time findings, MITRE ATT&amp;CK mappings, auto-coach</td></tr>
  <tr><td>Tool Grid</td><td>Bottom scrollbar</td><td>65+ tool cards — click to open panel, right-click for options</td></tr>
  <tr><td>Skill Panel</td><td>Right edge (XP badge)</td><td>XP bar, level badge, 8 domain skill bars, stats</td></tr>
  <tr><td>Agent Panel</td><td>Left edge (🤖 button)</td><td>Autonomous agent launcher, goal selector, live status</td></tr>
</table>
<div class="tip">💡 Add <code>--teach</code> to any tool command for inline educational output: <code>nmap -sV 10.0.0.1 --teach</code></div>

<!-- ═══════════════════════════════════════════════════════════════════════
     5. AI CONVERSATION ENGINE
═══════════════════════════════════════════════════════════════════════ -->
<h1 class="section" id="ai">5. AI Conversation Engine</h1>
<p>Type any question in plain English. ERR0RS detects conversational messages and routes them to the local LLM (llama3.2:3b via Ollama). Responses stream token-by-token in a purple chat bubble.</p>

<h2>Example Queries</h2>
<table>
  <tr><th>Query</th><th>Response</th></tr>
  <tr><td>explain sql injection</td><td>Full breakdown: mechanism, example, attack chain, fix</td></tr>
  <tr><td>walk me through kerberoasting</td><td>Step-by-step with exact commands</td></tr>
  <tr><td>what is CIS Control 6</td><td>All safeguards, implementation groups, examples</td></tr>
  <tr><td>how do I read nmap output</td><td>Line-by-line output interpretation guide</td></tr>
  <tr><td>what is MITRE ATT&amp;CK</td><td>All 14 tactics mapped</td></tr>
  <tr><td>difference between SSRF and CSRF</td><td>Side-by-side comparison with examples</td></tr>
  <tr><td>what should I do after finding port 445</td><td>Contextual next steps for SMB discovery</td></tr>
  <tr><td>coach me through this SQLi</td><td>Personalized step-by-step exploitation coaching</td></tr>
  <tr><td>what tools for AD enumeration</td><td>Recommended stack with rationale</td></tr>
  <tr><td>explain OWASP A03</td><td>Injection category — patterns and mitigations</td></tr>
</table>

<h2>Key Behaviors</h2>
<ul>
  <li><b>Streaming</b> — tokens appear as generated, not after a 20-second wait</li>
  <li><b>Context-aware</b> — knows your active target and recent findings</li>
  <li><b>20-turn memory</b> — maintains conversation history for multi-step coaching</li>
  <li><b>Clickable commands</b> — click any command in a response to paste it into the terminal</li>
  <li><b>Cold start</b> — first response ~15-20s (model loading). Subsequent: 2-3s to first token</li>
</ul>

<!-- ═══════════════════════════════════════════════════════════════════════
     6. COMMAND REFERENCE
═══════════════════════════════════════════════════════════════════════ -->
<h1 class="section" id="commands">6. Command Reference</h1>

<h2>Target & Status</h2>
<table>
  <tr><th>Command</th><th>Description</th></tr>
  <tr><td>target 192.168.1.100</td><td>Set active target IP</td></tr>
  <tr><td>target http://app.local</td><td>Set active web target</td></tr>
  <tr><td>status</td><td>Show current target, mode, findings summary</td></tr>
</table>

<h2>Autonomous Recon Engine</h2>
<table>
  <tr><th>Command</th><th>Description</th></tr>
  <tr><td>recon 192.168.1.100</td><td>Full auto-chain: passive → active → web → vuln → correlate</td></tr>
  <tr><td>recon 192.168.1.100 passive</td><td>DNS, cert transparency, WHOIS only</td></tr>
  <tr><td>recon 192.168.1.100 active</td><td>Passive + nmap port scan + banner grab + SMB scripts</td></tr>
  <tr><td>recon http://target.com web</td><td>Passive + active + WhatWeb + gobuster</td></tr>
  <tr><td>stop recon</td><td>Stop the running recon engine</td></tr>
</table>

<h2>Autonomous Agent (ReAct Loop)</h2>
<table>
  <tr><th>Command</th><th>Description</th></tr>
  <tr><td>agent 192.168.1.100</td><td>Full kill chain: recon → enum → vuln → exploit → report (20 steps)</td></tr>
  <tr><td>agent http://target.com web</td><td>Web app assessment (12 steps)</td></tr>
  <tr><td>agent 192.168.1.100 network</td><td>Network pentest (12 steps)</td></tr>
  <tr><td>agent 192.168.1.100 quick</td><td>Fast surface scan (6 steps)</td></tr>
  <tr><td>agent 192.168.1.100 stealth</td><td>Low-noise recon (8 steps)</td></tr>
  <tr><td>agent 192.168.1.100 ad</td><td>Active Directory — path to Domain Admin (10 steps)</td></tr>
  <tr><td>stop agent</td><td>Stop running agent</td></tr>
  <tr><td>agent status</td><td>Show state, findings, ports, vulns</td></tr>
</table>

<h2>AI Threat Detection</h2>
<table>
  <tr><th>Command</th><th>Description</th></tr>
  <tr><td>threat monitor</td><td>Start continuous monitoring (30s poll, 8 signatures, MITRE mapped)</td></tr>
  <tr><td>threat scan</td><td>Single scan now — show all current alerts</td></tr>
  <tr><td>stop threats</td><td>Stop monitoring</td></tr>
</table>

<h2>Tool Execution</h2>
<table>
  <tr><th>Command</th><th>Description</th></tr>
  <tr><td>nmap -sV 10.0.0.1</td><td>Port scan with version detection</td></tr>
  <tr><td>nmap --teach 10.0.0.1</td><td>Nmap with inline educational coaching</td></tr>
  <tr><td>nikto -h http://target.com</td><td>Web vulnerability scan (6,700+ checks)</td></tr>
  <tr><td>gobuster dir -u http://target -w /wordlist</td><td>Directory enumeration</td></tr>
  <tr><td>sqlmap -u "http://t/?q=1" --dbs</td><td>SQL injection scan and database enumeration</td></tr>
  <tr><td>hydra -l admin -P rockyou.txt ssh://target</td><td>SSH credential brute force</td></tr>
  <tr><td>nuclei -u http://target -t http/</td><td>Template-based vulnerability scan</td></tr>
  <tr><td>$ &lt;any shell command&gt;</td><td>Raw shell — $ prefix bypasses intent parser</td></tr>
  <tr><td>Ctrl+C (or button)</td><td>Stop running tool</td></tr>
</table>

<h2>Zero-Day Training</h2>
<table>
  <tr><th>Command</th><th>Description</th></tr>
  <tr><td>zeroday topics</td><td>List all 6 curriculum topics</td></tr>
  <tr><td>zeroday overview</td><td>What is 0day research? Mindset, categories, process</td></tr>
  <tr><td>zeroday teach fuzzing</td><td>AFL++ coverage-guided fuzzing — find crashes automatically</td></tr>
  <tr><td>zeroday binary_analysis</td><td>Ghidra static + GDB/pwndbg dynamic analysis</td></tr>
  <tr><td>zeroday source_audit</td><td>Systematic code auditing — data flow tracing, grep patterns</td></tr>
  <tr><td>zeroday exploit_dev</td><td>Stack overflows, ROP chains, pwntools cheatsheet</td></tr>
  <tr><td>zeroday cve_workflow</td><td>Responsible disclosure, CVE assignment, bug bounties</td></tr>
  <tr><td>zeroday tools</td><td>Check which research tools are installed</td></tr>
</table>

<h2>Hardware</h2>
<table>
  <tr><th>Command</th><th>Description</th></tr>
  <tr><td>flipper status</td><td>Connection check, firmware version, battery</td></tr>
  <tr><td>flipper evolve</td><td>XP evolution sequence (requires connection)</td></tr>
  <tr><td>flipper badusb &lt;name&gt;</td><td>Deploy BadUSB payload from library</td></tr>
  <tr><td>flipper rf scan</td><td>Sub-GHz spectrum scan</td></tr>
  <tr><td>flipper nfc scan</td><td>NFC/RFID card read</td></tr>
  <tr><td>wifi scan</td><td>Wireless discovery (requires monitor mode adapter)</td></tr>
  <tr><td>wifi deauth &lt;bssid&gt;</td><td>Deauthentication (authorized testing only)</td></tr>
  <tr><td>wifi crack &lt;capture&gt;</td><td>WPA2 handshake crack with rockyou</td></tr>
</table>

<h2>Reporting & Operations</h2>
<table>
  <tr><th>Command</th><th>Description</th></tr>
  <tr><td>report</td><td>Generate professional HTML penetration test report</td></tr>
  <tr><td>debrief</td><td>Engagement debrief summary to terminal</td></tr>
  <tr><td>killchain &lt;target&gt;</td><td>Automated 6-phase kill chain execution</td></tr>
  <tr><td>opsec check</td><td>OPSEC audit of current system</td></tr>
  <tr><td>campaign new &lt;name&gt;</td><td>Create new engagement campaign</td></tr>
  <tr><td>privesc linux &lt;target&gt;</td><td>Linux privilege escalation suggestions</td></tr>
  <tr><td>lateral smb &lt;target&gt;</td><td>SMB lateral movement</td></tr>
</table>

<!-- ═══════════════════════════════════════════════════════════════════════
     7. AUTO COACH
═══════════════════════════════════════════════════════════════════════ -->
<h1 class="section" id="coach">7. Auto Coach Engine</h1>
<p>After every tool completes, ERR0RS automatically analyzes output and fires a coaching block — 100% offline, no LLM needed. Deterministic rules cover 15+ tools and 20+ finding patterns. Each coaching block includes: severity icon, plain-English explanation, clickable next-step commands, and a defensive countermeasure.</p>

<table>
  <tr><th>Finding</th><th>Severity</th><th>Response Provided</th></tr>
  <tr><td>445/tcp open (SMB)</td><td><span class="badge crit">CRITICAL</span></td><td>EternalBlue check, enum4linux, NTLM relay options</td></tr>
  <tr><td>3389/tcp open (RDP)</td><td><span class="badge high">HIGH</span></td><td>BlueKeep check, credential spray, NLA status</td></tr>
  <tr><td>21/tcp open (FTP)</td><td><span class="badge high">HIGH</span></td><td>Anonymous access test, version CVEs</td></tr>
  <tr><td>6379/tcp open (Redis)</td><td><span class="badge crit">CRITICAL</span></td><td>Unauthenticated access, key dump, SSH key write</td></tr>
  <tr><td>VULNERABLE in NSE output</td><td><span class="badge crit">CRITICAL</span></td><td>CVE lookup, Metasploit search, exploit path</td></tr>
  <tr><td>Missing security headers</td><td><span class="badge med">MEDIUM</span></td><td>Clickjacking risk, header fix commands</td></tr>
  <tr><td>Admin panel found</td><td><span class="badge high">HIGH</span></td><td>Default credential testing, brute force options</td></tr>
  <tr><td>.git or .env exposed</td><td><span class="badge crit">CRITICAL</span></td><td>Source/secret extraction commands</td></tr>
  <tr><td>SQLi confirmed (sqlmap)</td><td><span class="badge crit">CRITICAL</span></td><td>DB dump commands, OS shell escalation path</td></tr>
  <tr><td>Creds cracked (hydra)</td><td><span class="badge crit">CRITICAL</span></td><td>Cross-service testing, CME, evil-winrm</td></tr>
  <tr><td>CRITICAL/HIGH (nuclei)</td><td><span class="badge crit">CRITICAL</span></td><td>Template name, CVE reference, manual verification</td></tr>
</table>

<!-- ═══════════════════════════════════════════════════════════════════════
     8. AUTONOMOUS AGENT
═══════════════════════════════════════════════════════════════════════ -->
<h1 class="section" id="agent">8. Autonomous Pentest Agent</h1>
<p>A full ReAct (Reason-Act-Observe) autonomous agent that plans and executes multi-step penetration tests independently. Uses the LLM at low temperature (0.2) for tactical precision. Falls back to deterministic rules if LLM is slow.</p>

<h2>The Loop</h2>
<ul>
  <li><b>OBSERVE</b> — current state: open ports, services, vulnerabilities, credentials, phase</li>
  <li><b>REASON</b> — LLM picks next tool from 21 options with full engagement context</li>
  <li><b>ACT</b> — builds exact shell command, streams every output line live</li>
  <li><b>ANALYZE</b> — parses output into structured findings, updates agent state</li>
  <li><b>REPEAT</b> — until goal complete, max steps reached, or operator stops</li>
</ul>

<h2>Goals</h2>
<table>
  <tr><th>Goal</th><th>Max Steps</th><th>Description</th></tr>
  <tr><td>full_chain</td><td>20</td><td>Complete pentest: recon → enum → vuln scan → exploit → post-exploit → report</td></tr>
  <tr><td>web</td><td>12</td><td>Web app: tech fingerprint → dir enum → vuln scan → exploit attempt</td></tr>
  <tr><td>network</td><td>12</td><td>Network: port scan → service enum → vuln check → exploit attempt</td></tr>
  <tr><td>ad</td><td>10</td><td>Active Directory: AD recon → Kerberoast → BloodHound → escalate to DA</td></tr>
  <tr><td>stealth</td><td>8</td><td>Low-noise: passive recon → slow scan → minimal enumeration</td></tr>
  <tr><td>quick</td><td>6</td><td>Fast surface: quick port scan → web check → summary report</td></tr>
</table>

<h2>What the Agent Chains Automatically</h2>
<ul>
  <li>Finds port 80/443 → chains: <code>whatweb</code> → <code>nikto</code> → <code>gobuster</code> → <code>nuclei</code></li>
  <li>Finds port 445 → chains: <code>nmap smb-vuln-ms17-010</code> → <code>enum4linux</code> → <code>crackmapexec</code></li>
  <li>Finds SSH → <code>hydra</code> brute force with rockyou</li>
  <li>Finds credentials → tests against every other discovered service</li>
  <li>Finds EternalBlue → escalates immediately (highest severity first)</li>
  <li>After each tool → auto-coach fires and explains the findings</li>
  <li>At completion → generates full penetration test report</li>
</ul>

<!-- ═══════════════════════════════════════════════════════════════════════
     9. THREAT DETECTION
═══════════════════════════════════════════════════════════════════════ -->
<h1 class="section" id="threat">9. AI-Powered Threat Detection</h1>
<p>Continuous monitoring of system logs, running processes, and network connections. Each alert includes MITRE ATT&amp;CK mapping and a 3-step response playbook. Poll interval: 30 seconds.</p>

<table>
  <tr><th>Signature</th><th>Severity</th><th>MITRE Technique</th></tr>
  <tr><td>brute_force_ssh</td><td><span class="badge high">HIGH</span></td><td>T1110.001 — Brute Force: Password Guessing</td></tr>
  <tr><td>port_scan</td><td><span class="badge med">MEDIUM</span></td><td>T1046 — Network Service Discovery</td></tr>
  <tr><td>web_attack_sqli</td><td><span class="badge crit">CRITICAL</span></td><td>T1190 — Exploit Public-Facing Application</td></tr>
  <tr><td>web_attack_path_traversal</td><td><span class="badge high">HIGH</span></td><td>T1083 — File and Directory Discovery</td></tr>
  <tr><td>privilege_escalation</td><td><span class="badge crit">CRITICAL</span></td><td>T1548 — Abuse Elevation Control Mechanism</td></tr>
  <tr><td>malware_process</td><td><span class="badge crit">CRITICAL</span></td><td>T1059 — Command and Scripting Interpreter</td></tr>
  <tr><td>lateral_movement</td><td><span class="badge crit">CRITICAL</span></td><td>T1021 — Remote Services</td></tr>
  <tr><td>data_exfiltration</td><td><span class="badge crit">CRITICAL</span></td><td>T1048 — Exfiltration Over Alternative Protocol</td></tr>
</table>

<!-- ═══════════════════════════════════════════════════════════════════════
     10. AUTONOMOUS RECON
═══════════════════════════════════════════════════════════════════════ -->
<h1 class="section" id="recon">10. Autonomous Recon Engine</h1>
<p>Five chained recon phases that run automatically. Each phase feeds the next — findings from port scanning drive web enumeration, which drives vulnerability checking.</p>

<table>
  <tr><th>Phase</th><th>Tools Used</th><th>What It Collects</th></tr>
  <tr><td>PASSIVE</td><td>dig, curl (crt.sh), whois</td><td>DNS records (A/MX/TXT/NS), subdomains via cert transparency, WHOIS emails</td></tr>
  <tr><td>ACTIVE</td><td>nmap, socket banner grab</td><td>Open ports, service versions, OS hints, raw banners</td></tr>
  <tr><td>WEB</td><td>whatweb, gobuster</td><td>CMS/framework/version fingerprints, hidden directories, exposed files</td></tr>
  <tr><td>VULN</td><td>nmap vuln scripts</td><td>Confirmed CVEs, VULNERABLE state per port</td></tr>
  <tr><td>CORRELATE</td><td>(internal)</td><td>Attack surface map — which findings connect to which attack paths</td></tr>
</table>

<!-- ═══════════════════════════════════════════════════════════════════════
     11. TEACH ENGINE
═══════════════════════════════════════════════════════════════════════ -->
<h1 class="section" id="teach">11. Teach Engine (23 Topics)</h1>
<p>Type any of these to get a full lesson: flags reference, output reading guide, next steps, and cautions. Works 100% offline.</p>

<h2>Tool Lessons (15)</h2>
<table>
  <tr><th>Command</th><th>What You Get</th></tr>
  <tr><td>teach me nmap</td><td>All flags, output interpretation, next steps, common mistakes</td></tr>
  <tr><td>explain gobuster</td><td>Modes (dir/dns/vhost), wordlists, status code meaning</td></tr>
  <tr><td>what is sqlmap</td><td>Attack types, tamper scripts, escalation paths</td></tr>
  <tr><td>teach me hydra</td><td>50+ protocols, safe threading, lockout avoidance</td></tr>
  <tr><td>explain bloodhound</td><td>AD graph reading — what attack paths actually mean</td></tr>
  <tr><td>teach me metasploit</td><td>search → use → options → exploit → post workflow</td></tr>
  <tr><td>explain crackmapexec</td><td>SMB/WinRM/RDP — credential testing, pass-the-hash</td></tr>
  <tr><td>what is nuclei</td><td>Templates, severity, tags, reading output</td></tr>
  <tr><td>teach me hashcat</td><td>Attack modes (-a), rules, masks, GPU vs CPU</td></tr>
  <tr><td>explain responder</td><td>LLMNR poisoning, NTLMv2 capture, relay vs crack</td></tr>
  <tr><td>teach me linpeas</td><td>Color coding, what to escalate, SUID/sudo paths</td></tr>
  <tr><td>teach me netcat</td><td>Listeners, file transfer, pivoting, bind vs reverse</td></tr>
  <tr><td>what is ffuf</td><td>URL/param/header fuzzing, filtering noise</td></tr>
  <tr><td>explain enum4linux</td><td>SMB null session, users, shares, password policy</td></tr>
  <tr><td>explain whatweb</td><td>CMS/framework detection, version identification</td></tr>
</table>

<h2>Concept Lessons (8)</h2>
<table>
  <tr><th>Command</th><th>What You Get</th></tr>
  <tr><td>what is CIS</td><td>All 18 CIS Controls v8 with implementation groups (IG1/IG2/IG3)</td></tr>
  <tr><td>explain OWASP</td><td>OWASP Top 10 2021 — all 10 categories, attack + defense</td></tr>
  <tr><td>what is MITRE ATT&amp;CK</td><td>All 14 tactics, technique IDs, detections, mitigations</td></tr>
  <tr><td>explain kill chain</td><td>7-phase Cyber Kill Chain — attacker vs defender view</td></tr>
  <tr><td>what is CIA triad</td><td>Confidentiality, Integrity, Availability — foundation of security</td></tr>
  <tr><td>explain incident response</td><td>NIST IR phases: Prepare → Detect → Contain → Eradicate → Recover</td></tr>
  <tr><td>explain threat modeling</td><td>STRIDE: Spoofing, Tampering, Repudiation, Info Disclosure, DoS, EoP</td></tr>
</table>

<!-- ═══════════════════════════════════════════════════════════════════════
     12. ZERO-DAY TRAINING
═══════════════════════════════════════════════════════════════════════ -->
<h1 class="section" id="zeroday">12. Zero-Day Training Module</h1>
<p>A complete vulnerability research curriculum — from mindset to responsible disclosure.</p>

<table>
  <tr><th>Command</th><th>Level</th><th>Content</th></tr>
  <tr><td>zeroday overview</td><td>🔰 Beginner</td><td>What is 0day research? The process, categories, tools of the trade</td></tr>
  <tr><td>zeroday fuzzing</td><td>⚡ Intermediate</td><td>Dumb → mutation → coverage-guided. AFL++ full workflow. Reading crashes.</td></tr>
  <tr><td>zeroday binary_analysis</td><td>🔥 Advanced</td><td>Ghidra static analysis, GDB+pwndbg dynamic, memory protections and bypasses</td></tr>
  <tr><td>zeroday source_audit</td><td>⚡ Intermediate</td><td>Systematic auditing: entry points, data flow tracing, grep patterns by language</td></tr>
  <tr><td>zeroday exploit_dev</td><td>🔥 Advanced</td><td>Stack overflow mechanics, ROP chains, pwntools cheatsheet, ASLR/NX/PIE bypass</td></tr>
  <tr><td>zeroday cve_workflow</td><td>⚡ Intermediate</td><td>Full responsible disclosure: confirm → report → 90 days → publish → bug bounty</td></tr>
  <tr><td>zeroday tools</td><td>—</td><td>Check which research tools (AFL++, Ghidra, pwntools, etc.) are installed</td></tr>
</table>

<!-- ═══════════════════════════════════════════════════════════════════════
     13. PROGRESSION
═══════════════════════════════════════════════════════════════════════ -->
<h1 class="section" id="progression">13. Operator Progression System</h1>

<h2>Operator Levels</h2>
<table>
  <tr><th>Badge</th><th>Level</th><th>XP Required</th><th>Meaning</th></tr>
  <tr><td>🔰</td><td>SCRIPT KIDDIE</td><td>0</td><td>Guided mode recommended. Start with Mission 01.</td></tr>
  <tr><td>🎯</td><td>APPRENTICE</td><td>100</td><td>Basics learned. Time to go deeper.</td></tr>
  <tr><td>⚡</td><td>PRACTITIONER</td><td>500</td><td>Can run real engagements. Stay ethical.</td></tr>
  <tr><td>🔥</td><td>SPECIALIST</td><td>1,500</td><td>Domain mastered. The network respects you.</td></tr>
  <tr><td>💀</td><td>OPERATOR</td><td>4,000</td><td>Full red team capability. You ARE the threat model.</td></tr>
  <tr><td>👑</td><td>ELITE</td><td>10,000</td><td>You don't just use tools — you build them.</td></tr>
</table>

<h2>Skill Domains (8)</h2>
<table>
  <tr><th>Domain</th><th>XP Sources</th></tr>
  <tr><td>🌐 Web App Security</td><td>nikto, gobuster, sqlmap, nuclei, ffuf, Juice Shop challenges</td></tr>
  <tr><td>🔌 Network Attacks</td><td>nmap, hydra, responder, crackmapexec, netstat</td></tr>
  <tr><td>🏢 Active Directory</td><td>bloodhound, mimikatz, crackmapexec, impacket</td></tr>
  <tr><td>📡 Wireless Hacking</td><td>aircrack, wifite, evil twin, handshake capture</td></tr>
  <tr><td>🔧 Hardware / Physical</td><td>Flipper Zero actions, BadUSB payloads, RF attacks</td></tr>
  <tr><td>🔍 Digital Forensics</td><td>volatility, autopsy, memory analysis</td></tr>
  <tr><td>🎭 Social Engineering</td><td>phishing campaigns, pretexting exercises</td></tr>
  <tr><td>🛡️ Blue Team / Defense</td><td>threat monitoring alerts, hardening actions, IR</td></tr>
</table>

<h2>XP Awards (Selected)</h2>
<table>
  <tr><th>Action</th><th>XP</th><th>Action</th><th>XP</th></tr>
  <tr><td>Run nmap</td><td>+10</td><td>Found vulnerability</td><td>+50</td></tr>
  <tr><td>Run sqlmap</td><td>+25</td><td>Found CVE</td><td>+75</td></tr>
  <tr><td>Run metasploit</td><td>+30</td><td>Found credentials</td><td>+60</td></tr>
  <tr><td>Run bloodhound</td><td>+35</td><td>Got shell access</td><td>+100</td></tr>
  <tr><td>Ask a question</td><td>+5</td><td>Complete CTF</td><td>+150</td></tr>
  <tr><td>Complete lesson</td><td>+30</td><td>Daily login</td><td>+10</td></tr>
  <tr><td>Complete recon</td><td>+40</td><td>Juice Shop challenge</td><td>+25</td></tr>
</table>

<!-- ═══════════════════════════════════════════════════════════════════════
     14. HARDWARE
═══════════════════════════════════════════════════════════════════════ -->
<h1 class="section" id="hardware">14. Hardware Integration</h1>
<table>
  <tr><th>Device</th><th>Capabilities</th></tr>
  <tr><td>Flipper Zero</td><td>RF Sub-GHz, NFC/RFID, IR, BadUSB/DuckyScript, GPIO, BLE. Evolution Engine: 10-level XP system, auto-detect on boot.</td></tr>
  <tr><td>WiFi Pineapple Nano</td><td>PineAP engine, client capture, evil twin, recon modules.</td></tr>
  <tr><td>Alfa AWUS036ACM</td><td>Monitor mode, packet injection, 2.4/5 GHz dual-band, WPA2 handshake capture.</td></tr>
  <tr><td>USB Rubber Ducky</td><td>DuckyScript payload library — 2,165 payloads in ChromaDB RAG.</td></tr>
  <tr><td>Bash Bunny</td><td>Multi-stage payloads, HID + storage attack modes.</td></tr>
  <tr><td>ESP32 + Marauder</td><td>WiFi scanning, BLE enumeration, deauth attacks.</td></tr>
  <tr><td>Hailo-10H NPU</td><td>On-device AI acceleration on Pi 5 via AI HAT+. Auto-detected at boot.</td></tr>
</table>

<!-- ═══════════════════════════════════════════════════════════════════════
     15. API REFERENCE
═══════════════════════════════════════════════════════════════════════ -->
<h1 class="section" id="api">15. REST API Reference</h1>
<p>Full API at <code>http://127.0.0.1:8765/api/</code></p>

<h2>GET Endpoints</h2>
<table>
  <tr><th>Endpoint</th><th>Returns</th></tr>
  <tr><td>GET /api/status</td><td>System status, loaded modules, version</td></tr>
  <tr><td>GET /api/progression</td><td>Operator XP, level, domain skills, achievements</td></tr>
  <tr><td>GET /api/agent/status</td><td>Current agent state, findings, ports, vulns</td></tr>
  <tr><td>GET /api/agent/goals</td><td>Available goals with phase descriptions</td></tr>
  <tr><td>GET /api/recon/status</td><td>Recon engine state and findings summary</td></tr>
  <tr><td>GET /api/threat/status</td><td>Threat detector state, alert count, last alert</td></tr>
  <tr><td>GET /api/zeroday/topics</td><td>Available curriculum topics list</td></tr>
  <tr><td>GET /api/onboarding</td><td>First-run status and wizard payload</td></tr>
  <tr><td>GET /api/phases</td><td>Kill chain phases and current phase</td></tr>
  <tr><td>GET /api/tools</td><td>Full tool registry with availability</td></tr>
  <tr><td>GET /api/narrator/feed</td><td>Last 100 live narrator log lines</td></tr>
</table>

<h2>POST Endpoints</h2>
<table>
  <tr><th>Endpoint</th><th>Payload</th><th>Action</th></tr>
  <tr><td>POST /api/command</td><td>{ command }</td><td>Execute any command</td></tr>
  <tr><td>POST /api/progression/award</td><td>{ event, context }</td><td>Award XP manually</td></tr>
  <tr><td>POST /api/onboarding/complete</td><td>{ agreed, skill_level, name }</td><td>Complete onboarding</td></tr>
  <tr><td>POST /api/target</td><td>{ target }</td><td>Set active target</td></tr>
  <tr><td>POST /api/flipper/action</td><td>{ action, params }</td><td>Flipper Zero command</td></tr>
  <tr><td>POST /api/wireless</td><td>{ action, target, params }</td><td>Wireless action</td></tr>
</table>

<!-- ═══════════════════════════════════════════════════════════════════════
     16. MODULE MAP
═══════════════════════════════════════════════════════════════════════ -->
<h1 class="section" id="modules">16. Module Map — 27 Modules at Boot</h1>
<table>
  <tr><th>Module</th><th>Function</th></tr>
  <tr><td>Language Layer</td><td>500+ operator phrasings, typo correction, intent routing</td></tr>
  <tr><td>Tool Executor</td><td>Async tool runner with ToolResult model + XP awards</td></tr>
  <tr><td>Live Terminal</td><td>PTY streaming, 500-line output buffer, auto-coach trigger</td></tr>
  <tr><td>Smart Wizard</td><td>11 tool wizards, 120+ trigger phrases</td></tr>
  <tr><td>Flipper Zero Studio</td><td>Full Flipper control and payload management</td></tr>
  <tr><td>Native AI Brain</td><td>5 reasoning modes, zero cloud dependency</td></tr>
  <tr><td>BAS Engine</td><td>MITRE ATT&amp;CK aligned breach and attack simulation</td></tr>
  <tr><td>Post-Exploitation</td><td>Lateral movement, privesc, persistence modules</td></tr>
  <tr><td>Wireless Module</td><td>WPA2, evil twin, packet injection, Pineapple integration</td></tr>
  <tr><td>Social Engineering</td><td>Phishing, pretexting, vishing frameworks</td></tr>
  <tr><td>Cloud Security</td><td>AWS, Azure, GCP security enumeration</td></tr>
  <tr><td>CTF Solver</td><td>Challenge framework with Juice Shop integration (18 solved)</td></tr>
  <tr><td>OPSEC Module</td><td>Operational security audit and guidance</td></tr>
  <tr><td>Phoenix Bridge</td><td>2,172-tool BlackArch arsenal (if Phoenix-OS installed)</td></tr>
  <tr><td>Live Narrator</td><td>Real-time action narration and operator feed</td></tr>
  <tr><td>Conversation Engine</td><td>Streaming LLM chat, 20-turn history, operator context injection</td></tr>
  <tr><td>Autonomous Agent</td><td>ReAct loop, 21 tools, 6 goals, LLM + deterministic fallback</td></tr>
  <tr><td>Recon Engine</td><td>5-phase auto-recon: passive→active→web→vuln→correlate</td></tr>
  <tr><td>Threat Detection</td><td>8 signatures, MITRE mapped, response playbooks, 30s poll</td></tr>
  <tr><td>Zero-Day Training</td><td>6 lessons: fuzzing, reversing, source audit, exploit dev, CVE workflow</td></tr>
  <tr><td>Blue Team Toolkit</td><td>Auto-hardening, PCAP analysis, report generation</td></tr>
  <tr><td>Campaign Manager</td><td>Multi-target engagement coordination</td></tr>
  <tr><td>Auto Kill Chain</td><td>6-phase automated attack sequences</td></tr>
  <tr><td>Professional Reporter</td><td>CVSS-scored, MITRE-linked HTML/PDF reports</td></tr>
  <tr><td>Credential Engine</td><td>Credential harvesting, cracking, stuffing automation</td></tr>
  <tr><td>AI Threat Intel</td><td>Threat landscape briefings, corporate intelligence reports</td></tr>
  <tr><td>Teach Engine</td><td>23 topics: 15 tool lessons + 8 security concepts, offline</td></tr>
</table>

<!-- ═══════════════════════════════════════════════════════════════════════
     17. PI 5 CYBERDECK
═══════════════════════════════════════════════════════════════════════ -->
<h1 class="section" id="pi5">17. Raspberry Pi 5 Cyberdeck</h1>
<p>ERR0RS was designed and primarily tested on a custom Pi 5 Cyberdeck running Kali Linux ARM64. This is the reference field deployment platform.</p>

<table>
  <tr><th>Component</th><th>Spec</th></tr>
  <tr><td>SBC</td><td>Raspberry Pi 5 8GB</td></tr>
  <tr><td>AI Accelerator</td><td>Hailo-10H NPU (26 TOPS) via AI HAT+ 2</td></tr>
  <tr><td>Storage</td><td>NVMe SSD via Geekworm X1004 PCIe HAT</td></tr>
  <tr><td>WiFi</td><td>Alfa AWUS036ACM (5GHz dual-band) + Pi built-in</td></tr>
  <tr><td>RF</td><td>Flipper Zero (RogueMaster) + CC1101 module</td></tr>
  <tr><td>Wireless Attack</td><td>WiFi Pineapple Nano</td></tr>
  <tr><td>HID Attack</td><td>ESP32 with Marauder firmware</td></tr>
  <tr><td>Power</td><td>7-cell 18650 battery pack</td></tr>
  <tr><td>OS</td><td>Kali Linux ARM64 (rolling)</td></tr>
  <tr><td>Total Cost</td><td>~$400–500 USD</td></tr>
</table>

<h2>Performance Notes</h2>
<ul>
  <li>LLM first response (cold): ~20 seconds (model loading from NVMe)</li>
  <li>LLM subsequent responses: 2-3 seconds to first token (model in RAM)</li>
  <li>Full response generation: 30-90 seconds depending on length</li>
  <li>RAM: 8GB — sufficient for llama3.2:3b + ERR0RS + tools simultaneously</li>
</ul>

<!-- ═══════════════════════════════════════════════════════════════════════
     18. TROUBLESHOOTING
═══════════════════════════════════════════════════════════════════════ -->
<h1 class="section" id="troubleshoot">18. Troubleshooting</h1>

<h2>LLM Not Responding</h2>
<pre>curl http://localhost:11434/api/tags     # Check Ollama is running
ollama serve                             # Start Ollama
ollama pull llama3.2:3b                  # Pull model if missing</pre>

<h2>ChromaDB Import Error (google.rpc)</h2>
<pre>pip install grpcio-status --break-system-packages
python3 -c "import chromadb; print(chromadb.__version__)"</pre>

<h2>rockyou.txt Not Found</h2>
<pre>cp /usr/share/wordlists/rockyou.txt.gz /tmp/ && gzip -d /tmp/rockyou.txt.gz
mkdir -p ~/.err0rs/wordlists && cp /tmp/rockyou.txt ~/.err0rs/wordlists/</pre>

<h2>Boot Errors</h2>
<pre>cd ~/ERR0RS-Ultimate
python3 -c "import src.ui.errorz_launcher" 2>&1 | grep -E "ERROR|Traceback"
python3 -m pytest tests/ -q              # Should show 28 passed</pre>

<h2>WebSocket Not Connecting</h2>
<pre>ss -tlnp | grep 8766                    # Check port is free
fuser -k 8766/tcp                       # Free stuck port</pre>

<h2>Push Rejected (git)</h2>
<pre>git branch --set-upstream-to=origin/main main
git pull origin main --allow-unrelated-histories
git push origin main</pre>

<h2>Tool Not Found</h2>
<pre>sudo apt install &lt;tool-name&gt;
# Common missing: enum4linux gobuster ffuf nuclei crackmapexec</pre>

<!-- ═══════════════════════════════════════════════════════════════════════
     19. QUICK REFERENCE
═══════════════════════════════════════════════════════════════════════ -->
<h1 class="section" id="quickref">19. Quick Reference</h1>

<h2>First Engagement Checklist</h2>
<pre>bash scripts/start_lab.sh               # 1. Start full lab environment
# Open http://127.0.0.1:8765            # 2. Open ERR0RS web UI
target 192.168.1.100                    # 3. Set your target
recon 192.168.1.100                     # 4. Auto recon (recommended start)
# OR:
agent 192.168.1.100 full_chain          # 4. Full autonomous pentest
# Watch the Intel Feed for findings     # 5. Monitor live findings
explain [anything you see]              # 6. Ask ERR0RS what it means
report                                  # 7. Generate professional report</pre>

<h2>Critical Path — Found Port 445</h2>
<pre>nmap --script smb-vuln-ms17-010 -p 445 &lt;target&gt;
enum4linux -a &lt;target&gt;
crackmapexec smb &lt;target&gt; --shares --users</pre>

<h2>Critical Path — Found Web Login</h2>
<pre>sqlmap -u "http://&lt;target&gt;/login" --forms --batch --dbs
nikto -h http://&lt;target&gt; -C all
gobuster dir -u http://&lt;target&gt; -w /usr/share/wordlists/dirb/common.txt</pre>

<h2>Critical Path — Got a Shell</h2>
<pre>privesc linux &lt;target&gt;
postex shell &lt;target&gt;
lateral smb &lt;target&gt;</pre>

<h2>Most Used Commands</h2>
<table>
  <tr><th>Command</th><th>Use When</th></tr>
  <tr><td>recon &lt;ip&gt;</td><td>Starting any engagement — full auto-chain recon</td></tr>
  <tr><td>agent &lt;ip&gt;</td><td>Want ERR0RS to run the entire pentest</td></tr>
  <tr><td>agent &lt;url&gt; web</td><td>Web app target only</td></tr>
  <tr><td>teach me &lt;topic&gt;</td><td>Learning any tool or technique</td></tr>
  <tr><td>explain &lt;anything&gt;</td><td>AI coaching on any security topic</td></tr>
  <tr><td>threat monitor</td><td>Defensive monitoring of your system</td></tr>
  <tr><td>report</td><td>Generate engagement report</td></tr>
  <tr><td>zeroday fuzzing</td><td>Vulnerability research training</td></tr>
  <tr><td>stop agent</td><td>Stop autonomous agent at any time</td></tr>
  <tr><td>status</td><td>Current engagement state at a glance</td></tr>
</table>

<!-- ═══════════════════════════════════════════════════════════════════════
     20. ETHICS
═══════════════════════════════════════════════════════════════════════ -->
<h1 class="section" id="ethics">20. Ethical Use & Legal Notice</h1>
<div class="warn">⚠ ERR0RS-Ultimate is for AUTHORIZED SECURITY TESTING, CTF COMPETITIONS, AND EDUCATION ONLY. Using these techniques against systems you do not own is a federal crime.</div>

<ul>
  <li>Computer Fraud and Abuse Act (CFAA) — United States</li>
  <li>Computer Misuse Act (CMA) — United Kingdom</li>
  <li>Equivalent cybercrime laws — worldwide</li>
</ul>

<h2>Authorized Targets</h2>
<ul>
  <li>Lab VMs and intentionally vulnerable targets you own (Juice Shop, Metasploitable)</li>
  <li>Systems with signed, written authorization to test</li>
  <li>CTF competition environments (HackTheBox, TryHackMe, CTFtime)</li>
  <li>Your organization's infrastructure with documented approval</li>
</ul>

<div class="note">💜 Purple Team Principle: Every offensive technique in ERR0RS is paired with its detection signature and defensive countermeasure. Security is a shared understanding problem.</div>

<!-- ═══════════════════════════════════════════════════════════════════════
     21. CITATION
═══════════════════════════════════════════════════════════════════════ -->
<h1 class="section" id="citation">21. Academic Citation</h1>
<p>ERR0RS-Ultimate originated as a semester research project at Oklahoma State University's cybersecurity program, donated to OSU's program for educational use and submitted to the Kali Linux community repository.</p>

<pre>@software{schneider2026err0rs,
  author    = {Schneider, Gary Holden},
  title     = {{ERR0RS-Ultimate}: A Fully Local AI-Powered Pentest Platform},
  year      = {2026},
  publisher = {GitHub},
  url       = {https://github.com/Gnosisone/ERR0RS-Ultimate},
  version   = {3.4.0}
}</pre>

<ul>
  <li>Repository: <code>https://github.com/Gnosisone/ERR0RS-Ultimate</code></li>
  <li>Research abstract: <code>RESEARCH.md</code></li>
  <li>Changelog: <code>CHANGELOG.md</code></li>
  <li>License: MIT</li>
</ul>

</main>

<script>
// ── Active nav tracking ─────────────────────────────────────────────────────
const sections = document.querySelectorAll('h1.section');
const navLinks  = document.querySelectorAll('#sidebar a');

const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      navLinks.forEach(l => l.classList.remove('active'));
      const link = document.querySelector(`#sidebar a[href="#${e.target.id}"]`);
      if (link) link.classList.add('active');
    }
  });
}, { rootMargin: '-20% 0px -70% 0px' });

sections.forEach(s => observer.observe(s));

// ── Search ──────────────────────────────────────────────────────────────────
function searchManual(q) {
  if (!q) {
    navLinks.forEach(l => l.style.display = '');
    document.querySelectorAll('.section-label').forEach(l => l.style.display = '');
    return;
  }
  q = q.toLowerCase();
  navLinks.forEach(l => {
    l.style.display = l.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}

// ── Smooth scroll ───────────────────────────────────────────────────────────
document.querySelectorAll('#sidebar a').forEach(a => {
  a.addEventListener('click', e => {
    e.preventDefault();
    const target = document.querySelector(a.getAttribute('href'));
    if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
});
</script>
</body>
</html>
"""

# Write it
output = '/home/kali/ERR0RS-Ultimate/docs/USER_MANUAL.html'
with open(output, 'w') as f:
    f.write(MANUAL_HTML)

size = len(MANUAL_HTML)
print(f"DONE: {output}")
print(f"Size: {size:,} chars ({size//1024} KB)")
print(f"Open with: xdg-open {output}")
print(f"Or serve:  python3 -m http.server 9999 --directory docs/")
