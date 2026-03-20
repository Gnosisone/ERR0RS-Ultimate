#!/usr/bin/env python3
"""
ERR0RS ULTIMATE – CVE Intelligence Agent

Responsibilities:
  • Query a LOCAL CVE database (JSON file that ships with the framework).
  • If the local DB misses, query the public NVD REST API (only when
    allow_remote is True – respects the data-privacy contract).
  • Score & rank findings by CVSS + exploit availability.

The agent is intentionally stateless between calls so it can run in
parallel with other agents without locking shared resources.
"""

import json
import logging
import os
import time
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class CVEEntry:
    cve_id            : str
    description       : str
    cvss_score        : float
    severity          : str                          # CRITICAL / HIGH / MEDIUM / LOW
    affected_products : List[str] = field(default_factory=list)
    exploit_available : bool     = False
    references        : List[str] = field(default_factory=list)
    published         : str      = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cve_id": self.cve_id, "description": self.description,
            "cvss_score": self.cvss_score, "severity": self.severity,
            "affected_products": self.affected_products,
            "exploit_available": self.exploit_available,
            "references": self.references, "published": self.published,
        }


# ---------------------------------------------------------------------------
# Seed data  –  bundled CVEs so the agent works OFFLINE out of the box
# ---------------------------------------------------------------------------
# In production you'd pre-download a larger snapshot; this covers the most
# common targets testers hit in labs and CTFs.

