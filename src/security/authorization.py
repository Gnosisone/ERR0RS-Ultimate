"""
ERR0RS ULTIMATE - Security Guardrails & Authorization
=======================================================
This module enforces ethical boundaries. NO tool in ERR0RS
executes without passing these checks first.

WHY THIS EXISTS:
----------------
Unauthorized access to computer systems is a FEDERAL CRIME
under the Computer Fraud and Abuse Act (CFAA) in the US,
and equivalent laws exist worldwide.

Every professional pentest firm requires WRITTEN authorization
before testing begins. ERR0RS enforces this programmatically.

TEACHING NOTE:
--------------
Understanding the legal and ethical framework around penetration
testing is just as important as the technical skills. A penetration
tester who works without proper authorization — even if they find
real vulnerabilities — can be prosecuted.

Key legal concepts:
  - Written Scope Agreement — What targets, what methods
  - Rules of Engagement     — What's allowed, what's not
  - Safe Harbor Clause      — Protection from liability
  - Responsible Disclosure  — How to report findings
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional


class AuthorizationManager:
    """
    Manages and enforces penetration test authorization.
    No tool executes without a valid authorization on file.
    """

    def __init__(self, auth_file: str = "authorization.json"):
        self.auth_file = auth_file
        self.active_authorizations: List[Dict] = []
        self._load_authorizations()

    def _load_authorizations(self):
        """Load saved authorizations from disk."""
        if os.path.exists(self.auth_file):
            try:
                with open(self.auth_file, 'r') as f:
                    self.active_authorizations = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.active_authorizations = []

    def _save_authorizations(self):
        """Persist authorizations to disk."""
        with open(self.auth_file, 'w') as f:
            json.dump(self.active_authorizations, f, indent=2, default=str)

    def create_authorization(self, client_name: str, targets: List[str],
                              scope_notes: str, tester_name: str,
                              start_date: str, end_date: str) -> Dict:
        """
        Create a new authorization record. The tester must confirm
        they have written permission before this generates.

        TEACHING NOTE:
        In the real world, this would be backed by a signed PDF
        contract. In ERR0RS, it's a digital record that the tester
        explicitly confirms. The confirmation is the legal protection.
        """
        auth = {
            "id": f"AUTH-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "client_name": client_name,
            "targets": targets,
            "scope_notes": scope_notes,
            "tester_name": tester_name,
            "start_date": start_date,
            "end_date": end_date,
            "created_at": datetime.now().isoformat(),
            "confirmed": False,
            "status": "pending",
        }
        self.active_authorizations.append(auth)
        self._save_authorizations()
        return auth

    def confirm_authorization(self, auth_id: str, confirmation_text: str) -> bool:
        """
        Tester must type the exact confirmation text to activate.
        This creates an audit trail proving they acknowledged scope.

        TEACHING NOTE:
        This is the "I confirm I have written authorization" step.
        Skipping it = no authorization = potential legal liability.
        """
        REQUIRED_TEXT = "I confirm I have written authorization to test the specified targets."

        if confirmation_text.strip() != REQUIRED_TEXT:
            print("❌ Confirmation text does not match. Authorization NOT activated.")
            print(f'   Type exactly: "{REQUIRED_TEXT}"')
            return False

        for auth in self.active_authorizations:
            if auth["id"] == auth_id:
                auth["confirmed"] = True
                auth["status"] = "active"
                auth["confirmed_at"] = datetime.now().isoformat()
                self._save_authorizations()
                print(f"✅ Authorization {auth_id} activated.")
                return True

        print(f"❌ Authorization {auth_id} not found.")
        return False

    def is_target_authorized(self, target: str) -> bool:
        """Check if a target is covered by any active authorization."""
        for auth in self.active_authorizations:
            if auth.get("status") != "active":
                continue
            # Check if target matches any authorized target
            for auth_target in auth.get("targets", []):
                if target == auth_target or target.startswith(auth_target):
                    return True
        return False

    def get_active_authorization(self, target: str) -> Optional[Dict]:
        """Get the active authorization covering a target."""
        for auth in self.active_authorizations:
            if auth.get("status") != "active":
                continue
            for auth_target in auth.get("targets", []):
                if target == auth_target or target.startswith(auth_target):
                    return auth
        return None
