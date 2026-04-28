# THE HUMAN VARIABLE — A Red Team Operator's Field Guide to Social Engineering
## ERR0RS ULTIMATE | Knowledge Document
### "The most sophisticated firewall in the world falls to a polite phone call."

---

## PART I — WHY THIS MATTERS MORE THAN ANY TOOL

Every year the cybersecurity industry spends hundreds of billions of dollars
on technology. Firewalls. EDR. SIEM. Zero Trust. MFA. WAF. DLP. PAM.

And every year, the Verizon Data Breach Investigations Report (DBIR) says
the same thing: **74-82% of breaches involve a human.**

Not a zero-day. Not an unpatched server. A human being who clicked a link,
answered a phone call, held a door open, or plugged in a USB drive they found
in the parking lot.

This is not because people are stupid. It's because **the human brain was not
designed to operate at enterprise scale in an adversarial digital environment.**
Our social instincts — trust, helpfulness, authority deference, reciprocity —
evolved for small tribal groups where everyone was known. Attackers weaponize
those exact instincts against us.

Kevin Mitnick — the most famous social engineer in history — spent years
breaking into the most secure systems in the world. He rarely needed to exploit
software. He just asked people for what he needed. And they gave it to him.

A red team operator who understands this is infinitely more dangerous —
and infinitely more valuable to a client — than one who only knows Metasploit.

---

## PART II — THE SCIENCE: SIX PRINCIPLES OF INFLUENCE

Robert Cialdini's research identified the cognitive shortcuts humans use
to make decisions. Every social engineering attack exploits one or more:

### 1. Reciprocity
*We feel obligated to return favors.*
Attack application: Send a small gift, do a small favor, help first.
Then make your real request. Compliance skyrockets.

### 2. Commitment & Consistency
*We honor commitments we've already made.*
Attack application: The "yes ladder." Get small agreements first.
Each yes makes the next compliance more likely. Never lead with the big ask.

### 3. Social Proof
*We follow what others are doing, especially in uncertain situations.*
Attack application: "Everyone else in your department already completed this."
"I've already spoken with your colleagues." Creates normalcy.

### 4. Authority
*We defer to people who appear to be in positions of authority.*
Attack application: Impersonate IT, HR, auditors, executives, law enforcement.
Authority signals: title, uniform, technical jargon, confidence.

### 5. Liking
*We say yes to people we like.*
Attack application: Mirror the target's tone. Use their name. Find common ground.
Reference mutual connections. Smile in your voice.

### 6. Scarcity & Urgency
*We make poor decisions under time pressure.*
Attack application: "Your account locks in 10 minutes."
"The auditors are on-site right now." Compressed decision time = poor judgment.

---

## PART III — THE ATTACK SURFACE MAP

```
DIGITAL VECTORS                    PHYSICAL VECTORS
─────────────────                  ────────────────
Phishing (email)                   Tailgating / Piggybacking
Spear Phishing                     Impersonation in person
Whaling (C-suite)                  Badge cloning (Proxmark3, Flipper Zero)
BEC (compromised email)            USB drops (Rubber Ducky payloads)
Smishing (SMS)                     Lock picking / bypass
Vishing (voice)                    Shoulder surfing
Clone Phishing                     Dumpster diving
QR Code Phishing                   Eavesdropping
                                   Rogue WiFi / Evil Twin AP

HYBRID (most effective)
───────────────────────
Phishing email → vishing follow-up → physical visit
OSINT → spear phish → credential capture → network access
USB drop → reverse shell → lateral movement
```

---

## PART IV — OSINT: BUILDING THE TARGET PROFILE

**Before any attack, operators spend significant time on reconnaissance.**
Generic attacks catch 10% of targets. Personalized attacks catch 60-70%.
The investment in OSINT directly multiplies attack effectiveness.

### What to Collect

