#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bounded publication check: stdlib imports, submodules, common secret patterns.

This is a reproducible check, not an exhaustive credential/leak detector.
It prints paths and categories only, never matched secret values.
"""

import ast
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "GitHub token": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})"),
    "AWS access key": re.compile(rb"(?:AKIA|ASIA)[A-Z0-9]{16}"),
    "credential URL": re.compile(rb"https?://[^/\s:@]+:[^/\s@]+@"),
}


def main():
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    findings = []
    count = 0
    for name in filter(None, paths):
        path = ROOT / name
        if name == ".gitmodules":
            findings.append((name, "submodule requires explicit provenance review"))
        if path.is_symlink():
            findings.append((name, "symlink requires explicit distribution review"))
            continue
        data = path.read_bytes()
        count += 1
        for category, pattern in PATTERNS.items():
            if pattern.search(data):
                findings.append((name, category))
        if path.suffix == ".py":
            tree = ast.parse(data.decode("utf-8"), filename=name)
            for node in ast.walk(tree):
                modules = ([n.name for n in node.names] if isinstance(node, ast.Import)
                           else [node.module] if isinstance(node, ast.ImportFrom) and not node.level else [])
                for module in filter(None, modules):
                    root = module.split(".")[0]
                    if root not in sys.stdlib_module_names and root not in {"ds_mock", "tests", "tools"}:
                        findings.append((name, "non-stdlib import: " + root))
    for path, category in findings:
        print(f"{path}: {category}")
    if findings:
        raise SystemExit(1)
    print(f"checked {count} tracked files: no external Python imports, submodules, symlinks or matched common secret patterns")
    print("Scope: current tracked snapshot; reachable public history is reviewed separately.")


if __name__ == "__main__":
    main()
