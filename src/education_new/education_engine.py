"""
ERR0RS ULTIMATE - Education Engine
====================================
This is the brain behind the teaching. Every time a tool runs,
every time a finding is generated, every time a report is built —
this engine attaches contextual education to it.

HOW IT WORKS:
-------------
1. A tool produces a Finding (e.g., "SQL Injection on /login")
2. The Education Engine looks up that finding type
3. It returns: WHAT it is, WHY it matters, HOW it works,
   and HOW to defend against it
4. That education gets embedded INTO the finding
5. The report engine renders it beautifully

WHY THIS MATTERS:
-----------------
Most pentest tools just say "VULNERABILITY FOUND" and dump raw output.
A junior analyst has to Google everything to understand what it means.
ERR0RS teaches inline. No context switching. No leaving the tool.
This is what makes it an industry gold standard learning platform.
"""

from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class EducationContent:
    """
    Structured teaching content for a specific topic.
    Every field answers a different question a learner would ask.
    """
    topic:        str    = ""
    what:         str    = ""    # What IS this? (definition)
    why:          str    = ""    # Why does it matter? (impact)
    how:          str    = ""    # How does it work? (mechanics)
    defend:       str    = ""    # How do defenders stop it?
    real_world:   str    = ""    # Real-world example or case study
    difficulty:   str    = "Beginner"  # Beginner | Intermediate | Advanced
    references:   List[str] = None

    def __post_init__(self):
        if self.references is None:
            self.references = []

    def to_markdown(self) -> str:
        """Render this education block as clean markdown."""
        lines = [
            f"## 📚 Learning: {self.topic}",
            "",
            f"### What is it?",
            self.what,
            "",
            f"### Why does it matter?",
            self.why,
            "",
            f"### How does it work?",
            self.how,
            "",
            f"### How do defenders stop it?",
            self.defend,
        ]
        if self.real_world:
            lines += ["", "### Real-World Example", self.real_world]
        if self.references:
            lines += ["", "### References"]
            for ref in self.references:
                lines.append(f"- {ref}")
        return "\n".join(lines)

    def to_html_block(self) -> str:
        """Render as a styled HTML education card for reports."""
        refs_html = "".join(
            f'<li><a href="{r}" target="_blank">{r}</a></li>'
            for r in self.references
        )
        return f"""
        <div class="education-card">
            <div class="edu-header">
                <span class="edu-icon">📚</span>
                <h3>Learning: {self.topic}</h3>
                <span class="edu-difficulty edu-{self.difficulty.lower()}">{self.difficulty}</span>
            </div>
            <div class="edu-section"><strong>What is it?</strong><p>{self.what}</p></div>
            <div class="edu-section"><strong>Why does it matter?</strong><p>{self.why}</p></div>
            <div class="edu-section"><strong>How does it work?</strong><p>{self.how}</p></div>
            <div class="edu-section"><strong>How do defenders stop it?</strong><p>{self.defend}</p></div>
            {"<div class='edu-section'><strong>Real-World Example</strong><p>" + self.real_world + "</p></div>" if self.real_world else ""}
            {"<div class='edu-section'><strong>References</strong><ul>" + refs_html + "</ul></div>" if self.references else ""}
        </div>
        """
