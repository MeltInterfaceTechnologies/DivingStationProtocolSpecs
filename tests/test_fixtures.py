# SPDX-License-Identifier: Apache-2.0
"""Static oracles: no fixture regeneration, network or wall-clock dependencies."""

import copy
import json
import struct
from pathlib import Path
import unittest

from ds_mock import protocol
from ds_mock.core import Station
from ds_mock.replay import describe, packet_from, run
from ds_mock.wire import Message, WireError, decode, encode

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "v2"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def case_message(base, change):
    """Input-only fixture notation; expected values are never expanded from it."""
    message = copy.deepcopy(base)
    types, args = message["types"], message["args"]
    if "repeat_records" in change:
        count = change["repeat_records"]
        types, args = types[:1] + types[1:] * count, args[:1] + args[1:] * count
    types = list(types)
    for key, value in change.get("set_args", {}).items():
        args[int(key)] = value
    for index in sorted(change.get("drop_args", []), reverse=True):
        del args[index]
        del types[index]
    for index, tag in change.get("replace_types", {}).items():
        types[int(index)] = tag
    return {"address": message["address"], "types": "".join(types), "args": args}


class WireFixtures(unittest.TestCase):
    def test_golden_packets(self):
        for case in load("wire.json")["valid"]:
            with self.subTest(case=case["id"]):
                packet = bytes.fromhex(case["packet_hex"])
                expected = case["message"]
                self.assertEqual(packet_from({"message": expected}), packet)
                self.assertEqual(decode(packet), Message(expected["address"], expected["types"], tuple(expected["args"])))

    def test_malformed_packets(self):
        for case in load("wire.json")["invalid"]:
            with self.subTest(case=case["id"]), self.assertRaises(WireError):
                decode(bytes.fromhex(case["packet_hex"]))

    def test_timestamp_words(self):
        for case in load("wire.json")["timestamps"]:
            with self.subTest(ms=case["ms"]):
                self.assertEqual(protocol.timestamp_words(case["ms"]), (case["hi"], case["lo"]))
                self.assertEqual(protocol.combine_timestamp(case["hi"], case["lo"]), case["ms"])

    def test_encoder_type_and_bounds(self):
        for message in (Message("/t", "i", (True,)), Message("/t", "i", (2**31,)),
                        Message("/t", "f", (1,)), Message("/t", "f", (1e100,)),
                        Message("/t", "s", ("a\0b",)), Message("/t", "x", (1,)),
                        Message("/t", "ii", (1,))):
            with self.subTest(message=message), self.assertRaises(WireError):
                encode(message)
        for ms in (-1, 2**64, 1.0, True):
            with self.subTest(timestamp=ms), self.assertRaises(ValueError):
                protocol.timestamp_words(ms)


