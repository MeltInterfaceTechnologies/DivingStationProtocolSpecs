#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify fixed-commit (v1) or containing-commit (v2) source hashes offline."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def git_bytes(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.PIPE)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify_revision(key, sha, repository):
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise SystemExit(f"{key} must be a full immutable commit SHA")
    try:
        git_bytes("cat-file", "-e", sha + "^{commit}")
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"missing {key} {sha} in the local Git objects; lock repository: {repository}. "
            "Fetch this repository's pinned commits. Repository-specific commit SHAs are not interchangeable."
        ) from exc


def content_identity(lock):
    groups = {name: lock[name] for name in ("spec_files", "mock_files", "fixture_files")}
    return digest(json.dumps(groups, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=ROOT / "conformance/revisions.json")
    parser.add_argument("--snapshot-commit", help="optional full SHA that must equal the checked-out commit")
    args = parser.parse_args()
    raw_lock = args.lock.read_bytes()
    lock = json.loads(raw_lock.decode("utf-8"))
    head = git_bytes("rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    if args.snapshot_commit:
        verify_revision("snapshot_commit", args.snapshot_commit, lock["repository"])
        if head != args.snapshot_commit:
            raise SystemExit("checkout differs from requested immutable snapshot commit")
    if (args.lock.resolve() == (ROOT / "conformance/revisions.json").resolve()
            or lock.get("schema_version") == 2):
        if raw_lock != git_bytes("show", head + ":conformance/revisions.json"):
            raise SystemExit("snapshot lock differs from its committed Git blob")
    if lock["schema_version"] == 1:
        for key in ("spec_commit", "mock_commit", "fixture_commit"):
            verify_revision(key, lock[key], lock["repository"])
        commits = {"spec_files": lock["spec_commit"], "mock_files": lock["mock_commit"],
                   "fixture_files": lock["fixture_commit"]}
    elif lock["schema_version"] == 2:
        if lock.get("snapshot_binding") != "containing-commit":
            raise SystemExit("unsupported snapshot binding")
        if lock.get("snapshot_sha256") != content_identity(lock):
            raise SystemExit("snapshot content identity mismatch")
        commits = dict.fromkeys(("spec_files", "mock_files", "fixture_files"), head)
    else:
        raise SystemExit("unsupported revision lock schema")
    for group, commit in commits.items():
        for name, expected in lock[group].items():
            path = ROOT / name
            if path.is_symlink() or ROOT not in path.resolve().parents:
                raise SystemExit(f"unsafe locked path: {name}")
            pinned = git_bytes("show", commit + ":" + name)
            if digest(pinned) != expected or digest(path.read_bytes()) != expected:
                raise SystemExit(f"snapshot mismatch: {name}")
    # New implementation/fixture files also require a new reviewed lock.
    for directory, group in (("ds_mock", "mock_files"), ("tests", "mock_files"),
                             ("integration_tests", "mock_files"), ("tools", "mock_files"),
                             ("fixtures/v2", "fixture_files")):
        suffixes = (".py",) if group == "mock_files" else (".json",)
        actual = {str(p.relative_to(ROOT)) for p in (ROOT / directory).rglob("*") if p.suffix in suffixes}
        declared = {p for p in lock[group] if p.startswith(directory + "/")}
        if actual != declared:
            raise SystemExit(f"unlocked or missing files in {directory}")
    print("verified checkout", head)
    for group, commit in commits.items():
        print("verified", group, commit)
    print("all locked files match both Git objects and the current checkout")


if __name__ == "__main__":
    main()
