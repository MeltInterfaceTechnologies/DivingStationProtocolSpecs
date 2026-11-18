# Independent v2 fixture case index

The normative source is the public v2 specification at `745e3903dc17f51d3e30e18d9dfa61bca7f0781f`. See [execution / limits](../../docs/mock-server.md) and [provenance](../../docs/mock-provenance.md).

These are independently authored input and decoded-value oracles. Review changes against the cited specification. The mock and SDK outputs do not define the expected bytes or values.

## Format

`wire.json` contains literal OSC hex, typed arguments, malformed packets and timestamp triples. `delivery.json` schema 2 contains shared inputs, specification references, a purpose for each base/case, and **`mock_expectation`** values targeting `ds_mock.protocol.inspect`. `layout-sentinels.json` schema 2 preserves three earlier layout anchors separately. `commands.json` and `scenarios/*.json` schema 1 describe the mock command engine and virtual transcripts. These files are a versioned v2 corpus.

Delivery input notation applies to a copied base message in this order: `repeat_records` repeats the record after the leading version (0 = empty); `set_args` replaces absolute zero-based arguments; `drop_args` removes argument and tag at each index; `replace_types` changes tags at absolute indices. Only inputs are expanded. `mock_expectation.verdict` is accept/ignore/reject for the mock validator. Accepted cases specify a record count and optional decoded fields. Every base includes full named records and independently encoded `packet_hex`. Float special values use `{"float":"nan"}`, `inf`, `-inf` tokens.

SDK repositories can reuse these inputs to write assertions against the normative specification. `mock_expectation` records the mock validator's regression behavior; this corpus does not assign SDK conformance verdicts.

