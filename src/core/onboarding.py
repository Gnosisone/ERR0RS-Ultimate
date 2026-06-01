#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║         ERR0RS ULTIMATE — FIRST RUN ONBOARDING WIZARD          ║
║              src/core/onboarding.py                             ║
║                                                                  ║
║  Detects first run. Walks beginners through:                    ║
║    1. What ERR0RS is and what it can do                         ║
║    2. Ethical use agreement (required)                           ║
║    3. Skill self-assessment (sets operator level)               ║
║    4. First mission assignment (guided first task)              ║
║    5. Hardware detection tour                                    ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone       ║
╚══════════════════════════════════════════════════════════════════╝
"""

import json
import os

ONBOARDING_FILE = os.path.expanduser("~/.err0rs/onboarding_complete.json")
PREFERENCES_FILE = os.path.expanduser("~/.err0rs/preferences.json")

DEFAULT_PREFERENCES = {
    "mode":              "guided",     # guided | standard | expert
    "show_explanations": True,
    "auto_coach":        True,         # ERR0RS proactively explains what tools do
    "skill_level":       0,            # 0=beginner ... 5=elite
    "name":              "Operator",
    "agreed_to_tos":     False,
    "first_mission":     "web_recon", # which tutorial to start with
    "theme":             "purple",
    "completed_missions": [],
}

FIRST_MISSIONS = {
    "web_recon": {
        "title": "Mission 01: Your First Recon",
        "description": "Use nmap and nikto to fingerprint a target web application.",
        "target": "http://localhost:3000",  # Juice Shop
        "steps": [
            {
                "id": 1,
                "instruction": "Let's start with port scanning. Type this in the terminal:",
                "command": "nmap -sV -p 80,443,3000,8080 localhost",
                "what_it_does": "nmap sends TCP probes to discover which services are listening. -sV means version detection — it tries to fingerprint exactly what's running.",
                "what_to_look_for": "Look for '3000/tcp open' — that's the Juice Shop web app. The service name and version tells us what software we're targeting.",
                "xp_reward": 30,
            },
            {
                "id": 2,
                "instruction": "Now let's scan for web vulnerabilities:",
                "command": "nikto -h http://localhost:3000",
                "what_it_does": "Nikto checks the web server for 6,700+ known vulnerabilities, dangerous files, and misconfigurations without sending any exploits.",
                "what_to_look_for": "Pay attention to 'X-Frame-Options header not present', missing security headers, and any '/api/' endpoints it finds.",
                "xp_reward": 30,
            },
            {
                "id": 3,
                "instruction": "Now find hidden directories:",
                "command": "gobuster dir -u http://localhost:3000 -w /usr/share/wordlists/dirb/common.txt -q",
                "what_it_does": "Gobuster rapidly tests thousands of URL paths. Developers often leave /admin, /backup, /api/v1 paths unlisted but accessible.",
                "what_to_look_for": "Any path returning 200 or 301 is accessible. /rest/ is the Juice Shop API root.",
                "xp_reward": 40,
            },
        ],
        "completion_message": "You've completed your first recon. You now know the target's attack surface. Every path you found is a potential entry point.",
    },
    "sql_basics": {
        "title": "Mission 02: SQL Injection Fundamentals",
        "description": "Learn how SQL injection works and exploit it manually before using automated tools.",
        "target": "http://localhost:3000",
        "steps": [
            {
                "id": 1,
                "instruction": "First, confirm the login endpoint is reachable. Send an EMPTY POST so the server tells us what it expects:",
                "command": "curl -s -X POST http://localhost:3000/rest/user/login -H 'Content-Type: application/json' -d '{}'",
                "what_it_does": "Hitting the API with an empty body forces the server to respond with validation errors. Those errors leak schema info — field names, validators, sometimes stack traces. Quietest possible recon move.",
                "what_to_look_for": "Note the error message structure (JSON), the field names mentioned (email, password), and the HTTP status code. This tells you the auth model BEFORE you start guessing payloads.",
                "xp_reward": 25,
            },
            {
                "id": 2,
                "instruction": "Now try a classic SQLi payload in the email field — the goal is to log in WITHOUT knowing a password:",
                "command": "curl -s -X POST http://localhost:3000/rest/user/login -H 'Content-Type: application/json' -d '{\"email\":\"\\' OR 1=1--\",\"password\":\"x\"}'",
                "what_it_does": "The payload `' OR 1=1--` closes the SQL string, adds an always-true condition, and comments out the rest of the query. If the app is vulnerable, the database returns the FIRST user in the table — usually admin.",
                "what_to_look_for": "If you get a JSON response with a `token` field, you just authenticated as the first user (admin). Save that token — you'll use it. If you get an error, the column may be different — try the next step.",
                "xp_reward": 50,
            },
            {
                "id": 3,
                "instruction": "Confirm the auth worked by decoding the JWT to see WHO you are:",
                "command": "echo 'PASTE_TOKEN_HERE' | cut -d'.' -f2 | base64 -d 2>/dev/null | python3 -m json.tool",
                "what_it_does": "JWTs are 3 base64-url-encoded sections joined by dots: header.payload.signature. We decode the payload (middle section) to see the user claims. No verification, just inspection — completely passive.",
                "what_to_look_for": "Look for 'email', 'role', and 'id' fields. If role='admin' you have admin access. If role='customer', the SQLi returned the first customer — useful but not admin yet. The JWT is your session — use it in Authorization headers.",
                "xp_reward": 40,
            },
            {
                "id": 4,
                "instruction": "Now use sqlmap to AUTOMATE finding more injection points across the app:",
                "command": "sqlmap -u 'http://localhost:3000/rest/products/search?q=test' --batch --random-agent --level 2 --risk 1",
                "what_it_does": "sqlmap probes the search endpoint with boolean-blind, time-blind, error-based, UNION, and stacked-query payloads. --batch auto-answers prompts. --random-agent rotates User-Agent per request to bypass naive WAF rules. --level 2 --risk 1 stays in the quieter range.",
                "what_to_look_for": "sqlmap will print 'parameter is vulnerable' if it confirms injection. Note WHICH technique worked (boolean, UNION, etc.) — that tells you the DB engine and how to craft manual payloads. Save findings to ~/.sqlmap/output/ for later analysis.",
                "xp_reward": 60,
            },
        ],
        "completion_message": "You've owned the login form manually AND scaled it with sqlmap. Next: try the JWT forge — alg:none — to escalate from customer to admin without re-injecting.",
    },

    "osint_recon": {
        "title": "Mission 03: OSINT & Passive Recon",
        "description": "Build a target's external footprint using only passive, public-source intel — the quiet phase before you ever touch the target.",
        # Safe teaching targets: example.com is IANA-reserved (never a real
        # victim), scanme.nmap.org is explicitly authorized for scan practice.
        "target": "example.com",
        "steps": [
            {
                "id": 1,
                "instruction": "Start passive — discover subdomains from public sources. The target never sees a packet:",
                "command": "subfinder -d example.com -silent",
                "what_it_does": "subfinder queries 30+ third-party sources (cert transparency logs, passive DNS) for subdomains. Because it never contacts the target's own servers, this is completely undetectable — the ideal first move.",
                "what_to_look_for": "Each line is a subdomain. More subdomains = bigger attack surface. In a real engagement you'd validate each against your authorized scope before going further. Note any dev/staging/admin hostnames — those are where easy wins hide.",
                "xp_reward": 30,
            },
            {
                "id": 2,
                "instruction": "Map what the organization owns — domains and IP blocks — with amass intel:",
                "command": "amass intel -d example.com -whois",
                "what_it_does": "amass intel pivots from one domain to related domains the same organization owns, using WHOIS data. This is how you turn 'one domain in scope' into the full picture of an org's internet presence.",
                "what_to_look_for": "Related domains and registrant info. In scoping, this tells you the true size of the target. Remember: finding an asset does NOT mean it's authorized — you'd confirm each with the client before testing.",
                "xp_reward": 35,
            },
            {
                "id": 3,
                "instruction": "Harvest public emails, names, and hosts tied to the domain:",
                "command": "theHarvester -d example.com -b duckduckgo,crtsh,bing -l 50",
                "what_it_does": "theHarvester scrapes search engines and public datasets for email addresses, employee names, and subdomains. Still fully passive — it pulls from third parties, never the target.",
                "what_to_look_for": "The email FORMAT (first.last@ vs flast@) is the real prize — it's what you'd use to build a username list for later password spraying. Employee names feed the people-OSINT phase next.",
                "xp_reward": 35,
            },
            {
                "id": 4,
                "instruction": "Pivot to people — check where a username exists across the web with sherlock:",
                "command": "sherlock johndoe --timeout 10",
                "what_it_does": "sherlock checks 400+ social/web platforms for a username. A reused handle links a person's accounts together, expanding your understanding of the human attack surface. Queries hit the SITES, not your target — silent.",
                "what_to_look_for": "Confirmed profiles (verify manually — false positives happen). Bios and posts often leak more seed data: other handles, employer confirmation, location, tech they use. This is how OSINT compounds — each find seeds the next query.",
                "xp_reward": 40,
            },
        ],
        "completion_message": "That's the passive-recon phase end to end: infrastructure (subfinder/amass) AND people (theHarvester/sherlock) — all without touching the target. In a real engagement you'd now have a validated, in-scope target list and arrive at ACTIVE recon already knowing the answers. Type 'teach recon-theory' or 'teach engagement-lifecycle' to see where this fits in the bigger picture.",
    },
}


def is_first_run() -> bool:
    return not os.path.exists(ONBOARDING_FILE)


def load_preferences() -> dict:
    if os.path.exists(PREFERENCES_FILE):
        try:
            with open(PREFERENCES_FILE) as f:
                prefs = json.load(f)
                # Merge with defaults for any new keys
                return {**DEFAULT_PREFERENCES, **prefs}
        except Exception:
            pass
    return dict(DEFAULT_PREFERENCES)


def save_preferences(prefs: dict):
    os.makedirs(os.path.dirname(PREFERENCES_FILE), exist_ok=True)
    with open(PREFERENCES_FILE, "w") as f:
        json.dump(prefs, f, indent=2)


def mark_onboarding_complete(prefs: dict):
    os.makedirs(os.path.dirname(ONBOARDING_FILE), exist_ok=True)
    with open(ONBOARDING_FILE, "w") as f:
        json.dump({"completed": True, "ts": str(__import__("datetime").datetime.now())}, f)
    save_preferences(prefs)


def get_onboarding_payload() -> dict:
    """Returns everything the frontend needs to render the onboarding wizard."""
    return {
        "type": "onboarding",
        "screens": [
            {
                "id": "welcome",
                "title": "Welcome to ERR0RS-Ultimate",
                "subtitle": "The open-source AI security platform built for students who can't afford enterprise tools.",
                "content": [
                    "ERR0RS is your AI-powered red team partner, security coach, and lab environment — all running locally on your machine.",
                    "It's not a hacking script. It's a learning platform that teaches you how attacks work, why they work, and how to defend against them.",
                    "Every tool, every technique comes with an explanation. You'll never just run a command and not know why.",
                ],
                "action": "next",
                "action_label": "Let's go →",
            },
            {
                "id": "ethics",
                "title": "Ethical Use Agreement",
                "subtitle": "This is not optional.",
                "content": [
                    "ERR0RS is for authorized security testing, CTF competitions, and education ONLY.",
                    "Using these techniques against systems you don't own or have explicit written permission to test is a federal crime under the CFAA and similar laws worldwide.",
                    "This platform will never be used to harm people. Security knowledge is power — use it to protect, not to destroy.",
                    "Violations are not ERR0RS's problem. They're yours.",
                ],
                "checkbox": "I understand. I will only use ERR0RS on systems I own or have explicit authorization to test.",
                "action": "agree",
                "action_label": "I agree — let's build →",
                "required": True,
            },
            {
                "id": "skill_assessment",
                "title": "Where are you right now?",
                "subtitle": "Be honest. ERR0RS adapts to your level.",
                "options": [
                    {
                        "id": 0,
                        "label": "Total beginner",
                        "description": "I've heard terms like 'SQL injection' but I've never run a security tool.",
                        "badge": "🔰",
                    },
                    {
                        "id": 1,
                        "label": "I've done some CTFs",
                        "description": "I can run nmap and I've completed a few basic challenges.",
                        "badge": "🎯",
                    },
                    {
                        "id": 2,
                        "label": "Intermediate — I run real engagements",
                        "description": "I understand the kill chain and have done basic pentests in lab environments.",
                        "badge": "⚡",
                    },
                    {
                        "id": 3,
                        "label": "Advanced — I'm here for the tooling",
                        "description": "I know what I'm doing. Give me the full platform.",
                        "badge": "🔥",
                    },
                ],
                "action": "select_skill",
            },
            {
                "id": "first_mission",
                "title": "Your First Mission",
                "subtitle": "Let's do something real.",
                "content": [
                    "We're going to run your first web recon against the OWASP Juice Shop — a deliberately vulnerable app we've included for you to practice on.",
                    "ERR0RS will explain every command before you run it. You'll understand what's happening, not just what buttons to press.",
                    "Ready?",
                ],
                "mission": FIRST_MISSIONS["web_recon"],
                "action": "start_mission",
                "action_label": "Start Mission 01 →",
            },
        ],
        "first_mission_steps": FIRST_MISSIONS["web_recon"]["steps"],
    }


def get_mission_step_coaching(step: dict) -> str:
    """Returns a rich coaching message for a mission step."""
    return f"""**{step['instruction']}**

```bash
{step['command']}
```

**What this does:** {step['what_it_does']}

**What to look for:** {step['what_to_look_for']}

**XP reward:** +{step['xp_reward']} XP when complete

---
*Run the command above in the terminal. ERR0RS will analyze the output and explain what it means.*"""
