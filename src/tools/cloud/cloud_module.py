"""
ERR0RS-Ultimate | Cloud Security Module
AWS / Azure / GCP enumeration, misconfiguration auditing, and credential validation.
Every technique includes TEACH (what it is / why it works) and DEFEND (how to detect/prevent).
"""

import subprocess
import shutil
from typing import Optional


CLOUD_BANNER = """
╔══════════════════════════════════════════════════════════╗
║         ☁  ERR0RS Cloud Security Module  ☁              ║
║   AWS · Azure · GCP · Misconfiguration Audit             ║
╚══════════════════════════════════════════════════════════╝
"""


# ─────────────────────────────────────────────
#  UTILITY
# ─────────────────────────────────────────────

def _run(cmd: list[str]) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.stdout.strip() or result.stderr.strip()
    except FileNotFoundError:
        return f"[!] Tool not found: {cmd[0]} — install it first."
    except subprocess.TimeoutExpired:
        return "[!] Command timed out."


def _tool_check(tool: str) -> bool:
    return shutil.which(tool) is not None

# ─────────────────────────────────────────────
#  AWS ENUMERATION
# ─────────────────────────────────────────────

def aws_whoami() -> str:
    """Identify current AWS caller identity."""
    teach = (
        "\n[TEACH] aws sts get-caller-identity reveals the IAM user/role you're operating as.\n"
        "        This is always the first step after obtaining AWS credentials.\n"
    )
    defend = (
        "[DEFEND] Monitor CloudTrail for sts:GetCallerIdentity calls from unexpected IPs.\n"
        "         Alert on calls outside business hours or from new regions.\n\n"
    )
    if not _tool_check("aws"):
        return teach + defend + "[!] AWS CLI not installed. Run: pip install awscli"
    return teach + defend + _run(["aws", "sts", "get-caller-identity"])


def aws_enumerate_iam() -> str:
    """Enumerate IAM users, roles, groups, and attached policies."""
    teach = (
        "\n[TEACH] IAM enumeration maps the permission landscape.\n"
        "        Misconfigured policies are the #1 AWS attack vector.\n"
        "        Tools: aws iam list-users, list-roles, list-attached-user-policies\n"
    )
    defend = (
        "[DEFEND] Use AWS IAM Access Analyzer. Enable least-privilege via SCPs.\n"
        "         Alert on iam:List* calls from non-admin roles.\n\n"
    )
    if not _tool_check("aws"):
        return teach + defend + "[!] AWS CLI not installed."
    users = _run(["aws", "iam", "list-users", "--output", "table"])
    roles = _run(["aws", "iam", "list-roles", "--output", "table"])
    return teach + defend + f"=== IAM USERS ===\n{users}\n\n=== IAM ROLES ===\n{roles}"


def aws_s3_audit() -> str:
    """Audit S3 buckets for public access and misconfiguration."""
    teach = (
        "\n[TEACH] Publicly accessible S3 buckets have caused some of the biggest breaches in history.\n"
        "        Check: bucket ACLs, bucket policies, Block Public Access settings.\n"
        "        Tool: aws s3 ls  +  aws s3api get-bucket-acl --bucket <name>\n"
    )
    defend = (
        "[DEFEND] Enable S3 Block Public Access at the account level.\n"
        "         Use AWS Config rule: s3-bucket-public-read-prohibited\n\n"
    )
    if not _tool_check("aws"):
        return teach + defend + "[!] AWS CLI not installed."
    buckets = _run(["aws", "s3", "ls"])
    return teach + defend + f"=== S3 BUCKETS ===\n{buckets}\n\n[*] Run per-bucket ACL check:\n    aws s3api get-bucket-acl --bucket <bucket-name>"


