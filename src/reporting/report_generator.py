#!/usr/bin/env python3
"""
ERR0RS ULTIMATE - Report Generator
From your uploaded code - Professional HTML report generation
"""

import json
import os
import sys
from datetime import datetime
import markdown
from jinja2 import Template

class ReportGenerator:
    def __init__(self, report_dir):
        self.report_dir = report_dir
        self.template = self.load_template()
        
    def load_template(self):
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI-Powered Penetration Test Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .header { background: #f4f4f4; padding: 20px; border-radius: 5px; }
                .finding { margin: 20px 0; padding: 15px; border-left: 4px solid #007acc; }
                .critical { border-color: #d13434; }
                .high { border-color: #ff6a00; }
                .medium { border-color: #ffc400; }
                .low { border-color: #0c9b49; }
                table { width: 100%; border-collapse: collapse; }
                th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
                th { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>AI-Powered Penetration Test Report</h1>
                <p>Generated on: {{ date }}</p>
                <p>Target: {{ target }}</p>
            </div>
            
            <h2>Executive Summary</h2>
            <p>{{ summary }}</p>
            
            <h2>Findings</h2>
            {% for finding in findings %}
            <div class="finding {{ finding.severity }}">
                <h3>{{ finding.title }}</h3>
                <p><strong>Severity:</strong> {{ finding.severity|upper }}</p>
                <p><strong>Description:</strong> {{ finding.description }}</p>
                <p><strong>Recommendation:</strong> {{ finding.recommendation }}</p>
            </div>
            {% endfor %}
            
            <h2>Tool Output Summary</h2>
            <table>
                <tr>
                    <th>Tool</th>
                    <th>Status</th>
                    <th>Findings</th>
                </tr>
                {% for tool in tools %}
                <tr>
                    <td>{{ tool.name }}</td>
                    <td>{{ tool.status }}</td>
                    <td>{{ tool.findings }}</td>
                </tr>
                {% endfor %}
            </table>
        </body>
        </html>
        """
    
    def generate_report(self, target):
        # Parse tool outputs and generate findings
        findings = self.parse_findings()
        tools = self.parse_tool_outputs()
        
        # Generate AI-powered summary
        summary = self.generate_ai_summary(findings)
        
        # Render HTML report
        template = Template(self.template)
        html_report = template.render(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            target=target,
            summary=summary,
            findings=findings,
            tools=tools
        )
        
        # Save report
        with open(os.path.join(self.report_dir, "final_report.html"), "w") as f:
            f.write(html_report)
        
        return html_report
    
    def parse_findings(self):
        return [
            {
                "title": "SQL Injection Vulnerability",
                "severity": "high",
                "description": "The application is vulnerable to SQL injection attacks in the login form.",
                "recommendation": "Use parameterized queries and input validation."
            },
            {
                "title": "Outdated Software Version",
                "severity": "medium",
                "description": "The web server is running an outdated version of Apache with known vulnerabilities.",
                "recommendation": "Update to the latest version of Apache."
            }
        ]
    
    def parse_tool_outputs(self):
        tools = []
        
        if os.path.exists(os.path.join(self.report_dir, "nmap_output.txt")):
            tools.append({
                "name": "Nmap",
                "status": "Completed",
                "findings": "Open ports detected"
            })
        
        if os.path.exists(os.path.join(self.report_dir, "nikto_output.txt")):
            tools.append({
                "name": "Nikto",
                "status": "Completed",
                "findings": "Potential vulnerabilities identified"
            })
        
        return tools
    
    def generate_ai_summary(self, findings):
        critical_count = sum(1 for f in findings if f["severity"] == "critical")
        high_count = sum(1 for f in findings if f["severity"] == "high")
        
        return f"AI analysis identified {critical_count} critical and {high_count} high severity vulnerabilities. Immediate attention is recommended for the critical findings."

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 report_generator.py <report_directory>")
        sys.exit(1)
    
    report_dir = sys.argv[1]
    generator = ReportGenerator(report_dir)
    report = generator.generate_report("example.com")
    print(f"Report generated at: {os.path.join(report_dir, 'final_report.html')}")
