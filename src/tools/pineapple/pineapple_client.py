"""
ERR0RS Pineapple Client
Handles REST API connection and authentication to the WiFi Pineapple Nano.
Default IP: 172.16.42.1  Port: 1471
API docs: https://github.com/hak5/wifi-pineapple-community
"""

import json
import urllib.request
import urllib.error
import urllib.parse

PINEAPPLE_IP   = "172.16.42.1"
PINEAPPLE_PORT = 1471
BASE_URL       = f"http://{PINEAPPLE_IP}:{PINEAPPLE_PORT}"
TIMEOUT        = 10


class PineappleClient:
    """
    Low-level REST API client for WiFi Pineapple Nano.
    Handles auth token and all HTTP communication.
    """

    def __init__(self, ip: str = PINEAPPLE_IP, port: int = PINEAPPLE_PORT,
                 password: str = None, token: str = None):
        self.ip       = ip
        self.port     = port
        self.base_url = f"http://{ip}:{port}"
        self.token    = token
        self.password = password
        self.connected = False

    # ------------------------------------------------------------------ #
    #  CONNECTION & AUTH                                                  #
    # ------------------------------------------------------------------ #

    def connect(self, password: str = None) -> dict:
        """Authenticate with Pineapple and retrieve API token"""
        pwd = password or self.password
        if not pwd:
            return {"success": False, "message": "Password required to connect."}
        payload = json.dumps({"password": pwd}).encode()
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/login",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = json.loads(resp.read())
            if "token" in data:
                self.token = data["token"]
                self.connected = True
                return {"success": True, "token": self.token,
                        "message": "Connected to WiFi Pineapple Nano"}
            return {"success": False, "message": str(data)}
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {e}"}

    def is_connected(self) -> bool:
        """Ping the Pineapple to verify connection"""
        try:
            result = self.get("/api/system/info")
            self.connected = "hostname" in result or "version" in result
            return self.connected
        except Exception:
            self.connected = False
            return False

    def disconnect(self):
        """Clear token and mark disconnected"""
        self.token = None
        self.connected = False
        return {"success": True, "message": "Disconnected from Pineapple"}

    # ------------------------------------------------------------------ #
    #  HTTP METHODS                                                       #
    # ------------------------------------------------------------------ #

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def get(self, endpoint: str) -> dict:
        """HTTP GET request to Pineapple API"""
        try:
            req = urllib.request.Request(
                f"{self.base_url}{endpoint}",
                headers=self._headers()
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"error": str(e)}

    def post(self, endpoint: str, data: dict = None) -> dict:
        """HTTP POST request to Pineapple API"""
        payload = json.dumps(data or {}).encode()
        try:
            req = urllib.request.Request(
                f"{self.base_url}{endpoint}",
                data=payload,
                headers=self._headers(),
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else {"success": True}
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"error": str(e)}

    def put(self, endpoint: str, data: dict = None) -> dict:
        """HTTP PUT request to Pineapple API"""
        payload = json.dumps(data or {}).encode()
        try:
            req = urllib.request.Request(
                f"{self.base_url}{endpoint}",
                data=payload,
                headers=self._headers(),
                method="PUT"
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else {"success": True}
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"error": str(e)}

    def delete(self, endpoint: str) -> dict:
        """HTTP DELETE request to Pineapple API"""
        try:
            req = urllib.request.Request(
                f"{self.base_url}{endpoint}",
                headers=self._headers(),
                method="DELETE"
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else {"success": True}
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------ #
    #  SYSTEM INFO                                                        #
    # ------------------------------------------------------------------ #

    def system_info(self) -> dict:
        """Get Pineapple system info: hostname, firmware, uptime, etc."""
        return self.get("/api/system/info")

    def system_resources(self) -> dict:
        """Get CPU, memory, storage usage"""
        return self.get("/api/system/resources")

    def reboot(self) -> dict:
        """Reboot the Pineapple"""
        return self.post("/api/system/reboot")

    def shutdown(self) -> dict:
        """Shutdown the Pineapple"""
        return self.post("/api/system/shutdown")
