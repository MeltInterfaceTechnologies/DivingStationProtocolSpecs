#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Inject common shared implementation mistakes; static fixture tests must fail."""

import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ds_mock import protocol
from tests.test_fixtures import DeliveryFixtures, WireFixtures


def rejects(label, context, test):
    output = io.StringIO()
    with context:
        result = unittest.TextTestRunner(stream=output).run(test)
    if result.errors:
        raise SystemExit(f"unexpected test error for mutation: {label}\n{output.getvalue()}")
    if not result.failures or result.skipped or result.expectedFailures or result.unexpectedSuccesses:
        raise SystemExit(f"oracle missed mutation: {label}\n{output.getvalue()}")
    print(f"detected: {label}")


def swap_fields(kind, a, b):
    types, fields = protocol.LAYOUTS[kind]
    names = list(fields)
    i, j = names.index(a), names.index(b)
    names[i], names[j] = names[j], names[i]
    return patch.dict(protocol.LAYOUTS, {kind: (types, tuple(names))})


def main():
    rejects("signed timestamp low word used without unsigned mask",
            patch.object(protocol, "combine_timestamp", lambda hi, lo: (hi << 32) | lo),
            WireFixtures("test_timestamp_words"))
    # The same layout drives both parser and serializer. Their mutual roundtrip
    # would still pass after these swaps; the independent named/byte oracles fail.
    rejects("shared skeleton w/x component swap",
            swap_fields("HandSkeleton", "thumb_cmc_q_w", "thumb_cmc_q_x"),
            DeliveryFixtures("test_base_packets_and_named_values"))
    rejects("shared sensor w/x component swap",
            swap_fields("RawSensorTransforms", "thumb_sensor_q_w", "thumb_sensor_q_x"),
            DeliveryFixtures("test_base_packets_and_named_values"))
    rejects("shared skeleton node order swap",
            swap_fields("HandSkeletonRaw", "index_cmc_p_x", "index_mcp_p_x"),
            DeliveryFixtures("test_serializers_against_independent_packets"))
    rejects("shared ergonomics value order swap",
            swap_fields("Ergonomics", "thumb_ip", "thumb_tilt"),
            DeliveryFixtures("test_base_packets_and_named_values"))


if __name__ == "__main__":
    main()
