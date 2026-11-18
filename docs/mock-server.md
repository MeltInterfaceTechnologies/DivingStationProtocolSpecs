# Common DSProtocol v2 mock and independent fixtures

[日本語](mock-server_JA.md) · [Case index](../fixtures/v2/README.md) · [Provenance](mock-provenance.md)

This is a reusable test peer for the public [v2 specification](ds_protocol_v2_EN.md)
at commit `745e3903dc17f51d3e30e18d9dfa61bca7f0781f`, targeting ContactGlove3 Pro /
DivingStation 2.0.0+. It runs on Python 3.10+ using the standard library.

## Get a fixed revision and run

The validated spec, mock and fixture commit SHAs and SHA-256 file hashes are
recorded in [`conformance/revisions.json`](../conformance/revisions.json).
Pin the full `mock_commit` / `fixture_commit` from that file in a consuming build.
The mock and its independently authored fixture expectations share a version.

```sh
git clone https://github.com/MeltInterfaceTechnologies/DivingStationProtocolSpecs.git
cd DivingStationProtocolSpecs
git checkout <full-published-mock_commit-from-revisions.json>
python3 -m unittest discover -s tests -v
python3 tools/check_oracle_sensitivity.py
```

The lock is added in a subsequent evidence commit, because a commit cannot
contain its own SHA. In an evidence checkout containing that lock, run:

```sh
python3 tools/verify_snapshot.py
python3 tools/audit_public.py
```

`verify_snapshot.py` compares each hash with both the pinned Git object and the
current file, and checks for additional unlocked Python/JSON files. Keep the
lock separately and pass `--lock /absolute/path/revisions.json` to verify the
implementation commit directly. Fetch full Git history; a ZIP or a shallow
checkout missing the pinned commits cannot perform the Git-object check.
Spec changes require reviewing the corresponding cases and publishing a new lock.
The lock identifies the exact inputs covered by the recorded tests.

## Deterministic conformance

```sh
python3 -m unittest discover -s tests -v
python3 tools/check_oracle_sensitivity.py
python3 -m ds_mock.replay fixtures/v2/scenarios/delivery-faults.json
```

These tests use integer virtual milliseconds, static bytes and explicit command
sources. They do not use sockets, sleeps, real time, random seeds or the demo.
`Station.receive(packet, source, now_ms)`, `advance(now_ms)`, `approve(...)` and
`publish(packet, now_ms)` are the reusable pure interface. Time must never move
backwards. A scenario's `expected` section is read by the tests only; the replay
engine never reads it. Replay prints actual results and never rewrites fixtures.

The static corpus includes:

| Corpus | Checks |
| --- | --- |
| `wire.json` | Four literal byte anchors, ten malformed/unsupported packets and eight timestamp boundaries, including signed high/low words |
| `delivery.json` | Seven normal named/byte oracles, three separate layout probes and 88 mock regression inputs: types, count/limit, complete records, atomic discard, ranges, UUID, UTF-8 byte limits and tracking states |
| `commands.json` | 39 command cases: profile statuses 0/1/2 and correlation, malformed requests, haptics bounds/NaN/Inf, unauthorized input and removed addresses |
| `scenarios/*.json` | Five exact transcripts: session identity, keepalive/expiry, virtual approval/capacity, loss, duplicates, reordered generation times and non-control tracking states |

