# SPDX-License-Identifier: Apache-2.0
"""Loopback UDP adapter for Station. Real timing belongs to integration/demo."""

import argparse
import json
from pathlib import Path
import socket
import time
from .core import Station
from .replay import stream_from

LIVE_HAPTICS_LIMIT = 1024


class UDPServer:
    def __init__(self, station=None, *, port=25791):
        self.station = station if station is not None else Station(haptics_limit=LIVE_HAPTICS_LIMIT)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.socket.bind(("127.0.0.1", port))
        except BaseException:
            self.socket.close()
            raise

    @property
    def address(self):
        return self.socket.getsockname()

    def close(self):
        self.socket.close()

    def _send(self, emissions):
        for emission in emissions:
            self.socket.sendto(emission.packet, emission.target)

    def poll(self, now_ms, *, timeout=0.0):
        """One bounded receive + virtual stream tick; useful for socket smoke tests."""
        self.socket.settimeout(timeout)
        outcome = None
        try:
            packet, source = self.socket.recvfrom(65535)
        except (socket.timeout, BlockingIOError):
            pass
        else:
            outcome, emissions = self.station.receive(packet, source, now_ms)
            self._send(emissions)
        self._send(self.station.advance(now_ms))
        return outcome

    def serve(self):
        start = time.monotonic_ns()
        while True:
            self.poll((time.monotonic_ns() - start) // 1_000_000, timeout=0.01)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=25791, help="0 selects a free loopback port")
    parser.add_argument("--stream", type=Path, help="JSON literal datagrams with relative millisecond offsets")
    args = parser.parse_args()
    stream = stream_from(json.loads(args.stream.read_text(encoding="utf-8"))) if args.stream else ()
    server = UDPServer(Station(stream=stream, haptics_limit=LIVE_HAPTICS_LIMIT), port=args.port)
    print(json.dumps({"listening": list(server.address), "mode": "literal replay"}), flush=True)
    try:
        server.serve()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()


if __name__ == "__main__":
    main()