The published [Records and validation](../../docs/ds_protocol_v2_EN.md#records-and-validation) rule still requires discarding the entire message when any record is invalid. This corpus adds no exception to that rule. For the 64-byte skeleton ID, 1200-byte datagram and profile-text boundary inputs, this work leaves unresolved how the stated limits and the general validation rule determine each SDK conformance assertion. An `unspecified` SDK assertion means only that this corpus has not assigned it; it does not establish that accepting the input is permitted by the specification. Observed SDK behavior is evidence for further specification interpretation, not a determination of conformance. Mock-specific finite-value probes are identified separately.

### Normal reception and layout probes

The seven `delivery.json` bases are normal, synthetic reception inputs. The two skeleton bases have 19 unit quaternions and the sensor base has five. Each uses an explicit signed permutation of `(1, 2, 4, 10) / 11` in **w, x, y, z** order: `1² + 2² + 4² + 10² = 11²`. All four components differ and every joint/sensor quaternion differs within its packet. `quaternion_design` stores the independent integer design; the literal values and bytes are rounded once to OSC float32. The squared norm differs from one only by float32 rounding. The pinned specification states component order; this normal-input design does not add a receiver normalization requirement or tolerance to it.

`layout-sentinels.json` retains the original three packet/value anchors for wire placement tests. Skeleton sentinels contain nonunit quaternion magnitudes and do not serve as normal SDK input. Their verdicts target only the mock's finite-value/layout validator. Sensor probes are also preserved for historical placement checks; use the new distinct-component sensor base to test all component swaps.

`normal-stream.json` replays Device, Ergonomics, Controller, HandSkeleton, HandSkeletonRaw and RawSensorTransforms once, with the same device ID `L`, complete Tracked data and normalized rotations. Its inventory remains present for polling. This stream tests serialization and receipt; the synthetic geometry is not an anatomical, kinematic, or physical-pose oracle.

Scenario steps use receive/approve/advance/publish with nondecreasing `at_ms`. A stream offset is relative to first authorization. Source tuples are explicit; TEST-NET IPs are virtual, never contacted. Every expected transcript includes outcome, emissions, session state and recorded haptics. Missing/duplicate/stale data do not acquire a new rejection policy: their delivery/interpretation follows only the pinned spec.

## Full delivery anchors

| Base | Arguments | Mock validator expectation |
| --- | ---: | --- |
| `device` | 11 | accept; full named record and packet bytes |
| `ergonomics` | 26 | accept; full named record and packet bytes |
| `controller` | 16 | accept; full named record and packet bytes |
| `skeleton` | 158 | accept; full named record and packet bytes |
| `raw_skeleton` | 157 | accept; full named record and packet bytes |
| `sensors` | 40 | accept; full named record and packet bytes |
| `profile` | 6 | accept; full named record and packet bytes |

## Delivery inputs and mock regression verdicts

| Case ID | Mock validator expectation | Source |
| --- | --- | --- |
| `device-wrong-version` | ignore | [spec](../../docs/ds_protocol_v2_EN.md#device-information) |
| `device-missing-argument` | reject | [spec](../../docs/ds_protocol_v2_EN.md#device-information) |
| `device-wrong-tag` | reject | [spec](../../docs/ds_protocol_v2_EN.md#device-information) |
| `ergonomics-wrong-version` | ignore | [spec](../../docs/ds_protocol_v2_EN.md#records-and-validation) |
| `ergonomics-missing-argument` | reject | [spec](../../docs/ds_protocol_v2_EN.md#records-and-validation) |
| `ergonomics-wrong-tag` | reject | [spec](../../docs/ds_protocol_v2_EN.md#records-and-validation) |
| `controller-wrong-version` | ignore | [spec](../../docs/ds_protocol_v2_EN.md#controller-input) |
| `controller-missing-argument` | reject | [spec](../../docs/ds_protocol_v2_EN.md#controller-input) |
| `controller-wrong-tag` | reject | [spec](../../docs/ds_protocol_v2_EN.md#controller-input) |
| `skeleton-wrong-version` | ignore | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-retargeted) |
| `skeleton-missing-argument` | reject | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-retargeted) |
| `skeleton-wrong-tag` | reject | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-retargeted) |
| `raw_skeleton-wrong-version` | ignore | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-raw) |
| `raw_skeleton-missing-argument` | reject | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-raw) |
| `raw_skeleton-wrong-tag` | reject | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-raw) |
| `sensors-wrong-version` | ignore | [spec](../../docs/ds_protocol_v2_EN.md#records-and-validation) |
| `sensors-missing-argument` | reject | [spec](../../docs/ds_protocol_v2_EN.md#records-and-validation) |
| `sensors-wrong-tag` | reject | [spec](../../docs/ds_protocol_v2_EN.md#records-and-validation) |
| `profile-wrong-version` | ignore | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information) |
| `profile-missing-argument` | reject | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information) |
| `profile-wrong-tag` | reject | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information) |
| `device-empty` | accept; 0 records | [spec](../../docs/ds_protocol_v2_EN.md#device-information) |
| `device-eight-records` | accept; 8 records | [spec](../../docs/ds_protocol_v2_EN.md#device-information) |
| `device-nine-records` | reject | [spec](../../docs/ds_protocol_v2_EN.md#device-information) |
| `ergonomics-empty` | accept; 0 records | [spec](../../docs/ds_protocol_v2_EN.md#records-and-validation) |
| `ergonomics-eight-records` | accept; 8 records | [spec](../../docs/ds_protocol_v2_EN.md#records-and-validation) |
| `ergonomics-nine-records` | reject | [spec](../../docs/ds_protocol_v2_EN.md#records-and-validation) |
| `controller-empty` | accept; 0 records | [spec](../../docs/ds_protocol_v2_EN.md#controller-input) |
| `controller-eight-records` | accept; 8 records | [spec](../../docs/ds_protocol_v2_EN.md#controller-input) |
| `controller-nine-records` | reject | [spec](../../docs/ds_protocol_v2_EN.md#controller-input) |
| `sensors-empty` | accept; 0 records | [spec](../../docs/ds_protocol_v2_EN.md#records-and-validation) |
| `sensors-eight-records` | accept; 8 records | [spec](../../docs/ds_protocol_v2_EN.md#records-and-validation) |
| `sensors-nine-records` | reject | [spec](../../docs/ds_protocol_v2_EN.md#records-and-validation) |
| `skeleton-empty` | reject | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-retargeted) |
| `skeleton-two-records` | reject | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-retargeted) |
| `skeleton-id-64-utf8-bytes` | accept; 1 records | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-retargeted) |
| `skeleton-id-65-utf8-bytes` | reject | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-retargeted) |
| `skeleton-oversize-datagram` | reject | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-retargeted) |
| `skeleton-state-1` | accept; 1 records | [spec](../../docs/ds_protocol_v2_EN.md#tracking-states) |
| `skeleton-state-2` | accept; 1 records | [spec](../../docs/ds_protocol_v2_EN.md#tracking-states) |
| `skeleton-undefined-state` | reject | [spec](../../docs/ds_protocol_v2_EN.md#tracking-states) |
| `skeleton-nan` | reject | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-retargeted) |
| `skeleton-inf` | reject | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-retargeted) |
| `skeleton--inf` | reject | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-retargeted) |
| `raw_skeleton-empty` | reject | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-raw) |
| `raw_skeleton-two-records` | reject | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-raw) |
| `raw_skeleton-id-64-utf8-bytes` | accept; 1 records | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-raw) |
| `raw_skeleton-id-65-utf8-bytes` | reject | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-raw) |
| `raw_skeleton-oversize-datagram` | reject | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-raw) |
| `raw_skeleton-state-1` | accept; 1 records | [spec](../../docs/ds_protocol_v2_EN.md#tracking-states) |
| `raw_skeleton-state-2` | accept; 1 records | [spec](../../docs/ds_protocol_v2_EN.md#tracking-states) |
| `raw_skeleton-undefined-state` | reject | [spec](../../docs/ds_protocol_v2_EN.md#tracking-states) |
| `raw_skeleton-nan` | reject | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-raw) |
| `raw_skeleton-inf` | reject | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-raw) |
| `raw_skeleton--inf` | reject | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-raw) |
| `skeleton-empty-uuid` | reject | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-retargeted) |
| `skeleton-non-ascii-uuid` | reject | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-retargeted) |
| `skeleton-bad-uuid-shape` | reject | [spec](../../docs/ds_protocol_v2_EN.md#hand-skeleton-retargeted) |
| `device-invalid-second-record-discards-all` | reject | [spec](../../docs/ds_protocol_v2_EN.md#device-information) |
| `device-battery` | reject | [spec](../../docs/ds_protocol_v2_EN.md#device-information) |
| `device-battery-negative` | reject | [spec](../../docs/ds_protocol_v2_EN.md#device-information) |
| `device-boolean` | reject | [spec](../../docs/ds_protocol_v2_EN.md#device-information) |
| `device-device-type` | reject | [spec](../../docs/ds_protocol_v2_EN.md#device-information) |
| `device-color` | reject | [spec](../../docs/ds_protocol_v2_EN.md#device-information) |
| `device-connection-state` | reject | [spec](../../docs/ds_protocol_v2_EN.md#device-information) |
| `device-power-boolean` | reject | [spec](../../docs/ds_protocol_v2_EN.md#device-information) |
| `device-battery-zero` | accept; 1 records | [spec](../../docs/ds_protocol_v2_EN.md#device-information) |
| `device-battery-full` | accept; 1 records | [spec](../../docs/ds_protocol_v2_EN.md#device-information) |
| `controller-button-out-of-range` | reject | [spec](../../docs/ds_protocol_v2_EN.md#controller-input) |
| `controller-trigger-out-of-range` | reject | [spec](../../docs/ds_protocol_v2_EN.md#controller-input) |
| `controller-axis-out-of-range` | reject | [spec](../../docs/ds_protocol_v2_EN.md#controller-input) |
| `controller-nan` | reject | [spec](../../docs/ds_protocol_v2_EN.md#controller-input) |
| `controller-inf` | reject | [spec](../../docs/ds_protocol_v2_EN.md#controller-input) |
| `controller-invalid-second-record-discards-all` | reject | [spec](../../docs/ds_protocol_v2_EN.md#controller-input) |
| `ergonomics-state-1` | accept; 1 records | [spec](../../docs/ds_protocol_v2_EN.md#tracking-states) |
| `ergonomics-state-2` | accept; 1 records | [spec](../../docs/ds_protocol_v2_EN.md#tracking-states) |
| `ergonomics-undefined-state` | reject | [spec](../../docs/ds_protocol_v2_EN.md#tracking-states) |
| `ergonomics-nan` | reject | [spec](../../docs/ds_protocol_v2_EN.md#records-and-validation) |
| `ergonomics-missing-second-record` | reject | [spec](../../docs/ds_protocol_v2_EN.md#records-and-validation) |
| `profile-utf8-byte-limits` | accept; 1 records | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information) |
| `profile-name-129-bytes` | reject | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information) |
| `profile-description-769-bytes` | reject | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information) |
| `profile-undefined-status` | reject | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information) |
| `profile-not-found` | accept; 1 records | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information) |
| `profile-not-found-must-have-empty-text` | reject | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information) |
| `profile-invalid-query` | accept; 1 records | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information) |
| `profile-invalid-query-must-have-empty-uuid` | reject | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information) |
| `raw-sensor-nonfinite-mock-policy` | reject | mock policy |

## Commands

| Case ID | Outcome | Source |
| --- | --- | --- |
| `profile-found` | profile | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information-request) |
| `profile-not-found-preserves-case` | profile | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information-request) |
| `profile-invalid-uuid-empty` | profile | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information-request) |
| `profile-invalid-uuid-shape` | profile | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information-request) |
| `profile-invalid-uuid-non-ascii` | profile | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information-request) |
| `profile-invalid-uuid-newline` | profile | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information-request) |
| `profile-wrong-version` | discard | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information-request) |
| `profile-wrong-request-id-type` | discard | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information-request) |
| `profile-wrong-uuid-type` | discard | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information-request) |
| `profile-short` | discard | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information-request) |
| `profile-long` | discard | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information-request) |
| `profile-unauthorized` | discard | [spec](../../docs/ds_protocol_v2_EN.md#retarget-profile-information-request) |
| `haptics-lower` | haptics | [spec](../../docs/ds_protocol_v2_EN.md#vibration) |
| `haptics-upper` | haptics | [spec](../../docs/ds_protocol_v2_EN.md#vibration) |
| `haptics-middle` | haptics | [spec](../../docs/ds_protocol_v2_EN.md#vibration) |
| `haptics-frequency-low` | discard | [spec](../../docs/ds_protocol_v2_EN.md#vibration) |
| `haptics-frequency-high` | discard | [spec](../../docs/ds_protocol_v2_EN.md#vibration) |
| `haptics-amplitude-low` | discard | [spec](../../docs/ds_protocol_v2_EN.md#vibration) |
| `haptics-amplitude-high` | discard | [spec](../../docs/ds_protocol_v2_EN.md#vibration) |
| `haptics-duration-low` | discard | [spec](../../docs/ds_protocol_v2_EN.md#vibration) |
| `haptics-duration-high` | discard | [spec](../../docs/ds_protocol_v2_EN.md#vibration) |
| `haptics-nan` | discard | [spec](../../docs/ds_protocol_v2_EN.md#vibration) |
| `haptics-inf` | discard | [spec](../../docs/ds_protocol_v2_EN.md#vibration) |
| `haptics-negative-inf` | discard | [spec](../../docs/ds_protocol_v2_EN.md#vibration) |
| `haptics-no-clamping` | discard | [spec](../../docs/ds_protocol_v2_EN.md#vibration) |
| `haptics-wrong-version` | discard | [spec](../../docs/ds_protocol_v2_EN.md#vibration) |
| `haptics-integer-frequency` | discard | [spec](../../docs/ds_protocol_v2_EN.md#vibration) |
| `haptics-missing-duration` | discard | [spec](../../docs/ds_protocol_v2_EN.md#vibration) |
| `haptics-unknown-device-mock-policy` | discard | [spec](../../docs/ds_protocol_v2_EN.md#vibration) |
| `haptics-unauthorized` | discard | [spec](../../docs/ds_protocol_v2_EN.md#vibration) |
| `connect-zero-port` | discard | [spec](../../docs/ds_protocol_v2_EN.md#connection-request) |
| `connect-negative-port` | discard | [spec](../../docs/ds_protocol_v2_EN.md#connection-request) |
| `connect-large-port` | discard | [spec](../../docs/ds_protocol_v2_EN.md#connection-request) |
| `connect-float-port` | discard | [spec](../../docs/ds_protocol_v2_EN.md#connection-request) |
| `connect-extra-port` | discard | [spec](../../docs/ds_protocol_v2_EN.md#connection-request) |
| `connect-missing-port` | discard | [spec](../../docs/ds_protocol_v2_EN.md#connection-request) |
| `removed-wrist` | discard | [spec](../../docs/ds_protocol_v2_EN.md#removed-protocols) |
| `removed-finger-haptics` | discard | [spec](../../docs/ds_protocol_v2_EN.md#removed-protocols) |
| `v1-unsupported` | discard | [spec](../../docs/ds_protocol_v2_EN.md#removed-protocols) |

## Virtual-time scenarios

| File | Purpose |
| --- | --- |
| [approval.json](scenarios/approval.json) | `virtual-approval-capacity-endpoint-replacement` |
| [delivery-faults.json](scenarios/delivery-faults.json) | `loss-duplicate-out-of-order-generation-time` |
| [expiry.json](scenarios/expiry.json) | `exact-expiry-and-rate-limit-policy` |
| [identity.json](scenarios/identity.json) | `same-receive-port-different-ip` |
| [sessions.json](scenarios/sessions.json) | `source-routing-keepalive-disconnect` |
