# Contributing to ERR0RS ULTIMATE

Thank you for your interest in contributing! ERR0RS ULTIMATE is built for the cybersecurity community, and we welcome contributions from everyone.

## 🎯 Ways to Contribute

### 1. Tool Integrations
Add new security tool integrations! We're targeting 150+ tools.

**What we need:**
- Nmap-style wrappers (see `src/tools/recon/nmap_tool.py` as template)
- Proper error handling
- Output parsing → Finding generation
- Remediation guidance
- Educational content

**Priority tools:**
- Burp Suite automation
- Hashcat integration
- John the Ripper
- Bloodhound automation
- PowerShell Empire
- Covenant C2
- Custom tools

### 2. AI Agents
Enhance or create new AI agents:
- Specialized agents (Mobile, Cloud, IoT, etc.)
- Agent coordination improvements
- New LLM provider integrations
- Prompt engineering optimizations

### 3. Education Content
Add to the knowledge base (`src/education/knowledge_base.py`):
- New vulnerability types
- Real-world case studies
- Defense strategies
- CTF walkthroughs

### 4. UI Improvements
- ERR0RZ mascot animations
- K.A.T. interface features
- Web dashboard enhancements
- Accessibility improvements

### 5. Documentation
- Tutorials
- Video guides
- Blog posts
- Translation

### 6. Bug Fixes
- Report issues on GitHub
- Submit fixes with tests
- Improve error handling

---

## 📋 Contribution Guidelines

### Code Style
- Follow PEP 8 for Python
- Use type hints where possible
- Add docstrings (Google style)
- Keep functions focused (< 50 lines)

### Documentation
- Update README for new features
- Add docstrings to all public methods
- Include usage examples
- Document security considerations

### Testing
- Write tests for new features
- Ensure existing tests pass: `python3 tests/test_errors.py`
- Add integration tests for tools
- Test on Kali Linux if possible

### Security
- Never commit API keys or credentials
- Use `.gitignore` properly
- Follow ethical guidelines
- Add guardrails for dangerous operations

---

## 🔄 Pull Request Process

1. **Fork the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/ERR0RS-Ultimate.git
   cd ERR0RS-Ultimate
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, documented code
   - Add tests
   - Update documentation

3. **Test thoroughly**
   ```bash
   python3 tests/test_errors.py
   python3 demo_report.py  # Should generate report
   ```

4. **Commit with clear messages**
   ```bash
   git add .
   git commit -m "feat: Add Burp Suite integration with Finding generation"
   ```

   **Commit message format:**
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation
   - `test:` Tests
   - `refactor:` Code refactoring
   - `style:` Formatting
   - `chore:` Maintenance

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then open a Pull Request on GitHub.

6. **PR Requirements:**
   - Clear description of changes
   - Link to related issues
   - Screenshots for UI changes
   - Test results
   - Security considerations

---

## 🛡️ Security Contributions

### Reporting Vulnerabilities
**DO NOT** open public issues for security vulnerabilities.

Instead, email: **G.holden.schneider@icloud.com**

Include:
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We'll respond within 48 hours and credit you in the fix.

### Security Best Practices
- Validate all user input
- Use parameterized queries
- Implement proper auth checks
- Add rate limiting
- Log security events
- Never trust tool output blindly

---

## 🎓 Educational Contributions

When adding educational content:

1. **Structure** (use EducationContent dataclass):
   - `what`: Definition
   - `why`: Impact/importance
   - `how`: Technical mechanics
   - `defend`: Blue team defense
   - `real_world`: Case study

2. **Quality Standards**:
   - Accurate information
   - Beginner-friendly language
   - Real-world examples
   - Both red & blue team perspectives
   - Include references

3. **Example:**
   ```python
   EducationContent(
       topic="Buffer Overflow",
       what="A buffer overflow occurs when...",
       why="This matters because attackers can...",
       how="The attack works by...",
       defend="Defenders prevent this by...",
       real_world="In 2003, the SQL Slammer worm...",
       difficulty="Intermediate",
       references=["https://cwe.mitre.org/data/definitions/120.html"]
   )
   ```

---

## 🤖 AI Agent Guidelines

When creating or modifying AI agents:

### Agent Structure
```python
class YourAgent(BaseAgent):
    def __init__(self, llm_provider):
        self.llm = llm_provider
        self.system_prompt = "Your specialized role..."
    
    async def analyze(self, data):
        # Agent logic
        pass
```

### Best Practices
- Clear system prompts
- Handle LLM failures gracefully
- Validate AI outputs
- Add human-in-the-loop for critical decisions
- Log all AI actions
- Test with multiple LLMs

---

## 🔧 Tool Integration Template

```python
#!/usr/bin/env python3
"""
ERR0RS ULTIMATE - YourTool Integration
=======================================
[Description of what the tool does]

TEACHING NOTE:
--------------
[Explain why this tool matters in pentesting]
"""

import subprocess
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from core.models import Finding, Severity, PentestPhase


class YourTool:
    TOOL_NAME = "yourtool"
    TIMEOUT = 120  # seconds
    
    def execute(self, target: str, context: dict = None) -> dict:
        """
        Run yourtool against target.
        
        Args:
            target: IP, hostname, or URL
            context: Previous tool outputs (optional)
        
        Returns:
            dict with tool_name, target, findings, success, duration, etc.
        """
        command = ["yourtool", "-options", target]
        command_str = " ".join(command)
        
        start = time.time()
        try:
            proc = subprocess.run(
                command, capture_output=True, text=True, 
                timeout=self.TIMEOUT
            )
            duration = time.time() - start
            findings = self._parse_output(proc.stdout, target)
            
            return {
                "tool_name": self.TOOL_NAME,
                "target": target,
                "phase": PentestPhase.SCANNING,
                "raw_output": proc.stdout,
                "command": command_str,
                "findings": findings,
                "success": True,
                "duration": duration,
            }
            
        except FileNotFoundError:
            return {"success": False, "error": "Tool not installed"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Timeout after {self.TIMEOUT}s"}
    
    def _parse_output(self, output: str, target: str) -> list:
        """Parse tool output into Finding objects."""
        findings = []
        # Your parsing logic here
        return findings
```

---

## 📝 Code Review Checklist

Before submitting, ensure:
- [ ] Code follows style guide
- [ ] All tests pass
- [ ] Documentation is updated
- [ ] No sensitive data in commits
- [ ] Error handling is robust
- [ ] Security guardrails are respected
- [ ] Educational value is clear
- [ ] Works on Kali Linux

---

## 🏆 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Credited in release notes
- Mentioned in documentation
- Given GitHub badges

Top contributors may be invited to the core team!

---

## 💬 Community

- **GitHub Discussions:** Ask questions, share ideas
- **Discord:** [Link TBD]
- **Twitter:** @ERR0RS_Ultimate [TBD]

---

## 📚 Resources

- [Python Style Guide](https://pep8.org/)
- [Git Best Practices](https://www.conventionalcommits.org/)
- [Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)

---

**Thank you for making ERR0RS ULTIMATE better! 💚**

*Every contribution, no matter how small, helps make the internet safer.*
