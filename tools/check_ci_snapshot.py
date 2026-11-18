#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify the public snapshot lock, allowing only the first unlocked payload."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_BASE = "745e3903dc17f51d3e30e18d9dfa61bca7f0781f"
PUBLIC_REPOSITORY = "https://github.com/MeltInterfaceTechnologies/DivingStationProtocolSpecs"
LOCK = "conformance/revisions.json"
READ_COMMANDS = {"rev-parse", "cat-file", "merge-base", "rev-list", "show", "ls-tree"}


class SnapshotError(ValueError):
    pass


def git_environment():
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_COUNT="0",
               GIT_NO_REPLACE_OBJECTS="1", GIT_NO_LAZY_FETCH="1", GIT_OPTIONAL_LOCKS="0",
               GIT_ALLOW_PROTOCOL="", GIT_TERMINAL_PROMPT="0")
    return env


def git(repo, command, *args):
    if command not in READ_COMMANDS:
        raise SnapshotError("Git mutation/network commands are forbidden")
    result = subprocess.run(["git", "--no-replace-objects", "--no-optional-locks",
                             "-c", "core.fsmonitor=false", "-c", "core.hooksPath=" + os.devnull,
                             "-C", str(repo), command, *args], env=git_environment(),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise SnapshotError("Git read failed: " + command)
    return result.stdout


def fixed_commit(repo, sha):
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise SnapshotError("a full immutable commit SHA is required")
    if git(repo, "rev-parse", "--verify", sha + "^{commit}").decode().strip() != sha:
        raise SnapshotError("commit did not resolve exactly")



def initial_payload(repo, head):
    rows = [line.split() for line in git(repo, "rev-list", "--parents", head, "^" + PUBLIC_BASE).decode().splitlines()]
    if rows == [[head, PUBLIC_BASE]]:
        return True
    # GitHub may wrap the first payload PR in a merge commit. The wrapper
    # contributes no new tree/blob, and no second payload revision is allowed.
    if len(rows) != 2:
        return False
    graph = {row[0]: row[1:] for row in rows}
    parents = graph.get(head, [])
    if len(parents) != 2 or PUBLIC_BASE not in parents:
        return False
    payload = next(parent for parent in parents if parent != PUBLIC_BASE)
    if graph.get(payload) != [PUBLIC_BASE]:
        return False
    return git(repo, "rev-parse", head + "^{tree}") == git(repo, "rev-parse", payload + "^{tree}")


def check_snapshot(repo=ROOT, base_commit=""):
    repo = Path(repo)
    if git(repo, "rev-parse", "--is-shallow-repository").strip() != b"false":
        raise SnapshotError("full public history is required; use fetch-depth: 0")
    head = git(repo, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    fixed_commit(repo, PUBLIC_BASE)
    git(repo, "merge-base", "--is-ancestor", PUBLIC_BASE, head)
    if base_commit:
        fixed_commit(repo, base_commit)
    path = repo / LOCK
    if path.is_symlink():
        raise SnapshotError("revision lock must be a regular file")
    if path.exists():
        lock = json.loads(path.read_text(encoding="utf-8"))
        if lock.get("schema_version") != 1 or lock.get("repository") != PUBLIC_REPOSITORY:
            raise SnapshotError("a published public schema 1 lock is required")
        if lock.get("spec_commit") != PUBLIC_BASE or lock.get("mock_commit") != lock.get("fixture_commit"):
            raise SnapshotError("public lock anchors differ from the reviewed publication")
        implementation = lock.get("mock_commit", "")
        fixed_commit(repo, implementation)
        git(repo, "merge-base", "--is-ancestor", implementation, head)
        git(repo, "merge-base", "--is-ancestor", PUBLIC_BASE, implementation)
        tracked = set(filter(None, git(repo, "ls-tree", "-r", "--name-only", "-z", head).decode().split("\0")))
        required_spec = {"docs/ds_protocol_v2.md", "docs/ds_protocol_v2_EN.md"}
        required_mock = {name for name in tracked if name.endswith(".py")
                         or name in {"LICENSE", "NOTICE", ".github/workflows/protocol-tests.yml"}}
        if set(lock.get("spec_files", {})) != required_spec:
            raise SnapshotError("published lock must cover both normative v2 specification files")
        if set(lock.get("mock_files", {})) != required_mock:
            raise SnapshotError("published lock must cover every Python, legal and workflow file")
        result = subprocess.run([sys.executable, "-B", str(repo / "tools/verify_snapshot.py"),
                                 "--snapshot-commit", head], cwd=repo,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=git_environment())
        if result.returncode:
            raise SnapshotError("published snapshot verification failed")
        print(result.stdout, end="")
        return "locked"
    # A PR cannot revert to the bootstrap exception after its base acquired a lock.
    if base_commit and git(repo, "rev-list", base_commit, "--", LOCK).strip():
        raise SnapshotError("the base history already requires a revision lock")
    if git(repo, "rev-list", head, "--", LOCK).strip():
        raise SnapshotError("a previously introduced revision lock cannot be removed")
    if not initial_payload(repo, head):
        raise SnapshotError("unlocked bootstrap permits exactly one payload commit and its identical-tree introduction merge")
    if base_commit and base_commit != PUBLIC_BASE:
        raise SnapshotError("the base has already passed initial introduction; a revision lock is required")
    return "bootstrap-unlocked"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-commit", default="", help="PR base or previous push commit supplied by the event")
    args = parser.parse_args()
    try:
        state = check_snapshot(base_commit=args.base_commit)
    except (SnapshotError, OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Snapshot check failed: {exc}\n")
    print("snapshot_state=" + state)
    if state == "bootstrap-unlocked":
        print("Initial introduction only: add the published lock before any follow-up revision.")


if __name__ == "__main__":
    main()
