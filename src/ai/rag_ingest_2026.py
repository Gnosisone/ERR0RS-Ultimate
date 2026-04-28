"""
ERR0RS-Ultimate :: RAG Knowledge Base Ingester
Kali 2026.1 + 7h30th3r0n3 Edition

Ingests:
  1. 7h30th3r0n3 GitHub repos (Evil-M5Project, Raspyjack, Evil-BW16, etc.)
  2. Kali 2026.1 new tools (MetasploitMCP, AdaptixC2, Atomic-Operator,
     Fluxion, SSTImap, WPProbe, XSStrike, GEF)
  3. Attack chain cheatsheets

Usage:
    python rag_ingest_2026.py                    # Full ingest
    python rag_ingest_2026.py --source kali2026  # Kali tools only
    python rag_ingest_2026.py --source 7h30      # 7h30 repos only
    python rag_ingest_2026.py --list             # Show current DB

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import os, sys, json, hashlib, argparse, subprocess, textwrap
from pathlib import Path

CHROMA_DB_PATH  = os.getenv("CHROMA_DB_PATH", os.path.expanduser("~/err0rs_chromadb"))
COLLECTION_NAME = "err0rs_knowledge"
CLONE_DIR       = os.path.expanduser("~/err0rs_rag_sources")
EMBED_MODEL     = os.getenv("EMBED_MODEL", "nomic-embed-text")

# ── 7h30th3r0n3 Repositories ──────────────────────────────────────
REPOS_7H30 = [
    {
        "repo":     "https://github.com/7h30th3r0n3/Evil-M5Project",
        "name":     "Evil-M5Project",
        "tags":     ["wifi","evil-twin","captive-portal","esp32","m5stack",
                     "deauth","karma","wardriving","bluetooth","ble-spam",
                     "wall-of-flipper","handshake-capture","honeypot"],
        "category": "wireless",
        "summary":  "Comprehensive ESP32/M5Stack offensive WiFi toolkit with 40+ features: Evil Twin, Karma, deauth, captive portals with credential harvesting, multi-ESP32 wardriving rigs, BLE Name Flood, Wall of Flipper BLE detection, PMKID/EAPOL capture, DHCP starvation, DNS poisoning, SSH shell, BadUSB, and on-device LLM chat."
    },
    {
        "repo":     "https://github.com/7h30th3r0n3/Raspyjack",
        "name":     "Raspyjack",
        "tags":     ["raspberry-pi","shark-jack","red-team","implant","evil-portal",
                     "exfiltration","mitm","responder","tailscale","reverse-shell"],
        "category": "hardware",
        "summary":  "Raspberry Pi red team implant inspired by Hak5 Shark Jack. WebUI, browser IDE for payloads, TLS via Caddy, Responder for LLMNR/NBT-NS credential interception, WPAD abuse, wardriving, Tailscale shell, reverse shells."
    },
    {
        "repo":     "https://github.com/7h30th3r0n3/Evil-BW16",
        "name":     "Evil-BW16",
        "tags":     ["dual-band","5ghz","2.4ghz","deauth","bw16","rtl8720dn",
                     "sniffer","beacon","probe","eapol","pwnagotchi"],
        "category": "wireless",
        "summary":  "Dual-band 2.4GHz and 5.8GHz deauthentication tool using BW16 (RTL8720dn). Serial-controlled. Sniffer modes for beacons, probes, deauth, EAPOL, Pwnagotchi detection."
    },
    {
        "repo":     "https://github.com/7h30th3r0n3/OllamaHound",
        "name":     "OllamaHound",
        "tags":     ["ollama","llm","reconnaissance","shodan","cve","ai-security"],
        "category": "recon",
        "summary":  "Mass recon and exploitation framework targeting exposed Ollama/LLM instances via Shodan. Pipeline: Scraper → Scanner (CVE fingerprint) → Connector (interactive exploitation)."
    },
    {
        "repo":     "https://github.com/7h30th3r0n3/NanoC6-ESP32-Honeypot",
        "name":     "NanoC6-ESP32-Honeypot",
        "tags":     ["honeypot","esp32","iot","service-emulation","webhook"],
        "category": "defensive",
        "summary":  "ESP32 honeypot emulating 12 ports: FTP, SSH, SMB, RDP, MySQL, Telnet, HTTP, HTTPS, MQTT, Redis. Discord/Telegram/SIEM webhook alerts. SPIFFS persistence."
    },
    {
        "repo":     "https://github.com/7h30th3r0n3/PwnGridSpam",
        "name":     "PwnGridSpam",
        "tags":     ["pwnagotchi","esp32","dos","pwngrid","ble"],
        "category": "wireless",
        "summary":  "ESP32 attack that spams Pwnagotchi PwnGrid network with custom face/name, causing Denial of Screen attacks."
    },
    {
        "repo":     "https://github.com/7h30th3r0n3/LFI-scan",
        "name":     "LFI-scan",
        "tags":     ["lfi","local-file-inclusion","web","directory-traversal"],
        "category": "web",
        "summary":  "Perl LFI/directory traversal scanner for web app security testing."
    },
]

# ── Kali 2026.1 Tool Documentation ───────────────────────────────
KALI_2026_TOOLS = [
    {
        "name": "MetasploitMCP", "package": "metasploit-mcp", "kali_version": "2026.1",
        "tags": ["metasploit","mcp","model-context-protocol","exploitation",
                 "payload","sessions","post-exploitation","ai-integration"],
        "category": "exploit",
        "description": "MetasploitMCP is an MCP server for the Metasploit Framework, official in Kali 2026.1. Bridges LLMs (Ollama/Claude) to full MSF exploitation. Tools: list_exploits, list_payloads, run_exploit, run_auxiliary_module, run_post_module, generate_payload, list_active_sessions, send_session_command, terminate_session, start_listener, stop_job. Transport: HTTP/SSE or STDIO. Setup: msfrpcd -P <pass> -S -a 127.0.0.1 -p 55553, then python MetasploitMCP.py --transport http --port 8085."
    },
    {
        "name": "AdaptixC2", "package": "adaptixc2", "kali_version": "2026.1",
        "tags": ["c2","command-and-control","post-exploitation","adversary-emulation","red-team"],
        "category": "c2",
        "description": "Extensible post-exploitation and adversarial emulation C2 framework in Kali 2026.1. Supports custom agent architecture, MITRE ATT&CK aligned TTPs, lateral movement, persistence, multi-operator collaboration, and malleable C2 profiles for traffic evasion."
    },
    {
        "name": "Atomic-Operator", "package": "atomic-operator", "kali_version": "2026.1",
        "tags": ["atomic-red-team","mitre-attck","purple-team","adversary-simulation"],
        "category": "c2",
        "description": "Execute Atomic Red Team MITRE ATT&CK tests across Windows/Linux/macOS. Purple team detection validation. Usage: atomic-operator run --techniques T1059.001 --os linux. Key techniques: T1059 (cmd exec), T1078 (valid accounts), T1110 (brute force), T1003 (credential dump)."
    },
    {
        "name": "Fluxion", "package": "fluxion", "kali_version": "2026.1",
        "tags": ["wifi","evil-twin","captive-portal","social-engineering","wpa2"],
        "category": "wireless",
        "description": "WiFi evil twin + captive portal social engineering tool in Kali 2026.1. Flow: scan AP → capture WPA handshake → jam AP (deauth flood) → spin up evil twin → present captive portal → verify submitted password against handshake → harvest credentials. Requires aircrack-ng suite and monitor-mode adapter."
    },
    {
        "name": "SSTImap", "package": "sstimap", "kali_version": "2026.1",
        "tags": ["ssti","server-side-template-injection","web","jinja2","twig","rce"],
        "category": "web",
        "description": "Auto SSTI detection and exploitation tool in Kali 2026.1. Engines: Jinja2, Twig, FreeMarker, Smarty, Mako, Velocity. RCE via template sandbox escape. Usage: sstimap -u 'http://target.com/page?name=test'. Jinja2 detect: {{7*7}}→49. Interactive shell mode post-exploitation."
    },
    {
        "name": "WPProbe", "package": "wpprobe", "kali_version": "2026.1",
        "tags": ["wordpress","cms","plugin-enum","web","vulnerability-assessment"],
        "category": "web",
        "description": "Fast WordPress plugin enumeration tool in Kali 2026.1. Passively fingerprints installed plugins and versions. Usage: wpprobe -u http://target-site.com -t 10. Chain: wpprobe → cross-ref WPScan vuln DB → nuclei -t wordpress/ → searchsploit [plugin] → MSF auxiliary/scanner/http/wordpress_*."
    },
    {
        "name": "XSStrike", "package": "xsstrike", "kali_version": "2026.1",
        "tags": ["xss","cross-site-scripting","web","dom-xss","waf-evasion"],
        "category": "web",
        "description": "Advanced XSS scanner with intelligent payload mutation in Kali 2026.1. Detects reflected, stored, DOM XSS. WAF fingerprinting and evasion. Crawl mode. Usage: xsstrike -u 'http://target.com/search?q=test' --crawl. Supports JSON APIs and header injection testing."
    },
    {
        "name": "GEF", "package": "gef", "kali_version": "2026.1",
        "tags": ["gdb","debugging","exploit-development","buffer-overflow","binary-exploitation"],
        "category": "exploit-dev",
        "description": "GDB Enhanced Features — modern debugger for exploit development in Kali 2026.1. Heap analysis, ROP gadget discovery, cyclic pattern generation (pattern create/offset), format string assistance, ASLR bypass helpers. Usage: gef → pattern create 200 → pattern offset $pc → rop --search 'pop rdi'."
    },
]

ATTACK_CHAINS = [
    {
        "name": "Internal Network Assessment Chain",
        "tags": ["attack-chain","internal","smb","windows","active-directory"],
        "content": "ERR0RS Internal Network Chain: PHASE 1 nmap_quick (service scan /24) → PHASE 2 msf auxiliary/scanner/smb/smb_ms17_010 + smb_enumshares + smb_enumusers → PHASE 3 nuclei (cves critical,high) → PHASE 4 if MS17-010: start_listener → run_exploit eternalblue → if web: nikto+sqlmap+xsstrike → PHASE 5 session_cmd sysinfo/getsystem/load kiwi/creds_all + run_post local_exploit_suggester → PHASE 6 lateral movement with creds via smb_login + hydra rdp → PHASE 7 generate_report html/pdf"
    },
    {
        "name": "Web Application Pentest Chain",
        "tags": ["attack-chain","web","owasp","sqli","xss","ssti"],
        "content": "ERR0RS Web App Chain: nmap (ports 80/443/8080/8443) → gobuster dir → nikto → nuclei (misconfigs,technologies) → wpprobe (if WordPress) → sqlmap (level 3 risk 2) → xsstrike (--crawl) → sstimap (level 2) → if RCE: msf generate_payload php/meterpreter/reverse_tcp → start_listener → catch session. OWASP Top 10: A01 broken access=gobuster+auth, A03 injection=sqlmap+sstimap, A07 auth=hydra, XSS=xsstrike."
    },
    {
        "name": "MetasploitMCP Quick Reference",
        "tags": ["metasploit","mcp","cheatsheet"],
        "content": "MetasploitMCP Setup: msfrpcd -P err0rs_local -S -a 127.0.0.1 -p 55553 | python MetasploitMCP.py --transport http --host 127.0.0.1 --port 8085. EternalBlue chain: start_listener(meterpreter/reverse_tcp) → run_exploit(ms17_010_eternalblue, RHOSTS, meterpreter). Web shell: generate_payload(php/meterpreter/reverse_tcp, raw) → upload → trigger → catch. Post-ex: list_sessions() → session_cmd(id, 'load kiwi') → session_cmd(id, 'creds_all') → run_post(local_exploit_suggester, id). Common auxiliary: smb_ms17_010, smb_enumshares, ssh_login, http_login."
    }
]


# ── Ingest Engine ─────────────────────────────────────────────────
def get_chroma_collection():
    try:
        import chromadb
        from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        embed_fn = OllamaEmbeddingFunction(
            url="http://localhost:11434/api/embeddings", model_name=EMBED_MODEL)
        return client.get_or_create_collection(
            name=COLLECTION_NAME, embedding_function=embed_fn,
            metadata={"hnsw:space": "cosine"})
    except ImportError:
        print("❌ chromadb not installed: pip install chromadb --break-system-packages")
        sys.exit(1)

def doc_id(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list:
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunks.append(" ".join(words[i:i + chunk_size]))
        i += chunk_size - overlap
    return chunks

def clone_repo(repo_url: str, dest: str) -> bool:
    if Path(dest).exists():
        subprocess.run(["git", "-C", dest, "pull", "--quiet"], capture_output=True)
        return True
    result = subprocess.run(["git", "clone", "--depth=1", "--quiet", repo_url, dest],
                            capture_output=True, text=True)
    return result.returncode == 0


def ingest_repo(collection, repo_info: dict, clone_path: str) -> int:
    count = 0
    extensions = {".py",".md",".txt",".ino",".c",".cpp",".h",".js",".sh",".yaml",".yml"}
    for fpath in Path(clone_path).rglob("*"):
        if not fpath.is_file(): continue
        if fpath.suffix.lower() not in extensions: continue
        if any(p in str(fpath) for p in [".git","node_modules","__pycache__"]): continue
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
            if len(content) < 50: continue
            rel_path = str(fpath.relative_to(clone_path))
            meta = {"source": repo_info["name"], "repo_url": repo_info["repo"],
                    "file": rel_path, "category": repo_info["category"],
                    "tags": ",".join(repo_info["tags"]), "type": "source_code"}
            for i, chunk in enumerate(chunk_text(content)):
                doc = f"[{repo_info['name']}] {rel_path}\n\n{chunk}"
                collection.upsert(ids=[doc_id(doc)], documents=[doc],
                                   metadatas=[{**meta, "chunk": i}])
                count += 1
        except Exception:
            pass
    # Ingest summary
    summary = f"[{repo_info['name']} OVERVIEW]\n\n{repo_info['summary']}"
    collection.upsert(ids=[doc_id(summary)], documents=[summary],
                       metadatas=[{"source": repo_info["name"],
                                   "category": repo_info["category"],
                                   "tags": ",".join(repo_info["tags"]),
                                   "type": "summary"}])
    return count + 1

def ingest_tools(collection, tools: list) -> int:
    for tool in tools:
        text = f"[TOOL: {tool['name']} | Kali {tool.get('kali_version','2026.1')}]\n\n{tool['description']}"
        collection.upsert(ids=[doc_id(text)], documents=[text],
                           metadatas={"source": tool["name"],
                                      "package": tool.get("package", tool["name"].lower()),
                                      "category": tool.get("category","unknown"),
                                      "tags": ",".join(tool.get("tags",[])),
                                      "kali_version": tool.get("kali_version","2026.1"),
                                      "type": "tool_documentation"})
    return len(tools)

def ingest_chains(collection, chains: list) -> int:
    for chain in chains:
        text = f"[ATTACK CHAIN: {chain['name']}]\n\n{chain['content']}"
        collection.upsert(ids=[doc_id(text)], documents=[text],
                           metadatas={"source": chain["name"], "category": "attack-chain",
                                      "tags": ",".join(chain.get("tags",[])),
                                      "type": "attack_chain"})
    return len(chains)


def main():
    parser = argparse.ArgumentParser(description="ERR0RS RAG Ingester — Kali 2026.1 Edition")
    parser.add_argument("--source", choices=["7h30","kali2026","chains","all"], default="all")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    print("\n" + "═"*55)
    print("  ERR0RS RAG Ingester — Kali 2026.1 + 7h30th3r0n3")
    print("═"*55 + "\n")

    collection = get_chroma_collection()
    print(f"✓ ChromaDB: {CHROMA_DB_PATH} ({collection.count()} existing docs)\n")

    if args.list:
        results = collection.get(include=["metadatas"])
        sources = {}
        for meta in results["metadatas"]:
            src = meta.get("source","unknown")
            sources[src] = sources.get(src, 0) + 1
        for src, count in sorted(sources.items()):
            print(f"  {src:40s} {count} chunks")
        print(f"\nTotal: {collection.count()} chunks")
        return

    total = 0
    os.makedirs(CLONE_DIR, exist_ok=True)

    if args.source in ("7h30","all"):
        print("📦 Ingesting 7h30th3r0n3 repositories...")
        for repo_info in REPOS_7H30:
            print(f"  → {repo_info['name']}")
            clone_path = os.path.join(CLONE_DIR, repo_info["name"])
            if clone_repo(repo_info["repo"], clone_path):
                n = ingest_repo(collection, repo_info, clone_path)
            else:
                n = ingest_repo(collection, repo_info, clone_path) if Path(clone_path).exists() else 1
                print(f"    ⚠ Clone failed — summary only")
            print(f"    ✓ {n} chunks")
            total += n

    if args.source in ("kali2026","all"):
        print("\n📦 Ingesting Kali 2026.1 tool docs...")
        n = ingest_tools(collection, KALI_2026_TOOLS)
        print(f"  ✓ {n} tool docs ingested")
        total += n

    if args.source in ("chains","all"):
        print("\n📦 Ingesting attack chain cheatsheets...")
        n = ingest_chains(collection, ATTACK_CHAINS)
        print(f"  ✓ {n} attack chains ingested")
        total += n

    print(f"\n{'═'*55}")
    print(f"  ✅ Done! {total} new chunks | Total: {collection.count()}")
    print(f"{'═'*55}\n")


if __name__ == "__main__":
    main()
