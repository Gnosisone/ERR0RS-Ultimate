#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Natural Language Expansion Layer v2.0
Wide-coverage NLP vocabulary for commanding, teaching, and guiding operatives.

This module extends language_layer.py with:
  - 500+ additional command phrasings per category
  - Beginner / intermediate / expert voice variants
  - Casual / formal / abbreviated phrasings
  - Red team slang and operator shorthand
  - Teaching request variants (hundreds of ways to ask "explain X")
  - Compound intent phrases ("scan then exploit", "find then teach me")
  - Typo tolerance and common misspellings
  - Question forms, imperative forms, declarative forms
  - Context-aware synonyms per tool

Import pattern:
    from src.core.language_expansion_v2 import (
        EXTENDED_TEACH_TRIGGERS,
        EXTENDED_TOOL_PHRASES,
        OPERATOR_SLANG,
        BEGINNER_PHRASES,
        COMPOUND_INTENTS,
        TYPO_MAP,
        TEACHING_RESPONSES,
        CONFIRMATION_WORDS,
        NEGATION_WORDS,
        PHASE_TRIGGERS,
        expand_keywords,
        fuzzy_match_tool,
        get_response_tone,
    )

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import re
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1 — EXTENDED TEACH TRIGGERS
# Every conceivable way a human says "I want to learn about X"
# ═══════════════════════════════════════════════════════════════════════════

EXTENDED_TEACH_TRIGGERS: list[str] = [

    # Direct commands
    "teach me", "teach me about", "teach me how", "teach me how to use",
    "teach me how to run", "teach me everything about",
    "give me a lesson on", "lesson on", "give me a lesson about",
    "give me a tutorial on", "give me a tutorial for",
    "give me a crash course", "crash course on", "crash course in",
    "crash course for", "give me an overview of", "overview of",
    "overview on", "give me a rundown", "rundown of", "rundown on",
    "give me the basics", "basics of", "basics on",
    "run me through", "walk me through", "walk me through how",
    "walk me through the", "take me through", "take me through the",
    "guide me through", "guide me on", "guide me with",

    # Explanation requests
    "explain", "explain to me", "explain how", "explain what",
    "explain why", "explain when", "explain where",
    "can you explain", "could you explain", "please explain",
    "break it down", "break down", "break this down",
    "break it down for me", "break this down for me",
    "dumb it down", "dumb it down for me", "eli5",
    "explain like i'm 5", "explain like im 5",
    "explain it simply", "explain it simply for me",
    "explain in simple terms", "explain in plain english",
    "explain in laymans terms", "simplify",

    # What is / What does
    "what is", "what's", "whats", "what exactly is",
    "what are", "what exactly are", "what were", "what was",
    "what does", "what do", "what did", "what would",
    "what can", "what could", "what should",
    "what is the purpose of", "what is the point of",
    "what is the goal of", "what is the use of",
    "what is the difference between", "whats the diff",
    "what are the types of", "what are the kinds of",
    "what makes", "what makes a good", "what makes a bad",

    # How does / How do
    "how does", "how do", "how do i", "how do you",
    "how do i use", "how do you use", "how can i",
    "how can i use", "how would i", "how would you",
    "how should i", "how should you", "how to",
    "how to use", "how to run", "how to execute",
    "how to perform", "how to do", "how to set up",
    "how to configure", "how to install", "how to launch",
    "how to start", "how to begin", "how to approach",
    "how is", "how are", "how was", "how were",
    "how does X work", "how does this work",

    # Why questions
    "why", "why does", "why do", "why is", "why are",
    "why would", "why should", "why use", "why use X over",
    "why is X better", "why is X worse", "why do we use",
    "what's the reason", "whats the reason",

    # Tell me
    "tell me", "tell me about", "tell me how", "tell me what",
    "tell me everything", "tell me everything about",
    "tell me more", "tell me more about",

    # Show me
    "show me", "show me how", "show me what", "show me an example",
    "show me examples", "show me the commands", "show me the syntax",
    "show me a demo", "show me how to use", "show me step by step",
    "show me the process", "show me how it works",

    # Let me know / Help me
    "let me know", "let me know how", "let me know what",
    "help me", "help me with", "help me understand",
    "help me learn", "help me figure out", "help me figure out how",
    "can you help me", "can you help me with", "i need help with",
    "i need help understanding", "i need help on",
    "i need to understand", "i need to know",
    "i need to learn", "i need to figure out",

    # Info / Information
    "give me info", "give me information", "info on", "info about",
    "information on", "information about", "details on", "details about",
    "tell me the details", "give me the details",
    "get me info", "get me information",
    "pull up info", "look up info",

    # Question starters (from beginners)
    "so what is", "okay what is", "okay so what is",
    "wait what is", "so how does", "okay how does",
    "wait how do i", "yo what is", "yo how do i",
    "hey what is", "hey how do i", "hey can you explain",

    # Beginner confessions
    "i dont know what", "i don't know what",
    "i dont know how", "i don't know how",
    "i dont understand", "i don't understand",
    "i'm confused about", "im confused about",
    "i'm lost on", "im lost on",
    "never used", "never heard of", "never seen",
    "first time using", "first time with",
    "complete beginner", "total beginner", "beginner here",
    "noob question", "newbie question",
    "stupid question but", "dumb question but",
    "probably basic but", "probably obvious but",
    "this might be dumb but",

    # Learning intent
    "learning", "studying", "practicing", "trying to learn",
    "trying to understand", "working on learning",
    "in the process of learning", "started learning",
    "just started learning", "new to", "new to this",
    "getting started with", "getting into",

    # Study mode
    "study", "studying this", "review",
    "quick review", "quiz me on", "test me on",
    "drill me on", "practice with me",

    # Deep dive
    "deep dive", "deep dive into", "deep dive on",
    "in depth", "in-depth", "in depth look at",
    "comprehensive overview", "comprehensive guide",
    "full guide", "complete guide", "advanced guide",
    "advanced explanation", "technical explanation",
    "technical deep dive", "under the hood",
    "how does it really work", "what really happens",
    "whats happening under the hood",

    # Reference requests
    "cheat sheet", "cheatsheet", "quick reference",
    "command reference", "flag reference", "syntax reference",
    "reference card", "all the commands", "list the commands",
    "all the flags", "list the flags", "all the options",

    # Operator style
    "brief me on", "brief me", "debrief me on",
    "intel on", "give me the intel", "situational awareness on",
    "what do i need to know about", "what should i know about",
    "key points on", "key takeaways on", "tldr on", "tl;dr",
    "bottom line on", "bottom line up front", "bluf",
    "need to know basis",
]


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2 — EXTENDED TOOL PHRASES
# Hundreds of additional natural language ways to invoke each tool
# ═══════════════════════════════════════════════════════════════════════════

