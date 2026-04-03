#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Hailo AI HAT+ 2 NPU Integration
===================================================
Raspberry Pi AI HAT+ 2 | Hailo-10H | 40 TOPS | 8GB LPDDR4X

Architecture:
  ERR0RS Brain → hailo_npu.py → [hailo-ollama server OR hailo_platform direct]
                               → fallback: Ollama CPU → builtin teach engine

IMPORTANT FACTS (from research, April 2026):
  - Hailo-10H uses hailo1x_pci kernel module (NOT hailo_pci — that's Hailo-8)
  - Supported models: Qwen2.5-1.5B, Qwen2.5-Coder-1.5B, Llama-3.2-1B, DeepSeek-R1-1.5B
  - NO GGUF support — Hailo runs HEF (Hailo Executable Format) only
  - hailo-ollama exposes Ollama-compatible REST API on port 8000
  - qwen2.5-coder:7b CANNOT run on Hailo-10H (exceeds 8GB on-module memory)
  - Real perf: ~6.5-9.5 tok/s NPU vs ~11.7 tok/s Pi5 CPU (NPU frees CPU for other work)
  - Best use: offload small LLM to NPU, use CPU for tool execution + UI

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import os
import json
import time
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

# ─── Hailo NPU model registry ─────────────────────────────────────────────────
# These are the ONLY models available for Hailo-10H as of April 2026.
# hailo-ollama uses these model names — they map to HEF files in the model zoo.

HAILO_LLM_MODELS = {
    # Default for ERR0RS — best code reasoning on Hailo-10H
    "qwen2.5-coder-1.5b": {
        "hailo_name": "qwen2.5-coder-1.5b-instruct",
        "params": "1.5B",
        "tok_per_sec": 6.5,
        "best_for": "code generation, pentest commands, tool guidance",
    },
    # General reasoning — slightly faster
    "qwen2.5-1.5b": {
        "hailo_name": "qwen2.5-1.5b-instruct",
        "params": "1.5B",
        "tok_per_sec": 9.45,
        "best_for": "general Q&A, threat intel, explanations",
    },
    # Smaller — fastest on NPU
    "llama3.2-1b": {
        "hailo_name": "llama3.2-1b-instruct",
        "params": "1B",
        "tok_per_sec": 7.0,
        "best_for": "fast responses, simple queries",
    },
    # DeepSeek reasoning
    "deepseek-r1-1.5b": {
        "hailo_name": "deepseek-r1-distill-qwen-1.5b",
        "params": "1.5B",
        "tok_per_sec": 6.5,
        "best_for": "step-by-step reasoning, complex analysis",
    },
}

# hailo-ollama default port (Hailo's custom Ollama-compatible server)
HAILO_OLLAMA_PORT = int(os.getenv("HAILO_OLLAMA_PORT", "8000"))
HAILO_OLLAMA_URL  = f"http://localhost:{HAILO_OLLAMA_PORT}"

# Standard Ollama fallback port
OLLAMA_URL = "http://localhost:11434"


# ─── Hardware detection ────────────────────────────────────────────────────────

class HailoDetector:
    """
    Detects Hailo-10H NPU and verifies all required software components.
    Uses multiple detection methods in order of reliability.
    """

    _cache: Optional[dict] = None   # cache result — detection is expensive

    @classmethod
    def detect(cls, force: bool = False) -> dict:
        """
        Full hardware + software detection.
        Returns a status dict with all findings.
        """
        if cls._cache and not force:
            return cls._cache

        result = {
            "hailo_found":        False,
            "chip":               None,
            "firmware_version":   None,
            "driver_module":      None,
            "device_node":        False,
            "hailortcli":         False,
            "hailo_platform_py":  False,
            "hailo_ollama":       False,
            "hailo_ollama_models": [],
            "pcie_detected":      False,
            "error":              None,
        }

        # 1. Check /dev/hailo0 device node
        result["device_node"] = Path("/dev/hailo0").exists()

        # 2. Check kernel module (must be hailo1x_pci for Hailo-10H, NOT hailo_pci)
        try:
            lsmod = subprocess.check_output(["lsmod"], text=True, timeout=3)
            if "hailo1x_pci" in lsmod:
                result["driver_module"] = "hailo1x_pci"
                result["hailo_found"]   = True
            elif "hailo_pci" in lsmod:
                result["driver_module"] = "hailo_pci"
                result["hailo_found"]   = True
                result["error"] = ("hailo_pci module loaded instead of hailo1x_pci — "
                                   "may be Hailo-8 driver. Run: sudo modprobe -r hailo_pci")
        except Exception:
            pass

        # 3. PCIe detection via lspci
        try:
            lspci = subprocess.check_output(
                ["lspci", "-nn"], text=True, timeout=3
            )
            # Hailo-10H: vendor 1e60, device 45c4
            if "1e60" in lspci and "45c4" in lspci:
                result["pcie_detected"] = True
                result["chip"] = "Hailo-10H"
                result["hailo_found"] = True
            elif "1e60" in lspci:
                result["pcie_detected"] = True
                result["chip"] = "Hailo (unknown variant)"
                result["hailo_found"] = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # 4. hailortcli firmware identify
        try:
            fw_out = subprocess.check_output(
                ["hailortcli", "fw-control", "identify"],
                text=True, timeout=8, stderr=subprocess.DEVNULL
            )
            result["hailortcli"] = True
            for line in fw_out.splitlines():
                if "Firmware Version:" in line:
                    result["firmware_version"] = line.split(":", 1)[1].strip()
                if "Device Architecture:" in line:
                    arch = line.split(":", 1)[1].strip()
                    result["chip"] = arch
                    result["hailo_found"] = True
        except FileNotFoundError:
            result["error"] = "hailortcli not found — install h10-hailort"
        except subprocess.TimeoutExpired:
            result["error"] = "hailortcli timed out — HAT may not be responding"
        except subprocess.CalledProcessError as e:
            result["error"] = f"hailortcli error: {e}"

        # 5. Python hailo_platform package
        try:
            import hailo_platform  # noqa
            result["hailo_platform_py"] = True
        except ImportError:
            pass

        # 6. hailo-ollama server reachability
        try:
            req = urllib.request.Request(
                f"{HAILO_OLLAMA_URL}/api/tags", method="GET"
            )
            with urllib.request.urlopen(req, timeout=2) as r:
                data = json.loads(r.read())
                models = [m.get("name", "") for m in data.get("models", [])]
                result["hailo_ollama"]        = True
                result["hailo_ollama_models"] = models
        except Exception:
            pass

        cls._cache = result
        return result

    @classmethod
    def is_available(cls) -> bool:
        """Quick check — is there a usable Hailo NPU backend?"""
        d = cls.detect()
        return d["hailo_found"] and (d["hailo_ollama"] or d["hailo_platform_py"])

    @classmethod
    def summary(cls) -> str:
        """Human-readable status string for the ERR0RS status endpoint."""
        d = cls.detect()
        if not d["hailo_found"]:
            return "❌ Hailo-10H not detected"
        chip  = d.get("chip", "Hailo")
        fw    = d.get("firmware_version", "unknown")
        drv   = d.get("driver_module", "?")
        parts = [f"✅ {chip} | FW {fw} | {drv}"]
        if d["hailo_ollama"]:
            models = ", ".join(d["hailo_ollama_models"][:3]) or "no models pulled"
            parts.append(f"hailo-ollama: {models}")
        if not d["hailo_ollama"]:
            parts.append("⚠️  hailo-ollama not running")
        return " | ".join(parts)


# ─── hailo-ollama inference client ────────────────────────────────────────────

class HailoOllamaClient:
    """
    Client for Hailo's Ollama-compatible LLM server (hailo-ollama).
    Runs on port 8000. Exposes /api/generate and /api/chat endpoints.

    NOTE: hailo-ollama is NOT the same as standard Ollama.
    - It serves pre-compiled HEF models from the Hailo GenAI model zoo
    - The CLI 'ollama' client doesn't work perfectly with it
    - But HTTP requests to /api/generate work identically
    - Models must be 'pulled' via hailo-ollama's own pull mechanism
    """

    def __init__(self, base_url: str = HAILO_OLLAMA_URL):
        self.base_url = base_url

    def is_running(self) -> bool:
        """Check if hailo-ollama server is up and responding."""
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=2):
                return True
        except Exception:
            return False

    def list_models(self) -> list:
        """Return list of pulled models from hailo-ollama."""
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=3) as r:
                data = json.loads(r.read())
                return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return []

    def generate(self, prompt: str, system: str = "",
                 model: str = "qwen2.5-coder-1.5b-instruct",
                 timeout: int = 60) -> dict:
        """
        Call hailo-ollama /api/generate endpoint.
        This runs inference on the Hailo-10H NPU.
        """
        body = json.dumps({
            "model":   model,
            "system":  system,
            "prompt":  prompt,
            "stream":  False,
            "options": {
                "temperature":  0.2,
                "num_predict":  1024,
                "top_p":        0.9,
            },
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        start = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data     = json.loads(r.read())
                response = data.get("response", "")
                ms       = int((time.time() - start) * 1000)
                return {
                    "status":     "success",
                    "response":   response,
                    "model":      data.get("model", model),
                    "latency_ms": ms,
                    "source":     "hailo_npu",
                    "backend":    "hailo-ollama",
                    "tok_per_sec": round(
                        data.get("eval_count", 0) /
                        max(data.get("eval_duration", 1) / 1e9, 0.001), 2
                    ),
                }
        except urllib.error.URLError as e:
            return {"status": "error", "response": f"hailo-ollama error: {e}",
                    "source": "hailo_npu"}
        except Exception as e:
            return {"status": "error", "response": str(e), "source": "hailo_npu"}

    def chat(self, messages: list, model: str = "qwen2.5-coder-1.5b-instruct",
             timeout: int = 60) -> dict:
        """Call hailo-ollama /api/chat endpoint (multi-turn conversations)."""
        body = json.dumps({
            "model":    model,
            "messages": messages,
            "stream":   False,
            "options":  {"temperature": 0.2, "num_predict": 1024},
        }).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        start = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data     = json.loads(r.read())
                content  = data.get("message", {}).get("content", "")
                ms       = int((time.time() - start) * 1000)
                return {"status": "success", "response": content,
                        "model": model, "latency_ms": ms,
                        "source": "hailo_npu", "backend": "hailo-ollama"}
        except Exception as e:
            return {"status": "error", "response": str(e), "source": "hailo_npu"}


# ─── Direct hailo_platform inference (non-LLM — vision / embeddings) ──────────

class HailoPlatformClient:
    """
    Direct Python API to hailo_platform (pyHailoRT).
    Used for NON-LLM inference tasks: vision models, embeddings, classification.

    For ERR0RS use cases:
      - Running malware classification HEF models
      - Network traffic anomaly detection
      - Binary analysis acceleration
      - Fast embedding generation for RAG (when a HEF embedding model is available)

    NOTE: LLM inference goes through HailoOllamaClient, not this class.
    The hailo_platform API is for arbitrary HEF model inference.
    """

    def __init__(self):
        self._available = None

    def is_available(self) -> bool:
        if self._available is None:
            try:
                import hailo_platform  # noqa
                self._available = True
            except ImportError:
                self._available = False
        return self._available

    def run_hef(self, hef_path: str, input_data,
                batch_size: int = 1) -> dict:
        """
        Run inference on any HEF model.
        Returns raw output buffers as numpy arrays.
        """
        if not self.is_available():
            return {"status": "error",
                    "error": "hailo_platform not installed — pip install hailort"}
        try:
            import numpy as np
            from hailo_platform import (
                VDevice, HailoSchedulingAlgorithm,
                FormatType, HEF
            )
            params = VDevice.create_params()
            params.scheduling_algorithm = HailoSchedulingAlgorithm.ROUND_ROBIN

            with VDevice(params) as vdevice:
                infer_model = vdevice.create_infer_model(hef_path)
                infer_model.set_batch_size(batch_size)
                infer_model.input().set_format_type(FormatType.FLOAT32)
                infer_model.output().set_format_type(FormatType.FLOAT32)

                output_buf = np.empty(
                    infer_model.output().shape, dtype=np.float32
                )
                with infer_model.configure() as cfg:
                    bindings = cfg.create_bindings()
                    bindings.input().set_buffer(
                        np.array(input_data, dtype=np.float32)
                    )
                    bindings.output().set_buffer(output_buf)
                    cfg.run([bindings], timeout_ms=5000)

            return {
                "status":  "success",
                "output":  output_buf.tolist(),
                "source":  "hailo_platform_direct",
                "hef":     hef_path,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# ─── ERR0RS Hailo Brain — smart inference router ──────────────────────────────

class HailoBrain:
    """
    The ERR0RS Hailo inference layer.
    Provides the same interface as errz_brain.py's ask() function,
    but routes through Hailo-10H NPU when available.

    Priority chain:
      1. hailo-ollama NPU (port 8000) — fastest, frees CPU
      2. Standard Ollama CPU (port 11434) — reliable fallback
      3. ERR0RS builtin teach engine — always-available offline fallback

    Model selection on Hailo:
      - ERR0RS defaults to qwen2.5-coder-1.5b for all queries (best code reasoning)
      - For general intel queries: qwen2.5-1.5b (slightly faster)
      - IMPORTANT: 7B models are NOT available on Hailo-10H
    """

    def __init__(self):
        self.hailo_client   = HailoOllamaClient()
        self.platform_client = HailoPlatformClient()
        self._best_hailo_model = None

    def _get_best_hailo_model(self) -> Optional[str]:
        """Find the best available model on hailo-ollama."""
        if self._best_hailo_model:
            return self._best_hailo_model
        available = self.hailo_client.list_models()
        if not available:
            return None
        # Preference order
        preferred = [
            "qwen2.5-coder-1.5b-instruct",
            "qwen2.5-1.5b-instruct",
            "llama3.2-1b-instruct",
            "deepseek-r1-distill-qwen-1.5b",
        ]
        for m in preferred:
            if any(m in a for a in available):
                self._best_hailo_model = m
                return m
        # Any available model
        self._best_hailo_model = available[0]
        return self._best_hailo_model

    def ask(self, prompt: str, system: str = "", mode: str = "auto",
            timeout: int = 90) -> dict:
        """
        Main inference entry point. Mirrors errz_brain.ask() interface.
        Routes to best available backend automatically.
        """
        # Try hailo-ollama NPU first
        if self.hailo_client.is_running():
            model = self._get_best_hailo_model()
            if model:
                result = self.hailo_client.generate(
                    prompt=prompt, system=system,
                    model=model, timeout=timeout
                )
                if result["status"] == "success":
                    result["backend_chain"] = "hailo_npu_primary"
                    result["hailo_model"]   = model
                    return result

        # Fallback: standard Ollama on CPU
        try:
            import os as _os
            _m = _os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
            body = json.dumps({
                "model":  _m,
                "system": system,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 1024},
            }).encode()
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/generate",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            start = time.time()
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read())
                return {
                    "status":       "success",
                    "response":     data.get("response", ""),
                    "model":        _m,
                    "latency_ms":   int((time.time() - start) * 1000),
                    "source":       "ollama_cpu",
                    "backend":      "ollama",
                    "backend_chain":"hailo_unavailable_ollama_fallback",
                }
        except Exception:
            pass

        # Final fallback: builtin teach engine
        return {
            "status":       "offline",
            "response":     ("[ERR0RS] No inference backend available.\n"
                             "hailo-ollama: not running | Ollama: offline\n"
                             "Type 'teach me [tool]' for offline lessons."),
            "source":       "builtin_fallback",
            "backend_chain":"all_backends_failed",
        }

    def status(self) -> dict:
        """Full NPU + software status for /api/status endpoint."""
        det = HailoDetector.detect(force=True)
        models = self.hailo_client.list_models()
        return {
            "hailo_detected":     det["hailo_found"],
            "chip":               det.get("chip"),
            "firmware":           det.get("firmware_version"),
            "driver":             det.get("driver_module"),
            "device_node":        det["device_node"],
            "hailortcli":         det["hailortcli"],
            "hailo_platform_py":  det["hailo_platform_py"],
            "hailo_ollama_up":    self.hailo_client.is_running(),
            "hailo_ollama_url":   HAILO_OLLAMA_URL,
            "hailo_models":       models,
            "best_model":         self._get_best_hailo_model(),
            "pcie_detected":      det["pcie_detected"],
            "setup_error":        det.get("error"),
            "summary":            HailoDetector.summary(),
        }


# ─── Driver + software installation helper ────────────────────────────────────

HAILO_INSTALL_SCRIPT = """#!/bin/bash
# ERR0RS — Hailo-10H NPU Setup Script for Kali Linux ARM64
# Run: sudo bash scripts/install_hailo.sh

set -e
RED='\\033[0;31m'; CYAN='\\033[0;36m'; GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'; NC='\\033[0m'

echo -e "${CYAN}"
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║   ERR0RS — Hailo-10H NPU Setup                  ║"
echo "  ║   Kali Linux ARM64 | Raspberry Pi 5             ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo -e "${NC}"

# ── Verify Pi 5 ──────────────────────────────────────────────────
if ! grep -q "Raspberry Pi 5" /proc/cpuinfo 2>/dev/null; then
    echo -e "${YELLOW}[!] Not running on Pi 5 — some steps may not apply${NC}"
fi

# ── Check PCIe config ────────────────────────────────────────────
echo -e "${CYAN}[*] Checking /boot/firmware/config.txt PCIe settings...${NC}"
CONFIG="/boot/firmware/config.txt"
if ! grep -q "dtparam=pciex1" "$CONFIG" 2>/dev/null; then
    echo "dtparam=pciex1" >> "$CONFIG"
    echo -e "  ${GREEN}✓ Added dtparam=pciex1${NC}"
fi
if ! grep -q "dtparam=pciex1_gen=3" "$CONFIG" 2>/dev/null; then
    echo "dtparam=pciex1_gen=3" >> "$CONFIG"
    echo -e "  ${GREEN}✓ Added dtparam=pciex1_gen=3 (PCIe Gen3 speed)${NC}"
fi

# ── Remove conflicting hailo_pci (Hailo-8) driver if present ─────
echo -e "${CYAN}[*] Removing conflicting hailo_pci driver (Hailo-8)...${NC}"
modprobe -r hailo_pci 2>/dev/null && echo -e "  ${GREEN}✓ Removed hailo_pci${NC}" || true
if [ -f "/lib/modules/$(uname -r)/updates/dkms/hailo_pci.ko" ]; then
    rm -f "/lib/modules/$(uname -r)/updates/dkms/hailo_pci.ko"
    depmod -a
    echo -e "  ${GREEN}✓ Removed hailo_pci.ko from DKMS${NC}"
fi

# ── GCC version fix (Kali gcc-14 vs kernel gcc-12) ───────────────
echo -e "${CYAN}[*] Fixing GCC version for kernel module compilation...${NC}"
if ! command -v gcc-12 &>/dev/null; then
    apt install -y gcc-12 g++-12
fi
update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-12 12 \\
    --slave /usr/bin/g++ g++ /usr/bin/g++-12 2>/dev/null || true
echo -e "  ${GREEN}✓ gcc-12 ready for DKMS compilation${NC}"

# ── Add Raspberry Pi apt repository ──────────────────────────────
echo -e "${CYAN}[*] Adding Raspberry Pi apt repository...${NC}"
if [ ! -f "/etc/apt/keyrings/raspberrypi-archive-keyring.gpg" ]; then
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://archive.raspberrypi.com/debian/raspberrypi.gpg.key \\
      | gpg --dearmor -o /etc/apt/keyrings/raspberrypi-archive-keyring.gpg
fi
cat > /etc/apt/sources.list.d/raspberrypi.list << 'REPO'
deb [arch=arm64 signed-by=/etc/apt/keyrings/raspberrypi-archive-keyring.gpg] http://archive.raspberrypi.com/debian trixie main
REPO

# Pin Hailo packages to RPi repo, everything else stays at low priority
cat > /etc/apt/preferences.d/raspberrypi-pin << 'PIN'
Package: *
Pin: origin archive.raspberrypi.com
Pin-Priority: 1

Package: h10-hailort-pcie-driver h10-hailort hailort hailort-* libhailort* hailo*
Pin: origin archive.raspberrypi.com
Pin-Priority: 1001
PIN

apt update -qq
echo -e "  ${GREEN}✓ RPi repository added and pinned${NC}"

# ── Install Hailo-10H driver + runtime ───────────────────────────
echo -e "${CYAN}[*] Installing Hailo-10H driver and HailoRT...${NC}"
apt install -y dkms h10-hailort-pcie-driver h10-hailort
echo -e "  ${GREEN}✓ Hailo-10H driver installed (hailo1x_pci)${NC}"

# ── Install Python hailo_platform ────────────────────────────────
echo -e "${CYAN}[*] Installing hailo_platform Python bindings...${NC}"
pip install hailort --break-system-packages -q 2>/dev/null || \\
pip3 install hailort --break-system-packages -q 2>/dev/null || \\
echo -e "  ${YELLOW}~ pip install hailort failed — try manually from hailo.ai Developer Zone${NC}"

# ── Install hailo-apps (GenAI examples including hailo-ollama) ────
echo -e "${CYAN}[*] Installing hailo-apps (hailo-ollama + GenAI examples)...${NC}"
if [ ! -d "/opt/hailo-apps" ]; then
    git clone https://github.com/hailo-ai/hailo-apps.git /opt/hailo-apps
fi
cd /opt/hailo-apps
pip install -e . --break-system-packages -q 2>/dev/null || true
echo -e "  ${GREEN}✓ hailo-apps installed${NC}"

# ── Install GenAI model zoo (HEF models) ─────────────────────────
echo -e "${CYAN}[*] Installing Hailo GenAI model zoo...${NC}"
apt install -y hailo-gen-ai-model-zoo 2>/dev/null || {
    echo -e "  ${YELLOW}~ hailo-gen-ai-model-zoo not in apt — checking hailo-apps...${NC}"
    ls /opt/hailo-apps/resources/models/ 2>/dev/null || \\
    echo -e "  ${YELLOW}  Download models manually from hailo.ai Developer Zone${NC}"
}

# ── Create hailo-ollama systemd service ──────────────────────────
echo -e "${CYAN}[*] Creating hailo-ollama systemd service...${NC}"
cat > /etc/systemd/system/hailo-ollama.service << 'SERVICE'
[Unit]
Description=Hailo-10H NPU LLM Server (Ollama-compatible API)
After=network.target

[Service]
Type=simple
User=kali
WorkingDirectory=/opt/hailo-apps
ExecStart=/opt/hailo-apps/venv/bin/python -m hailo_apps.gen_ai_apps.hailo_ollama.server --port 8000
Restart=on-failure
RestartSec=5
Environment=HAILO_OLLAMA_PORT=8000

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable hailo-ollama.service
echo -e "  ${GREEN}✓ hailo-ollama service created and enabled${NC}"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   HAILO-10H SETUP COMPLETE                       ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Reboot required to load hailo1x_pci driver      ║${NC}"
echo -e "${GREEN}║                                                  ║${NC}"
echo -e "${GREEN}║  After reboot, verify with:                      ║${NC}"
echo -e "${GREEN}║    lspci | grep -i hailo                         ║${NC}"
echo -e "${GREEN}║    lsmod | grep hailo                            ║${NC}"
echo -e "${GREEN}║    hailortcli fw-control identify                ║${NC}"
echo -e "${GREEN}║    ls -la /dev/hailo0                            ║${NC}"
echo -e "${GREEN}║                                                  ║${NC}"
echo -e "${GREEN}║  Then start hailo-ollama:                        ║${NC}"
echo -e "${GREEN}║    sudo systemctl start hailo-ollama             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
read -p "Reboot now? [Y/n]: " -n 1 -r
[[ $REPLY =~ ^[Yy]$|^$ ]] && reboot
"""


def write_install_script(dest: str = None) -> str:
    """Write the Hailo install script to disk and return the path."""
    if dest is None:
        dest = str(Path(__file__).resolve().parents[2] / "scripts" / "install_hailo.sh")
    Path(dest).write_text(HAILO_INSTALL_SCRIPT)
    Path(dest).chmod(0o755)
    return dest


# ─── HTTP handler for /api/hailo endpoint ─────────────────────────────────────

_hailo_brain: Optional["HailoBrain"] = None

def get_hailo_brain() -> "HailoBrain":
    global _hailo_brain
    if _hailo_brain is None:
        _hailo_brain = HailoBrain()
    return _hailo_brain


def handle_hailo_request(payload: dict) -> dict:
    """
    Route handler for /api/hailo endpoint in errorz_launcher.py

    Actions:
      status   — full Hailo NPU + software status
      ask      — inference query (routes to best backend)
      detect   — re-run hardware detection
      install  — write install script and return path
      models   — list available hailo-ollama models
      diagnose — step-by-step connection diagnosis
    """
    action = payload.get("action", "status")
    brain  = get_hailo_brain()

    if action == "status":
        return {"status": "ok", **brain.status()}

    elif action == "ask":
        prompt  = payload.get("prompt", "")
        system  = payload.get("system", "You are ERR0RS, an AI pentest assistant.")
        mode    = payload.get("mode", "auto")
        if not prompt:
            return {"status": "error", "error": "No prompt provided"}
        result = brain.ask(prompt, system=system, mode=mode)
        return result

    elif action == "detect":
        HailoDetector._cache = None   # force refresh
        det = HailoDetector.detect(force=True)
        return {"status": "ok", "detection": det, "summary": HailoDetector.summary()}

    elif action == "install":
        path = write_install_script()
        return {
            "status":  "ok",
            "script":  path,
            "run_with": f"sudo bash {path}",
            "note": ("Run this script on the Pi to install the Hailo-10H driver, "
                     "HailoRT, hailo_platform Python bindings, hailo-apps, "
                     "and create the hailo-ollama systemd service."),
        }

    elif action == "models":
        models = brain.hailo_client.list_models()
        return {
            "status":           "ok",
            "hailo_ollama_up":  brain.hailo_client.is_running(),
            "models":           models,
            "supported_models": list(HAILO_LLM_MODELS.keys()),
            "note": ("hailo-ollama only supports models pre-compiled to HEF format. "
                     "GGUF models (qwen2.5-coder:7b etc) are NOT compatible with Hailo-10H."),
        }

    elif action == "diagnose":
        steps = []
        det = HailoDetector.detect(force=True)

        # PCIe
        if det["pcie_detected"]:
            steps.append(("✅", "PCIe", f"Hailo-10H detected at PCI address (1e60:45c4)"))
        else:
            steps.append(("❌", "PCIe", "Hailo not found in lspci — check HAT physical connection and dtparam=pciex1"))

        # Kernel module
        if det["driver_module"] == "hailo1x_pci":
            steps.append(("✅", "Driver", "hailo1x_pci module loaded (correct for Hailo-10H)"))
        elif det["driver_module"] == "hailo_pci":
            steps.append(("⚠️", "Driver", "hailo_pci loaded — this is the Hailo-8 driver, not Hailo-10H. Run: sudo modprobe -r hailo_pci"))
        else:
            steps.append(("❌", "Driver", "No Hailo kernel module loaded — install h10-hailort-pcie-driver"))

        # Device node
        if det["device_node"]:
            steps.append(("✅", "/dev/hailo0", "Device node exists — kernel driver working"))
        else:
            steps.append(("❌", "/dev/hailo0", "Device node missing — driver not loaded or permission issue"))

        # hailortcli
        if det["hailortcli"]:
            steps.append(("✅", "hailortcli", f"Firmware: {det.get('firmware_version', 'unknown')}"))
        else:
            steps.append(("❌", "hailortcli", f"hailortcli failed: {det.get('error', 'not installed')}"))

        # Python bindings
        if det["hailo_platform_py"]:
            steps.append(("✅", "hailo_platform", "Python bindings installed"))
        else:
            steps.append(("⚠️", "hailo_platform", "hailo_platform not installed — pip install hailort"))

        # hailo-ollama
        if det["hailo_ollama"]:
            models = ", ".join(det["hailo_ollama_models"]) or "(no models pulled)"
            steps.append(("✅", "hailo-ollama", f"Running on port {HAILO_OLLAMA_PORT} | Models: {models}"))
        else:
            steps.append(("❌", "hailo-ollama", (
                f"hailo-ollama not running on port {HAILO_OLLAMA_PORT}. "
                "Start with: sudo systemctl start hailo-ollama  "
                "OR: python -m hailo_apps.gen_ai_apps.hailo_ollama.server --port 8000"
            )))

        # Summary
        ok = sum(1 for s in steps if s[0] == "✅")
        output = "\n".join(f"  {icon} [{name}] {msg}" for icon, name, msg in steps)
        output += f"\n\nDiagnosis: {ok}/{len(steps)} checks passed"
        if ok < len(steps):
            output += "\n\nRun: sudo bash scripts/install_hailo.sh  to fix all issues"

        return {"status": "ok", "stdout": output, "checks": ok, "total": len(steps)}

    return {"status": "error", "error": f"Unknown action: {action}"}


# ─── Module-level convenience functions (used by errz_inference.py) ───────────

def hailo_available() -> bool:
    """True if Hailo NPU is detected and hailo-ollama is running."""
    return HailoDetector.is_available()


def hailo_infer(prompt: str, system: str = "", mode: str = "auto") -> dict:
    """
    Direct inference call — used by errz_inference.py backend router.
    Returns same dict shape as errz_brain.ask().
    """
    return get_hailo_brain().ask(prompt, system=system, mode=mode)


def hailo_status_line() -> str:
    """One-line status for the ERR0RS boot banner."""
    return HailoDetector.summary()


# ─── Self-test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[ERR0RS] Hailo NPU Integration Self-Test\n" + "="*54)
    result = handle_hailo_request({"action": "diagnose"})
    print(result.get("stdout", "No output"))
    print("\nStatus:")
    brain = get_hailo_brain()
    status = brain.status()
    for k, v in status.items():
        print(f"  {k}: {v}")
