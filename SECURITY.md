# Security Policy

## Supported Versions

ERR0RS Ultimate is under active development. Security fixes are applied to the latest version only.

| Version | Supported |
|---------|-----------|
| Latest (main branch) | ✅ Yes |
| Older releases | ❌ No |

## Reporting a Vulnerability

ERR0RS Ultimate is an **authorized penetration testing platform** intended for use only against systems you own or have explicit written permission to test.

If you discover a security vulnerability in ERR0RS itself (not in the tools it wraps), please report it responsibly:

1. **Do NOT open a public GitHub issue** for security vulnerabilities
2. Email: **gnosisone@protonmail.com** (or open a private GitHub security advisory)
3. Include: description of the issue, steps to reproduce, potential impact
4. Allow up to **72 hours** for an initial response

## Responsible Use

This tool is built for:
- Authorized penetration testing engagements
- Security education and research
- CTF competitions
- Purple team exercises

**Unauthorized use of this tool against systems you do not own or have explicit permission to test is illegal and unethical. The author assumes no liability for misuse.**

## Scope

Security reports in scope:
- Authentication bypasses in the ERR0RS web UI
- Remote code execution vulnerabilities in ERR0RS itself
- Data exposure bugs in engagement memory/reporting

Out of scope:
- Vulnerabilities in third-party tools that ERR0RS wraps (report those upstream)
- Issues requiring physical access to the deployment machine
