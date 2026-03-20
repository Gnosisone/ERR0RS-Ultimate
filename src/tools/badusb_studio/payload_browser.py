"""
ERR0RS BadUSB Studio - Payload Browser
Browses Hak5 PayloadHub (GitHub), local library, and opens Payload Studio
"""

import os
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

CACHE_DIR = Path(__file__).parent / "payloads" / "cache"
LOCAL_DIR = Path(__file__).parent / "payloads" / "local"

HAK5_API_BASE = "https://api.github.com/repos/hak5/usbrubberducky-payloads/contents/payloads/library"
HAK5_RAW_BASE = "https://raw.githubusercontent.com/hak5/usbrubberducky-payloads/master/payloads/library"
PAYLOAD_STUDIO_URL = "https://payloadstudio.hak5.org"

CACHE_EXPIRY_SECONDS = 3600  # 1 hour


class PayloadBrowser:
    """Browse Hak5 PayloadHub, local library, and Payload Studio"""

    def __init__(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        self._category_cache = None
        self._cache_time = 0

    # ------------------------------------------------------------------ #
    #  HAK5 PAYLOAD HUB                                                   #
    # ------------------------------------------------------------------ #

    def get_hak5_categories(self) -> list[dict]:
        """Fetch top-level categories from Hak5 PayloadHub via GitHub API"""
        now = time.time()
        if self._category_cache and (now - self._cache_time) < CACHE_EXPIRY_SECONDS:
            return self._category_cache

        try:
            req = urllib.request.Request(
                HAK5_API_BASE,
                headers={"User-Agent": "ERR0RS-Ultimate/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            categories = [
                {"name": item["name"], "path": item["path"], "url": item["url"]}
                for item in data if item["type"] == "dir"
            ]
            self._category_cache = categories
            self._cache_time = now
            return categories
        except Exception as e:
            return [{"error": str(e)}]

    def get_hak5_payloads(self, category: str) -> list[dict]:
        """Fetch payloads within a specific category"""
        url = f"{HAK5_API_BASE}/{category}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ERR0RS-Ultimate/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            return [
                {"name": item["name"], "category": category}
                for item in data if item["type"] == "dir"
            ]
        except Exception as e:
            return [{"error": str(e)}]

    def fetch_hak5_payload(self, category: str, payload_name: str) -> str | None:
        """Download a specific payload from Hak5 PayloadHub"""
        url = f"{HAK5_RAW_BASE}/{category}/{payload_name}/payload.txt"
        cache_file = CACHE_DIR / f"{category}__{payload_name}.txt"

        # Return cached version if fresh
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < CACHE_EXPIRY_SECONDS:
                return cache_file.read_text(encoding="utf-8")

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ERR0RS-Ultimate/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode("utf-8")
            cache_file.write_text(content, encoding="utf-8")
            return content
        except Exception as e:
            return None

    def search_hak5_payloads(self, keyword: str) -> list[dict]:
        """Search Hak5 PayloadHub by keyword across all categories"""
        results = []
        categories = self.get_hak5_categories()
        for cat in categories:
            if "error" in cat:
                continue
            payloads = self.get_hak5_payloads(cat["name"])
            for p in payloads:
                if "error" not in p and keyword.lower() in p["name"].lower():
                    results.append(p)
        return results

    # ------------------------------------------------------------------ #
    #  LOCAL PAYLOAD LIBRARY                                              #
    # ------------------------------------------------------------------ #

    def list_local_payloads(self) -> list[str]:
        """List all locally saved payloads"""
        return [f.name for f in LOCAL_DIR.glob("*.txt")]

    def load_local_payload(self, filename: str) -> str | None:
        """Load a locally saved payload"""
        path = LOCAL_DIR / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def save_local_payload(self, name: str, content: str) -> str:
        """Save a payload to the local library"""
        if not name.endswith(".txt"):
            name += ".txt"
        path = LOCAL_DIR / name
        path.write_text(content, encoding="utf-8")
        return str(path)

    def delete_local_payload(self, filename: str) -> bool:
        """Delete a locally saved payload"""
        path = LOCAL_DIR / filename
        if path.exists():
            path.unlink()
            return True
        return False

    # ------------------------------------------------------------------ #
    #  PAYLOAD STUDIO                                                     #
    # ------------------------------------------------------------------ #

    def open_payload_studio(self):
        """Open Hak5 Payload Studio in the default browser"""
        import webbrowser
        webbrowser.open(PAYLOAD_STUDIO_URL)
        return f"Opened Payload Studio: {PAYLOAD_STUDIO_URL}"

    def open_payload_studio_with_payload(self, payload_content: str):
        """
        Save payload to local file and open Payload Studio.
        User can manually import since free tier does not expose a write API.
        """
        import webbrowser
        temp_path = LOCAL_DIR / "_payload_studio_export.txt"
        temp_path.write_text(payload_content, encoding="utf-8")
        webbrowser.open(PAYLOAD_STUDIO_URL)
        return (
            f"Payload saved to: {temp_path}\n"
            f"Payload Studio opened. Use File > Import to load your payload."
        )