EXTENDED_TOOL_PHRASES: dict[str, list[str]] = {

    "nmap": [
        # Beginner
        "scan that ip", "scan this ip", "scan the ip",
        "check that host", "check this host", "check the host",
        "check what ports are open", "what ports are open on",
        "see what's running on", "see whats running on",
        "look at the network", "look at that machine",
        "poke that machine", "poke that host",
        "sniff out the ports", "find what services",
        "what services are running", "what is running on",
        # Intermediate
        "run a scan on", "run nmap against", "run nmap on",
        "do a port scan", "do a network scan", "do a recon scan",
        "do recon on", "start recon", "kick off recon",
        "enumerate the host", "enumerate services",
        "enumerate the target", "fingerprint the host",
        "fingerprint the target", "identify the os",
        "detect the os", "grab service banners",
        # Expert
        "syn scan", "stealth scan", "half open scan",
        "full connect scan", "xmas scan", "null scan",
        "fin scan", "idle scan", "zombie scan",
        "version scan", "aggressive scan", "comprehensive scan",
        "do a minus a", "nmap dash a", "run minus sv minus sc",
        "scan all ports", "scan full range",
        "scan top thousand", "scan top ports",
        "run nse scripts", "run vuln scripts on",
        "run smb vuln script", "check eternalblue",
        # Operator shorthand
        "recon target", "map the target", "map the host",
        "profile the target", "do target profiling",
        "initial scan", "quick recon", "fast scan",
        "full recon sweep", "deep scan", "thorough scan",
    ],

    "metasploit": [
        # Beginner
        "how do i use metasploit", "how to use msf",
        "open metasploit", "start metasploit", "launch metasploit",
        "fire up msf", "run msf", "get into metasploit",
        "load metasploit", "start msfconsole",
        # Tool invocation
        "use the exploit", "fire the exploit", "run the exploit",
        "launch the exploit", "send the exploit", "drop an exploit",
        "use ms17-010", "try eternalblue", "run eternalblue",
        "fire eternalblue", "hit it with eternalblue",
        "exploit that smb", "attack the smb", "attack port 445",
        "exploit that rdp", "exploit that service",
        "try to get a shell", "get a shell on", "pop a shell",
        "get meterpreter", "drop a meterpreter", "open meterpreter",
        "get code execution", "get rce", "get remote execution",
        "gain access", "break in", "get in", "compromise the host",
        # Payload
        "generate payload", "make payload", "create payload",
        "set up payload", "use reverse tcp", "use meterpreter",
        "stage the payload", "deliver the payload",
        # Handler
        "set up handler", "start listener", "open listener",
        "catch the shell", "wait for connection", "listen for shell",
        "set up multi handler", "run multi handler",
        # Post exploit
        "after i get shell", "after the shell", "once i have shell",
        "what do i do after shell", "next steps after shell",
    ],

    "msfvenom": [
        "make a payload", "create a payload", "generate a payload",
        "build a payload", "craft a payload", "forge a payload",
        "make an exe payload", "make a windows payload",
        "make a linux payload", "make an android payload",
        "make a php shell", "make a web shell",
        "make a reverse shell", "make a bind shell",
        "make a meterpreter payload", "generate meterpreter",
        "create an exe", "build an exe", "generate an exe",
        "create a malicious exe", "trojan an exe", "inject into exe",
        "make a hta file", "make a vba macro",
        "make a powershell payload", "generate ps1 payload",
        "encode the payload", "encode with shikata",
        "make it bypass av", "bypass antivirus", "av bypass",
        "make it fud", "make it undetectable", "evade av",
        "generate shellcode", "make shellcode", "create shellcode",
        "make a war file", "generate war file",
        "make a jsp shell", "create jsp shell",
        "make an apk", "create android apk", "generate apk",
        "embed payload in", "inject into binary",
        "msfvenom for windows", "msfvenom for linux",
        "msfvenom for android", "msfvenom for mac",
    ],

    "hydra": [
        # Beginner
        "try to login", "try logins", "try passwords",
        "test the login", "test credentials", "test passwords",
        "guess the password", "guess passwords",
        "try to brute force", "try brute forcing",
        "can we brute force", "brute force the login",
        # Service specific
        "brute force ssh", "attack ssh", "crack ssh password",
        "brute force ftp", "attack ftp", "crack ftp password",
        "brute force rdp", "attack rdp", "crack rdp",
        "brute force smb", "attack smb", "crack smb",
        "brute force the web login", "attack the login form",
        "attack http login", "crack http login",
        "brute force wordpress", "crack wordpress login",
        "attack mysql", "brute force database",
        # Spray
        "spray passwords", "do a spray", "run a spray",
        "password spray", "spray the domain", "spray the network",
        "try common passwords", "try default passwords",
        "test default creds", "check default credentials",
        # Wordlist
        "use rockyou", "throw rockyou at it",
        "run rockyou against", "use the wordlist",
        "dictionary attack on", "wordlist attack on",
    ],

    "hashcat": [
        # Beginner
        "crack this hash", "crack this", "crack that hash",
        "what is this hash", "decode this hash",
        "reverse this hash", "unhash this",
        "break this hash", "break the hash",
        "run hashcat on", "throw hashcat at",
        # Hash type specific
        "crack the ntlm hash", "crack the md5",
        "crack the sha1", "crack the sha256",
        "crack the bcrypt", "crack the wpa2 hash",
        "crack the kerberos ticket", "crack the tgs",
        "crack the net-ntlmv2", "crack the responder hash",
        # Method
        "dictionary crack", "wordlist crack", "rule based crack",
        "mask attack", "brute force the hash",
        "gpu crack", "run a gpu crack",
        "crack with rockyou", "throw rockyou at the hash",
        # Identify
        "what type of hash", "identify this hash",
        "what hash algorithm", "hashid",
    ],

    "sqlmap": [
        # Beginner
        "test this url for sql", "test this for sql injection",
        "check if this is vulnerable to sql",
        "is this url vulnerable", "is this page injectable",
        "look for sql injection", "find sql injection",
        "test the login for sqli", "check the form for sqli",
        "inject into the url", "inject into the form",
        # Intermediate
        "dump the users table", "dump the passwords",
        "dump the database", "extract the database",
        "enumerate the databases", "list the databases",
        "find the tables", "enumerate the tables",
        "get the schema", "dump the schema",
        "extract usernames and passwords",
        # Expert
        "run blind sqli", "test boolean based",
        "test time based blind", "test error based",
        "try union injection", "run union select",
        "get os shell via sql", "sqlmap os shell",
        "sqlmap with tamper", "bypass waf with sqlmap",
        "run sqlmap through burp", "sqlmap with proxy",
        "sqlmap batch mode", "sqlmap no prompts",
    ],

    "gobuster": [
        # Beginner
        "find hidden pages", "find hidden directories",
        "find hidden files", "look for hidden files",
        "check for admin panel", "find the admin panel",
        "look for admin", "find login page",
        "find hidden login", "look for login",
        "search for directories", "look for directories",
        "find files on the server",
        # Intermediate
        "run a directory scan", "do a directory scan",
        "dir bust that server", "dir bust it",
        "brute force the directories", "fuzz the directories",
        "fuzz the paths", "fuzz the website",
        "use dirb on", "directory enumeration",
        "enumerate the web directories",
        # Wordlist specific
        "use the common wordlist", "use dirbuster wordlist",
        "use raft wordlist", "use seclists",
        "run against medium wordlist", "run against big wordlist",
        # Extension
        "find php files", "find txt files",
        "look for backup files", "find config files",
        "find env files", "find git repos",
        "check for dot env", "check for git",
    ],

    "aircrack": [
        # Beginner
        "how do i hack wifi", "hack the wifi",
        "get the wifi password", "crack the wifi",
        "recover the wifi password", "find the wifi password",
        "get into the wifi", "access the wifi",
        "crack the wpa2", "crack the wpa",
        "crack the wireless network", "break the wifi",
        # Intermediate
        "capture the handshake", "grab the handshake",
        "get the 4 way handshake", "get the eapol handshake",
        "monitor the wifi", "put adapter in monitor mode",
        "start monitor mode", "enable monitor mode",
        "deauth the client", "kick the client off",
        "disconnect the client", "send deauth frames",
        "run airmon ng", "run airodump ng", "run aireplay ng",
        # Crack
        "run aircrack on the cap file", "crack the cap file",
        "crack the pcap", "crack the handshake file",
        "run hashcat on the wifi hash", "crack wifi with hashcat",
        "convert cap to hc22000", "convert to hashcat format",
        # Saved passwords
        "check saved wifi", "dump saved wifi passwords",
        "show saved wifi passwords", "recover saved wifi",
        "netsh wlan", "show the wlan profiles",
    ],

    "mimikatz": [
        "run mimikatz", "use mimikatz", "launch mimikatz",
        "dump credentials", "dump creds", "extract creds",
        "extract credentials", "harvest credentials",
        "dump windows passwords", "get the hashes",
        "dump the hashes", "extract ntlm hashes",
        "dump lsass", "read lsass", "attack lsass",
        "dump sam database", "dump the sam",
        "get kerberos tickets", "steal kerberos tickets",
        "do pass the hash", "pass the hash attack",
        "do dcsync", "run dcsync", "dcsync attack",
        "pull domain hashes", "pull all hashes",
        "golden ticket attack", "make a golden ticket",
        "forge a golden ticket", "create golden ticket",
        "silver ticket", "make a silver ticket",
        "kiwi", "load kiwi", "use kiwi module",
        "sekurlsa", "lsadump", "privilege debug",
    ],

    "armitage": [
        "open armitage", "launch armitage", "start armitage",
        "use armitage", "run armitage", "gui for metasploit",
        "visual metasploit", "graphical metasploit",
        "metasploit gui", "armitage hail mary",
        "hail mary attack", "find attacks in armitage",
        "armitage team server", "collaborative metasploit",
        "team red team", "shared sessions",
        "armitage cortana", "cortana script",
        "automate armitage", "armitage automation",
    ],

    "bloodhound": [
        "run bloodhound", "use bloodhound", "launch bloodhound",
        "map the active directory", "map the domain",
        "find attack paths", "find the path to da",
        "path to domain admin", "find domain admin path",
        "enumerate active directory", "ad enumeration",
        "sharphound", "run sharphound", "collect ad data",
        "ingest bloodhound data", "import into bloodhound",
        "shortest path to da", "attack path to dc",
        "find privilege escalation path", "find ad vulns",
        "kerberoastable accounts", "find kerberoastable",
        "find asrep roastable", "find delegations",
        "find unconstrained delegation",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3 — OPERATOR SLANG & RED TEAM JARGON
# ERR0RS understands how actual operators talk on engagements
# ═══════════════════════════════════════════════════════════════════════════

OPERATOR_SLANG: dict[str, str] = {

    # General action verbs (map to category)
    "pop":              "exploit",     # "pop that box"
    "pwn":              "exploit",     # "pwn the host"
    "root":             "privesc",     # "root the box"
    "own":              "exploit",     # "own that machine"
    "0wn":              "exploit",     # "0wn that box"
    "dominate":         "exploit",     # "dominate the network"
    "compromise":       "exploit",     # "compromise the host"
    "land":             "exploit",     # "land on the box"
    "hit":              "exploit",     # "hit that machine"
    "nail":             "exploit",     # "nail the dc"
    "drop":             "payload",     # "drop a payload"
    "plant":            "payload",     # "plant a shell"
    "throw":            "exploit",     # "throw an exploit at it"
    "fire":             "exploit",     # "fire the exploit"
    "launch":           "exploit",     # "launch the attack"
    "yeet":             "exploit",     # informal: "yeet that exploit"

    # Shell related
    "shell":            "shell",       # "get a shell"
    "meterp":           "meterpreter", # "drop a meterp"
    "meter":            "meterpreter", # "open a meter"
    "rev shell":        "shell",       # "set up a rev shell"
    "revshell":         "shell",
    "callback":         "shell",       # "wait for the callback"
    "c2":               "c2",          # "set up c2"
    "beacon":           "c2",          # "beacon home"

    # Credential slang
    "creds":            "credentials", # "dump creds"
    "hashes":           "credentials", # "get the hashes"
    "hash dump":        "credentials", # "hash dump the box"
    "dump":             "credentials", # "dump the box"
    "loot":             "credentials", # "loot the machine"
    "harvest":          "credentials", # "harvest creds"
    "pillage":          "post_exploit",# "pillage the box"
    "ransack":          "post_exploit",# "ransack the system"

    # Recon slang
    "enum":             "enumerate",   # "enum the host"
    "footprint":        "recon",       # "footprint the target"
    "fingerprint":      "recon",       # "fingerprint the target"
    "poke":             "recon",       # "poke around"
    "prod":             "recon",       # "prod the target"
    "probe":            "recon",       # "probe the host"
    "map":              "recon",       # "map the network"
    "scope":            "recon",       # "scope out the target"
    "recon":            "recon",       # "recon the target"
    "do recon":         "recon",
    "run recon":        "recon",
    "kick off recon":   "recon",

    # Pivoting / movement slang
    "move through":     "lateral",     # "move through the network"
    "move laterally":   "lateral",
    "hop":              "lateral",     # "hop to the next box"
    "jump":             "lateral",     # "jump to the dc"
    "pivot to":         "lateral",     # "pivot to the internal"
    "tunnel":           "pivot",       # "tunnel through"
    "set up a tunnel":  "pivot",
    "chain":            "pivot",       # "chain through"

    # Privilege slang
    "escalate":         "privesc",     # "escalate on the box"
    "esc":              "privesc",     # "esc privs"
    "get system":       "privesc",     # "get system on the box"
    "getsystem":        "privesc",
    "become system":    "privesc",
    "become root":      "privesc",
    "root the box":     "privesc",
    "go system":        "privesc",

    # AD slang
    "da":               "domain_admin",# "get da"
    "domain admin":     "domain_admin",
    "get da":           "domain_admin",
    "become da":        "domain_admin",
    "reach da":         "domain_admin",
    "dc":               "domain_controller",
    "domain controller":"domain_controller",
    "hit the dc":       "domain_controller",
    "attack the dc":    "domain_controller",
    "krbtgt":           "golden_ticket",
    "golden":           "golden_ticket",
    "make a golden":    "golden_ticket",
    "forge a ticket":   "golden_ticket",

    # Defense evasion slang
    "fud":              "evasion",     # "make it fud"
    "bypass av":        "evasion",
    "evade av":         "evasion",
    "dodge av":         "evasion",
    "ghost":            "evasion",     # "ghost through defenses"
    "fly under":        "evasion",     # "fly under the radar"
    "stay under radar": "evasion",
    "live off the land":"lolbas",
    "lotl":             "lolbas",
    "lolbas":           "lolbas",

    # Exfil slang
    "exfil":            "exfiltration",
    "exfiltrate":       "exfiltration",
    "steal data":       "exfiltration",
    "pull data":        "exfiltration",
    "snag data":        "exfiltration",
    "grab data":        "exfiltration",
    "data out":         "exfiltration",
    "get data out":     "exfiltration",

    # General engagement terms
    "box":              "target",      # "that box"
    "machine":          "target",      # "that machine"
    "target":           "target",
    "victim":           "target",
    "host":             "target",
    "node":             "target",
    "asset":            "target",
    "scope":            "target",
    "in scope":         "target",
    "objective":        "goal",
    "goals":            "goal",
    "roe":              "rules_of_engagement",
    "rules of engagement": "rules_of_engagement",
    "engagement":       "pentest",
    "op":               "operation",
    "operation":        "operation",
    "mission":          "operation",
}


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4 — BEGINNER PHRASES
# How beginners phrase things — often wrong or vague — ERR0RS corrects gently
# ═══════════════════════════════════════════════════════════════════════════

BEGINNER_PHRASES: dict[str, str] = {

    # Common beginner confusions (phrase → correct topic)
    "how do i hack":                    "pentesting_methodology",
    "teach me to hack":                 "pentesting_methodology",
    "i want to hack":                   "pentesting_methodology",
    "how do i start hacking":           "pentesting_methodology",
    "how to become a hacker":           "pentesting_methodology",
    "what does a hacker do":            "pentesting_methodology",
    "is hacking legal":                 "ethics_and_authorization",
    "how do i hack without getting caught": "opsec",
    "how do i stay anonymous":          "opsec",
    "what is a shell":                  "shell_basics",
    "what is a reverse shell":          "reverse_shell",
    "what is a payload":                "payload_basics",
    "what is metasploit":               "metasploit",
    "what is a vulnerability":          "vulnerability_basics",
    "what is an exploit":               "exploitation_basics",
    "what is sql injection":            "sql injection",
    "what is xss":                      "xss",
    "what is a pentest":                "pentesting_methodology",
    "what is penetration testing":      "pentesting_methodology",
    "what is a red team":               "red_team",
    "what is a blue team":              "blue_team",
    "what is a purple team":            "purple_team",
    "what is nmap":                     "nmap",
    "what is kali linux":               "kali_basics",
    "what is parrot os":                "parrot_basics",
    "how do i use kali":                "kali_basics",
    "what is a cve":                    "cve_basics",
    "what is cvss":                     "cvss_basics",
    "what is the cia triad":            "cia_triad",
    "what is osint":                    "osint",
    "what is social engineering":       "social_engineering",
    "what is phishing":                 "phishing",
    "what is malware":                  "malware_basics",
    "what is a trojan":                 "malware_basics",
    "what is ransomware":               "ransomware",
    "what is a firewall":               "firewall_basics",
    "what is a vpn":                    "vpn_basics",
    "what is encryption":               "encryption_basics",
    "what is a hash":                   "hashing_basics",
    "how does wifi work":               "wifi_basics",
    "how does the internet work":       "networking_basics",
    "what is tcp ip":                   "networking_basics",
    "what is dns":                      "dns_basics",
    "what is https":                    "https_basics",
    "what is active directory":         "active_directory_basics",
    "what is ldap":                     "ldap_basics",
    "what is kerberos":                 "kerberos",
    "can mimikatz crack wifi":          "wireless_tool_selection",
    "does aircrack crack windows":      "wireless_tool_selection",
    "why isnt my exploit working":      "troubleshooting",
    "why isnt metasploit working":      "troubleshooting",
    "how do i get a meterpreter shell": "metasploit",
    "how do i dump passwords":          "credentials",
    "how do i crack a password":        "hashcat",
    "can i hack with my phone":         "mobile_pentest",
    "can i hack with a raspberry pi":   "pi_pentest",
}


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5 — COMPOUND INTENT PHRASES
# "Do X and then Y" — ERR0RS chains multiple actions together
# ═══════════════════════════════════════════════════════════════════════════

COMPOUND_INTENTS: dict[str, list[str]] = {

    "scan_then_exploit": [
        "scan then exploit", "scan and exploit", "recon then attack",
        "recon and exploit", "find vulnerabilities then exploit",
        "scan for vulnerabilities and exploit",
        "enumerate then exploit", "enum and attack",
        "find open ports then exploit", "scan ports and attack",
        "scan the host and get a shell",
        "recon the box then pop it",
        "fingerprint then exploit", "probe then attack",
    ],

    "scan_then_teach": [
        "scan and explain", "scan and teach me",
        "scan and tell me what you find",
        "run nmap and explain the results",
        "scan then break it down", "scan and walk me through",
        "scan with teach mode", "scan --teach",
        "do a scan and educate me",
        "enumerate and explain",
        "probe and tell me what it means",
    ],

    "exploit_then_escalate": [
        "exploit then escalate", "get shell then escalate",
        "get shell then root", "shell then privesc",
        "land shell then privesc", "compromise then escalate",
        "foothold then escalate", "initial access then escalate",
        "get in then get root", "pop the box then root it",
        "exploit and escalate", "get access and escalate",
    ],

    "escalate_then_dump": [
        "escalate then dump creds", "root then dump",
        "get system then dump", "become admin then dump hashes",
        "privesc then harvest creds", "get root then dump passwords",
        "escalate then loot", "root and loot",
        "get system and dump", "escalate and credential dump",
    ],

    "exploit_then_pivot": [
        "exploit then pivot", "get shell then pivot",
        "compromise then move laterally", "foothold then lateral movement",
        "initial access then spread", "land then pivot",
        "pop the box then move to internal",
        "get in then move through network",
        "exploit and pivot", "compromise and lateral",
    ],

    "full_chain": [
        "full attack chain", "full pentest", "full engagement",
        "all phases", "scan exploit escalate pivot dump report",
        "from recon to report", "full red team operation",
        "end to end", "start to finish", "a to z attack",
        "full automated pentest", "autonomous pentest",
        "run everything", "do it all", "full auto",
        "complete the engagement", "full kill chain",
        "full chain attack", "from foothold to domain admin",
    ],

    "teach_then_run": [
        "teach me then run it", "explain then execute",
        "explain then run", "show me how then do it",
        "teach me the command then run it",
        "explain what it does then run",
        "walk me through it then launch",
        "brief me then fire it",
    ],

    "defend_then_attack": [
        "attack then detect", "attack then defend",
        "simulate then detect", "red then blue",
        "attack and measure detection",
        "run the attack and check logs",
        "purple team this", "full purple team loop",
        "attack then build detection rule",
        "exploit then write sigma rule",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6 — TYPO MAP
# Common misspellings and typos ERR0RS corrects silently
# ═══════════════════════════════════════════════════════════════════════════

TYPO_MAP: dict[str, str] = {

    # Tool name typos
    "nmpa":           "nmap",
    "anmap":          "nmap",
    "namp":           "nmap",
    "namap":          "nmap",
    "n map":          "nmap",
    "mataslpoit":     "metasploit",
    "metasplot":      "metasploit",
    "metaspliot":     "metasploit",
    "metasplit":      "metasploit",
    "metasplolit":    "metasploit",
    "metaspoit":      "metasploit",
    "msfc":           "msfconsole",
    "msfconole":      "msfconsole",
    "msfconosle":     "msfconsole",
    "msfvemon":       "msfvenom",
    "msfvenon":       "msfvenom",
    "msfvnem":        "msfvenom",
    "hydrea":         "hydra",
    "hyrda":          "hydra",
    "hydrs":          "hydra",
    "haydra":         "hydra",
    "hashchat":       "hashcat",
    "hashtat":        "hashcat",
    "haschcat":       "hashcat",
    "gobsuter":       "gobuster",
    "gobsuter":       "gobuster",
    "gobsuster":      "gobuster",
    "gobustr":        "gobuster",
    "go buster":      "gobuster",
    "nikot":          "nikto",
    "nikot":          "nikto",
    "niko":           "nikto",
    "sqlmpa":         "sqlmap",
    "sqplmap":        "sqlmap",
    "sql map":        "sqlmap",
    "sqlmaps":        "sqlmap",
    "aicrack":        "aircrack",
    "aircrak":        "aircrack",
    "aircracak":      "aircrack",
    "aircarck":       "aircrack",
    "mimikatze":      "mimikatz",
    "mimikats":       "mimikatz",
    "mimikartz":      "mimikatz",
    "mimimkatz":      "mimikatz",
    "wireshrak":      "wireshark",
    "wirehsark":      "wireshark",
    "wirshark":       "wireshark",
    "wireshak":       "wireshark",
    "burpsuit":       "burp suite",
    "burpsiute":      "burp suite",
    "burpsuite":      "burp suite",
    "bupr suite":     "burp suite",
    "bloodhoud":      "bloodhound",
    "bloodhounf":     "bloodhound",
    "nuclei":         "nuclei",      # already correct, common confusion
    "nuceli":         "nuclei",
    "subifnder":      "subfinder",
    "subfidner":      "subfinder",
    "sub finder":     "subfinder",

    # Concept typos
    "sqli":           "sql injection",
    "xss":            "xss",
    "xxs":            "xss",
    "ssx":            "xss",
    "csrf":           "csrf",
    "csruf":          "csrf",
    "csrd":           "csrf",
    "ssrf":           "ssrf",
    "sssrf":          "ssrf",
    "srf":            "ssrf",
    "priv esc":       "privilege escalation",
    "privesc":        "privilege escalation",
    "priv-esc":       "privilege escalation",
    "priv escalation":"privilege escalation",
    "privlege esc":   "privilege escalation",
    "privledge":      "privilege escalation",
    "revshell":       "reverse shell",
    "rev shell":      "reverse shell",
    "reverese shell": "reverse shell",
    "pth":            "pass the hash",
    "pass-the-hash":  "pass the hash",
    "passthehash":    "pass the hash",
    "lpe":            "local privilege escalation",
    "rce":            "remote code execution",
    "lfi":            "local file inclusion",
    "rfi":            "remote file inclusion",
    "idor":           "insecure direct object reference",
    "ssti":           "server side template injection",
    "ssji":           "server side javascript injection",
    "deauth":         "deauthentication",
    "de auth":        "deauthentication",
    "4 way handshake":"four way handshake",
    "4way":           "four way handshake",
    "wpa 2":          "wpa2",
    "w p a 2":        "wpa2",
}


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7 — TEACHING RESPONSE TEMPLATES
# How ERR0RS frames teaching responses based on context
# ═══════════════════════════════════════════════════════════════════════════

TEACHING_RESPONSES: dict[str, str] = {

    "beginner_intro": (
        "[ERR0RS] Great question for a beginner. Let me break this down "
        "step by step from the ground up."
    ),

    "tool_intro": (
        "[ERR0RS] Here's everything you need to know about {tool}. "
        "I'll cover what it is, how it works, when to use it, and the exact commands."
    ),

    "concept_intro": (
        "[ERR0RS] Let me teach you about {concept}. "
        "Understanding this is core to offensive security — pay attention."
    ),

    "before_run": (
        "[ERR0RS] Before I run this, here's what {tool} is doing and why:\n"
    ),

    "after_run": (
        "[ERR0RS] That's what just happened. Here's what those results mean:\n"
    ),

    "wrong_tool": (
        "[ERR0RS] Hold up — that's the wrong tool for that job. "
        "Here's what you actually want to use and why:"
    ),

    "correction": (
        "[ERR0RS] Small correction — {wrong} won't do what you think. "
        "The right approach is {right}. Here's why:"
    ),

    "tool_not_found": (
        "[ERR0RS] I don't have a built-in lesson for '{topic}' yet. "
        "But here's what I know, and I'll pass this to Ollama for a deeper answer:"
    ),

    "phase_intro": (
        "[ERR0RS] You're in the {phase} phase of the engagement. "
        "Here's what that means and what tools apply:"
    ),

    "purple_intro": (
        "[ERR0RS PURPLE] Running attack AND detection simultaneously. "
        "I'll execute the offensive action, then show you what a defender sees:"
    ),

    "authorization_warning": (
        "[ERR0RS] REMINDER: This tool requires explicit written authorization "
        "before use against any system you don't own. Always get it in writing."
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 8 — CONFIRMATION AND NEGATION WORDS
# ERR0RS detects when operatives say yes, no, cancel, confirm
# ═══════════════════════════════════════════════════════════════════════════

CONFIRMATION_WORDS: list[str] = [
    # Standard yes
    "yes", "yep", "yeah", "yup", "yea", "ya", "yah",
    "sure", "sure thing", "of course", "absolutely",
    "definitely", "certainly", "affirmative",
    # Operator style
    "go", "go ahead", "go for it", "execute", "run it",
    "fire", "fire it", "fire away", "launch it",
    "do it", "do it now", "just do it",
    "yes please", "please do", "go ahead and run",
    "lets go", "let's go", "lets do it", "let's do it",
    "confirmed", "confirm", "roger", "roger that",
    "copy", "copy that", "wilco", "solid", "green light",
    "all good", "good to go", "gtg", "green",
    # Casual
    "ok", "okay", "k", "kk", "yea do it",
    "sounds good", "looks good", "good", "great",
    "perfect", "works", "works for me",
]

NEGATION_WORDS: list[str] = [
    # Standard no
    "no", "nope", "nah", "na", "negative",
    "don't", "dont", "do not", "stop", "halt",
    "cancel", "abort", "abort mission",
    "hold on", "hold up", "wait", "wait up",
    "actually no", "actually don't", "never mind",
    "nevermind", "nvm", "forget it", "skip it",
    "skip", "pass", "not now", "not yet",
    # Operator style
    "negative", "stand down", "stand by",
    "hold", "hold fire", "cease", "cease fire",
    "belay that", "belay", "disregard",
    "abort abort", "stop stop",
]


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 9 — ENGAGEMENT PHASE TRIGGERS
# Detects what phase of the kill chain the operator is in
# ═══════════════════════════════════════════════════════════════════════════

PHASE_TRIGGERS: dict[str, list[str]] = {

    "phase_1_recon": [
        "start recon", "begin recon", "kick off recon", "initial recon",
        "passive recon", "active recon", "osint", "external recon",
        "find the target", "gather intelligence", "gather intel",
        "target profiling", "attack surface", "footprinting",
        "initial scan", "discovery scan", "host discovery",
        "what's out there", "what do we know about",
        "phase 1", "recon phase", "reconnaissance",
    ],

    "phase_2_scan": [
        "scanning phase", "enumeration phase", "service enumeration",
        "port scanning", "vulnerability scanning", "vuln assessment",
        "service fingerprinting", "enumerate services",
        "enumerate the target", "full scan", "deep scan",
        "phase 2", "scan phase", "vulnerability assessment",
        "find vulnerabilities", "check for vulns",
    ],

    "phase_3_exploit": [
        "exploitation phase", "attack phase", "gaining access",
        "initial access", "foothold", "get a foothold",
        "exploit the target", "attack the target",
        "fire the exploit", "run the exploit",
        "phase 3", "exploit phase", "gaining foothold",
        "compromise the target", "pop the box",
    ],

    "phase_4_postexploit": [
        "post exploitation", "post exploit", "post access",
        "after initial access", "i have a shell", "i have access",
        "got a shell", "got meterpreter", "shell established",
        "foothold established", "now what", "whats next",
        "next steps", "after shell", "post compromise",
        "phase 4", "post exploit phase",
    ],

    "phase_5_privesc": [
        "privilege escalation", "escalation phase", "privesc",
        "getting root", "getting system", "becoming admin",
        "escalate on the box", "need higher privs",
        "i have low priv", "running as low priv user",
        "need to escalate", "phase 5", "privesc phase",
    ],

    "phase_6_lateral": [
        "lateral movement", "moving laterally", "pivoting phase",
        "spreading through network", "moving to next host",
        "pivot to next target", "internal network access",
        "move to internal", "phase 6", "lateral phase",
        "spreading the foothold", "expanding access",
    ],

    "phase_7_persist": [
        "persistence", "establishing persistence", "maintain access",
        "staying persistent", "backdoor the system",
        "install backdoor", "set up persistence",
        "make sure i keep access", "persistent access",
        "phase 7", "persistence phase",
    ],

    "phase_8_exfil": [
        "exfiltration", "exfil phase", "data exfiltration",
        "getting data out", "stealing the data",
        "pull the data", "exfil the loot",
        "get files out", "exfiltrate data",
        "phase 8", "exfil stage",
    ],

    "phase_9_report": [
        "reporting phase", "create the report", "write the report",
        "document findings", "generate report",
        "summarize the engagement", "debrief",
        "phase 9", "report phase", "final report",
        "engagement summary", "finding summary",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 10 — TONE DETECTION
# ERR0RS adjusts its teaching style based on operator experience level
# ═══════════════════════════════════════════════════════════════════════════

TONE_INDICATORS: dict[str, str] = {

    "beginner": [
        "beginner", "newbie", "noob", "new to this", "just starting",
        "getting started", "first time", "never done this",
        "dont know", "dont understand", "confused", "lost",
        "simple explanation", "eli5", "dumb it down",
        "in plain english", "laymans terms",
    ],

    "intermediate": [
        "intermediate", "some experience", "know the basics",
        "used it before", "familiar with", "know a bit",
        "understand the concept", "need a refresher",
        "been doing this for a while", "apprentice",
    ],

    "expert": [
        "expert", "advanced", "senior", "experienced",
        "know what i'm doing", "just need the command",
        "skip the basics", "skip the explanation",
        "tl;dr", "just the flags", "just the syntax",
        "no hand holding", "cut to the chase",
        "just tell me the command", "just give me the command",
        "command only", "flags only", "quick ref",
        "veteran", "operator", "red team operator",
    ],

    "operator": [
        "operator", "operative", "red teamer", "red team",
        "professional", "on an engagement", "in the field",
        "on a live op", "active engagement",
        "need this fast", "time sensitive", "quick",
        "what's the fastest way", "fastest method",
        "most efficient", "most effective",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 11 — HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def _normalize(text: str) -> str:
    """Lowercase, strip, collapse whitespace."""
    return re.sub(r'\s+', ' ', text.lower().strip())


def expand_keywords(term: str) -> list[str]:
    """
    Given a keyword, return all known aliases and variants.
    Useful for building search indexes.

    Example:
        expand_keywords("nmap") → ["nmap", "port scan", "network scan", ...]
    """
    results = [term]
    lower = term.lower()

    # Check EXTENDED_TOOL_PHRASES
    if lower in EXTENDED_TOOL_PHRASES:
        results.extend(EXTENDED_TOOL_PHRASES[lower])

    # Check OPERATOR_SLANG (reverse lookup)
    for slang, category in OPERATOR_SLANG.items():
        if category == lower or category == term:
            results.append(slang)

    # Check TYPO_MAP (reverse lookup)
    for typo, correct in TYPO_MAP.items():
        if correct == lower:
            results.append(typo)

    return list(set(results))


def fuzzy_match_tool(text: str) -> tuple[Optional[str], float]:
    """
    Try to match user text to a tool name, returning (tool_name, confidence).
    Confidence: 1.0 = exact, 0.8 = typo corrected, 0.6 = slang matched, 0.4 = partial.
    Returns (None, 0.0) if no match found.
    """
    lower = _normalize(text)
    words = lower.split()

    # Exact match in EXTENDED_TOOL_PHRASES keys
    if lower in EXTENDED_TOOL_PHRASES:
        return (lower, 1.0)

    # Typo correction
    for typo, correct in TYPO_MAP.items():
        if typo in lower:
            return (correct, 0.8)

    # Operator slang
    for slang, category in OPERATOR_SLANG.items():
        if slang in lower:
            return (category, 0.6)

    # Partial match in tool phrase lists
    for tool, phrases in EXTENDED_TOOL_PHRASES.items():
        for phrase in phrases:
            phrase_words = phrase.split()
            if all(w in words for w in phrase_words if len(w) > 3):
                return (tool, 0.4)

    return (None, 0.0)


def get_response_tone(text: str) -> str:
    """
    Detect the operator's experience level from their message.
    Returns: 'beginner' | 'intermediate' | 'expert' | 'operator'
    """
    lower = _normalize(text)
    for tone, indicators in TONE_INDICATORS.items():
        if any(ind in lower for ind in indicators):
            return tone
    return 'intermediate'  # default


def detect_compound_intent(text: str) -> Optional[str]:
    """
    Detect if the user wants to chain multiple actions.
    Returns compound intent key or None.
    """
    lower = _normalize(text)
    for intent_key, phrases in COMPOUND_INTENTS.items():
        if any(phrase in lower for phrase in phrases):
            return intent_key
    return None


def detect_engagement_phase(text: str) -> Optional[str]:
    """
    Detect which kill chain phase the operator is currently in.
    Returns phase key or None.
    """
    lower = _normalize(text)
    for phase, triggers in PHASE_TRIGGERS.items():
        if any(t in lower for t in triggers):
            return phase
    return None


def correct_typo(text: str) -> tuple[str, bool]:
    """
    Correct known typos in the input text.
    Returns (corrected_text, was_corrected).
    """
    lower = text.lower()
    corrected = lower
    was_corrected = False
    for typo, correct in TYPO_MAP.items():
        if typo in corrected:
            corrected = corrected.replace(typo, correct)
            was_corrected = True
    return (corrected, was_corrected)


def is_beginner_confusion(text: str) -> Optional[str]:
    """
    Check if the user is asking a classic beginner confusion question.
    Returns the correct topic key to route to, or None.
    """
    lower = _normalize(text)
    for phrase, topic in BEGINNER_PHRASES.items():
        if phrase in lower:
            return topic
    return None


def get_operator_slang_category(text: str) -> Optional[str]:
    """
    Detect operator slang and return the underlying category.
    """
    lower = _normalize(text)
    best = None
    best_len = 0
    for slang, category in OPERATOR_SLANG.items():
        if slang in lower and len(slang) > best_len:
            best = category
            best_len = len(slang)
    return best


# ── Self-test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        ("yo how do i pop that box", "exploit"),
        ("teach me mimikatz from scratch", "teach"),
        ("can mimikatz crack wifi", "wireless_tool_selection"),
        ("scan then exploit the target", "scan_then_exploit"),
        ("brute force the ssh login on 10.0.0.1", "hydra"),
        ("crack this ntlm hash: aabbccdd", "hashcat"),
        ("mataslpoit is confusing", "metasploit"),
        ("i want to learn sql injection", "sql injection"),
        ("exploit then escalate then dump creds", "exploit_then_escalate"),
        ("im a beginner how do i start hacking", "pentesting_methodology"),
        ("just give me the nmap command no explanation", "expert"),
    ]

    print("[ERR0RS v2] Language Expansion Self-Test\n" + "="*60)
    for text, expected in tests:
        corrected, fixed = correct_typo(text)
        tool, conf  = fuzzy_match_tool(corrected)
        phase       = detect_engagement_phase(corrected)
        compound    = detect_compound_intent(corrected)
        tone        = get_response_tone(corrected)
        beginner    = is_beginner_confusion(corrected)
        slang       = get_operator_slang_category(corrected)

        print(f"\n  INPUT   : '{text}'")
        if fixed:
            print(f"  CORRECTED: '{corrected}'")
        print(f"  TOOL    : {tool} (conf={conf:.1f})")
        print(f"  PHASE   : {phase}")
        print(f"  COMPOUND: {compound}")
        print(f"  TONE    : {tone}")
        print(f"  BEGINNER: {beginner}")
        print(f"  SLANG   : {slang}")
    print("\n" + "="*60)