Wire integers and floats use big-endian OSC int32/float32, with explicit tags and
NUL padding, following the [OSC 1.0 specification](https://opensoundcontrol.stanford.edu/spec-1_0.html).
DSProtocol's UTF-8 strings extend OSC 1.0's ASCII string description. The codec
is a deliberately limited flat-message implementation, not a general OSC library.
Timestamp words are signed on the wire and combined as unsigned 32-bit halves.
OSC transmission time and frame generation time are separate.

Expected named values and bytes are static specification-referenced oracles. Delivery `mock_expectation` verdicts describe the mock validator; this corpus does not assign SDK conformance verdicts. SDK assertions must follow the normative specification, including [whole-message discard for an invalid record](ds_protocol_v2_EN.md#records-and-validation). The corpus provides no exception. How the ID/datagram/profile-text limits and that general rule determine the boundary cases' SDK assertions remains unresolved in this work. An unassigned assertion does not establish permission to accept an input. See the [fixture scope](../fixtures/v2/README.md).
Short wire anchors use literal hex; complete packets were authored independently
with `struct`. Changes to expectations require review of the corresponding spec
section. Input-only edits and repetitions reduce duplication in delivery cases.
Full named records, byte anchors and table-order oracles complement roundtrips.
The sensitivity command injects five shared mistakes: timestamp signedness,
skeleton and sensor w/x order, node order and ergonomics order. Each must cause assertion failures
in an independent fixture test, with zero unexpected test errors. Its scope is
these five mutations.

## UDP integration and literal replay

Run transport checks separately:

```sh
python3 -m unittest discover -s integration_tests -v
python3 -m ds_mock.server --port 25791 --stream fixtures/v2/normal-stream.json
```

The server binds **127.0.0.1 only**. Use `--port 0` to select a free port; the first
JSON line reports the bound port. A client must send `/DS2/HC/Connect` with its
receive port, then keep the same sending socket for keepalive, profile, haptics
and Disconnect. Choose a port distinct from any running DivingStation instance.
Stop with Ctrl+C. Without `--stream`, only commands are served.

The literal stream is replayed once per new authorized session, with offsets
relative to its first authorization. Keepalive does not rewind it. Approval
starts the stream clock; expiry and Disconnect stop delivery. A tick emits all
due packets in listed order, without sorting their generation timestamps.
The six-message example sends normal Device, Ergonomics, Controller, HandSkeleton, HandSkeletonRaw and RawSensorTransforms inputs for ID `L` once. Skeleton and sensor quaternions have unit norm within float32 rounding and distinct w/x/y/z components. The inventory remains present for polling. The geometry is synthetic; it does not establish anatomical or kinematic accuracy. A stream item has `at_ms` plus either `packet_hex` or a
`message` with explicit `address`, `types`, `args`; use hex for malformed OSC.
`{"float":"nan"}`, `{"float":"inf"}` and `{"float":"-inf"}` represent nonfinite
arguments in portable JSON. Fault injection bypasses delivery validation on
purpose. Never treat those datagrams as conforming server output.

Payload bytes and order are fixed; UDP delivery latency, loss and scheduling
are operating-system behavior. Socket tests use bounded timeouts. The offline
suite is the deterministic gate; UDP tests verify the adapter separately.

## Illustrative demo

```sh
python3 -m ds_mock.demo --port 25791
# Bounded smoke run:
python3 -m ds_mock.demo --port 0 --frames 2
```

The demo uses wall-clock generation times and illustrative left/right motion.
It emits Device, Ergonomics, Controller, RawSensorTransforms, HandSkeleton and
HandSkeletonRaw. Its device IDs are `MOCK-L` and `MOCK-R`; profile UUIDs are
`00000000-0000-4000-8000-000000000001` and `...0002`. Profile queries return
synthetic display text. Haptics validates/logs a command in `Station.haptics`,
with no physical effect or protocol acknowledgement. Both live CLIs retain only the newest
1024 accepted haptics records; the pure offline engine retains complete history.
Offline replay rejects a truncation policy. Demo poses use metres,
negative X toward fingertips, mirrored Z and parent-local wxyz quaternions.
Raw and retargeted poses share values; no retargeting is performed.
Use the demo to explore client behavior and the static fixture suite for conformance.

## Automated checks

The repository workflow runs the fixture, mutation and separate UDP commands on
Ubuntu with Python 3.10, 3.12 and 3.13. See [snapshot phases](../conformance/validation.md#automated-checks)
for the first unlocked payload and subsequent required-lock checks.

## Coverage and limits

| Area | Included | Limits / mock policies |
| --- | --- | --- |
| v2 delivery layouts | All seven addresses, counts, explicit tags, whole-message rejection, finite IK-derived data, controller ranges, device enums, profile status/size rules | Numeric layout sentinels are not measured poses. No IK, retargeting, biomechanics, calibration, quaternion normalization or geometric correctness checks |
| Skeleton | 25 positions, 19 parent-local wxyz rotations, one record, 64-byte UTF-8 ID and 1200-byte ceiling | Invalid/missing values are rejected; no zero/identity fallback |
| Tracking | States 0/1/2; 1/2 remain displayable but `usable_for_control=false` | Control/interpolation/velocity behavior of a consuming application remains untested |
| Sessions | Source endpoint + receive port, separate IP identities, 30s keepalive scenarios, expiry at 90,000ms, Disconnect, virtual approval | Loopback UDP only; no LAN settings, approval modal, cryptographic auth, denial/revocation UI or production security verification |
| Commands | Per-source profile response (not global broadcast); status 0/1/2; request ID preserved; bounded haptics without clamping | Fixed profiles/devices. Same source endpoint registered to multiple receive ports gets a response on each; that multiplexing policy is not claimed as production behavior |
| Timing / faults | Explicit loss, duplication, bad bytes, bad fields, generation timestamps out of order | Spec does not define duplicate/stale rejection or a client timeout rule; the mock imposes neither. No bandwidth/stress or network-fragmentation simulation |
| Capacity / retry | Default cap 8 including pending sessions; sub-second retries ignored without refreshing expiry; receive identity replacement requires fresh approval | Spec requires a client cap but gives no number, and tells clients not to retry under 1s without defining a server response. These responses are mock policies |
| Sensor data / haptics | Finite synthetic sensor values; haptics only for the two synthetic IDs | Extra mock policies: reject nonfinite RawSensorTransforms and commands for unknown synthetic IDs |
| OSC / products | Flat `i`, `f`, `s` messages for v2 / CG3 Pro | No bundles/timetags, pattern expansion, other OSC tags, v1, Wrist, Hand/HandQuat, finger haptics, standard CG3 or other v1 devices |

Validation covers static protocol cases and the loopback adapter. Hardware behavior,
SDK interoperability, production LAN security and performance require checks in
the target environment.
