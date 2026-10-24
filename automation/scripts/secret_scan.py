#!/usr/bin/env python3
"""Credential scan over tracked files. Prints rule + file:line only, never matched values.

Exit: 0 clean, 1 findings, git's own status if git cannot list files.
"""
import math
import re
import subprocess
import sys
from pathlib import Path

PLACEHOLDER = re.compile(r"(?i)^[\"']?(redacted|changeme|example|placeholder|xxx+|\*+|<[^>]*>|\$\{?[A-Za-z_]|\{\{|\.\.\.|__[A-Z0-9_]+__)")
MAX_BYTES = 2_000_000

LINE_RULES = [
    ("known-token-prefix", re.compile(r"(glpat-[A-Za-z0-9_-]{20,}|github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,})"), None),
    ("private-key", re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"), None),
    ("basic-auth-flag", re.compile(r"(?i)(?:curl|wget|http)\b.*?(?:\s-u|--user)[ =]+[\"']?[A-Za-z_][A-Za-z0-9_.@-]*:([^\s\"']+)"), 1),
    ("authorization-basic", re.compile(r"(?i)authorization:\s*basic\s+([A-Za-z0-9+/=]{8,})"), 1),
    ("rathole-token", re.compile(r"(?i)\b(?:default_)?token\s*=\s*([\"']?[^\s\"'#]+)"), 1),
    ("url-credentials", re.compile(r"[a-z][a-z0-9+.-]*://[^/\s:@]+:([^/\s@$<{]{4,})@"), 1),
]
RATHOLE_FILE = re.compile(r"(?i)rathole|\.toml")
ASSIGN = re.compile(r"(?i)([A-Za-z0-9_.-]*(?:pass(?:word)?|secret|token|api[_-]?key|encryption[_-]?key|credential)[A-Za-z0-9_.-]*)[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9+/_=-]{32,})(?![A-Za-z0-9+/_=-])")


def entropy(s):
    return -sum(s.count(c) / len(s) * math.log2(s.count(c) / len(s)) for c in set(s))


def high_entropy(token):
    if re.fullmatch(r"[0-9a-fA-F]+", token) and len(token) in (32, 40, 64):
        return False  # git/sha digests
    if not (re.search(r"[A-Za-z]", token) and re.search(r"\d", token)):
        return False
    return entropy(token) >= 4.2


def scan_text(path, text):
    findings = []
    lines = text.splitlines()
    for n, line in enumerate(lines, 1):
        for name, rx, group in LINE_RULES:
            m = rx.search(line)
            if not m:
                continue
            if name == "rathole-token" and not RATHOLE_FILE.search(path) and "default_token" not in line:
                continue
            if group and PLACEHOLDER.match(m.group(group)):
                continue
            findings.append((name, n))
        # high-entropy values assigned to secret-looking keys (skips URLs/queries)
        for m in ASSIGN.finditer(line):
            cand = m.group(2)
            if high_entropy(cand) and not PLACEHOLDER.match(cand):
                findings.append(("high-entropy-token", n))
                break
    # base64 data: blocks inside Kubernetes Secret manifests
    if re.search(r"(?m)^kind:\s*Secret\s*$", text):
        in_data = False
        for n, line in enumerate(lines, 1):
            if re.match(r"^(data|stringData):\s*$", line):
                in_data = line.startswith("data")
                continue
            if in_data:
                m = re.match(r"^\s+[A-Za-z0-9_.-]+:\s*([A-Za-z0-9+/=]{8,})\s*$", line)
                if m and not PLACEHOLDER.match(m.group(1)):
                    findings.append(("k8s-secret-base64-data", n))
                elif line and not line.startswith((" ", "\t", "#")):
                    in_data = False
    return findings


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    proc = subprocess.run(
        ["git", "-c", f"safe.directory={root}", "-C", str(root), "ls-files", "-z"],
        capture_output=True,
    )
    if proc.returncode != 0:
        print(f"Credential check failed to execute (Git exit {proc.returncode}).", file=sys.stderr)
        return proc.returncode
    found = 0
    for rel in proc.stdout.decode("utf-8", "replace").split("\0"):
        if not rel:
            continue
        p = root / rel
        try:
            if not p.is_file() or p.stat().st_size > MAX_BYTES:
                continue
            raw = p.read_bytes()
        except OSError:
            continue
        if b"\0" in raw:
            continue
        for rule, line in sorted(set(scan_text(rel, raw.decode("utf-8", "replace")))):
            print(f"{rel}:{line}: {rule}")
            found += 1
    if found:
        print(f"Credential-like content found ({found} finding(s), values withheld).", file=sys.stderr)
        return 1
    print("Tracked-file credential-pattern check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
