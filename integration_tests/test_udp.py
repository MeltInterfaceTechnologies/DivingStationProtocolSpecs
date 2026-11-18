# SPDX-License-Identifier: Apache-2.0
"""Bounded loopback transport smoke tests, separate from virtual conformance."""

import json
from pathlib import Path
import socket
import struct
import unittest
from ds_mock.core import Station
from ds_mock.server import LIVE_HAPTICS_LIMIT, UDPServer


def osc_string(value):
    raw = value.encode("utf-8") + b"\0"
    return raw + b"\0" * (-len(raw) % 4)


def packet(message):
    # Independent test client encoder, never imports the mock's codec.
    result = osc_string(message["address"]) + osc_string("," + message["types"])
    for tag, value in zip(message["types"], message["args"]):
        result += osc_string(value) if tag == "s" else struct.pack(">" + tag, value)
    return result


def message(address, types, args):
    return {"address": "/DS2/HC/" + address, "types": types, "args": args}


class LoopbackTests(unittest.TestCase):
    def setUp(self):
        self.server = UDPServer(port=0)
        self.addCleanup(self.server.close)
        self.a, self.b, self.recv_a, self.recv_b = [self.udp() for _ in range(4)]

    def udp(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("127.0.0.1", 0))
        sock.settimeout(1.0)
        self.addCleanup(sock.close)
        return sock

    def send(self, sock, msg, at_ms):
        sock.sendto(packet(msg), self.server.address)
        return self.server.poll(at_ms, timeout=1.0)

    def test_source_routing_disconnect_and_malformed_recovery(self):
        port_a, port_b = self.recv_a.getsockname()[1], self.recv_b.getsockname()[1]
        self.assertEqual(self.send(self.a, message("Connect", "i", [port_a]), 0), "connected")
        self.assertEqual(self.send(self.b, message("Connect", "i", [port_b]), 0), "connected")
        cases = json.loads((Path(__file__).resolve().parents[1] / "fixtures/v2/commands.json").read_text())
        case = next(c for c in cases["cases"] if c["id"] == "profile-found")
        self.assertEqual(self.send(self.a, case["message"], 10), "profile")
        self.assertEqual(self.recv_a.recv(4096), packet(case["expected"]["emissions"][0]["message"]))
        self.recv_b.settimeout(0.05)
        with self.assertRaises(socket.timeout):
            self.recv_b.recv(4096)
        # A different sending socket cannot use the existing authority.
        self.assertEqual(self.send(self.b, message("Disconnect", "i", [port_a]), 20), "discard")
        self.a.sendto(b"bad!", self.server.address)
        self.assertEqual(self.server.poll(30, timeout=1.0), "discard")
        self.assertEqual(self.send(self.a, message("Disconnect", "i", [port_a]), 40), "disconnected")
        self.assertEqual(self.send(self.a, case["message"], 50), "discard")
        self.assertEqual(self.send(self.b, case["message"], 60), "profile")
        self.assertEqual(self.recv_b.recv(4096), packet(case["expected"]["emissions"][0]["message"]))

    def test_default_live_history_is_bounded(self):
        self.assertEqual(self.server.station.haptics_limit, LIVE_HAPTICS_LIMIT)
        port_a = self.recv_a.getsockname()[1]
        self.assertEqual(self.send(self.a, message("Connect", "i", [port_a]), 0), "connected")
        for now_ms in range(1, LIVE_HAPTICS_LIMIT + 2):
            self.assertEqual(self.send(self.a, message("MOCK-L/Haptics/Body", "ifff", [2, 250.0, 0.5, 0.25]), now_ms), "haptics")
        history = self.server.station.haptics
        self.assertEqual(len(history), LIVE_HAPTICS_LIMIT)
        self.assertEqual(history[0]["at_ms"], 2)
        self.assertEqual(history[-1]["at_ms"], LIVE_HAPTICS_LIMIT + 1)

    def test_literal_stream_bytes_are_not_reencoded(self):
        stream = [(0, b"bad!"), (20, bytes.fromhex("2f7400002c000000"))]
        self.server.station = Station(stream=stream)
        port_a = self.recv_a.getsockname()[1]
        self.assertEqual(self.send(self.a, message("Connect", "i", [port_a]), 0), "connected")
        self.assertEqual(self.recv_a.recv(4096), b"bad!")
        self.assertIsNone(self.server.poll(20))
        self.assertEqual(self.recv_a.recv(4096), bytes.fromhex("2f7400002c000000"))


if __name__ == "__main__":
    unittest.main()
