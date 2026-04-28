const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  LevelFormat, PageBreak, Header, Footer, PageNumber
} = require('docx');
const fs = require('fs');

const C = {
  purple:'7B2FBE', purpleDark:'4C1D95', purpleLight:'C084FC',
  cyan:'22D3EE', green:'22C55E', red:'EF4444', orange:'F59E0B',
  white:'FFFFFF', gray:'6B7280', grayLight:'E5E7EB',
  black:'000000', codeBg:'F3F0FF',
};

const noBorder = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
const allNoBorder = { top:noBorder, bottom:noBorder, left:noBorder, right:noBorder };
const thinBorder = (col) => ({ style: BorderStyle.SINGLE, size: 4, color: col||'CCCCCC' });
const allThin = (col) => ({ top:thinBorder(col), bottom:thinBorder(col), left:thinBorder(col), right:thinBorder(col) });

const bold  = (t,c,s) => new TextRun({ text:t, bold:true, color:c||C.black, size:s||22, font:'Arial' });
const norm  = (t,c,s) => new TextRun({ text:t, color:c||C.black, size:s||22, font:'Arial' });
const mono  = (t,c)   => new TextRun({ text:t, font:'Courier New', size:18, color:c||C.purpleDark });

const h1 = (t) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [new TextRun({ text:t, font:'Arial', size:36, bold:true, color:C.purpleDark })],
  spacing: { before:360, after:180 },
  border: { bottom: { style:BorderStyle.SINGLE, size:8, color:C.purple, space:6 } }
});
const h2 = (t) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  children: [new TextRun({ text:t, font:'Arial', size:28, bold:true, color:C.purple })],
  spacing: { before:300, after:120 }
});
const h3 = (t) => new Paragraph({
  heading: HeadingLevel.HEADING_3,
  children: [new TextRun({ text:t, font:'Arial', size:24, bold:true, color:C.purpleDark })],
  spacing: { before:240, after:100 }
});
const p = (...runs) => new Paragraph({ children:runs, spacing:{ before:60, after:120 } });
const spacer = (b) => new Paragraph({ children:[new TextRun('')], spacing:{ before:b||120, after:0 } });
const code = (t) => new Paragraph({
  children:[new TextRun({ text:t, font:'Courier New', size:18, color:C.purpleDark })],
  spacing:{ before:40, after:40 },
  indent:{ left:360 },
  shading:{ fill:C.codeBg, type:ShadingType.CLEAR },
  border:{ left:{ style:BorderStyle.SINGLE, size:12, color:C.purple, space:4 } }
});
const bullet = (...runs) => new Paragraph({
  numbering:{ reference:'bullets', level:0 },
  children:runs, spacing:{ before:40, after:60 }
});
const pageBreak = () => new Paragraph({ children:[new PageBreak()] });

const TABLE_W = 9360;
const headerCell = (t, w) => new TableCell({
  width:{ size:w, type:WidthType.DXA },
  borders:allThin(C.purple),
  shading:{ fill:C.purpleDark, type:ShadingType.CLEAR },
  margins:{ top:80, bottom:80, left:120, right:120 },
  children:[new Paragraph({ children:[bold(t, C.white, 20)] })]
});
const dataCell = (t, w, s) => new TableCell({
  width:{ size:w, type:WidthType.DXA },
  borders:allThin('DDDDDD'),
  shading:{ fill:s||C.white, type:ShadingType.CLEAR },
  margins:{ top:60, bottom:60, left:120, right:120 },
  children:[new Paragraph({ children:[norm(t, C.black, 20)] })]
});
const monoCell = (t, w, s) => new TableCell({
  width:{ size:w, type:WidthType.DXA },
  borders:allThin('DDDDDD'),
  shading:{ fill:s||C.codeBg, type:ShadingType.CLEAR },
  margins:{ top:60, bottom:60, left:120, right:120 },
  children:[new Paragraph({ children:[mono(t)] })]
});

const twoCol = (rows) => new Table({
  width:{ size:TABLE_W, type:WidthType.DXA },
  columnWidths:[3120, 6240],
  rows:[
    new TableRow({ children:[headerCell('COMMAND',3120), headerCell('DESCRIPTION',6240)] }),
    ...rows.map(([cmd,desc], i) => new TableRow({ children:[
      monoCell(cmd, 3120, i%2===0 ? C.codeBg : 'EEEAFF'),
      dataCell(desc, 6240, i%2===0 ? C.white : 'F9F7FF'),
    ]}))
  ]
});

const threeCol = (h, rows, w) => new Table({
  width:{ size:TABLE_W, type:WidthType.DXA },
  columnWidths: w || [2400,3360,3600],
  rows:[
    new TableRow({ children: h.map((x,i) => headerCell(x, (w||[2400,3360,3600])[i])) }),
    ...rows.map(([a,b,c], i) => new TableRow({ children:[
      monoCell(a, (w||[2400,3360,3600])[0], i%2===0 ? C.codeBg : 'EEEAFF'),
      dataCell(b, (w||[2400,3360,3600])[1], i%2===0 ? C.white : 'F9F7FF'),
      dataCell(c, (w||[2400,3360,3600])[2], i%2===0 ? C.white : 'F9F7FF'),
    ]}))
  ]
});

const boldCell = (t, w, s) => new TableCell({
  width:{ size:w, type:WidthType.DXA },
  borders:allThin('DDDDDD'),
  shading:{ fill:s||C.white, type:ShadingType.CLEAR },
  margins:{ top:60, bottom:60, left:120, right:120 },
  children:[new Paragraph({ children:[bold(t, C.purpleDark, 20)] })]
});

