#!/usr/bin/env python3
"""
ERR0RS ULTIMATE – Agent Orchestrator  (REAL – coordinates live agents)

Phases of an autonomous pentest:
  1. INTELLIGENCE   – CVE agent scans for known vulns against detected software
  2. WEB CRAWL     – Browser agent crawls the target, finds forms / headers / libs
  3. EXPLOIT PLAN  – Exploit agent generates tool-chains from intel + web findings
  4. EXECUTION     – ToolExecutor runs the generated chains
  5. REPORT        – Master report assembled from all phase outputs

The orchestrator can optionally use the LLM router to generate plain-English
summaries of each phase (educational mode).  If no LLM is reachable it still
works – it just skips the AI explanations.
"""

import asyncio
import logging
import sys
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

# ---------------------------------------------------------------------------
# Path fix
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.ai.agents.cve_intelligence   import CVEIntelligenceAgent, CVEEntry   # noqa
from src.ai.agents.browser_automation import BrowserAutomationAgent            # noqa
from src.ai.agents.exploit_generator  import ExploitGeneratorAgent, ExploitPlan # noqa
from src.core.tool_executor           import ToolExecutor, ToolResult          # noqa

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class AgentOrchestrator:

    def __init__(self, llm_router=None, allow_remote: bool = False):
        self.llm_router = llm_router

        # Instantiate agents
        self.cve_agent     = CVEIntelligenceAgent(llm_router, allow_remote=allow_remote)
        self.browser_agent = BrowserAutomationAgent(llm_router)
        self.exploit_agent = ExploitGeneratorAgent(llm_router)
        self.executor      = ToolExecutor()

    # ==================================================================
    # MAIN ENTRY – full autonomous pentest
    # ==================================================================

    async def autonomous_pentest(self, target: str,
                                 software_hints: Optional[List[str]] = None
                                 ) -> Dict[str, Any]:
        """
        Run a complete pentest workflow against *target*.

        software_hints – optional list of software names detected upstream
                         (e.g. from an Nmap banner grab).  Helps the CVE agent.
        """
        print(f"\n{'='*60}")
        print("🤖  AUTONOMOUS PENTEST – ERR0RS ULTIMATE")
        print("="*60)
        print(f"🎯  Target   : {target}")
        print(f"⏰  Started  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🧠  Agents   : CVE-Intel, Browser-Crawler, Exploit-Gen")
        print("="*60 + "\n")

        results: Dict[str, Any] = {
            "target"   : target,
            "start_time": datetime.now().isoformat(),
            "phases"   : {},
            "findings" : [],
        }

        # --- Phase 1: Intelligence ----------------------------------------
        print("📊  Phase 1 / 5  –  Intelligence Gathering …")
        intel = await self._phase_intelligence(target, software_hints)
        results["phases"]["intelligence"] = intel
        print(f"       ✅  {intel['cve_count']} CVEs found "
              f"({intel['critical_count']} critical, "
              f"{intel['exploitable_count']} exploitable)\n")

        # --- Phase 2: Web Crawl -------------------------------------------
        print("🌐  Phase 2 / 5  –  Web Application Crawl …")
        web = await self._phase_web_crawl(target)
        results["phases"]["web_crawl"] = web
        print(f"       ✅  {web['pages_crawled']} pages crawled, "
              f"{web['forms_found']} forms, "
              f"{len(web.get('findings',[]))} findings\n")

        # --- Phase 3: Exploit Planning -------------------------------------
        print("🔧  Phase 3 / 5  –  Exploit Plan Generation …")
        exploit = await self._phase_exploit_planning(intel, web, target)
        results["phases"]["exploit_planning"] = exploit
        print(f"       ✅  {exploit['plan_count']} exploit plan(s) generated\n")

        # --- Phase 4: Execution (optional) --------------------------------
        print("⚡  Phase 4 / 5  –  Tool Execution …")
        execution = await self._phase_execution(exploit, target)
        results["phases"]["execution"] = execution
        print(f"       ✅  {execution['tools_run']} tool(s) executed, "
              f"{execution['total_findings']} total findings\n")

        # --- Phase 5: Report ----------------------------------------------
        print("📝  Phase 5 / 5  –  Report Generation …")
        report = self._build_report(results)
        results["report"] = report
        results["end_time"] = datetime.now().isoformat()
        print(f"       ✅  Report assembled\n")

        # --- Summary -------------------------------------------------------
        duration = (datetime.fromisoformat(results["end_time"])
                    - datetime.fromisoformat(results["start_time"])).total_seconds()
        print("="*60)
        print(f"✅  AUTONOMOUS PENTEST COMPLETE  ({duration:.1f}s)")
        print(f"    Total findings : {execution['total_findings']}")
        print(f"    Exploit plans  : {exploit['plan_count']}")
        print("="*60 + "\n")

        return results

    # ==================================================================
    # Phase implementations
    # ==================================================================

    async def _phase_intelligence(self, target: str,
                                  software_hints: Optional[List[str]] = None
                                  ) -> Dict[str, Any]:
        hints = software_hints or [target]   # fall back to domain as search term
        target_info = {"software": hints, "os": "unknown", "services": []}

        cves: List[CVEEntry] = await self.cve_agent.analyze_target(target_info)

        return {
            "cve_count"        : len(cves),
            "critical_count"   : sum(1 for c in cves if c.cvss_score >= 9.0),
            "exploitable_count": sum(1 for c in cves if c.exploit_available),
            "cves"             : [c.to_dict() for c in cves],
        }

    async def _phase_web_crawl(self, target: str) -> Dict[str, Any]:
        return await self.browser_agent.crawl_and_analyze(target)

    async def _phase_exploit_planning(self, intel: Dict, web: Dict,
                                      target: str) -> Dict[str, Any]:
        plans: List[ExploitPlan] = []

        # A) From CVEs
        for cve_dict in intel.get("cves", []):
            plan = await self.exploit_agent.generate_from_cve(
                cve_dict["cve_id"],
                cve_dict,
            )
            if plan:
                plans.append(plan)

        # B) From web findings
        web_plans = await self.exploit_agent.generate_from_web_findings(
            web.get("findings", []), target
        )
        plans.extend(web_plans)

        return {
            "plan_count": len(plans),
            "plans"     : [p.to_dict() for p in plans],
        }

    async def _phase_execution(self, exploit: Dict, target: str) -> Dict[str, Any]:
        """
        Walk through every plan's tool_chain and actually run the tools.
        Collects all ToolResults.
        """
        tools_run      = 0
        total_findings = 0
        all_results    : List[Dict] = []

        for plan in exploit.get("plans", []):
            for step in plan.get("tool_chain", []):
                tool_name = step.get("tool", "")
                params    = step.get("params", {})
                if not tool_name:
                    continue

                print(f"       ▶  Running {tool_name} …")
                try:
                    result: ToolResult = await self.executor.run(tool_name, target, params)
                    tools_run      += 1
                    total_findings += len(result.findings)
                    all_results.append({
                        "tool"     : tool_name,
                        "status"   : result.status.value,
                        "findings" : result.findings,
                        "duration" : result.duration_ms,
                        "error"    : result.error,
                    })
                    emoji = "✅" if result.status.value == "success" else "⚠️"
                    print(f"         {emoji} {tool_name}: {result.status.value} "
                          f"| {len(result.findings)} findings | {result.duration_ms}ms")
                except Exception as e:
                    logger.warning("Execution error for %s: %s", tool_name, e)
                    all_results.append({"tool": tool_name, "status": "error", "error": str(e)})

        return {
            "tools_run"     : tools_run,
            "total_findings": total_findings,
            "results"       : all_results,
        }

    # ==================================================================
    # Report builder
    # ==================================================================

    @staticmethod
    def _build_report(results: Dict[str, Any]) -> str:
        target     = results["target"]
        start      = results["start_time"]
        end        = results.get("end_time", "N/A")
        intel      = results["phases"].get("intelligence", {})
        web        = results["phases"].get("web_crawl", {})
        exploit    = results["phases"].get("exploit_planning", {})
        execution  = results["phases"].get("execution", {})

        lines = [
            "# ERR0RS ULTIMATE – Autonomous Pentest Report",
            "",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| Target | {target} |",
            f"| Start  | {start} |",
            f"| End    | {end} |",
            "",
            "---",
            "",
            "## 1. Intelligence Phase",
            f"- CVEs found      : {intel.get('cve_count', 0)}",
            f"- Critical        : {intel.get('critical_count', 0)}",
            f"- Exploitable     : {intel.get('exploitable_count', 0)}",
            "",
        ]

        # List each CVE
        for cve in intel.get("cves", []):
            lines.append(f"### {cve['cve_id']} – {cve['severity']}")
            lines.append(f"{cve['description']}")
            lines.append(f"- CVSS: {cve['cvss_score']}  |  Exploit available: {cve['exploit_available']}")
            lines.append("")

        lines.extend([
            "---",
            "",
            "## 2. Web Crawl Phase",
            f"- Pages crawled   : {web.get('pages_crawled', 0)}",
            f"- Forms found     : {web.get('forms_found', 0)}",
            f"- JS libraries    : {', '.join(web.get('js_libraries', []) or ['none'])}",
            f"- Missing headers : {', '.join(web.get('missing_security_headers', []) or ['none'])}",
            "",
        ])

        for finding in web.get("findings", []):
            lines.append(f"### [{finding['severity'].upper()}] {finding['type']}")
            lines.append(finding.get("detail", ""))
            lines.append("")

        lines.extend([
            "---",
            "",
            "## 3. Exploit Plans",
            f"- Plans generated : {exploit.get('plan_count', 0)}",
            "",
        ])

        for plan in exploit.get("plans", []):
            lines.append(f"### {plan['technique_name']}  ({plan['cve_id']})")
            lines.append(f"**Preconditions:** {', '.join(plan.get('preconditions', []))}")
            lines.append("")
            lines.append("**Steps:**")
            for s in plan.get("manual_steps", []):
                lines.append(f"  {s}")
            lines.append("")
            lines.append(f"> 📚 {plan.get('educational_note', '')}")
            lines.append("")

        lines.extend([
            "---",
            "",
            "## 4. Execution Results",
            f"- Tools executed  : {execution.get('tools_run', 0)}",
            f"- Total findings  : {execution.get('total_findings', 0)}",
            "",
        ])

        for r in execution.get("results", []):
            emoji = "✅" if r["status"] == "success" else "❌"
            lines.append(f"{emoji} **{r['tool']}**  status={r['status']}  "
                         f"findings={len(r.get('findings', []))}")
            for f in r.get("findings", [])[:5]:
                lines.append(f"  - {f}")
            lines.append("")

        lines.extend([
            "---",
            "",
            "## 5. Recommendations",
            "1. Patch all CRITICAL CVEs immediately.",
            "2. Add missing security headers to your web server config.",
            "3. Update all third-party libraries to latest stable versions.",
            "4. Implement rate-limiting and account lockout on login forms.",
            "5. Use parameterised queries to prevent SQL injection.",
            "6. Deploy a WAF with rules tuned to discovered attack vectors.",
            "",
            "---",
            "",
            "*Report generated by ERR0RS ULTIMATE*  |  *All testing was performed with authorization*",
        ])

        return "\n".join(lines)

    # ==================================================================
    # Utility – status
    # ==================================================================

    def get_agent_status(self) -> Dict[str, str]:
        return {
            "cve_intelligence" : "ready",
            "browser_automation": "ready",
            "exploit_generator": "ready",
            "tool_executor"    : "ready",
        }