class DeliveryFixtures(unittest.TestCase):
    def test_specification_orders(self):
        orders = load("delivery.json")["layouts"]
        for actual, name in ((protocol.NODES, "nodes"), (protocol.ROTATIONS, "rotations"),
                             (protocol.ERGONOMICS, "ergonomics"), (protocol.SENSORS, "sensors")):
            self.assertEqual(list(actual), orders[name])

    def test_base_packets_and_named_values(self):
        for name, base in load("delivery.json")["bases"].items():
            with self.subTest(base=name):
                packet = bytes.fromhex(base["packet_hex"])
                self.assertEqual(packet_from({"message": base["message"]}), packet)
                self.assertEqual(protocol.inspect(decode(packet)), base["mock_expectation"])

    def test_serializers_against_independent_packets(self):
        for name, base in load("delivery.json")["bases"].items():
            kind = base["message"]["address"].removeprefix("/DS2/HC/")
            if kind not in protocol.LAYOUTS:
                continue
            with self.subTest(base=name):
                self.assertEqual(encode(protocol.delivery(kind, base["mock_expectation"]["records"])),
                                 bytes.fromhex(base["packet_hex"]))

    def test_normal_and_invalid_cases(self):
        data = load("delivery.json")
        for case in data["cases"]:
            with self.subTest(case=case["id"]):
                packet = packet_from({"message": case_message(data["bases"][case["base"]]["message"], case["input"])})
                actual = protocol.inspect(decode(packet))
                expected = case["mock_expectation"]
                self.assertEqual(actual["verdict"], expected["verdict"])
                self.assertEqual(actual, protocol.inspect(decode(packet)))
                if expected["verdict"] == "accept":
                    self.assertEqual(len(actual["records"]), expected["record_count"])
                    for record, fields in zip(actual["records"], expected.get("fields", [])):
                        for key, value in fields.items():
                            self.assertEqual(record[key], value)
                else:
                    self.assertNotIn("records", actual)  # no partially accepted message

    def test_normal_quaternions_have_independent_unit_design(self):
        data = load("delivery.json")
        for name, count in (("skeleton", 19), ("raw_skeleton", 19), ("sensors", 5)):
            base = data["bases"][name]
            design = base["quaternion_design"]
            self.assertEqual(design["component_order"], list("wxyz"))
            self.assertEqual(design["denominator"], 11)
            self.assertEqual(len(design["numerators"]), count)
            self.assertEqual(len({tuple(q) for q in design["numerators"]}), count)
            members = data["layouts"]["sensors" if name == "sensors" else "rotations"]
            record = base["mock_expectation"]["records"][0]
            for index, (member, numerators) in enumerate(zip(members, design["numerators"])):
                with self.subTest(base=name, member=member):
                    self.assertEqual(sorted(abs(n) for n in numerators), [1, 2, 4, 10])
                    self.assertEqual(sum(n * n for n in numerators), 11 * 11)
                    expected = [struct.unpack(">f", struct.pack(">f", n / 11))[0] for n in numerators]
                    self.assertEqual(len(set(expected)), 4)
                    self.assertAlmostEqual(sum(v * v for v in expected), 1.0, places=6)
                    prefix = member
                    self.assertEqual([record[prefix + "_q_" + axis] for axis in "wxyz"], expected)
                    start = (8 + index * 7) if name == "sensors" else (82 if name == "skeleton" else 81) + index * 4
                    self.assertEqual(base["message"]["args"][start:start + 4], expected)

    def test_layout_sentinels_are_separate_static_oracles(self):
        data = load("layout-sentinels.json")
        self.assertEqual(data["purpose"], "wire-layout-only")
        self.assertEqual(data["sdk_assertions"], "unspecified")
        self.assertEqual(set(data["bases"]), {"skeleton", "raw_skeleton", "sensors"})
        for name, base in data["bases"].items():
            with self.subTest(base=name):
                packet = bytes.fromhex(base["packet_hex"])
                self.assertEqual(packet_from({"message": base["message"]}), packet)
                self.assertEqual(protocol.inspect(decode(packet)), base["mock_expectation"])
                kind = base["message"]["address"].removeprefix("/DS2/HC/")
                self.assertEqual(encode(protocol.delivery(kind, base["mock_expectation"]["records"])), packet)
                if name != "sensors":
                    q = base["message"]["args"][82 if name == "skeleton" else 81:86 if name == "skeleton" else 85]
                    self.assertGreater(abs(sum(v * v for v in q) - 1), 0.01)

    def test_mock_verdicts_do_not_define_sdk_acceptance(self):
        data = load("delivery.json")
        self.assertEqual(data["schema_version"], 2)
        self.assertEqual(data["expectation_target"], "ds_mock.protocol.inspect")
        self.assertEqual(data["normative_validation"], {
            "spec": "ds_protocol_v2_EN.md#records-and-validation",
            "invalid_record_action": "discard-entire-message", "corpus_exceptions": []})
        self.assertEqual(data["boundary_interpretation"], "unresolved-by-this-corpus")
        self.assertEqual(data["sdk_assertions"],
                         "not assigned by this corpus; normative obligations remain unchanged")
        for row in list(data["bases"].values()) + data["cases"]:
            self.assertNotIn("expected", row)
            self.assertIn("mock_expectation", row)
            self.assertIn("spec", row)
            self.assertIn("purpose", row)
        boundaries = [c for c in data["cases"] if "id-65-utf8-bytes" in c["id"]]
        self.assertEqual(len(boundaries), 2)
        for case in boundaries:
            self.assertEqual(case["sdk_assertions"], "unspecified")
            self.assertEqual(case["spec_scope"], "limit-boundary; SDK conformance interpretation unresolved by this corpus; whole-message discard rule unchanged")

    def test_normal_stream_contains_all_six_data_inputs(self):
        bases = load("delivery.json")["bases"]
        stream = load("normal-stream.json")
        names = ("device", "ergonomics", "controller", "skeleton", "raw_skeleton", "sensors")
        self.assertEqual(len(stream), len(names))
        for item, name in zip(stream, names):
            self.assertEqual(item["at_ms"], 0)
            self.assertEqual(item["message"], bases[name]["message"])

    def test_missing_values_never_default(self):
        for kind in ("HandSkeleton", "HandSkeletonRaw", "Ergonomics"):
            with self.subTest(kind=kind), self.assertRaises(KeyError):
                protocol.delivery(kind, [{"id": "L"}])

    def test_skeleton_sizes_and_utf8_bytes(self):
        data = load("delivery.json")
        for base_name, argc in (("skeleton", 158), ("raw_skeleton", 157)):
            message = case_message(data["bases"][base_name]["message"], {"set_args": {"1": "é" * 32}})
            packet = packet_from({"message": message})
            self.assertEqual(len(decode(packet).args), argc)
            self.assertLessEqual(len(packet), 1200)
            self.assertEqual(protocol.inspect(decode(packet))["verdict"], "accept")

    def test_unknown_addresses_are_unsupported(self):
        for address in ("/DS/HC/Hand", "/DS2/HC/Wrist", "/DS2/HC/HandQuat", "/unknown"):
            self.assertEqual(protocol.inspect(Message(address, "i", (2,))), {"verdict": "unsupported"})