// ── CONTENT ───────────────────────────────────────────────────────────────────
const children = [

  // COVER
  new Paragraph({ alignment:AlignmentType.CENTER, spacing:{ before:720, after:120 },
    children:[new TextRun({ text:'ERR0RS-ULTIMATE', font:'Arial', size:72, bold:true, color:C.purple })] }),
  new Paragraph({ alignment:AlignmentType.CENTER, spacing:{ before:0, after:120 },
    children:[new TextRun({ text:'USER MANUAL', font:'Arial', size:48, bold:true, color:C.purpleDark })] }),
  new Paragraph({ alignment:AlignmentType.CENTER, spacing:{ before:120, after:240 },
    children:[new TextRun({ text:'Version 3.4.0  ·  April 2026  ·  github.com/Gnosisone/ERR0RS-Ultimate', font:'Arial', size:22, color:C.gray, italics:true })] }),
  new Paragraph({ alignment:AlignmentType.CENTER, spacing:{ before:0, after:120 },
    shading:{ fill:C.purpleDark, type:ShadingType.CLEAR },
    children:[new TextRun({ text:'100% Local  ·  Zero Cloud Dependency  ·  Open Source  ·  Built for Everyone', font:'Arial', size:22, color:C.white })] }),
  new Paragraph({ alignment:AlignmentType.CENTER, spacing:{ before:240, after:720 },
    children:[new TextRun({ text:'Gary Holden Schneider (Eros)  ·  GitHub: Gnosisone', font:'Arial', size:20, color:C.gray })] }),

  pageBreak(),

  // 1. WHAT IS ERR0RS
  h1('1. What Is ERR0RS-Ultimate?'),
  p(norm('ERR0RS-Ultimate is a fully local, AI-powered security platform that wraps 27 security modules in a conversational interface. It teaches offensive and defensive techniques inline, coaches operators through engagements, runs tools autonomously, and generates professional reports — all without sending a single byte to the cloud.')),
  spacer(),
  p(norm('Built for two audiences simultaneously: the security student who has never run a pentest and the professional operator who needs a faster, smarter workflow. Every tool run is explained. Every finding is analyzed. Every attack technique is paired with its defensive countermeasure.')),
  spacer(),
  h2('Core Design Principles'),
  bullet(bold('Zero cloud dependency — '), norm('all LLM inference runs locally via Ollama. No API keys, no external calls.')),
  bullet(bold('Offline first — '), norm('teach engine, auto-coach, agent, and threat detection all work without internet.')),
  bullet(bold('Purple team — '), norm('every offensive technique paired with its defensive countermeasure and MITRE ATT&CK mapping.')),
  bullet(bold('Teach by default — '), norm('no command runs without explanation of what it does and why it works.')),
  bullet(bold('Progressive — '), norm('XP system and operator levels track skill growth across 8 security domains.')),

  pageBreak(),

  // 2. INSTALLATION
  h1('2. Installation'),
  h2('System Requirements'),
  new Table({ width:{ size:TABLE_W, type:WidthType.DXA }, columnWidths:[3000,6360], rows:[
    new TableRow({ children:[headerCell('REQUIREMENT',3000), headerCell('NOTES',6360)] }),
    ...[ ['Kali Linux / Parrot / Ubuntu','x86_64 or ARM64. Kali recommended — all security tools pre-installed.'],
      ['Python 3.10+','Check: python3 --version'],
      ['git','sudo apt install git'],
      ['Ollama','Installed automatically by install.sh'],
      ['4 GB free disk','For llama3.2:3b (2.0 GB) + Python dependencies'],
      ['Node 20-22 (optional)','Required for OWASP Juice Shop lab target only'],
    ].map(([a,b],i) => new TableRow({ children:[
      monoCell(a,3000,i%2===0?C.codeBg:'EEEAFF'), dataCell(b,6360,i%2===0?C.white:'F9F7FF')
    ]}))
  ]}),
  spacer(),
  h2('Standard Install (Kali / Parrot)'),
  code('git clone https://github.com/Gnosisone/ERR0RS-Ultimate.git'),
  code('cd ERR0RS-Ultimate'),
  code('sudo bash install.sh'),
  code('bash start_err0rs.sh'),
  spacer(),
  p(bold('Important: ', C.red), norm('Do NOT run '), mono('cp configs/config.template.env .env'), norm(' after install.sh — it overwrites the auto-generated secret key. The installer creates .env automatically.')),
  spacer(),
  h2('Full Lab (Juice Shop + Ollama + ERR0RS)'),
  code('bash scripts/start_lab.sh'),
  spacer(),
  h2('Raspberry Pi 5'),
  code('sudo bash scripts/pi5_first_boot.sh'),
  code('sudo bash scripts/install_hailo_h10.sh   # If you have the AI HAT+'),
  code('sudo bash install.sh'),
  spacer(),
  h2('Access'),
  bullet(bold('Web UI: '), mono('http://127.0.0.1:8765')),
  bullet(bold('WebSocket: '), mono('ws://127.0.0.1:8766')),
  bullet(bold('API: '), mono('http://127.0.0.1:8765/api/')),

  pageBreak(),

  // 3. FIRST RUN
  h1('3. First Run — Onboarding Wizard'),
  p(norm('On first launch, ERR0RS presents a 4-screen guided wizard:')),
  spacer(),
  new Table({ width:{ size:TABLE_W, type:WidthType.DXA }, columnWidths:[1440,2520,5400], rows:[
    new TableRow({ children:[headerCell('SCREEN',1440), headerCell('TITLE',2520), headerCell('WHAT HAPPENS',5400)] }),
    ...[ ['1','Welcome','Introduction to ERR0RS philosophy and capabilities'],
      ['2','Ethics Agreement','Required agreement — must click through before accessing tools'],
      ['3','Skill Assessment','Sets guided vs standard vs expert mode automatically'],
      ['4','First Mission','Guided nmap → nikto → gobuster walkthrough on Juice Shop'],
    ].map(([a,b,c],i) => new TableRow({ children:[
      monoCell(a,1440,i%2===0?C.codeBg:'EEEAFF'),
      dataCell(b,2520,i%2===0?C.white:'F9F7FF'),
      dataCell(c,5400,i%2===0?C.white:'F9F7FF'),
    ]}))
  ]}),
  spacer(),
  h2('Mode Toggle'),
  p(norm('Click the mode badge in the terminal header to switch between modes:')),
  bullet(bold('🔰 GUIDED: '), norm('Rotating example placeholders, teach mode on, mission coach visible, coaching on every output')),
  bullet(bold('⚡ EXPERT: '), norm('Clean interface, coaching available on demand, full command access')),

  pageBreak(),

  // 4. UI LAYOUT
  h1('4. Web UI Layout'),
  new Table({ width:{ size:TABLE_W, type:WidthType.DXA }, columnWidths:[2160,2400,4800], rows:[
    new TableRow({ children:[headerCell('PANE',2160), headerCell('LOCATION',2400), headerCell('CONTENTS',4800)] }),
    ...[ ['Pentest Phases','Top-left sidebar','Kill chain phase tracker, engagement timeline, intel feed'],
      ['Live Terminal','Center main','Interactive terminal, streaming output, coaching blocks'],
      ['Intel Feed','Right sidebar','Real-time findings, auto-coach analysis, MITRE ATT&CK mappings'],
      ['Tool Grid','Bottom scrollbar','65+ tool cards — click to open panel, right-click for options'],
      ['Skill Panel','Right edge (XP badge)','XP bar, level badge, 8 domain skill bars, stats'],
      ['Agent Panel','Left edge (🤖 button)','Autonomous agent launcher, goal selector, live dashboard'],
    ].map(([a,b,c],i) => new TableRow({ children:[
      dataCell(a,2160,i%2===0?C.codeBg:'EEEAFF'),
      dataCell(b,2400,i%2===0?C.white:'F9F7FF'),
      dataCell(c,4800,i%2===0?C.white:'F9F7FF'),
    ]}))
  ]}),

  pageBreak(),

  // 5. AI CONVERSATION
  h1('5. AI Conversation Engine'),
  p(norm('Type any question or security topic in plain English. ERR0RS automatically detects conversational messages and routes them to the local LLM (llama3.2:3b via Ollama) instead of the tool executor.')),
  spacer(),
  h2('Example Queries'),
  twoCol([
    ['explain sql injection','Full explanation with examples, attack vector, defense'],
    ['walk me through kerberoasting','Step-by-step attack with exact commands'],
    ['what is CIS Control 6','All safeguards, implementation groups, examples'],
    ['how do I read nmap output','Output interpretation — what each line means'],
    ['what is MITRE ATT&CK','Full framework — all 14 tactics mapped'],
    ['difference between SSRF and CSRF','Side-by-side comparison with examples'],
    ['coach me through this SQLi','Personalized step-by-step exploitation coaching'],
    ['what tools for AD enumeration','Recommended tool stack with rationale'],
    ['explain OWASP A03','Injection category — patterns and mitigations'],
    ['what should I do after port 445','Contextual next steps for SMB discovery'],
  ]),
  spacer(),
  h2('Response Notes'),
  bullet(bold('Streaming: '), norm('Tokens appear as generated in a purple chat bubble — not a 20-second wait')),
  bullet(bold('Context-aware: '), norm('ERR0RS knows your active target and recent findings — responses are engagement-specific')),
  bullet(bold('20-turn memory: '), norm('Conversation history maintained across turns for coherent multi-step coaching')),
  bullet(bold('Clickable commands: '), norm('Any command in a response can be clicked to paste into the terminal')),
  bullet(bold('Cold start: '), norm('First response after launch takes ~15-20s (model loading). All subsequent: 2-3s to first token')),

  pageBreak(),

  // 6. COMMAND REFERENCE
  h1('6. Command Reference'),

  h2('Target & Status'),
  twoCol([
    ['target 192.168.1.100','Set active target IP'],
    ['target http://app.local','Set active web target'],
    ['status','Show current target, mode, findings'],
  ]),
  spacer(),

  h2('Recon Engine (Autonomous)'),
  twoCol([
    ['recon 192.168.1.100','Full auto-chain: passive → active → web → vuln → correlate'],
    ['recon 192.168.1.100 passive','DNS, cert transparency, WHOIS only'],
    ['recon 192.168.1.100 active','Passive + nmap + banner grab + SMB scripts'],
    ['recon http://target.com web','Passive + active + WhatWeb + gobuster'],
    ['stop recon','Stop the running recon engine'],
  ]),
  spacer(),

  h2('Autonomous Agent (ReAct Loop)'),
  twoCol([
    ['agent 192.168.1.100','Full kill chain: recon → enum → vuln → exploit → report (20 steps)'],
    ['agent http://target.com web','Web app assessment (12 steps)'],
    ['agent 192.168.1.100 network','Network pentest (12 steps)'],
    ['agent 192.168.1.100 quick','Fast surface scan (6 steps)'],
    ['agent 192.168.1.100 stealth','Low-noise recon (8 steps)'],
    ['agent 192.168.1.100 ad','Active Directory — path to Domain Admin (10 steps)'],
    ['stop agent','Stop running agent'],
    ['agent status','Show current state, findings, ports, vulns'],
  ]),
  spacer(),

  h2('Threat Detection'),
  twoCol([
    ['threat monitor','Start continuous monitoring (30s poll, 8 signatures)'],
    ['threat scan','Single scan right now — show all alerts'],
    ['stop threats','Stop monitoring'],
  ]),
  spacer(),

  h2('Tool Execution'),
  twoCol([
    ['nmap -sV 10.0.0.1','Port scan with version detection'],
    ['nmap --teach 10.0.0.1','Nmap with inline educational coaching'],
    ['nikto -h http://target.com','Web vulnerability scan (6,700+ checks)'],
    ['gobuster dir -u http://target -w /wordlist','Directory enumeration'],
    ['sqlmap -u "http://t/q=1" --dbs','SQL injection scan'],
    ['hydra -l admin -P rockyou.txt ssh://target','SSH brute force'],
    ['nuclei -u http://target -t http/','Template-based vulnerability scan'],
    ['$ <any shell command>','Raw shell ($ prefix bypasses intent parser)'],
  ]),
  spacer(),

  h2('Education — Teach Engine (23 Topics)'),
  p(norm('Type any of these for a full lesson: flags reference, output reading guide, next steps, and cautions.')),
  spacer(),
  h3('Tools (15 lessons):'),
  twoCol([
    ['teach me nmap','All flags, output reading, next steps, common mistakes'],
    ['explain gobuster','Modes, wordlists, status code meaning'],
    ['what is sqlmap','Attack types, tamper scripts, escalation path'],
    ['teach me hydra','Protocols, safe threading, lockout avoidance'],
    ['explain bloodhound','AD graph reading — what the attack paths mean'],
    ['teach me metasploit','Search → use → options → exploit → post workflow'],
    ['explain crackmapexec','SMB/WinRM/RDP — credential testing, pass-the-hash'],
    ['what is nuclei','Templates, severity, tags, reading output'],
    ['teach me hashcat','Modes (-a), rules, masks, GPU vs CPU'],
    ['explain responder','LLMNR poisoning, NTLMv2 capture, relay vs crack'],
    ['teach me linpeas','Reading output, color coding, what to escalate'],
    ['teach me netcat','Listeners, file transfer, pivoting, bind vs reverse'],
    ['what is ffuf','URL/param/header fuzzing, filtering noise'],
    ['explain enum4linux','SMB null session, users, shares, password policy'],
    ['explain whatweb','CMS/framework detection, version identification'],
  ]),
  spacer(),
  h3('Concepts (8 lessons):'),
  twoCol([
    ['what is CIS','All 18 CIS Controls v8 with implementation groups (IG1/2/3)'],
    ['explain OWASP','OWASP Top 10 2021 — all categories, attack + defense'],
    ['what is MITRE ATT&CK','All 14 tactics, technique IDs, detections, mitigations'],
    ['explain kill chain','7-phase Cyber Kill Chain — attacker vs defender view'],
    ['what is CIA triad','Confidentiality, Integrity, Availability explained'],
    ['explain incident response','NIST IR phases — Prepare, Detect, Contain, Eradicate, Recover'],
    ['explain threat modeling','STRIDE — Spoofing, Tampering, Repudiation, Info Disclosure, DoS, EoP'],
    ['(and more via AI)','Ask ERR0RS anything not in the static curriculum'],
  ]),
  spacer(),

  h2('Zero-Day Training'),
  twoCol([
    ['zeroday topics','List all 6 curriculum topics'],
    ['zeroday overview','What is 0day research? Mindset, categories, process'],
    ['zeroday teach fuzzing','AFL++ coverage-guided fuzzing — find crashes automatically'],
    ['zeroday binary_analysis','Ghidra static + GDB/pwndbg dynamic analysis'],
    ['zeroday source_audit','Systematic code auditing — data flow tracing, grep patterns'],
    ['zeroday exploit_dev','Stack overflows, ROP chains, pwntools cheatsheet'],
    ['zeroday cve_workflow','Responsible disclosure, CVE assignment, bug bounties'],
    ['zeroday tools','Check which research tools are installed'],
  ]),
  spacer(),

  h2('Hardware Commands'),
  twoCol([
    ['flipper status','Connection check, firmware version, battery level'],
    ['flipper evolve','XP evolution sequence (requires connection)'],
    ['flipper badusb <name>','Deploy BadUSB payload from library'],
    ['flipper rf scan','Sub-GHz spectrum scan'],
    ['flipper nfc scan','NFC/RFID card read'],
    ['wifi scan','Wireless discovery (requires monitor mode adapter)'],
    ['wifi deauth <bssid>','Deauthentication (authorized testing only)'],
    ['wifi crack <capture>','WPA2 handshake crack'],
  ]),
  spacer(),

  h2('Reporting & Operations'),
  twoCol([
    ['report','Generate professional HTML penetration test report'],
    ['debrief','Engagement debrief summary to terminal'],
    ['killchain <target>','Automated 6-phase kill chain'],
    ['opsec check','OPSEC audit of current system'],
    ['campaign new <name>','Create new engagement campaign'],
    ['ctf web','CTF hints for web challenges'],
    ['privesc linux <target>','Linux privilege escalation suggestions'],
    ['lateral smb <target>','SMB lateral movement'],
  ]),

  pageBreak(),

  // 7. AUTO COACH
  h1('7. Auto Coach Engine'),
  p(norm('After every tool completes, ERR0RS automatically analyzes the output and fires a coaching block — offline, no LLM required. Deterministic rules cover 15+ tools and 20+ finding patterns.')),
  spacer(),
  threeCol(['FINDING','SEVERITY','RESPONSE PROVIDED'],
    [ ['445/tcp open (SMB)','🔴 CRITICAL','EternalBlue check, enum4linux, NTLM relay options'],
      ['3389/tcp open (RDP)','🟠 HIGH','BlueKeep check, credential spray, NLA status'],
      ['21/tcp open (FTP)','🟠 HIGH','Anonymous access test, version CVEs'],
      ['6379/tcp open (Redis)','🔴 CRITICAL','Unauthenticated access, key dump, SSH key write'],
      ['VULNERABLE in NSE','🔴 CRITICAL','CVE lookup, MSF search, exploit path'],
      ['Missing headers (nikto)','🟡 MEDIUM','Clickjacking risk, fix commands'],
      ['Admin panel found','🟠 HIGH','Default credential testing, brute force options'],
      ['.git or .env exposed','🔴 CRITICAL','Source/secret extraction commands'],
      ['SQLi confirmed (sqlmap)','🔴 CRITICAL','DB dump, OS shell escalation path'],
      ['Creds cracked (hydra)','🔴 CRITICAL','Cross-service testing, CME, evil-winrm'],
    ],
    [2800, 2000, 4560]
  ),
  spacer(),
  p(norm('Each coaching block: severity icon, plain-English explanation, clickable next-step commands (click to paste into terminal), and a defensive countermeasure.')),

  pageBreak(),

  // 8. AUTONOMOUS AGENT
  h1('8. Autonomous Pentest Agent'),
  p(norm('A full ReAct (Reason-Act-Observe) autonomous agent that plans and executes multi-step penetration tests independently, using the LLM to reason over findings and decide what to do next.')),
  spacer(),
  h2('The Loop'),
  bullet(bold('OBSERVE: '), norm('current findings — open ports, services, vulnerabilities, credentials, current phase')),
  bullet(bold('REASON: '), norm('LLM picks next tool from 21 options with full state context (falls back to deterministic rules if LLM slow)')),
  bullet(bold('ACT: '), norm('builds exact shell command, streams every output line live to terminal')),
  bullet(bold('ANALYZE: '), norm('parses output into structured findings, updates agent state')),
  bullet(bold('REPEAT: '), norm('until goal complete, max steps reached, or operator stops it')),
  spacer(),

  h2('Agent Goals'),
  new Table({ width:{ size:TABLE_W, type:WidthType.DXA }, columnWidths:[2000,1800,5560], rows:[
    new TableRow({ children:[headerCell('GOAL',2000), headerCell('MAX STEPS',1800), headerCell('DESCRIPTION',5560)] }),
    ...[ ['full_chain','20','Complete pentest: recon→enum→vuln scan→exploit→post-exploit→report'],
      ['web','12','Web app: tech fingerprint→dir enum→vuln scan→exploit attempt'],
      ['network','12','Network: port scan→service enum→vuln check→exploit attempt'],
      ['ad','10','Active Directory: AD recon→Kerberoast→BloodHound→escalate to DA'],
      ['stealth','8','Low-noise: passive recon→slow scan→minimal enumeration'],
      ['quick','6','Fast surface: quick port scan→web check→summary report'],
    ].map(([a,b,c],i) => new TableRow({ children:[
      monoCell(a,2000,i%2===0?C.codeBg:'EEEAFF'),
      dataCell(b,1800,i%2===0?C.white:'F9F7FF'),
      dataCell(c,5560,i%2===0?C.white:'F9F7FF'),
    ]}))
  ]}),
  spacer(),

  h2('What the Agent Does Automatically'),
  bullet(norm('Scans ports → immediately selects service-specific tools for what it finds')),
  bullet(norm('Finds port 80/443 → chains: whatweb → nikto → gobuster → nuclei')),
  bullet(norm('Finds port 445 → chains: nmap smb-vuln-ms17-010 → enum4linux → crackmapexec')),
  bullet(norm('Finds SSH → hydra brute force with rockyou')),
  bullet(norm('Finds credentials → tests against every other discovered service')),
  bullet(norm('Finds EternalBlue → escalates immediately (highest severity first)')),
  bullet(norm('After each tool → auto-coach fires and explains the findings')),
  bullet(norm('At completion → generates full penetration test report')),
  spacer(),
  p(norm('Launch via Agent Panel (🤖 button on left edge) or terminal: '), mono('agent 192.168.1.100 full_chain')),

  pageBreak(),

  // 9. THREAT DETECTION
  h1('9. AI-Powered Threat Detection'),
  p(norm('Continuous monitoring of system logs, running processes, and network connections. Each alert includes MITRE ATT&CK mapping and a 3-step response playbook. 30-second poll interval. Runs as a background thread.')),
  spacer(),
  threeCol(['SIGNATURE','SEVERITY','MITRE TECHNIQUE'],
    [ ['brute_force_ssh','🟠 HIGH','T1110.001 — Brute Force: Password Guessing'],
      ['port_scan','🟡 MEDIUM','T1046 — Network Service Discovery'],
      ['web_attack_sqli','🔴 CRITICAL','T1190 — Exploit Public-Facing Application'],
      ['web_attack_path_traversal','🟠 HIGH','T1083 — File and Directory Discovery'],
      ['privilege_escalation','🔴 CRITICAL','T1548 — Abuse Elevation Control Mechanism'],
      ['malware_process','🔴 CRITICAL','T1059 — Command and Scripting Interpreter'],
      ['lateral_movement','🔴 CRITICAL','T1021 — Remote Services'],
      ['data_exfiltration','🔴 CRITICAL','T1048 — Exfiltration Over Alternative Protocol'],
    ],
    [2800, 1800, 4760]
  ),
  spacer(),
  p(norm('Commands: '), mono('threat monitor'), norm(' → '), mono('threat scan'), norm(' → '), mono('stop threats')),

  pageBreak(),

  // 10. PROGRESSION
  h1('10. Operator Progression System'),
  h2('Levels'),
  new Table({ width:{ size:TABLE_W, type:WidthType.DXA }, columnWidths:[900,2520,1800,4140], rows:[
    new TableRow({ children:[headerCell('',900), headerCell('LEVEL',2520), headerCell('XP REQUIRED',1800), headerCell('MEANING',4140)] }),
    ...[ ['🔰','SCRIPT KIDDIE','0','Guided mode recommended. Start with Mission 01.'],
      ['🎯','APPRENTICE','100',"Basics learned. Time to go deeper."],
      ['⚡','PRACTITIONER','500','Can run real engagements. Stay ethical.'],
      ['🔥','SPECIALIST','1,500','Domain mastered. The network respects you.'],
      ['💀','OPERATOR','4,000','Full red team capability. You ARE the threat model.'],
      ['👑','ELITE','10,000',"You don't just use tools — you build them."],
    ].map(([a,b,c,d],i) => new TableRow({ children:[
      dataCell(a,900,i%2===0?'F9F7FF':'EEEAFF'),
      boldCell(b,2520,i%2===0?C.white:'F9F7FF'),
      monoCell(c,1800,i%2===0?C.codeBg:'EEEAFF'),
      dataCell(d,4140,i%2===0?C.white:'F9F7FF'),
    ]}))
  ]}),
  spacer(),
  h2('Skill Domains (8)'),
  twoCol([
    ['🌐 Web App Security','nmap, nikto, gobuster, sqlmap, nuclei, ffuf, Juice Shop challenges'],
    ['🔌 Network Attacks','nmap, hydra, responder, crackmapexec, netstat'],
    ['🏢 Active Directory','bloodhound, mimikatz, crackmapexec, impacket tools'],
    ['📡 Wireless Hacking','aircrack, wifite, evil twin, handshake capture'],
    ['🔧 Hardware / Physical','Flipper Zero, BadUSB payloads, RF attacks, ESP32'],
    ['🔍 Digital Forensics','volatility, autopsy, memory analysis tools'],
    ['🎭 Social Engineering','phishing campaigns, pretexting exercises'],
    ['🛡️ Blue Team / Defense','threat monitoring alerts, hardening actions, IR'],
  ]),
  spacer(),
  p(norm('View progression: click XP badge on right edge. Toasts appear bottom-right when XP is awarded.')),

  pageBreak(),

  // 11. HARDWARE
  h1('11. Hardware Integration'),
  new Table({ width:{ size:TABLE_W, type:WidthType.DXA }, columnWidths:[2400,6960], rows:[
    new TableRow({ children:[headerCell('DEVICE',2400), headerCell('CAPABILITIES',6960)] }),
    ...[ ['Flipper Zero','RF Sub-GHz, NFC/RFID, IR, BadUSB/DuckyScript, GPIO, BLE. Evolution Engine: 10-level XP system, auto-detect on boot.'],
      ['WiFi Pineapple Nano','PineAP engine, client capture, evil twin, recon modules.'],
      ['Alfa AWUS036ACM','Monitor mode, packet injection, 2.4/5 GHz dual-band, WPA2 handshake.'],
      ['USB Rubber Ducky','DuckyScript payload library — 2,165 payloads in ChromaDB RAG.'],
      ['Bash Bunny','Multi-stage payloads, HID + storage attack modes.'],
      ['ESP32 + Marauder','WiFi scanning, BLE enum, deauth attacks.'],
      ['Hailo-10H NPU','On-device AI acceleration on Pi 5 via AI HAT+. Auto-detected at boot.'],
    ].map(([a,b],i) => new TableRow({ children:[
      dataCell(a,2400,i%2===0?C.codeBg:'EEEAFF'),
      dataCell(b,6960,i%2===0?C.white:'F9F7FF'),
    ]}))
  ]}),

  pageBreak(),

  // 12. API
  h1('12. REST API Reference'),
  p(norm('Full API at '), mono('http://127.0.0.1:8765/api/')),
  spacer(),
  h2('GET Endpoints'),
  twoCol([
    ['GET /api/status','System status, loaded modules, version'],
    ['GET /api/progression','Operator XP, level, domain skills, achievements'],
    ['GET /api/agent/status','Current agent state, findings, ports, vulns'],
    ['GET /api/agent/goals','Available goals with phase descriptions'],
    ['GET /api/recon/status','Recon engine state and findings summary'],
    ['GET /api/threat/status','Threat detector state, alert count, last alert'],
    ['GET /api/zeroday/topics','Available curriculum topics'],
    ['GET /api/onboarding','First-run status and wizard data'],
    ['GET /api/phases','Kill chain phases and current phase'],
    ['GET /api/tools','Full tool registry with availability'],
    ['GET /api/narrator/feed','Last 100 live narrator log lines'],
  ]),
  spacer(),
  h2('POST Endpoints'),
  twoCol([
    ['POST /api/command','Execute command: { command }'],
    ['POST /api/progression/award','Award XP: { event, context }'],
    ['POST /api/onboarding/complete','Complete setup: { agreed, skill_level, name }'],
    ['POST /api/target','Set target: { target }'],
    ['POST /api/flipper/action','Flipper command: { action, params }'],
    ['POST /api/wireless','Wireless action: { action, target, params }'],
  ]),

  pageBreak(),

  // 13. 27 MODULES
  h1('13. Module Map — 27 Modules at Boot'),
  twoCol([
    ['Language Layer','500+ operator phrasings, typo correction, intent routing'],
    ['Integration Adapter','Tool registry patch system'],
    ['Tool Executor','Async tool runner with ToolResult model'],
    ['Live Terminal','PTY streaming, 500-line output buffer, auto-coach trigger'],
    ['Smart Wizard','11 tool wizards, 120+ trigger phrases'],
    ['Terminal Bridge','OS terminal launcher v2.0'],
    ['Flipper Zero Studio','Full Flipper control and payload management'],
    ['Native AI Brain','5 reasoning modes, zero cloud dependency'],
    ['BAS Engine','MITRE ATT&CK aligned breach and attack simulation'],
    ['Post-Exploitation','Lateral movement, privesc, persistence modules'],
    ['Wireless Module','WPA2, evil twin, packet injection, Pineapple integration'],
    ['Social Engineering','Phishing, pretexting, vishing frameworks'],
    ['Cloud Security','AWS, Azure, GCP security enumeration'],
    ['CTF Solver','Challenge framework with Juice Shop (18 challenges solved)'],
    ['OPSEC Module','Operational security audit and guidance'],
    ['Phoenix Bridge','2,172-tool BlackArch arsenal (if Phoenix-OS installed)'],
    ['Live Narrator','Real-time action narration, operator feed'],
    ['Conversation Engine','Streaming LLM chat, 20-turn history, operator context injection'],
    ['Autonomous Agent','ReAct loop, 21 tools, 6 goals, LLM + deterministic fallback'],
    ['Recon Engine','5-phase auto-recon: passive→active→web→vuln→correlate'],
    ['Threat Detection','8 signatures, MITRE mapped, response playbooks, 30s poll'],
    ['Zero-Day Training','6 lessons: fuzzing, reversing, source audit, exploit dev, CVE workflow'],
    ['Blue Team Toolkit','Auto-hardening, PCAP analysis, report generation'],
    ['Campaign Manager','Multi-target engagement coordination'],
    ['Auto Kill Chain','6-phase automated attack sequences'],
    ['Professional Reporter','CVSS-scored, MITRE-linked HTML/PDF reports'],
    ['Credential Engine','Credential harvesting, cracking, stuffing automation'],
    ['AI Threat Intel','Threat landscape briefings, corporate intelligence reports'],
    ['Compliance Mapper','CIS, NIST, PCI-DSS, HIPAA, SOC 2, ISO 27001 mapping'],
    ['Teach Engine','23 topics: 15 tools + 8 security concepts, works offline'],
    ['Social Eng Engine','Full SE framework — phishing through vishing'],
    ['Flipper Evolution','10-level XP system, firmware detection, auto watcher daemon'],
  ]),

  pageBreak(),

  // 14. TROUBLESHOOTING
  h1('14. Troubleshooting'),
  h2('LLM Not Responding'),
  code('curl http://localhost:11434/api/tags          # Check Ollama is running'),
  code('ollama serve                                  # Start Ollama'),
  code('ollama pull llama3.2:3b                       # Pull model if missing'),
  spacer(),
  h2('ChromaDB Import Error (google.rpc)'),
  code('pip install grpcio-status --break-system-packages'),
  code('python3 -c "import chromadb; print(chromadb.__version__)"'),
  spacer(),
  h2('rockyou.txt Not Found'),
  code('cp /usr/share/wordlists/rockyou.txt.gz /tmp/ && gzip -d /tmp/rockyou.txt.gz'),
  code('mkdir -p ~/.err0rs/wordlists && cp /tmp/rockyou.txt ~/.err0rs/wordlists/'),
  spacer(),
  h2('Boot Errors'),
  code('python3 -c "import src.ui.errorz_launcher" 2>&1 | grep -E "ERROR|Traceback"'),
  code('python3 -m pytest tests/ -q                  # Should show 28 passed'),
  code('pip install -r requirements-kali.txt --break-system-packages'),
  spacer(),
  h2('WebSocket Not Connecting'),
  code('ss -tlnp | grep 8766                         # Check port is free'),
  code('fuser -k 8766/tcp                            # Free stuck port'),
  spacer(),
  h2('Tool Not In PATH'),
  code('sudo apt install <tool-name>'),
  code('# Common: enum4linux gobuster ffuf nuclei crackmapexec'),

  pageBreak(),

  // 15. QUICK REF
  h1('15. Quick Reference'),
  h2('First Engagement Checklist'),
  bullet(bold('1. '), norm('Start lab: '), mono('bash scripts/start_lab.sh')),
  bullet(bold('2. '), norm('Open browser: '), mono('http://127.0.0.1:8765')),
  bullet(bold('3. '), norm('Set target: '), mono('target 192.168.1.100')),
  bullet(bold('4. '), norm('Auto recon: '), mono('recon 192.168.1.100')),
  bullet(bold('5. '), norm('Or full auto: '), mono('agent 192.168.1.100 full_chain')),
  bullet(bold('6. '), norm('Watch Intel Feed for findings')),
  bullet(bold('7. '), norm('Ask ERR0RS anything: '), mono('explain what this means')),
  bullet(bold('8. '), norm('Generate report: '), mono('report')),
  spacer(),

  h2('Critical Path — Found Port 445'),
  code('nmap --script smb-vuln-ms17-010 -p 445 <target>'),
  code('enum4linux -a <target>'),
  code('crackmapexec smb <target> --shares --users'),
  spacer(),

  h2('Critical Path — Found Web Login'),
  code('sqlmap -u "http://<target>/login" --forms --batch --dbs'),
  code('nikto -h http://<target> -C all'),
  code('gobuster dir -u http://<target> -w /usr/share/wordlists/dirb/common.txt'),
  spacer(),

  h2('Critical Path — Got a Shell'),
  code('privesc linux <target>'),
  code('postex shell <target>'),
  code('lateral smb <target>'),
  spacer(),

  pageBreak(),

  // 16. ETHICS
  h1('16. Ethical Use & Legal Notice'),
  new Paragraph({
    shading:{ fill:'FFF3F3', type:ShadingType.CLEAR },
    border:{ left:{ style:BorderStyle.SINGLE, size:12, color:C.red, space:4 } },
    indent:{ left:360 },
    spacing:{ before:120, after:120 },
    children:[bold('ERR0RS-Ultimate is for AUTHORIZED SECURITY TESTING, CTF COMPETITIONS, AND EDUCATION ONLY.', C.red, 24)]
  }),
  spacer(),
  bullet(norm('Computer Fraud and Abuse Act (CFAA) — United States')),
  bullet(norm('Computer Misuse Act (CMA) — United Kingdom')),
  bullet(norm('Equivalent cybercrime laws — worldwide')),
  spacer(),
  p(norm('Ethical use agreement required on first run. Every offensive technique is paired with its detection signature and defensive countermeasure. Security is a shared understanding problem.')),
  spacer(),
  h2('Authorized Targets'),
  bullet(norm('Lab VMs and intentionally vulnerable targets you own (Juice Shop, Metasploitable)')),
  bullet(norm('Systems with signed, written authorization')),
  bullet(norm('CTF competition environments (HackTheBox, TryHackMe, CTFtime)')),
  bullet(norm('Your organization\'s infrastructure with documented approval')),
  spacer(),

  pageBreak(),

  // 17. CITATION
  h1('17. Academic Citation'),
  p(norm('ERR0RS-Ultimate originated as a semester research project at Oklahoma State University\'s cybersecurity program, donated to OSU\'s program for educational use and submitted to the Kali Linux community repository.')),
  spacer(),
  h2('BibTeX'),
  code('@software{schneider2026err0rs,'),
  code('  author  = {Schneider, Gary Holden},'),
  code('  title   = {{ERR0RS-Ultimate}: A Fully Local AI-Powered Pentest Platform},'),
  code('  year    = {2026},'),
  code('  url     = {https://github.com/Gnosisone/ERR0RS-Ultimate},'),
  code('  version = {3.4.0}'),
  code('}'),
  spacer(),
  h2('Links'),
  bullet(norm('Repository: '), mono('https://github.com/Gnosisone/ERR0RS-Ultimate')),
  bullet(norm('License: MIT')),
  bullet(norm('Changelog: CHANGELOG.md')),
  bullet(norm('Research abstract: RESEARCH.md')),
  bullet(norm('Contributing: CONTRIBUTING.md')),

];