BUNDLED_CVES: List[Dict] = [
    {"cve_id":"CVE-2021-44228","description":"Apache Log4j RCE (Log4Shell)","cvss":10.0,
     "severity":"CRITICAL","products":["apache log4j","log4j2"],"exploit":True,
     "refs":["https://nvd.nist.gov/vuln/detail/CVE-2021-44228"],"published":"2021-12-10"},
    {"cve_id":"CVE-2021-34527","description":"Windows Print Spooler RCE (PrintNightmare)","cvss":8.8,
     "severity":"HIGH","products":["windows","print spooler"],"exploit":True,
     "refs":["https://nvd.nist.gov/vuln/detail/CVE-2021-34527"],"published":"2021-07-01"},
    {"cve_id":"CVE-2020-11022","description":"jQuery XSS via HTML parsing","cvss":6.1,
     "severity":"MEDIUM","products":["jquery"],"exploit":True,
     "refs":["https://nvd.nist.gov/vuln/detail/CVE-2020-11022"],"published":"2020-04-27"},
    {"cve_id":"CVE-2021-3156","description":"Sudo heap buffer overflow (Sequoia)","cvss":7.8,
     "severity":"HIGH","products":["sudo"],"exploit":True,
     "refs":["https://nvd.nist.gov/vuln/detail/CVE-2021-3156"],"published":"2021-01-26"},
    {"cve_id":"CVE-2019-11358","description":"jQuery prototype pollution","cvss":6.1,
     "severity":"MEDIUM","products":["jquery"],"exploit":False,
     "refs":["https://nvd.nist.gov/vuln/detail/CVE-2019-11358"],"published":"2019-04-11"},
    {"cve_id":"CVE-2021-41773","description":"Apache httpd 2.4.49 path traversal & RCE","cvss":9.8,
     "severity":"CRITICAL","products":["apache httpd","apache http server"],"exploit":True,
     "refs":["https://nvd.nist.gov/vuln/detail/CVE-2021-41773"],"published":"2021-10-05"},
    {"cve_id":"CVE-2017-0144","description":"EternalBlue – SMB remote code execution","cvss":8.1,
     "severity":"HIGH","products":["windows","smb"],"exploit":True,
     "refs":["https://nvd.nist.gov/vuln/detail/CVE-2017-0144"],"published":"2017-03-14"},
    {"cve_id":"CVE-2014-0160","description":"Heartbleed – OpenSSL information disclosure","cvss":7.5,
     "severity":"HIGH","products":["openssl"],"exploit":True,
     "refs":["https://nvd.nist.gov/vuln/detail/CVE-2014-0160"],"published":"2014-04-07"},
    {"cve_id":"CVE-2020-1472","description":"Netlogon ZeroLogon – Windows domain controller","cvss":9.8,
     "severity":"CRITICAL","products":["windows","netlogon"],"exploit":True,
     "refs":["https://nvd.nist.gov/vuln/detail/CVE-2020-1472"],"published":"2020-08-11"},
    {"cve_id":"CVE-2022-22965","description":"Spring Framework SpEL injection (Spring4Shell)","cvss":9.8,
     "severity":"CRITICAL","products":["spring framework","spring boot"],"exploit":True,
     "refs":["https://nvd.nist.gov/vuln/detail/CVE-2022-22965"],"published":"2022-04-01"},
]


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class CVEIntelligenceAgent:
    """
    Queries CVE databases (local first, remote optional) and returns
    ranked, structured findings.
    """

    def __init__(self, llm_router=None, allow_remote: bool = False):
        self.llm_router   = llm_router
        self.allow_remote = allow_remote
        self._local_db    = self._load_local_db()

    # ------------------------------------------------------------------
    # DB loading
    # ------------------------------------------------------------------

    def _load_local_db(self) -> List[Dict]:
        """
        Try to read an extended JSON dump from disk first.
        Fall back to the bundled seed data.
        """
        db_path = Path(__file__).resolve().parent.parent / "data" / "cve_db.json"
        if db_path.exists():
            try:
                return json.loads(db_path.read_text())
            except Exception as e:
                logger.warning("Could not load cve_db.json: %s – using bundled data", e)
        return BUNDLED_CVES

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    async def analyze_target(self, target_info: Dict[str, Any]) -> List[CVEEntry]:
        """
        Given a dict like:
            {"software": ["apache log4j", "jquery"],
             "os": "linux",
             "services": ["ssh", "http"]}
        Return a sorted list of matching CVEEntry objects (highest CVSS first).
        """
        software_terms = [s.lower() for s in target_info.get("software", [])]
        os_term        = target_info.get("os", "").lower()
        service_terms  = [s.lower() for s in target_info.get("services", [])]

        # Combine all search terms
        all_terms = software_terms + ([os_term] if os_term else []) + service_terms

        matches: List[CVEEntry] = []
        seen_ids: set = set()

        # 1. Search local DB
        for entry in self._local_db:
            products = [p.lower() for p in entry.get("products", [])]
            if self._terms_match(all_terms, products):
                cve = self._dict_to_entry(entry)
                if cve.cve_id not in seen_ids:
                    matches.append(cve)
                    seen_ids.add(cve.cve_id)

        # 2. Optionally hit NVD API (only if remote allowed & we found nothing)
        if not matches and self.allow_remote and requests:
            matches.extend(await self._query_nvd(all_terms))

        # Sort: highest CVSS first, then exploit_available
        matches.sort(key=lambda c: (c.cvss_score, int(c.exploit_available)), reverse=True)
        return matches

    async def lookup_cve(self, cve_id: str) -> Optional[CVEEntry]:
        """Direct lookup by CVE ID (e.g. 'CVE-2021-44228')."""
        cve_id = cve_id.upper().strip()
        for entry in self._local_db:
            if entry.get("cve_id", "").upper() == cve_id:
                return self._dict_to_entry(entry)
        # Remote fallback
        if self.allow_remote and requests:
            return await self._query_nvd_single(cve_id)
        return None

    # ------------------------------------------------------------------
    # NVD API helpers  (only called when allow_remote=True)
    # ------------------------------------------------------------------

    async def _query_nvd(self, terms: List[str]) -> List[CVEEntry]:
        """Search NVD by keyword."""
        if not terms:
            return []
        keyword = " ".join(terms[:3])          # NVD prefers short queries
        url = ("https://services.nvd.nist.gov/rest/json/cves/2.0"
               f"?keywordSearch={keyword}&resultsPerPage=10")
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
            return [self._nvd_item_to_entry(v)
                    for v in data.get("vulnerabilities", [])]
        except Exception as e:
            logger.warning("NVD query failed: %s", e)
            return []

    async def _query_nvd_single(self, cve_id: str) -> Optional[CVEEntry]:
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            vulns = r.json().get("vulnerabilities", [])
            return self._nvd_item_to_entry(vulns[0]) if vulns else None
        except Exception as e:
            logger.warning("NVD single lookup failed: %s", e)
            return None

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _terms_match(search_terms: List[str], products: List[str]) -> bool:
        """True if ANY search term appears in ANY product string."""
        for term in search_terms:
            for prod in products:
                if term in prod or prod in term:
                    return True
        return False

    @staticmethod
    def _dict_to_entry(d: Dict) -> CVEEntry:
        return CVEEntry(
            cve_id            = d.get("cve_id", ""),
            description       = d.get("description", ""),
            cvss_score        = float(d.get("cvss", d.get("cvss_score", 0.0))),
            severity          = d.get("severity", "UNKNOWN"),
            affected_products = d.get("products", d.get("affected_products", [])),
            exploit_available = bool(d.get("exploit", d.get("exploit_available", False))),
            references        = d.get("refs", d.get("references", [])),
            published         = d.get("published", ""),
        )

    @staticmethod
    def _nvd_item_to_entry(item: Dict) -> CVEEntry:
        """Parse one NVD API vulnerability object into our CVEEntry."""
        cve   = item.get("cve", {})
        cve_id = cve.get("id", "")
        desc_list = cve.get("descriptions", [])
        desc = next((d["value"] for d in desc_list if d.get("lang") == "en"), "")

        # CVSS – try v3.1 then v3.0
        cvss = 0.0
        severity = "UNKNOWN"
        metrics  = cve.get("metrics", {})
        for key in ("cvssMetricV31", "cvssMetricV30"):
            if key in metrics and metrics[key]:
                data = metrics[key][0].get("cvssData", {})
                cvss     = float(data.get("baseScore", 0.0))
                severity = data.get("baseSeverity", "UNKNOWN")
                break

        # Affected products (CPE)
        products: List[str] = []
        for conf in cve.get("configurations", []):
            for node in conf.get("nodes", []):
                for op in node.get("cpeMatch", []):
                    cpe = op.get("criteria", "")
                    # cpe:2.3:<part>:<vendor>:<product>:…
                    parts = cpe.split(":")
                    if len(parts) >= 4:
                        products.append(f"{parts[3]} {parts[4]}" if len(parts) > 4 else parts[3])

        refs = [r.get("url", "") for r in cve.get("references", [])]

        return CVEEntry(
            cve_id=cve_id, description=desc, cvss_score=cvss,
            severity=severity, affected_products=products,
            exploit_available=(cvss >= 9.0),   # heuristic
            references=refs,
        )
