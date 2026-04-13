# src/ui/dashboard/routes/pages.py
# ERR0RS-Ultimate — HTML page routes
#
# Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone

from __future__ import annotations
import os
from flask import Blueprint, current_app, render_template, abort, send_from_directory

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def index():
    ctx = current_app.config.get("SHARED_CTX")
    hm  = current_app.config.get("HARDWARE_MANAGER")
    we  = current_app.config.get("WORKFLOW_ENGINE")
    return render_template(
        "dashboard.html",
        session=ctx.summary() if ctx else {},
        devices=hm.list_devices() if hm else [],
        workflows=we.list() if we else [],
    )


@pages_bp.route("/report/<path:filename>")
def view_report(filename: str):
    rg         = current_app.config.get("REPORT_GENERATOR")
    report_dir = getattr(rg, "report_dir", "reports") if rg else "reports"
    full_path  = os.path.join(report_dir, filename)

    if not os.path.isfile(full_path):
        abort(404)

    if filename.endswith(".html"):
        with open(full_path) as fh:
            return fh.read()

    with open(full_path) as fh:
        content = fh.read()
    return render_template("report_view.html", content=content, filename=filename)


@pages_bp.route("/payload_studio")
def payload_studio():
    return render_template("payload_studio.html")


@pages_bp.route("/reports")
def reports_page():
    rg         = current_app.config.get("REPORT_GENERATOR")
    report_dir = getattr(rg, "report_dir", "reports") if rg else "reports"
    files = []
    if os.path.isdir(report_dir):
        files = sorted(
            f for f in os.listdir(report_dir)
            if f.endswith((".md", ".html", ".json"))
        )
    return render_template("reports.html", files=files)