// ── BUILD DOC ─────────────────────────────────────────────────────────────────
const doc = new Document({
  numbering: {
    config: [
      { reference:'bullets',
        levels:[{ level:0, format:LevelFormat.BULLET, text:'•', alignment:AlignmentType.LEFT,
          style:{ paragraph:{ indent:{ left:720, hanging:360 } } } }] },
    ]
  },
  styles: {
    default: { document: { run: { font:'Arial', size:22 } } },
    paragraphStyles: [
      { id:'Heading1', name:'Heading 1', basedOn:'Normal', next:'Normal', quickFormat:true,
        run:{ size:36, bold:true, font:'Arial', color:C.purpleDark },
        paragraph:{ spacing:{ before:360, after:180 }, outlineLevel:0 } },
      { id:'Heading2', name:'Heading 2', basedOn:'Normal', next:'Normal', quickFormat:true,
        run:{ size:28, bold:true, font:'Arial', color:C.purple },
        paragraph:{ spacing:{ before:300, after:120 }, outlineLevel:1 } },
      { id:'Heading3', name:'Heading 3', basedOn:'Normal', next:'Normal', quickFormat:true,
        run:{ size:24, bold:true, font:'Arial', color:C.purpleDark },
        paragraph:{ spacing:{ before:240, after:100 }, outlineLevel:2 } },
    ]
  },
  sections:[{
    properties: {
      page: {
        size:{ width:12240, height:15840 },
        margin:{ top:1080, right:1080, bottom:1080, left:1080 }
      }
    },
    headers: {
      default: new Header({ children:[new Paragraph({
        border:{ bottom:{ style:BorderStyle.SINGLE, size:4, color:C.purple, space:6 } },
        spacing:{ before:0, after:120 },
        children:[
          new TextRun({ text:'ERR0RS-ULTIMATE  ·  USER MANUAL v3.4.0  ·  github.com/Gnosisone/ERR0RS-Ultimate', font:'Arial', size:16, color:C.gray })
        ]
      })] })
    },
    footers: {
      default: new Footer({ children:[new Paragraph({
        border:{ top:{ style:BorderStyle.SINGLE, size:4, color:C.purple, space:6 } },
        spacing:{ before:120, after:0 },
        children:[
          new TextRun({ text:'AUTHORIZED SECURITY TESTING AND EDUCATION ONLY  ·  MIT LICENSE  ·  Page ', font:'Arial', size:16, color:C.gray }),
          new TextRun({ children:[PageNumber.CURRENT], font:'Arial', size:16, color:C.purple }),
        ]
      })] })
    },
    children,
  }]
});

const OUTPUT = '/home/kali/ERR0RS-Ultimate/docs/ERR0RS_Ultimate_User_Manual_v3.4.0.docx';
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(OUTPUT, buf);
  console.log('DONE:', OUTPUT, '(' + Math.round(buf.length/1024) + 'KB)');
}).catch(e => { console.error('ERROR:', e.message); process.exit(1); });