def aws_key_validator(access_key: str, secret_key: str) -> str:
    """Validate whether AWS keys are live/active."""
    teach = (
        "\n[TEACH] Leaked AWS keys found in GitHub repos, Pastebin, etc. can be validated\n"
        "        without triggering obvious alerts by calling sts:GetCallerIdentity.\n"
        "        This is a read-only call that doesn't modify resources.\n"
    )
    defend = (
        "[DEFEND] Enable AWS GuardDuty (detects credential exfil).\n"
        "         Rotate keys immediately on exposure. Use git-secrets pre-commit hooks.\n\n"
    )
    import os
    env = os.environ.copy()
    env["AWS_ACCESS_KEY_ID"] = access_key
    env["AWS_SECRET_ACCESS_KEY"] = secret_key
    env["AWS_DEFAULT_REGION"] = "us-east-1"
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"],
            capture_output=True, text=True, timeout=15, env=env
        )
        if result.returncode == 0:
            return teach + defend + f"[+] VALID KEYS!\n{result.stdout}"
        return teach + defend + f"[-] Keys invalid or expired.\n{result.stderr}"
    except FileNotFoundError:
        return teach + defend + "[!] AWS CLI not installed."


def aws_prowler_scan() -> str:
    """Run Prowler cloud security assessment (must be installed)."""
    teach = (
        "\n[TEACH] Prowler is an open-source AWS/Azure/GCP security tool that checks\n"
        "        hundreds of controls including CIS Benchmarks, GDPR, HIPAA, SOC2.\n"
        "        GitHub: https://github.com/prowler-cloud/prowler\n"
    )
    defend = (
        "[DEFEND] Run Prowler regularly in CI/CD pipelines.\n"
        "         Integrate findings into a SIEM for continuous compliance monitoring.\n\n"
    )
    if not _tool_check("prowler"):
        return teach + defend + "[!] Prowler not installed. Install: pip install prowler"
    return teach + defend + _run(["prowler", "aws", "--quick-inventory"])


# ─────────────────────────────────────────────
#  AZURE ENUMERATION
# ─────────────────────────────────────────────

def azure_whoami() -> str:
    """Identify current Azure subscription and account context."""
    teach = (
        "\n[TEACH] az account show reveals which subscription and tenant you're authenticated to.\n"
        "        Always verify scope before any enumeration or modification.\n"
    )
    defend = (
        "[DEFEND] Enable Azure Activity Log and Microsoft Defender for Cloud.\n"
        "         Alert on logins from anonymous proxy IPs.\n\n"
    )
    if not _tool_check("az"):
        return teach + defend + "[!] Azure CLI not installed. Install: https://docs.microsoft.com/cli/azure/install-azure-cli"
    return teach + defend + _run(["az", "account", "show"])


def azure_enumerate_rbac() -> str:
    """Enumerate Azure role assignments across the subscription."""
    teach = (
        "\n[TEACH] RBAC misconfiguration is the top Azure attack vector.\n"
        "        Overly permissive roles (Owner/Contributor) on service principals\n"
        "        allow privilege escalation to the entire subscription.\n"
    )
    defend = (
        "[DEFEND] Use Azure Policy to enforce least privilege.\n"
        "         Regularly review role assignments with Azure AD Access Reviews.\n\n"
    )
    if not _tool_check("az"):
        return teach + defend + "[!] Azure CLI not installed."
    return teach + defend + _run(["az", "role", "assignment", "list", "--output", "table"])


def azure_storage_audit() -> str:
    """List Azure storage accounts and check for anonymous blob access."""
    teach = (
        "\n[TEACH] Publicly accessible Azure Blob Storage has exposed millions of records.\n"
        "        Anonymous access level: Container (all blobs public) vs Blob (individual) vs Private.\n"
    )
    defend = (
        "[DEFEND] Disable 'Allow Blob Anonymous Access' at storage account level.\n"
        "         Use Azure Policy: 'Storage accounts should prevent shared key access'.\n\n"
    )
    if not _tool_check("az"):
        return teach + defend + "[!] Azure CLI not installed."
    return teach + defend + _run(["az", "storage", "account", "list", "--output", "table"])


# ─────────────────────────────────────────────
#  GCP ENUMERATION
# ─────────────────────────────────────────────

