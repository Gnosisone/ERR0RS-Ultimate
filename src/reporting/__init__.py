#!/usr/bin/env python3
"""ERR0RS ULTIMATE — reporting package"""
try:
    from .pro_reporter import ProReporter, reporter, generate_report, handle_report_command
    _PRO_OK = True
except Exception:
    _PRO_OK = False

try:
    from .report_generator import ReportGenerator
except Exception:
    pass

__all__ = ["ProReporter", "reporter", "generate_report", "handle_report_command"]
