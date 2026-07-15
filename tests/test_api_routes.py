"""
API integration tests for the knowledge router (src/ui/knowledge_api.py).

Drives the real routes over HTTP via httpx's ASGITransport — the modern
replacement for the version-fragile starlette TestClient (which broke under
httpx>=0.28). No pytest-asyncio needed: each call runs through asyncio.run.

This gives the knowledge endpoints genuine request/response coverage.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import asyncio

import httpx
import pytest
from fastapi import FastAPI

from src.ui.knowledge_api import knowledge_router


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(knowledge_router)
    return app


def _req(method: str, path: str, *, params=None, json=None):
    async def go():
        transport = httpx.ASGITransport(app=_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
            return await c.request(method, path, params=params, json=json)
    return asyncio.run(go())


def GET(path, **params):
    return _req("GET", path, params=params or None)


def POST(path, json):
    return _req("POST", path, json=json)


# ── Purple ──────────────────────────────────────────────────────────────────

def test_purple_list():
    r = GET("/purple")
    assert r.status_code == 200
    body = r.json()
    assert "pass-the-hash" in [t["key"] for t in body["techniques"]]
    assert "sigma" in body["surfaces"]


def test_purple_technique_and_unknown():
    assert GET("/purple/pth").json()["name"] == "Pass-the-Hash"
    assert "error" in GET("/purple/bogus").json()


# ── Anatomy ─────────────────────────────────────────────────────────────────

def test_anatomy():
    body = GET("/anatomy", cmd="nmap -sV -p- 10.0.0.5").json()
    assert body["tool"] == "nmap" and body["parts"]


# ── Interpret ───────────────────────────────────────────────────────────────

def test_interpret():
    nmap = ("Nmap scan report for 10.0.0.10\n"
            "PORT   STATE SERVICE\n445/tcp open microsoft-ds")
    body = POST("/interpret", {"output": nmap}).json()
    assert body["tool"] == "nmap" and body["findings"]


# ── Roadmap ─────────────────────────────────────────────────────────────────

def test_roadmap_full_and_stage():
    assert len(GET("/roadmap").json()["roadmap"]) == 10
    assert GET("/roadmap", stage="5").json()["name"] == "Active Directory"


# ── Cheats ──────────────────────────────────────────────────────────────────

def test_cheat_all_and_query():
    assert GET("/cheat").json()["categories"]
    assert GET("/cheat", q="kerberos").json()["results"]


# ── Registry ────────────────────────────────────────────────────────────────

def test_tools_and_dossier():
    tools = GET("/tools").json()
    assert "nmap" in tools["tools"] and isinstance(tools["drift"], int)
    assert GET("/tool/nmap").json()["name"] == "nmap"
    assert "error" in GET("/tool/not-a-tool").json()


def test_rag_tools_corpus():
    docs = GET("/rag/tools").json()["documents"]
    assert docs and all("id" in d and "text" in d for d in docs)


# ── Results literacy ────────────────────────────────────────────────────────

def test_results_and_unknown():
    assert "reading" in GET("/results/nmap").json()
    body = GET("/results/nope").json()
    assert "error" in body and body["available"]