def gcp_whoami() -> str:
    """Identify current GCP account and project."""
    teach = (
        "\n[TEACH] gcloud config list shows your active project, account, and region.\n"
        "        GCP service account keys (JSON) are high-value targets — treat like passwords.\n"
    )
    defend = (
        "[DEFEND] Use Workload Identity Federation instead of service account key files.\n"
        "         Enable Cloud Audit Logs for all services.\n\n"
    )
    if not _tool_check("gcloud"):
        return teach + defend + "[!] gcloud CLI not installed. https://cloud.google.com/sdk/docs/install"
    return teach + defend + _run(["gcloud", "config", "list"])


def gcp_enumerate_iam() -> str:
    """Enumerate GCP IAM policy bindings for the current project."""
    teach = (
        "\n[TEACH] GCP IAM bindings map members to roles at project/folder/org level.\n"
        "        Overly broad bindings (allUsers, allAuthenticatedUsers) are critical findings.\n"
    )
    defend = (
        "[DEFEND] Enable Security Command Center. Use VPC Service Controls.\n"
        "         Audit primitive roles (Owner, Editor, Viewer) — migrate to predefined roles.\n\n"
    )
    if not _tool_check("gcloud"):
        return teach + defend + "[!] gcloud CLI not installed."
    project = _run(["gcloud", "config", "get-value", "project"])
    return teach + defend + _run(["gcloud", "projects", "get-iam-policy", project, "--format=table"])


def gcp_storage_audit() -> str:
    """List GCS buckets and check for public access."""
    teach = (
        "\n[TEACH] GCS buckets with allUsers or allAuthenticatedUsers ACLs are publicly accessible.\n"
        "        Use: gsutil ls -la  and  gsutil iam get gs://bucket-name\n"
    )
    defend = (
        "[DEFEND] Enable uniform bucket-level access. Disable legacy ACLs.\n"
        "         Use Org Policy: storage.publicAccessPrevention = enforced\n\n"
    )
    if not _tool_check("gsutil"):
        return teach + defend + "[!] gsutil not found. Install Google Cloud SDK."
    return teach + defend + _run(["gsutil", "ls", "-la"])


# ─────────────────────────────────────────────
#  MAIN DISPATCHER
# ─────────────────────────────────────────────

def run_cloud(action: str, **kwargs) -> str:
    print(CLOUD_BANNER)
    dispatch = {
        "aws_whoami": aws_whoami,
        "aws_iam": aws_enumerate_iam,
        "aws_s3": aws_s3_audit,
        "aws_keys": lambda: aws_key_validator(kwargs.get("access_key",""), kwargs.get("secret_key","")),
        "aws_prowler": aws_prowler_scan,
        "azure_whoami": azure_whoami,
        "azure_rbac": azure_enumerate_rbac,
        "azure_storage": azure_storage_audit,
        "gcp_whoami": gcp_whoami,
        "gcp_iam": gcp_enumerate_iam,
        "gcp_storage": gcp_storage_audit,
    }
    fn = dispatch.get(action)
    if fn:
        return fn()
    # Help menu
    menu = "\n[Cloud Security Module — Available Actions]\n\n"
    menu += "  AWS:\n"
    menu += "    aws_whoami     — Current caller identity\n"
    menu += "    aws_iam        — IAM users, roles, policies\n"
    menu += "    aws_s3         — S3 bucket public access audit\n"
    menu += "    aws_keys       — Validate leaked access key/secret\n"
    menu += "    aws_prowler    — Full Prowler cloud security scan\n\n"
    menu += "  Azure:\n"
    menu += "    azure_whoami   — Current subscription context\n"
    menu += "    azure_rbac     — Role assignments enumeration\n"
    menu += "    azure_storage  — Storage account audit\n\n"
    menu += "  GCP:\n"
    menu += "    gcp_whoami     — Current project and account\n"
    menu += "    gcp_iam        — IAM policy bindings\n"
    menu += "    gcp_storage    — GCS bucket audit\n"
    return menu
