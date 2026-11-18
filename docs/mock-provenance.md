# Specification sources and license

The specifications, mock, fixtures, tests and documentation use the
[Apache License, Version 2.0](../LICENSE). Copyright information is in [NOTICE](../NOTICE).

| Source | Revision | Use |
| --- | --- | --- |
| [DSProtocol v2](https://github.com/MeltInterfaceTechnologies/DivingStationProtocolSpecs/tree/745e3903dc17f51d3e30e18d9dfa61bca7f0781f) | `745e3903dc17f51d3e30e18d9dfa61bca7f0781f` | Message layouts, limits, commands and states |
| [OSC 1.0](https://opensoundcontrol.stanford.edu/spec-1_0.html) | Version 1.0, 2002-03-26 | Flat-message syntax |

The implementation uses Python's standard library. Fixture expectations are
static values reviewed against the specification. The [case index](../fixtures/v2/README.md)
links each group to its specification section; the [mock guide](mock-server.md)
describes supported messages and simulator policies.

After publication, `conformance/revisions.json` identifies the public specification,
implementation and fixture commits and their file hashes. Use it with
`python3 tools/verify_snapshot.py` for Git-object verification.
