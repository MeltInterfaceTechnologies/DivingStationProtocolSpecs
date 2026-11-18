# Validation scope

The standard-library-only v2 peer is covered by 34 offline unittest methods,
seven normal message byte/named-value oracles, three separate layout probes, 88 mock regression inputs, 39 command
cases and five virtual-time transcripts. Five deliberately shared mistakes must
produce assertion failures without unexpected test errors. Three separate
loopback UDP tests check transport behavior and bounded live haptics history.

CPython 3.10.22, 3.12.14 and 3.13.5 were exercised on cloud Linux. The bounded
demo and offline CLI were checked separately from the deterministic suite.

```sh
python3 -m unittest discover -s tests -v
python3 tools/check_oracle_sensitivity.py
python3 -m unittest discover -s integration_tests -v
```

The published revision lock is generated only after the public implementation
commit exists and is added in a following evidence commit. From that checkout,
run `python3 tools/verify_snapshot.py` to compare Git objects and current files.
A file-only payload cannot perform Git-object or revision-lock checks yet.

Validation covers the cases above and the loopback transport adapter. Hardware
behavior, production LAN authorization/security and performance require checks
in the target environment. SDK conformance assertions must follow the normative specification. This suite
records shared inputs and mock behavior, leaving boundary interpretation
unresolved here. Unassigned SDK assertions do not relax the requirement to
discard an entire message containing an invalid record.

## Automated checks

The repository workflow runs the commands above on Ubuntu with Python 3.10,
3.12 and 3.13. It uses read-only repository permissions and official actions
pinned to full commit IDs. Runtime dependencies remain Python's standard library.

`python3 tools/check_ci_snapshot.py` checks the published snapshot phase using
full Git history. The first payload directly on the published specification base
may run as `bootstrap-unlocked`. An initial merge wrapper is allowed only when
its tree is identical to that payload. Every follow-up revision requires the
published lock; removing it or reverting through a PR with a locked base fails.
The workflow supplies the PR base or previous push commit to this check.
A shallow checkout fails this phase check. The runtime and UDP suites remain
separate, and the illustrative demo is run manually.

A reviewed lock may identify a newer published implementation ancestor for a
subsequent release. It must cover both normative v2 specification files and all
tracked Python, license/notice and workflow files. Dropping these hash entries
fails validation; source changes require an updated reviewed lock.

The public snapshot helper supports Git 2.43 and later. It blocks automatic
object-transport access in both its Git reads and the child verifier; obtain the
full history and required objects before running the check.
