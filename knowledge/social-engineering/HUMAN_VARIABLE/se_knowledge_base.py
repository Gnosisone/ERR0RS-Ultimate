# ERR0RS ULTIMATE — Social Engineering & The Human Variable
# Complete Red Team Knowledge Base
# ============================================================
# "Technology is not the weakest link. People are."
#  — Kevin Mitnick, The Art of Deception
#
# This knowledge base covers the psychology, methodology, and
# techniques behind social engineering from a RED TEAM perspective.
# The goal: understand it deeply so you can test it, defend against
# it, and build organizations that are resistant to it.
#
# LEGAL: All techniques require explicit written authorization.
# Social engineering testing without consent is a federal crime.
# ============================================================

SE_KNOWLEDGE_BASE = {

# ═══════════════════════════════════════════════════════════════
# FOUNDATION — WHY THE HUMAN IS THE PRIMARY ATTACK SURFACE
# ═══════════════════════════════════════════════════════════════

"why_human_variable": {
    "title": "The Human Variable — Why People Are the #1 Attack Surface",
    "tldr": (
        "Technology can be patched. Humans cannot be patched. "
        "The human brain has cognitive vulnerabilities that are consistent, "
        "predictable, and exploitable. This makes people the most reliable "
        "entry point into any organization — regardless of technical controls."
    ),
    "the_truth": (
        "Verizon's Data Breach Investigations Report (DBIR) consistently "
        "shows that 74-82% of breaches involve the human element. Phishing, "
        "pretexting, stolen credentials, and insider threats dominate. "
        "You can spend $10 million on firewalls, EDR, SIEM, and Zero Trust "
        "architecture — and a single employee clicking a link bypasses all of it.\n\n"
        "The best penetration testers in the world will tell you the same thing: "
        "the fastest, most reliable path into any organization is through a person, "
        "not a vulnerability scanner. Kevin Mitnick — arguably the most famous "
        "hacker in history — said he never needed to break encryption or exploit "
        "software. He just asked people for what he needed, and they gave it to him."
    ),
    "the_psychology": (
        "The human brain is NOT designed to detect deception at scale. "
        "It evolved for small tribal groups where most people were known and trusted. "
        "The cognitive shortcuts (heuristics) that make us efficient also make us "
        "exploitable. These are not weaknesses unique to uneducated people — "
        "they affect everyone, including security professionals.\n\n"
        "Core cognitive vulnerabilities:\n"
        "  AUTHORITY BIAS: We defer to people who appear to be in authority.\n"
        "  SOCIAL PROOF: We follow what others are doing.\n"
        "  SCARCITY/URGENCY: We make poor decisions under time pressure.\n"
        "  RECIPROCITY: We feel obligated to return favors.\n"
        "  LIKING: We comply with people we like or find attractive.\n"
        "  COMMITMENT/CONSISTENCY: We honor commitments we've already made.\n"
        "  FEAR: We act irrationally to avoid negative outcomes.\n"
        "  CURIOSITY: We click things we shouldn't because we want to know.\n"
        "  HELPFULNESS: We want to be useful and avoid conflict.\n"
        "  TRUST by DEFAULT: We assume legitimacy until proven otherwise."
    ),
    "cialdini_principles": (
        "Robert Cialdini's 7 Principles of Influence form the scientific "
        "foundation of social engineering. Every SE attack uses one or more:\n\n"
        "1. RECIPROCITY — Give something first. The target feels obligated.\n"
        "   Example: 'I stayed late to help you last week, can you just...' \n\n"
        "2. COMMITMENT/CONSISTENCY — Get small yeses first. Escalate.\n"
        "   Example: Get them to confirm their name, then department, then access.\n\n"
        "3. SOCIAL PROOF — 'Everyone else in your department already did this.'\n"
        "   Example: 'I've already spoken with your colleagues, they all verified.'\n\n"
        "4. AUTHORITY — Impersonate someone with power over the target.\n"
        "   Example: Pose as IT, HR, C-suite, auditor, law enforcement.\n\n"
        "5. LIKING — People say yes to people they like.\n"
        "   Example: Find common ground, mirror behavior, use their name.\n\n"
        "6. SCARCITY — Create urgency. Compress decision time.\n"
        "   Example: 'The system will lock in 10 minutes if you don't verify.'\n\n"
        "7. UNITY — We trust members of our in-group.\n"
        "   Example: 'As a fellow veteran / parent / engineer, I understand...'"
    ),
    "attack_taxonomy": (
        "Social engineering attacks fall into four delivery vectors:\n\n"
        "DIGITAL:  Phishing (email), Smishing (SMS), Vishing (voice),\n"
        "          Spear phishing, Whaling, Business Email Compromise (BEC)\n\n"
        "PHYSICAL: Tailgating, Impersonation in person, USB drops,\n"
        "          Badge cloning, Dumpster diving, Shoulder surfing\n\n"
        "HYBRID:   Combination of digital + physical (most effective)\n"
        "          e.g., Phishing email + phone call + fake badge\n\n"
        "INSIDER:  Disgruntled employees, coerced employees, planted agents"
    ),
    "red_team_truth": (
        "On a real red team engagement, SE is almost always the fastest path.\n"
        "A phishing email takes 20 minutes to build and deploy.\n"
        "A vishing call takes 5 minutes and bypasses every technical control.\n"
        "A physical impersonation gets you past $500,000 worth of access controls.\n\n"
        "The technical tools — Metasploit, Mimikatz, Cobalt Strike — are often\n"
        "SECONDARY. SE gets the initial foothold. Technical tools expand it.\n"
        "This is why the most dangerous threat actors in the world — nation-state\n"
        "APTs, organized crime, ransomware groups — all lead with phishing."
    ),
},

# ═══════════════════════════════════════════════════════════════
# OSINT — RECONNAISSANCE ON THE HUMAN TARGET
# ═══════════════════════════════════════════════════════════════

"osint_human_recon": {
    "title": "OSINT — Reconnaissance on Human Targets",
    "tldr": (
        "Before any social engineering attack, operators spend significant "
        "time profiling human targets. The more you know, the more believable "
        "your pretext. OSINT on humans is the foundation of effective SE."
    ),
    "why_recon_first": (
        "Generic phishing catches 10% of recipients. Targeted spear phishing "
        "with good OSINT catches 60-70%. The difference is personalization.\n\n"
        "If you know: the target's manager's name, their current project, "
        "their dog's name from Instagram, and their college — your email "
        "reads as completely legitimate. They never question it."
    ),
    "tools_and_methods": {
        "LinkedIn": (
            "The gold mine. LinkedIn reveals: full name, job title, "
            "department, manager (inferred), colleagues, job history, "
            "skills, projects they mention, events they attended, "
            "certifications they hold, technologies they use.\n"
            "Technique: Build an org chart of the entire target company "
            "just from LinkedIn. Find who's in IT. Find who's in finance. "
            "Find who's new (easiest targets — they don't know the culture yet)."
        ),
        "theHarvester": (
            "Email address harvesting.\n"
            "Command: theHarvester -d targetcompany.com -l 500 -b all\n"
            "Finds: employee emails, subdomains, hosts, IPs\n"
            "Use output to build target list for phishing campaigns."
        ),
        "Hunter.io": (
            "Email format discovery.\n"
            "Go to hunter.io, enter company domain.\n"
            "Shows: email format (firstname.lastname@company.com),\n"
            "       verified employee emails, confidence scores.\n"
            "Then: generate emails for all LinkedIn employees using the format."
        ),
        "Maltego": (
            "Graph-based OSINT visualization.\n"
            "Transforms: Person → Email → Domain → IP → Social Profiles\n"
            "Shows relationships between entities visually.\n"
            "Finds connections a manual search would miss.\n"
            "Community edition is free, commercial has more transforms."
        ),
        "Sherlock": (
            "Username search across 300+ platforms.\n"
            "Command: python3 sherlock.py targetusername\n"
            "Finds: all accounts with that username across the internet.\n"
            "Reveals: hobbies, interests, location clues, other names used."
        ),
        "Google Dorking": (
            "Targeted Google searches to find exposed employee data.\n"
            "site:linkedin.com/in 'company name' 'job title'\n"
            "site:company.com filetype:pdf 'employee'\n"
            "site:company.com inurl:staff\n"
            "'@company.com' filetype:xls\n"
            "Finds: employee directories, org charts, email lists."
        ),
        "Social Media": (
            "Facebook/Instagram: Personal life details for pretexting.\n"
            "  - Name of spouse, children, pets → password hints\n"
            "  - Location check-ins → where they live/work/travel\n"
            "  - Employer listed → confirms LinkedIn data\n"
            "  - Photos in office → badge design, desk layout, tech stack\n\n"
            "Twitter/X: Real-time intelligence.\n"
            "  - Complaints about work systems → tech stack clues\n"
            "  - Travel announcements → timing for attacks\n"
            "  - Conversations with colleagues → org chart data"
        ),
        "WHOIS + DNS": (
            "whois targetcompany.com → Admin contact emails, phone numbers\n"
            "dig targetcompany.com MX → Mail server (helps craft believable emails)\n"
            "dig targetcompany.com TXT → SPF records → understand email security\n"
            "Reverse IP lookup → Find other domains on same infrastructure"
        ),
        "Breach Data": (
            "Check if target employees appear in past data breaches.\n"
            "Tools: HaveIBeenPwned API, DeHashed, IntelligenceX\n"
            "Finds: leaked passwords (reused?), old emails, phone numbers\n"
            "If their old password was 'Company2018!' → try 'Company2024!'"
        ),
        "Physical Recon": (
            "Drive/walk past the target location:\n"
            "  - What's the badge look like? (Color, logo placement)\n"
            "  - What uniform does security/IT wear?\n"
            "  - What vendors come and go? (Delivery companies, IT support)\n"
            "  - Where do smokers congregate? (Easy tailgating opportunity)\n"
            "  - What's visible through windows?\n"
            "  - How does the door access work? (Badge tap? PIN? Guard?)"
        ),
    },
    "building_target_profile": (
        "OSINT output → Target Profile document:\n\n"
        "PERSONAL: Full name, personal email, phone, address area, family\n"
        "PROFESSIONAL: Title, department, manager, team members, tenure\n"
        "TECHNICAL: What systems they use (from job postings, LinkedIn skills)\n"
        "BEHAVIORAL: Work hours (social media), travel patterns, interests\n"
        "PASSWORDS: Breach data, common patterns based on personal info\n"
        "PRETEXT HOOKS: What would make them respond? Fear? Authority? Curiosity?\n\n"
        "This profile drives every decision about attack vector and pretext."
    ),
},

# ═══════════════════════════════════════════════════════════════
# PHISHING — EMAIL-BASED SOCIAL ENGINEERING
# ═══════════════════════════════════════════════════════════════

"phishing_deep_dive": {
    "title": "Phishing — The #1 Initial Access Vector",
    "tldr": (
        "Phishing uses deceptive emails to trick targets into "
        "revealing credentials, clicking malicious links, or opening "
        "malicious attachments. It is responsible for over 90% of "
        "successful cyberattacks worldwide."
    ),
    "phishing_types": {
        "Mass Phishing": (
            "Sent to thousands of recipients with generic content.\n"
            "Low personalization. Relies on volume.\n"
            "Example: 'Your account has been suspended. Click here.'\n"
            "Catch rate: 5-10% of recipients."
        ),
        "Spear Phishing": (
            "Targeted at specific individuals or organizations.\n"
            "High personalization using OSINT data.\n"
            "Example: Email to 'John' from 'his manager Sarah' about\n"
            "         'the Q3 budget report they discussed on Tuesday.'\n"
            "Catch rate: 60-70% of recipients."
        ),
        "Whaling": (
            "Spear phishing targeting executives (CEO, CFO, CISO).\n"
            "Higher effort. Higher reward.\n"
            "CEO Fraud: Impersonate CEO to instruct CFO to wire funds.\n"
            "These attacks cost organizations billions annually."
        ),
        "Business Email Compromise (BEC)": (
            "Attacker takes over a real email account (no spoofing needed).\n"
            "Most credible form — legitimate email address.\n"
            "Used for: wire fraud, credential theft, supply chain attacks.\n"
            "FBI reports BEC losses exceed $2.9 billion annually."
        ),
        "Vishing": (
            "Voice phishing — phone calls.\n"
            "Caller impersonates: IT support, HR, bank, IRS, vendor.\n"
            "Advantages: Real-time rapport building, harder to verify,\n"
            "            voice builds trust faster than email.\n"
            "Most effective when combined with a prior phishing email."
        ),
        "Smishing": (
            "SMS phishing.\n"
            "High open rate (98% vs 20% for email).\n"
            "Common: 'Your package has been held. Verify here: [link]'\n"
            "        'Your bank account is locked. Text YES to confirm.'"
        ),
        "Clone Phishing": (
            "Take a legitimate email, clone it exactly, swap the link.\n"
            "Pretend to be a resend: 'Resending — the link was broken.'\n"
            "Requires: access to one real email the target received.\n"
            "Very effective because everything looks exactly right."
        ),
    },
    "anatomy_of_effective_phish": (
        "A high-quality phishing email has these elements:\n\n"
        "SENDER SPOOFING:\n"
        "  Display name: 'Sarah Mitchell - IT Help Desk'\n"
        "  Actual address: support@company-helpdesk.net (lookalike domain)\n"
        "  Legitimate-looking: subdomain tricks, unicode characters\n\n"
        "SUBJECT LINE — must create urgency or curiosity:\n"
        "  'Action Required: Your account will be locked in 24 hours'\n"
        "  'John — Q3 bonus payout — verify your banking details'\n"
        "  'Security alert: Unusual login from Moscow detected'\n"
        "  '[EXTERNAL] Re: Tuesday meeting notes'\n\n"
        "BODY — must look exactly like real corporate communications:\n"
        "  - Use real logo (scraped from company website)\n"
        "  - Match font, color scheme, footer style\n"
        "  - Reference real events/projects (from OSINT)\n"
        "  - Use target's actual manager's name\n"
        "  - Include legitimate-looking links alongside the malicious one\n\n"
        "CALL TO ACTION — clear, simple, urgent:\n"
        "  'Click here to verify' / 'Open attachment to review' /\n"
        "  'Reply with confirmation' / 'Call this number immediately'\n\n"
        "LEGITIMACY SIGNALS:\n"
        "  - Email footer with real company address\n"
        "  - Confidentiality notice\n"
        "  - Unsubscribe link (makes it look like legitimate comms system)\n"
        "  - Correct grammar and professional tone"
    ),
    "technical_infrastructure": (
        "What you need to run a phishing campaign:\n\n"
        "DOMAIN: Register lookalike domain\n"
        "  - Add typosquatting: cornpany.com vs company.com\n"
        "  - Add subdomain: mail.company-support.com\n"
        "  - Add TLD swap: company.net vs company.com\n"
        "  - Allow domain to 'age' (fresh domains flagged by filters)\n\n"
        "EMAIL INFRASTRUCTURE:\n"
        "  - Set up SPF, DKIM, DMARC on lookalike domain (boosts deliverability)\n"
        "  - Use SendGrid, Mailgun, or Amazon SES for delivery\n"
        "  - Warm up sending IP gradually (start with 10/day, scale up)\n"
        "  - Rotate sending addresses and domains\n\n"
        "LANDING PAGE:\n"
        "  - Clone the real login page using HTTrack or wget\n"
        "  - Host on VPS (not linked to your identity)\n"
        "  - Capture: username, password, MFA token (real-time relay)\n"
        "  - Redirect to real site after capture (target never knows)\n\n"
        "TRACKING:\n"
        "  - Unique link per target (track who clicked)\n"
        "  - Pixel tracking in email body (track who opened)\n"
        "  - Log: timestamp, IP, browser, OS, username submitted"
    ),
    "tools": {
        "GoPhish": (
            "Open-source phishing framework.\n"
            "Features: Campaign management, email templates, landing pages,\n"
            "          real-time dashboard, per-target tracking, reporting.\n"
            "Install: apt install gophish\n"
            "Start: ./gophish → admin interface at https://localhost:3333\n"
            "Workflow: Groups → Templates → Landing Pages → Sending Profile → Campaign"
        ),
        "Evilginx2": (
            "Reverse proxy phishing framework. Bypasses MFA.\n"
            "How it works: Sits between target and legitimate site.\n"
            "              Captures session tokens IN ADDITION to credentials.\n"
            "              Even if target uses MFA — attacker gets the session cookie.\n"
            "Install: git clone https://github.com/kgretzky/evilginx2\n"
            "Phishlets: Pre-built configs for Gmail, Microsoft, Facebook, etc.\n"
            "Critical capability: Modern MFA bypass."
        ),
        "Social Engineering Toolkit (SET)": (
            "Comprehensive SE framework built into Kali.\n"
            "Command: setoolkit\n"
            "Options: Spear phishing, credential harvester, website cloner,\n"
            "         PowerShell payloads, mass mailer, QRCode generator.\n"
            "Best for: Quick credential harvesting pages, payload delivery."
        ),
        "Modlishka": (
            "Another reverse proxy for real-time credential capture.\n"
            "Similar to Evilginx but different architecture.\n"
            "Supports: 2FA bypass, custom domains, SSL termination."
        ),
    },
    "pretext_examples": {
        "IT Password Reset": (
            "From: helpdesk@company-it-support.com\n"
            "Subject: [URGENT] Password Expiration Notice — Action Required Today\n\n"
            "Hi John,\n\n"
            "Our security system has flagged your account for mandatory password "
            "reset due to potential exposure in a recent third-party breach.\n\n"
            "Your access will be suspended at 5:00 PM today if you do not "
            "complete the reset process.\n\n"
            "Reset your password now: [MALICIOUS LINK]\n\n"
            "If you need assistance, call the IT Help Desk at x5555.\n\n"
            "— IT Security Team"
        ),
        "CEO Wire Transfer (BEC)": (
            "From: ceo.lastname@company-corp.com [spoofed]\n"
            "Subject: Confidential — Time Sensitive\n\n"
            "Hi Sarah,\n\n"
            "I'm in a board meeting and need you to process an urgent wire "
            "transfer. This is time-sensitive and confidential — please do not "
            "discuss with others until complete.\n\n"
            "$47,500 to be wired to our new vendor. I'll send account details "
            "in 5 minutes. Please confirm you can handle this now.\n\n"
            "— Michael [CEO first name]"
        ),
        "HR Benefits Update": (
            "From: hr-benefits@company-hrportal.net\n"
            "Subject: Action Required: Update Your Benefits Selections by Friday\n\n"
            "Dear Team Member,\n\n"
            "Open enrollment ends this Friday. All employees must log in to "
            "verify their benefits selections or default enrollment will apply.\n\n"
            "Several employees in your department have already completed this.\n\n"
            "Access your benefits portal: [CREDENTIAL HARVESTER]\n\n"
            "— Human Resources"
        ),
    },
    "red_team_notes": (
        "OPSEC:\n"
        "- Never phish from your own IP or infrastructure linked to you\n"
        "- Use VPS paid with cryptocurrency or gift cards\n"
        "- Rotate infrastructure between campaigns\n"
        "- Use HTTPS on landing pages (targets trust the padlock)\n\n"
        "BYPASSING FILTERS:\n"
        "- Age your domain (register weeks before campaign)\n"
        "- Set correct SPF/DKIM/DMARC records\n"
        "- Avoid spam trigger words in subject\n"
        "- Use redirect chains (legitimate site → your page)\n"
        "- QR codes in emails bypass URL scanners\n"
        "- HTML smuggling bypasses attachment scanners\n\n"
        "PURPLE TEAM NOTE:\n"
        "Detection: Email gateway logs, proxy logs showing new domains,\n"
        "DNS queries to lookalike domains, failed MFA attempts.\n"
        "Defense: DMARC enforcement, email security gateways,\n"
        "security awareness training, MFA everywhere."
    ),
},

# ═══════════════════════════════════════════════════════════════
# VISHING — VOICE PHISHING DEEP DIVE
# ═══════════════════════════════════════════════════════════════

"vishing": {
    "title": "Vishing — Voice-Based Social Engineering",
    "tldr": (
        "Phone calls are the most underestimated attack vector. "
        "A skilled caller can extract credentials, reset passwords, "
        "and obtain physical access in a single 5-minute conversation. "
        "Voice builds trust faster than any other medium."
    ),
    "why_voice_works": (
        "Human voice activates parts of the brain that text cannot reach.\n"
        "We are wired to respond to voices — it triggers empathy,\n"
        "social obligation, and authority compliance automatically.\n\n"
        "Key advantages for attackers:\n"
        "- Real-time rapport building and course correction\n"
        "- Harder for target to verify identity mid-call\n"
        "- Urgency is more believable verbally\n"
        "- Target cannot screenshot or forward the call for review\n"
        "- Most organizations have NO vishing detection capability"
    ),
    "call_framework": (
        "Every successful vishing call follows this structure:\n\n"
        "1. HOOK (0-10 seconds): Establish authority immediately.\n"
        "   'Hi, this is Mike from the IT Security team calling about\n"
        "    an urgent security incident on your account.'\n\n"
        "2. RAPPORT (10-30 seconds): Make them comfortable.\n"
        "   Use their name. Reference something real (from OSINT).\n"
        "   Mirror their tone and pace. Be professional and calm.\n\n"
        "3. PRETEXT (30-90 seconds): Build the believable scenario.\n"
        "   Explain WHY you're calling. Use technical-sounding details.\n"
        "   Reference real systems, real processes, real people.\n\n"
        "4. ELICITATION (varies): Extract what you need.\n"
        "   Never ask directly at first. Build to it naturally.\n"
        "   Use the 'yes ladder' — small agreements before the big ask.\n\n"
        "5. CLOSE: Get what you need and exit gracefully.\n"
        "   Thank them. Give them a ticket number (fake but believable).\n"
        "   Tell them what to expect next (normalizes the interaction)."
    ),
    "voice_techniques": {
        "Authority Spoofing": (
            "Caller ID can be spoofed trivially using:\n"
            "  - SpoofCard, SpoofTel, Caller ID Faker apps\n"
            "  - Twilio API with custom caller ID\n"
            "  - Asterisk PBX with custom CID settings\n\n"
            "Always spoof to match the pretext:\n"
            "  - IT Help Desk → spoof internal extension (x5555)\n"
            "  - Bank → spoof bank's real 1-800 number\n"
            "  - Vendor → spoof vendor's main line"
        ),
        "Voice Changers": (
            "If gender-swapping or accent adjustment helps the pretext:\n"
            "  - Clownfish Voice Changer (Windows, real-time)\n"
            "  - MorphVOX Pro (professional quality)\n"
            "  - Voicemod (real-time)\n"
            "  - Adobe Podcast (AI voice enhancement)\n"
            "AI voice cloning (ElevenLabs) can clone a specific person's voice\n"
            "with just 30 seconds of sample audio. Deepfake audio is here."
        ),
        "The Yes Ladder": (
            "Never ask for what you want directly.\n"
            "Build a series of small agreements first:\n\n"
            "'Can you confirm your name for me?' → Yes\n"
            "'And you're in the Accounting department?' → Yes\n"
            "'You have access to the AP system?' → Yes\n"
            "'Great. I'm going to walk you through a verification process.' → OK\n"
            "'Can you open the system for me?' → Sure\n"
            "'What does it show on screen?' → [gives information]\n\n"
            "Each 'yes' makes the next compliance more likely.\n"
            "The brain wants to stay consistent with prior agreements."
        ),
        "Urgency Creation": (
            "Manufactured urgency compresses decision time.\n"
            "Compressed decision time = poor judgment = compliance.\n\n"
            "Scripts:\n"
            "'We're detecting active malware on your workstation RIGHT NOW.'\n"
            "'Your account will be locked in the next 15 minutes.'\n"
            "'The auditors are on-site and need this information immediately.'\n"
            "'I have three other tickets — I need to resolve yours NOW or escalate.'"
        ),
        "Technical Intimidation": (
            "Use technical jargon to establish expertise and overwhelm.\n"
            "The target doesn't understand it — they defer to 'the expert.'\n\n"
            "'We're seeing anomalous lateral movement in your subnet segment,\n"
            "and the SIEM has flagged your workstation's MAC address as\n"
            "the origin of the C2 beacon. I need to verify your credentials\n"
            "so we can isolate the affected endpoint before the SOC escalates.'\n\n"
            "The target understands almost none of that. They hear:\n"
            "'Something bad is happening and you need to cooperate.'"
        ),
        "Elicitation Techniques": (
            "From professional intelligence tradecraft:\n\n"
            "BRACKETING: Give a false range to extract real answer.\n"
            "  'Most organizations have 5-10 people in IT. You probably\n"
            "   have around 8?' → Target corrects: 'No, we have 23.'\n\n"
            "FLATTERY: Compliment expertise to get information.\n"
            "  'You clearly know this system well. How does the backup\n"
            "   process work on your end?' → Target explains everything.\n\n"
            "QUID PRO QUO: Offer something first.\n"
            "  'I can tell you exactly what's causing the slowness\n"
            "   if you can just confirm your username for me first.'\n\n"
            "APPEAL TO EGO: People like being the expert.\n"
            "  'Can you walk me through how you handle the account lockouts?\n"
            "   Our documentation is unclear and you seem to know this best.'"
        ),
    },
    "pretexts": {
        "IT Help Desk": (
            "Most reliable pretext. Every company has IT support.\n"
            "Script: 'Hi, this is support calling from the IT team.\n"
            "We're rolling out a critical security patch today and need\n"
            "to verify your account is ready. Can I get your username\n"
            "so I can confirm your profile is set up correctly?'"
        ),
        "HR/Payroll": (
            "Targets the desire to get paid correctly.\n"
            "Script: 'We're updating our direct deposit system before\n"
            "Friday's payroll run. I just need to confirm your employee\n"
            "ID and verify the last 4 digits of your SSN match our records.'"
        ),
        "Security Audit": (
            "Exploits compliance culture in regulated industries.\n"
            "Script: 'I'm calling from Corporate Risk Management. We're\n"
            "conducting a security audit and your department was flagged.\n"
            "I need to verify that your credentials are current and your\n"
            "system access matches what HR has on file.'"
        ),
        "Vendor/Supplier": (
            "Many employees handle vendor relationships.\n"
            "Script: 'Hi, this is calling from Acme Systems — we handle\n"
            "your company's backup services. We need to verify the server\n"
            "credentials are still correct before tonight's backup window.'"
        ),
    },
    "red_team_vishing_workflow": (
        "Pre-call preparation (30 minutes):\n"
        "  1. OSINT target: name, role, manager name, department\n"
        "  2. Research company: IT systems used, help desk number, culture\n"
        "  3. Build pretext around REAL context (ongoing project, recent news)\n"
        "  4. Set up spoofed caller ID\n"
        "  5. Write call script but be ready to improvise\n"
        "  6. Record the call (with consent in your jurisdiction)\n\n"
        "During call:\n"
        "  - Speak with confidence — hesitation kills credibility\n"
        "  - Use their name naturally\n"
        "  - If challenged: don't panic, deflect with more detail\n"
        "  - If successful: exit quickly and gracefully\n\n"
        "Post-call:\n"
        "  - Document exactly what was obtained and how\n"
        "  - Note what worked and what created resistance\n"
        "  - Add to engagement report with recommendations"
    ),
},

# ═══════════════════════════════════════════════════════════════
# PHYSICAL SOCIAL ENGINEERING
# ═══════════════════════════════════════════════════════════════

"physical_se": {
    "title": "Physical Social Engineering — Boots on the Ground",
    "tldr": (
        "Physical social engineering bypasses every digital security control. "
        "Tailgating, impersonation, and pretexting in person are often "
        "the fastest paths to critical infrastructure. A confident walk "
        "and a convincing uniform defeats a $1M access control system."
    ),
    "tailgating": {
        "definition": (
            "Following an authorized person through a secured door "
            "without using your own credentials. Also called 'piggybacking.'\n"
            "Success rate in studies: 70-80% of attempts succeed.\n"
            "The human instinct not to be rude overcomes security training."
        ),
        "techniques": (
            "HANDS FULL METHOD:\n"
            "Carry boxes, equipment, coffee trays. People hold doors for\n"
            "someone whose hands are full. Works nearly every time.\n\n"
            "THE HURRY METHOD:\n"
            "Act like you're rushing. Walk fast. Look stressed.\n"
            "People don't stop someone who looks busy and legitimate.\n\n"
            "THE CONVERSATION METHOD:\n"
            "Strike up a conversation with an employee near the door.\n"
            "Walk in mid-conversation — they assume you're authorized.\n\n"
            "SMOKER'S ENTRANCE:\n"
            "Smoke breaks create low-security side entrances.\n"
            "Employees prop doors open, bypass card readers.\n"
            "This is consistently the weakest physical entry point."
        ),
    },
    "impersonation": {
        "IT Contractor": (
            "Most universal. Every building has IT contractors.\n"
            "Equipment: Laptop bag, network cable, generic polo shirt.\n"
            "Pretext: 'I'm here to upgrade the network switch in server room 3.'\n"
            "Confidence is the costume. Walk like you own the building."
        ),
        "Delivery Person": (
            "High-volume foot traffic makes delivery expected.\n"
            "Equipment: Box/package addressed to real employee (OSINT).\n"
            "Pretext: 'Package for John Smith. I need a signature.'\n"
            "Gets you: Physical access, employee names confirmed, layout intel."
        ),
        "Fire Inspector / Safety Auditor": (
            "Authority plus urgency plus legitimate reason to access anywhere.\n"
            "Pretext: 'I'm from the city fire marshal office doing a safety\n"
            "inspection. I need to check all server rooms and electrical panels.'\n"
            "Few employees will challenge a fire inspector — liability fear."
        ),
        "Cleaning Crew": (
            "Invisible by design. Cleaning staff are overlooked everywhere.\n"
            "Accessed after hours — most secure areas are open.\n"
            "Can: plant hardware keyloggers, take photos, pull documents,\n"
            "     install rogue network devices, access unlocked workstations."
        ),
        "New Employee": (
            "New employees don't know the culture, so they're forgiven.\n"
            "They also look uncertain — which looks exactly like a new employee.\n"
            "Pretext: 'Hi, I just started in marketing last week. I'm trying\n"
            "to find the IT desk to get my badge sorted out.'\n"
            "People help confused new employees without questioning identity."
        ),
    },
    "physical_tools": {
        "Lock Picks": (
            "Basic pick set for pin tumbler locks.\n"
            "Bump keys for faster entry on standard locks.\n"
            "Most interior office doors are trivial to pick.\n"
            "Practice tool: Transparent practice locks before field use."
        ),
        "Badge Cloners": (
            "Proxmark3: Professional RFID/NFC read/write device.\n"
            "  Can clone HID, EM4100, MIFARE, iClass badges.\n"
            "  Range: 1-2 inches for passive reads.\n"
            "Flipper Zero: Consumer-friendly RFID cloner.\n"
            "  Reads 125kHz (HID, EM4100) in badge scanning range.\n"
            "  Covert long-range readers can clone at 3+ feet.\n"
            "Reality: Most building access systems use 125kHz HID — easily cloned."
        ),
        "USB Drops": (
            "Leave labeled USB drives in target parking lot/lobby.\n"
            "Label examples: 'Q4 Salaries', 'Layoff List', 'Executive Photos'\n"
            "Studies show 45-98% of found USBs get plugged in.\n"
            "Payload options:\n"
            "  - HID attack (Rubber Ducky payload auto-executes)\n"
            "  - LNK file pointing to attacker's server (credential capture)\n"
            "  - AutoRun malware (older Windows systems)\n"
            "  - Hardware keylogger disguised as USB drive"
        ),
        "Shoulder Surfing": (
            "Observe credentials, PINs, or sensitive data visually.\n"
            "Locations: coffee shops, open office plans, public transport.\n"
            "Tools: Camera in glasses, phone propped as 'reading', binoculars.\n"
            "Specific targets: badge PIN pads, laptop screens, phone PINs."
        ),
        "Dumpster Diving": (
            "Legal in most public spaces (varies by jurisdiction).\n"
            "Targets: Company dumpsters for discarded documents.\n"
            "Often finds: Org charts, employee directories, vendor lists,\n"
            "             system diagrams, login credentials on sticky notes,\n"
            "             old hard drives, backup tapes, policy documents."
        ),
    },
    "physical_engagement_workflow": (
        "PHASE 1 — Passive Physical Recon (no contact):\n"
        "  Drive/walk the area. Photograph entrances, parking, badge readers.\n"
        "  Note shift changes, delivery windows, smoking areas.\n"
        "  Observe employee attire, badge styles, vendor vehicles.\n\n"
        "PHASE 2 — Active Physical Recon (limited contact):\n"
        "  Enter lobby. Photograph directory, note reception process.\n"
        "  Attempt visitor badge process to understand procedures.\n"
        "  Test if anyone challenges photography/presence.\n\n"
        "PHASE 3 — Penetration Attempt:\n"
        "  Use pretext and equipment. Execute entry plan.\n"
        "  If challenged: stay calm, refer to pretext confidently,\n"
        "                 or gracefully abort and try different vector.\n\n"
        "PHASE 4 — Objective Execution:\n"
        "  Document what can be accessed (photos, screenshots).\n"
        "  Plant devices if authorized (rubber ducky, keylogger, rogue AP).\n"
        "  Collect physical evidence (documents, badges, credentials).\n\n"
        "PHASE 5 — Exfil and Reporting:\n"
        "  Exit cleanly. Document everything with timestamps.\n"
        "  Report: what succeeded, how, what physical controls failed."
    ),
},

# ═══════════════════════════════════════════════════════════════
# PRETEXTING — THE ART OF THE STORY
# ═══════════════════════════════════════════════════════════════

"pretexting": {
    "title": "Pretexting — Building Believable False Identities and Scenarios",
    "tldr": (
        "A pretext is a fabricated scenario that justifies why you're "
        "asking for what you want. The best pretexts contain maximum "
        "truth — only the identity and intent are false. "
        "Good pretexting requires research, practice, and adaptability."
    ),
    "pretext_framework": (
        "Every pretext needs four components:\n\n"
        "1. WHO YOU ARE: A specific, verifiable-sounding identity.\n"
        "   Bad: 'I'm from IT'\n"
        "   Good: 'I'm Mike Torres, Senior Engineer on the Infrastructure team.'\n\n"
        "2. WHY YOU'RE HERE: Plausible reason connected to their world.\n"
        "   Bad: 'I need access to the server room.'\n"
        "   Good: 'We're installing the new Palo Alto firewall that was approved\n"
        "          in Q3 planning. Your VP of IT, Jennifer, signed off on it.'\n\n"
        "3. WHY NOW: Urgency that explains why there's no prior notice.\n"
        "   Bad: 'I just need to check something.'\n"
        "   Good: 'The maintenance window was moved up to today because of the\n"
        "          executive team's schedule change for next week.'\n\n"
        "4. WHAT YOU NEED: Ask for one specific thing, not everything.\n"
        "   Bad: 'Can I have access to all your systems?'\n"
        "   Good: 'I just need 10 minutes in the server room — someone can\n"
        "          escort me if you prefer. I'll be out before noon.'"
    ),
    "pretext_categories": {
        "Authority Pretexts": (
            "Leverage authority hierarchy. People comply with those above them.\n"
            "Examples:\n"
            "- Executive assistant of CEO needing urgent assistance\n"
            "- Corporate auditor doing compliance review\n"
            "- Regulatory inspector (OSHA, FDA, fire marshal)\n"
            "- Law enforcement conducting investigation\n"
            "- Corporate security investigating a breach\n"
            "Key: The higher the authority, the less people question."
        ),
        "Technical Expert Pretexts": (
            "Leverage technical knowledge gap. Most employees aren't technical.\n"
            "Examples:\n"
            "- IT support fixing a known system issue\n"
            "- Network engineer upgrading infrastructure\n"
            "- Security team responding to an incident\n"
            "- Software vendor doing a maintenance update\n"
            "Key: Use real technical terminology. Confuse, don't clarify."
        ),
        "Peer/Colleague Pretexts": (
            "Leverage social trust in same-level relationships.\n"
            "Examples:\n"
            "- New employee who needs help navigating the building\n"
            "- Remote employee visiting the office for first time\n"
            "- Employee from another department needing assistance\n"
            "- Contractor working on a shared project\n"
            "Key: People want to help colleagues. Exploit helpfulness."
        ),
        "Vendor/Service Pretexts": (
            "Leverage existing vendor relationships.\n"
            "Examples:\n"
            "- Delivery or courier requiring signature\n"
            "- Office supply vendor restocking\n"
            "- Building maintenance or facilities\n"
            "- Copier repair technician\n"
            "Key: Research which vendors actually service the target."
        ),
    },
    "pretext_research_checklist": (
        "Before executing any pretext, verify you know:\n"
        "[ ] Target's full name and role\n"
        "[ ] Target's manager's name\n"
        "[ ] Relevant company systems/vendors (for technical pretexts)\n"
        "[ ] Recent company news (acquisitions, audits, system upgrades)\n"
        "[ ] Company email format and phone system style\n"
        "[ ] What the company's IT/HR/security team is actually called\n"
        "[ ] Building layout (lobby procedures, badge requirements)\n"
        "[ ] Cultural norms (casual vs formal? security-conscious?)\n\n"
        "The more accurate the pretext, the less likely a challenge."
    ),
},

# ═══════════════════════════════════════════════════════════════
# DEFENSE — BUILDING HUMAN-RESISTANT ORGANIZATIONS
# ═══════════════════════════════════════════════════════════════

"human_defense": {
    "title": "Defending Against Social Engineering — The Human Firewall",
    "tldr": (
        "Technology cannot stop social engineering. Only trained, "
        "aware, and empowered humans can. Building a 'human firewall' "
        "requires ongoing training, cultural change, clear processes, "
        "and removing the shame from reporting mistakes."
    ),
    "why_training_fails": (
        "Annual security awareness training does not work.\n"
        "Studies show: within 72 hours, people forget 70% of training content.\n"
        "The compliance checkbox approach creates the illusion of security.\n\n"
        "What DOES work:\n"
        "- Frequent, short, contextual training (not annual marathons)\n"
        "- Simulated phishing campaigns with immediate teachable feedback\n"
        "- Psychological safety — no punishment for clicking (learn, don't shame)\n"
        "- Role-specific training (finance needs BEC training, not generic SE)\n"
        "- Making reporting easy and rewarded\n"
        "- Leadership modeling secure behavior publicly"
    ),
    "defense_layers": {
        "Technical Controls": (
            "These reduce but don't eliminate the attack surface:\n"
            "- Email security gateway (filter obvious phishing)\n"
            "- DMARC/SPF/DKIM enforcement (reduce spoofed email)\n"
            "- Multi-factor authentication everywhere (limit credential theft impact)\n"
            "- Phishing-resistant MFA: FIDO2/passkeys (not SMS/TOTP — bypassed by Evilginx)\n"
            "- DNS filtering (block known malicious domains)\n"
            "- EDR (catch payload execution)\n"
            "- Privileged Access Workstations (PAW) for admin tasks\n"
            "- Zero Trust Network Access (assume breach, verify everything)"
        ),
        "Process Controls": (
            "Humans need clear rules that remove ambiguity:\n"
            "- Verification process for ALL password resets (never over phone)\n"
            "- Wire transfer dual-authorization with out-of-band confirmation\n"
            "- 'No IT will ever ask for your password' — must be stated repeatedly\n"
            "- Visitor management system with pre-registration required\n"
            "- Badge policy: challenge anyone not wearing badge visibly\n"
            "- Vendor verification process before granting physical/digital access\n"
            "- Incident reporting: who to call, how, how fast (make it easy)"
        ),
        "Cultural Controls": (
            "Security culture is the strongest long-term defense:\n"
            "- Make 'I got a weird email/call' normal and celebrated to report\n"
            "- Remove blame: 'the attacker fooled you — let's learn together'\n"
            "- Security as enabler, not policeman\n"
            "- Empower employees to say no and verify — even to 'executives'\n"
            "- Regular red team exercises published internally (normalize the threat)\n"
            "- Security champions in every department"
        ),
        "Simulated Phishing Programs": (
            "Run monthly simulated phishing campaigns:\n"
            "- Use GoPhish or commercial platforms (KnowBe4, Proofpoint)\n"
            "- Vary the pretexts (IT, HR, vendor, executive)\n"
            "- Track: click rate, credential submission rate, report rate\n"
            "- Immediate training for those who click (not punishment)\n"
            "- Celebrate high report rates — reporting is the win\n"
            "- Measure improvement over time, not snapshot failure rates\n\n"
            "Target metrics:\n"
            "  - Click rate below 5%\n"
            "  - Credential submission below 1%\n"
            "  - Report rate above 70%"
        ),
    },
    "red_team_to_blue_feedback": (
        "After every SE engagement, provide defenders with:\n\n"
        "WHAT WORKED:\n"
        "- Which pretexts succeeded and why\n"
        "- Which employees were most susceptible (by role, not name)\n"
        "- What OSINT enabled the attack\n"
        "- Which technical controls were bypassed and how\n\n"
        "WHAT FAILED:\n"
        "- Which employees challenged and how they did it correctly\n"
        "- Which technical controls blocked or slowed the attack\n"
        "- What could have detected the attack earlier\n\n"
        "RECOMMENDATIONS:\n"
        "- Specific training content for specific roles\n"
        "- Process improvements\n"
        "- Technical control gaps\n"
        "- Verification procedure improvements"
    ),
},

# ═══════════════════════════════════════════════════════════════
# SE TOOL REFERENCE (for ERR0RS automation)
# ═══════════════════════════════════════════════════════════════

"se_tools": {
    "title": "Social Engineering Tools Reference",
    "tldr": "Authoritative tool reference for SE red team operations.",
    "tools": {
        "GoPhish": {
            "purpose": "Phishing campaign management platform",
            "install": "apt install gophish OR download from getgophish.com",
            "run": "./gophish → https://localhost:3333 (admin:gophish)",
            "workflow": "Groups → Email Templates → Landing Pages → Sending Profiles → Campaign",
            "key_features": ["Per-target tracking", "Real-time dashboard", "HTML email editor", "Credential capture", "Timeline reports"],
        },
        "SET": {
            "purpose": "Social Engineering Toolkit — comprehensive SE framework",
            "install": "Pre-installed on Kali. Command: setoolkit",
            "menu": {
                "1": "Spear-Phishing Attack Vectors",
                "2": "Website Attack Vectors (credential harvester, cloner)",
                "3": "Infectious Media Generator (USB autorun)",
                "4": "Create a Payload and Listener (reverse shell)",
                "5": "Mass Mailer Attack",
                "6": "Arduino-Based Attack Vector",
                "7": "SMS Spoofing Attack Vector",
                "8": "QRCode Generator Attack Vector",
                "9": "Powershell Attack Vectors",
            },
        },
        "Evilginx2": {
            "purpose": "MFA-bypassing reverse proxy phishing",
            "install": "git clone https://github.com/kgretzky/evilginx2 && go build",
            "run": "sudo ./evilginx -p ./phishlets/",
            "concepts": ["Phishlets define per-service config", "Lures are per-target URLs", "Sessions capture full auth cookies"],
            "critical_use": "Capturing session tokens bypasses TOTP and push MFA",
        },
        "theHarvester": {
            "purpose": "Email, subdomain, and employee OSINT",
            "command": "theHarvester -d company.com -l 500 -b all",
            "sources": ["Google", "Bing", "LinkedIn", "Shodan", "VirusTotal", "Hunter.io"],
        },
        "Maltego": {
            "purpose": "Graph-based OSINT and relationship mapping",
            "install": "Pre-installed on Kali. Commercial license for full transforms.",
            "entities": ["Person", "Email", "Phone", "Domain", "Organization", "IP"],
            "use": "Map full organizational relationships from minimal seed data",
        },
        "Sherlock": {
            "purpose": "Username search across 300+ social platforms",
            "install": "pip3 install sherlock-project",
            "command": "sherlock targetusername",
        },
        "Zphisher": {
            "purpose": "Ready-made phishing pages for 30+ platforms",
            "install": "git clone https://github.com/htr-tech/zphisher",
            "use": "Quick credential harvesting pages. For authorized testing only.",
        },
    },
},

} # End SE_KNOWLEDGE_BASE


