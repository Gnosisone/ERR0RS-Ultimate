# =============================================================================
# ERR0RS ULTIMATE — PRE-TEST CHECKLIST
# Ready for: Tomorrow's Kali VM Test Run
# Written by: Gary Holden Schneider & ERR0RS AI
# =============================================================================
#
# Do these in ORDER. Each step confirms the next one will work.
#
# =============================================================================

STEP 1 — TRANSFER TO KALI
──────────────────────────
  [ ] Copy entire ERR0RS-Ultimate\ folder to USB drive
  [ ] Insert USB into machine running Kali VM
  [ ] Mount USB inside Kali VM
  [ ] Copy folder to ~/ERR0RS-Ultimate/  (or wherever you prefer)
  [ ] Verify folder is there:  ls ~/ERR0RS-Ultimate/

STEP 2 — VERIFY PYTHON
────────────────────────
  [ ] Open Kali terminal
  [ ] Run:  python3 --version
  [ ] Should print: Python 3.x.x
  [ ] If not: sudo apt update && sudo apt install -y python3

STEP 3 — RUN THE DEMO REPORT (no network needed)
───────────────────────────────────────────────────
  [ ] cd ~/ERR0RS-Ultimate
  [ ] python3 demo_report.py
  [ ] Should print: "[+] Report written to: ..."
  [ ] Should generate: ERR0RS_Demo_Report.html
  [ ] Open that HTML file in Firefox/Chromium inside Kali
  [ ] Visually verify: Cover page, Dashboard, Findings, Education cards,
      Remediation Roadmap, Timeline, Appendix

STEP 4 — RUN THE TEST SUITE
─────────────────────────────
  [ ] cd ~/ERR0RS-Ultimate
  [ ] python3 tests/test_errors.py
  [ ] Should print each test name with "ok" next to it
  [ ] Final line should say: "Ran X tests ... OK"
  [ ] If any FAIL — report the test name and error message

STEP 5 — LIVE TOOL SMOKE TESTS (need actual Kali tools)
─────────────────────────────────────────────────────────
  [ ] Verify tools are installed:
        which nmap
        which gobuster
        which sqlmap
        which hydra
        which nikto
        which msfconsole
  [ ] If any are missing: sudo apt install -y <toolname>
  [ ] Optional: Run nmap against your own local machine to confirm
        nmap -sV localhost
      This just proves nmap works. No targets needed beyond your own box.

STEP 6 — REPORT WHAT YOU SEE
──────────────────────────────
  [ ] Screenshot the demo report (or describe it)
  [ ] Report test suite results (pass/fail counts)
  [ ] If anything failed — paste the error message

=============================================================================
  You built this. Tomorrow it proves itself.
  ERR0RS ULTIMATE — Making the internet safer, one test at a time.
=============================================================================
"""