| Category | Sources | What It Enables |
|---|---|---|
| Name, role, dept | LinkedIn, company website | Personalization |
| Manager name | LinkedIn org chart | Authority pretext |
| Email format | Hunter.io, theHarvester | Target list generation |
| Technical stack | Job postings, LinkedIn skills | Technical pretext |
| Personal interests | Social media | Rapport building |
| Past breaches | HaveIBeenPwned, DeHashed | Password patterns |
| Physical location | Google Maps, site visit | Physical pretext |
| Vendor relationships | LinkedIn, job posts | Vendor pretext |

### Core OSINT Tools

**theHarvester** — Email and subdomain harvesting
```bash
theHarvester -d targetcompany.com -l 500 -b all
```

**Sherlock** — Username enumeration across 300+ platforms
```bash
python3 sherlock.py targetusername
```

**Maltego** — Relationship mapping and visualization
```
Person → Email → LinkedIn → Company → Colleagues → Org Chart
```

**Google Dorking** — Targeted search for exposed employee data
```
site:linkedin.com/in "Target Company" "IT Manager"
"@targetcompany.com" filetype:xlsx
site:targetcompany.com inurl:staff OR inurl:team
```

---

## PART V — PHISHING CAMPAIGNS

### The Anatomy of a High-Quality Phish

A successful phishing email must pass **the 3-second scan test**: when a busy
person glances at it, it must look completely legitimate.

**Five elements of a convincing phishing email:**

1. **Sender appearance** — Display name looks right. Domain is a convincing lookalike.
2. **Subject line** — Creates urgency, curiosity, or fear without triggering spam filters.
3. **Body content** — Matches the company's real communication style. References real context.
4. **Call to action** — Simple, specific, urgent.
5. **Legitimacy signals** — Company logo, footer, confidentiality notice, realistic links.

### Infrastructure Requirements

```
DOMAIN:      Register lookalike (company-support.net, cornpany.com)
             Age it 30+ days. Set SPF, DKIM, DMARC records.

DELIVERY:    SendGrid / Amazon SES / self-hosted SMTP
             Warm up IP gradually (10/day → 100/day → campaign)

LANDING PAGE: Clone with HTTrack. Host on VPS. Capture + redirect.
              Use HTTPS — targets trust the padlock.

TRACKING:    Per-target unique URLs. Email open pixels.
             Log: IP, browser, OS, timestamp, credentials.
```

### Tools

| Tool | Use Case | MFA Bypass |
|---|---|---|
| GoPhish | Campaign management, tracking, reporting | No |
| Evilginx2 | Reverse proxy — captures session tokens | **YES** |
| SET | Quick credential pages, payload delivery | No |
| Zphisher | Ready-made pages for 30+ platforms | No |

### GoPhish Workflow
```
1. ./gophish → admin panel https://localhost:3333
2. Sending Profiles → configure SMTP relay
3. Email Templates → build phishing email
4. Landing Pages → clone target login page
5. Users & Groups → import target CSV
6. Campaigns → link all components → Launch
7. Monitor Results dashboard in real time
```

---

## PART VI — VISHING (VOICE PHISHING)

Voice calls are the most underestimated attack vector in security.
A skilled operator can extract credentials, reset passwords, and
obtain physical access in a single 5-minute phone call.

### The Call Framework

```
1. HOOK (0-10s):    Establish identity and authority immediately.
2. RAPPORT (10-30s): Use their name. Be calm and professional.
3. PRETEXT (30-90s): Build the believable scenario with real details.
4. YES LADDER:       Small agreements before the big ask.
5. ELICITATION:      Extract the objective naturally.
6. CLOSE:            Exit gracefully. Give them a ticket number.
```

### The Yes Ladder in Action
```
"Can you confirm you're at your workstation?"           → Yes
"And you're logged into the system currently?"          → Yes
"You haven't noticed anything unusual today?"           → No
"Great, let me pull up your account."                   → OK
"Can you confirm your username for me?"                 → [GIVES IT]
```
*Each 'yes' lowers resistance to the next request.*

### Technical Support (Caller ID Spoof to Internal Extension)
```
"Hi, this is Mike from IT Security. Am I speaking with [name]?
We've detected anomalous activity on your account. Our monitoring
flagged unusual login patterns — we're calling everyone in [dept]
as a precaution. Can I walk you through a quick verification?"
```