# ═══════════════════════════════════════════════════════════════
# KEYWORD ROUTING — maps user phrases to knowledge entries
# ═══════════════════════════════════════════════════════════════

SE_KEYWORD_MAP = {
    # Human variable / psychology
    "human variable":           "why_human_variable",
    "human attack surface":     "why_human_variable",
    "human factor":             "why_human_variable",
    "psychology of hacking":    "why_human_variable",
    "why people get hacked":    "why_human_variable",
    "cialdini":                 "why_human_variable",
    "influence":                "why_human_variable",
    "cognitive bias":           "why_human_variable",
    "social engineering basics":"why_human_variable",
    "social engineering intro": "why_human_variable",
    "what is social engineering":"why_human_variable",

    # OSINT
    "osint":                    "osint_human_recon",
    "human osint":              "osint_human_recon",
    "target recon":             "osint_human_recon",
    "person recon":             "osint_human_recon",
    "employee recon":           "osint_human_recon",
    "theharvester":             "osint_human_recon",
    "maltego":                  "osint_human_recon",
    "sherlock":                 "osint_human_recon",
    "find emails":              "osint_human_recon",
    "email harvesting":         "osint_human_recon",
    "linkedin recon":           "osint_human_recon",
    "hunter.io":                "osint_human_recon",

    # Phishing
    "phishing":                 "phishing_deep_dive",
    "spear phishing":           "phishing_deep_dive",
    "spearphishing":            "phishing_deep_dive",
    "whaling":                  "phishing_deep_dive",
    "bec":                      "phishing_deep_dive",
    "business email compromise":"phishing_deep_dive",
    "clone phishing":           "phishing_deep_dive",
    "email phishing":           "phishing_deep_dive",
    "phishing campaign":        "phishing_deep_dive",
    "phishing email":           "phishing_deep_dive",
    "gophish":                  "phishing_deep_dive",
    "evilginx":                 "phishing_deep_dive",
    "mfa bypass phishing":      "phishing_deep_dive",
    "credential harvesting":    "phishing_deep_dive",
    "fake login page":          "phishing_deep_dive",

    # Vishing
    "vishing":                  "vishing",
    "voice phishing":           "vishing",
    "phone phishing":           "vishing",
    "phone call attack":        "vishing",
    "caller id spoof":          "vishing",
    "spoofed call":             "vishing",
    "elicitation":              "vishing",
    "yes ladder":               "vishing",
    "pretexting call":          "vishing",
    "smishing":                 "vishing",
    "sms phishing":             "vishing",

    # Physical
    "physical social engineering": "physical_se",
    "physical penetration test":   "physical_se",
    "tailgating":                  "physical_se",
    "piggybacking":                "physical_se",
    "impersonation":               "physical_se",
    "badge cloning":               "physical_se",
    "usb drop":                    "physical_se",
    "dumpster diving":             "physical_se",
    "shoulder surfing":            "physical_se",
    "lock picking":                "physical_se",
    "proxmark":                    "physical_se",
    "physical access":             "physical_se",

    # Pretexting
    "pretexting":               "pretexting",
    "pretext":                  "pretexting",
    "building a pretext":       "pretexting",
    "create a pretext":         "pretexting",
    "fake identity":            "pretexting",
    "false identity":           "pretexting",

    # Defense
    "se defense":               "human_defense",
    "social engineering defense": "human_defense",
    "human firewall":           "human_defense",
    "security awareness":       "human_defense",
    "phishing training":        "human_defense",
    "awareness training":       "human_defense",
    "simulated phishing":       "human_defense",

    # Tools
    "set":                      "se_tools",
    "setoolkit":                "se_tools",
    "social engineer toolkit":  "se_tools",
    "se tools":                 "se_tools",
}
