# SPDX-License-Identifier: Apache-2.0
"""Pure session/command/replay engine. Every operation receives virtual time.

The engine never reads fixtures or expected results. Test-only approval and
publish hooks allow LAN/session and malformed-delivery cases without LAN I/O.
"""

from dataclasses import dataclass
import ipaddress
import math
import re
from .protocol import PREFIX, is_uuid
from .wire import Message, WireError, decode, encode

LEFT_PROFILE = "00000000-0000-4000-8000-000000000001"
RIGHT_PROFILE = "00000000-0000-4000-8000-000000000002"
PROFILES = {
    LEFT_PROFILE: ("Mock left", "Synthetic left profile; no retargeting."),
    RIGHT_PROFILE: ("Mock right", "Synthetic right profile; no retargeting."),
}
DEVICES = ("MOCK-L", "MOCK-R")
_HAPTICS = re.compile(r"/DS2/HC/([^/]+)/Haptics/Body", re.ASCII)


@dataclass(frozen=True)
class Emission:
    target: tuple[str, int]
    packet: bytes


@dataclass
class Session:
    source: tuple[str, int]
    receive_port: int
    last_connect_ms: int
    approved: bool
    stream_start_ms: int | None
    cursor: int = 0

    @property
    def target(self):
        return self.source[0], self.receive_port


class Station:
    """Bounded authorized sessions, source routing and literal scheduled packets.

    max_clients=8 and ignoring sub-second Connect retries are mock policies;
    the spec gives no numeric client cap or required server rate-limit response.
    Session expiration is enforced at elapsed >= 90,000 ms, including pending
    sessions. New source endpoints replace a session with the same IP/recv port.
    Haptics history is complete by default for offline transcripts. Live adapters
    can retain only the newest haptics_limit records, without rejecting commands.
    """

    def __init__(self, *, require_approval=False, max_clients=8, stream=(), haptics_limit=None):
        if type(max_clients) is not int or max_clients < 1:
            raise ValueError("max_clients must be a positive integer")
        if type(require_approval) is not bool:
            raise ValueError("require_approval must be boolean")
        if haptics_limit is not None and (type(haptics_limit) is not int or haptics_limit < 1):
            raise ValueError("haptics_limit must be a positive integer or None")
        self.haptics_limit = haptics_limit
        self.require_approval = require_approval
        self.max_clients = max_clients
        self.stream = tuple(stream)
        previous = -1
        for at_ms, packet in self.stream:
            if type(at_ms) is not int or at_ms < 0 or at_ms < previous or type(packet) is not bytes:
                raise ValueError("stream offsets must be ordered nonnegative integer milliseconds")
            previous = at_ms
        self.sessions = {}
        self.haptics = []
        self.now_ms = -1

    def _advance_clock(self, now_ms):
        if type(now_ms) is not int or now_ms < 0 or now_ms < self.now_ms:
            raise ValueError("virtual clock must be a nondecreasing nonnegative integer")
        self.now_ms = now_ms
        self.sessions = {key: session for key, session in self.sessions.items()
                         if now_ms - session.last_connect_ms < 90_000}

    @staticmethod
    def _source(source):
        ip, port = source
        ipaddress.IPv4Address(ip)
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("invalid source port")
        return ip, port

    def _authorized(self, source):
        return [s for s in self.sessions.values() if s.source == source and s.approved]

    def receive(self, packet: bytes, source: tuple[str, int], now_ms: int):
        """Return (outcome, emissions); malformed input is discarded atomically."""
        self._advance_clock(now_ms)
        source = self._source(source)
        try:
            message = decode(packet)
        except WireError:
            return "discard", []
        address, types, args = message.address, message.types, message.args
        if address in (PREFIX + "Connect", PREFIX + "Disconnect"):
            if types != "i" or not 1 <= args[0] <= 65535:
                return "discard", []
            port = args[0]
            key = source[0], port
            current = self.sessions.get(key)
            if address.endswith("Disconnect"):
                if not current or current.source != source or not current.approved:
                    return "discard", []
                del self.sessions[key]
                return "disconnected", []
            if current and now_ms - current.last_connect_ms < 1000:
                return "rate_limited", []
            if current and current.source == source:
                current.last_connect_ms = now_ms
                return ("connected" if current.approved else "pending"), []
            # The receive identity is (IP, port_recv); authority also binds the
            # source UDP port. Replacing the endpoint requires fresh approval.
            if not current and len(self.sessions) >= self.max_clients:
                return "capacity", []
            approved = not self.require_approval
            self.sessions[key] = Session(source, port, now_ms, approved,
                                         now_ms if approved else None)
            return ("connected" if approved else "pending"), []
        sessions = self._authorized(source)
        if not sessions:
            return "discard", []
        if address == PREFIX + "HandSkeleton/Profile/Get":
            if types != "iis" or args[0] != 2:
                return "discard", []
            _, request, uuid = args
            stored_uuid = uuid.lower()
            if not is_uuid(uuid):
                uuid, status, name, description = "", 2, "", ""
            elif stored_uuid in PROFILES:
                uuid, status = stored_uuid, 0
                name, description = PROFILES[stored_uuid]
            else:
                status, name, description = 1, "", ""
            response = encode(Message(PREFIX + "HandSkeleton/Profile", "iisiss",
                                      (2, request, uuid, status, name, description)))
            return "profile", [Emission(s.target, response) for s in sessions]
        match = _HAPTICS.fullmatch(address)
        if match:
            if types != "ifff" or args[0] != 2 or match[1] not in DEVICES:
                return "discard", []
            _, frequency, amplitude, duration = args
            if not (all(math.isfinite(v) for v in (frequency, amplitude, duration))
                    and 100.0 <= frequency <= 500.0 and 0.0 <= amplitude <= 1.0
                    # The wire contains float32(0.001), not Python's float64 literal.
                    and 0.001 <= duration <= 1.0):
                return "discard", []
            self.haptics.append({"at_ms": now_ms, "source": list(source), "id": match[1],
                                 "frequency": frequency, "amplitude": amplitude, "duration": duration})
            if self.haptics_limit is not None:
                del self.haptics[:-self.haptics_limit]
            return "haptics", []
        return "discard", []

    def approve(self, source, receive_port, now_ms):
        """Virtual approval hook; never exposed as a network OSC command."""
        self._advance_clock(now_ms)
        source = self._source(source)
        session = self.sessions.get((source[0], receive_port))
        if not session or session.source != source:
            return "discard", []
        if not session.approved:
            session.approved = True
            session.stream_start_ms = now_ms
        return "approved", []

    def publish(self, packet: bytes, now_ms: int):
        """Fault-injection hook: send literal bytes, including malformed data."""
        self._advance_clock(now_ms)
        return [Emission(s.target, packet) for _, s in sorted(self.sessions.items()) if s.approved]

    def advance(self, now_ms: int):
        self._advance_clock(now_ms)
        emissions = []
        for _, session in sorted(self.sessions.items()):
            if not session.approved:
                continue
            while session.cursor < len(self.stream):
                offset, packet = self.stream[session.cursor]
                if now_ms - session.stream_start_ms < offset:
                    break
                emissions.append(Emission(session.target, packet))
                session.cursor += 1
        return emissions

    def state(self):
        return [{"source": list(s.source), "receive_port": s.receive_port,
                 "approved": s.approved, "last_connect_ms": s.last_connect_ms}
                for _, s in sorted(self.sessions.items())]