### Caller ID Spoofing Tools
- SpoofCard / SpoofTel — consumer apps
- Twilio API — programmable caller ID
- Asterisk PBX — full telephony control

---

## PART VII — PHYSICAL SOCIAL ENGINEERING

**Physical access defeats every technical control.**
A determined operator with a convincing uniform and a box of equipment
can walk into most corporate buildings without a valid badge.

### Entry Techniques

| Technique | Success Rate | Requirements |
|---|---|---|
| Tailgating (hands full) | ~80% | Boxes, equipment bags |
| Smoker's entrance | ~90% | Timing, observation |
| New employee pretext | ~75% | Casual confidence |
| Delivery impersonation | ~70% | Package, target name |
| IT contractor | ~65% | Laptop bag, polo shirt |

### Physical Tools

**Proxmark3** — Professional RFID/NFC reader/writer
- Clones HID, EM4100, MIFARE, iClass badges
- Most building access badges are 125kHz HID — trivially cloned

**Flipper Zero** — Reads 125kHz RFID at badge distance
- Compact, covert, easy to carry

**Lock Pick Set** — Most interior office doors are trivial to pick

**USB Drops** — Label as "Q4 Salaries" or "Executive Layoff List"
- Studies: 45-98% of found USBs get plugged in
- Payload: HID attack, LNK credential capture, hardware keylogger

---

## PART VIII — BUILDING HUMAN-RESISTANT ORGANIZATIONS

*Understanding the attack is useless without building the defense.*

### What Doesn't Work
- Annual compliance training (forgotten within 72 hours)
- Checkbox security awareness programs
- Punishing employees who click phishing tests
- Generic training not tailored to role-specific risks

### What Does Work

**Simulated Phishing (Monthly)**
- GoPhish campaigns with immediate teachable feedback
- Track: click rate (<5%), credential submission (<1%), report rate (>70%)
- Celebrate reporting — it's the correct behavior

**Role-Specific Training**
- Finance → BEC and wire fraud scenarios
- Executives → Targeted spear phishing and whaling
- IT → Vendor impersonation and technical pretexts
- Reception → Tailgating and in-person impersonation

**Process Controls That Matter**
- Password resets: NEVER over the phone — always self-service portal
- Wire transfers: dual authorization + out-of-band callback
- Visitor management: pre-registration required for all visitors
- Badge policy: everyone challenges badge-less individuals

**Phishing-Resistant MFA**
- FIDO2/Passkeys (hardware security keys) → immune to Evilginx2
- TOTP and SMS MFA → bypassed by reverse proxy attacks
- Push MFA → vulnerable to MFA fatigue attacks

---

## PART IX — PURPLE TEAM — ATTACK AND MEASURE

After every SE engagement, provide defenders with:

### Detection Opportunities
```
EMAIL:    New domains not seen before (30-day lookback)
          Failed DMARC checks on spoofed senders
          Links to lookalike domains in email body
          Unusual email volume from known domains

NETWORK:  DNS queries to newly registered domains
          HTTP POST to unfamiliar external IPs (credential submission)
          Traffic to domains registered <30 days ago

ENDPOINT: New process execution from browser (payload clicked)
          PowerShell download from internet
          Unusual parent-child process relationships

VOICE:    Unusual caller ID patterns in phone logs
          Password reset requests correlated with phone activity
          Out-of-hours call activity
```

### MITRE ATT&CK Mapping
```
T1566.001  Phishing: Spearphishing Attachment
T1566.002  Phishing: Spearphishing Link
T1566.003  Phishing: Spearphishing via Service
T1598.003  Phishing for Information: Spearphishing Link
T1534      Internal Spearphishing (post-compromise BEC)
T1204.001  User Execution: Malicious Link
T1204.002  User Execution: Malicious File
T1078      Valid Accounts (credential theft outcome)
T1557      Adversary-in-the-Middle (Evilginx2 technique)
```

---

*ERR0RS ULTIMATE | Social Engineering Knowledge Base*
*All techniques require explicit written authorization from the client.*
*Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone*