class CommandFixtures(unittest.TestCase):
    def test_commands(self):
        for case in load("commands.json")["cases"]:
            with self.subTest(case=case["id"]):
                station = Station()
                source = ("127.0.0.1", 41000)
                if case.get("connected", True):
                    station.receive(packet_from({"message": {"address": "/DS2/HC/Connect", "types": "i", "args": [42000]}}), source, 0)
                outcome, emissions = station.receive(packet_from(case), source, 1000)
                self.assertEqual({"outcome": outcome, "emissions": describe(emissions), "haptics": station.haptics}, case["expected"])

    def test_malformed_commands_do_not_mutate_session(self):
        for case in load("wire.json")["invalid"]:
            station = Station()
            outcome, emissions = station.receive(bytes.fromhex(case["packet_hex"]), ("127.0.0.1", 41000), 0)
            self.assertEqual((outcome, emissions, station.state(), station.haptics), ("discard", [], [], []))


class VirtualScenarios(unittest.TestCase):
    def test_scenarios_are_repeatable(self):
        paths = sorted((FIXTURES / "scenarios").glob("*.json"))
        self.assertEqual(len(paths), 5)
        for path in paths:
            data = json.loads(path.read_text(encoding="utf-8"))
            with self.subTest(scenario=data["id"]):
                self.assertEqual(run(data), data["expected"])
                self.assertEqual(run(data), data["expected"])

    def test_loss_order_time_and_control_eligibility(self):
        data = load("scenarios/delivery-faults.json")
        actual = run(data)
        observations = []
        for step in actual:
            for emission in step["emissions"]:
                try:
                    result = protocol.inspect(decode(packet_from(emission)))
                except WireError:
                    result = {"verdict": "malformed"}
                if result["verdict"] == "accept":
                    record = result["records"][0]
                    result = {"verdict": "accept", "generated_at_ms": record["generated_at_ms"],
                              "usable_for_control": record["usable_for_control"]}
                observations.append(result)
        self.assertEqual(observations, data["delivery_expectations"])
        self.assertEqual(actual[2]["emissions"], [])  # lost frame at 10ms remains absent

    def test_keepalive_does_not_restart_stream(self):
        packet = bytes.fromhex("2f7400002c000000")
        station = Station(stream=[(0, packet), (30000, packet)])
        connect = packet_from({"message": {"address": "/DS2/HC/Connect", "types": "i", "args": [42000]}})
        station.receive(connect, ("127.0.0.1", 41000), 0)
        self.assertEqual(len(station.advance(0)), 1)
        station.receive(connect, ("127.0.0.1", 41000), 30000)
        self.assertEqual(len(station.advance(30000)), 1)
        self.assertEqual(station.advance(30000), [])

    def test_stream_waits_for_approval_and_stops_on_expiry(self):
        station = Station(require_approval=True, stream=[(0, b"test"), (90000, b"late")])
        connect = packet_from({"message": {"address": "/DS2/HC/Connect", "types": "i", "args": [42000]}})
        source = ("127.0.0.1", 41000)
        station.receive(connect, source, 0)
        self.assertEqual(station.advance(100), [])
        station.approve(source, 42000, 100)
        self.assertEqual([e.packet for e in station.advance(100)], [b"test"])
        self.assertEqual(station.advance(90000), [])

    def test_rejects_backward_virtual_clock_and_bad_schedule(self):
        station = Station()
        station.advance(5)
        with self.assertRaises(ValueError):
            station.advance(4)
        for stream in ([(1, b"test"), (0, b"test")], [(-1, b"test")], [(1.0, b"test")]):
            with self.subTest(stream=stream), self.assertRaises(ValueError):
                Station(stream=stream)

    def test_nonfinite_faults_have_portable_json_output(self):
        data = {"steps": [
            {"at_ms": 0, "op": "receive", "source": ["127.0.0.1", 41000],
             "message": {"address": "/DS2/HC/Connect", "types": "i", "args": [42000]}},
            {"at_ms": 0, "op": "publish", "packet_hex": "2f7400002c6600007fc00000"}]}
        actual = run(data)[1]["emissions"][0]
        self.assertEqual(actual, {"target": ["127.0.0.1", 42000],
                         "message": {"address": "/t", "types": "f", "args": [{"float": "nan"}]}})
        json.dumps(actual, allow_nan=False)

    def test_expected_values_do_not_drive_replay(self):
        data = load("scenarios/expiry.json")
        expected = run(data)
        data["expected"] = ["deliberately wrong oracle"]
        self.assertEqual(run(data), expected)


if __name__ == "__main__":
    unittest.main()
