# SPDX-License-Identifier: Apache-2.0
"""OSC flat-message subset: explicit int32, float32 and UTF-8 string tags.

DSProtocol extends OSC 1.0's ASCII string description to UTF-8. Bundles,
address patterns and all other OSC tags are deliberately outside this peer.
"""

from dataclasses import dataclass
import struct


class WireError(ValueError):
    """Malformed or unsupported OSC packet."""


@dataclass(frozen=True)
class Message:
    address: str
    types: str
    args: tuple


def _string(value: str) -> bytes:
    if type(value) is not str or "\0" in value:
        raise WireError("OSC strings must be strings without NUL")
    try:
        raw = value.encode("utf-8") + b"\0"
    except UnicodeError as exc:
        raise WireError("invalid UTF-8 string") from exc
    return raw + b"\0" * (-len(raw) % 4)


def encode(message: Message) -> bytes:
    if not message.address.startswith("/"):
        raise WireError("flat OSC address required")
    if len(message.types) != len(message.args):
        raise WireError("argument/tag count mismatch")
    parts = [_string(message.address), _string("," + message.types)]
    for tag, value in zip(message.types, message.args):
        try:
            if tag == "i" and type(value) is int:
                parts.append(struct.pack(">i", value))
            elif tag == "f" and type(value) is float:
                parts.append(struct.pack(">f", value))
            elif tag == "s":
                parts.append(_string(value))
            else:
                raise WireError("unsupported tag or mismatched Python type")
        except (struct.error, OverflowError) as exc:
            raise WireError("number does not fit OSC 32-bit value") from exc
    return b"".join(parts)


def decode(packet: bytes) -> Message:
    if not packet or len(packet) % 4:
        raise WireError("OSC packet size must be a nonzero multiple of four")
    offset = 0

    def string() -> str:
        nonlocal offset
        end = packet.find(b"\0", offset)
        if end < 0:
            raise WireError("unterminated OSC string")
        next_offset = (end + 4) & ~3
        if next_offset > len(packet) or any(packet[end:next_offset]):
            raise WireError("invalid OSC string padding")
        try:
            result = packet[offset:end].decode("utf-8")
        except UnicodeError as exc:
            raise WireError("invalid UTF-8") from exc
        offset = next_offset
        return result

    address = string()
    if not address.startswith("/"):
        raise WireError("bundles and non-address packets are unsupported")
    types = string()
    if not types.startswith(","):
        raise WireError("explicit OSC type tags required")
    args = []
    for tag in types[1:]:
        if tag == "s":
            args.append(string())
        elif tag in "if":
            if offset + 4 > len(packet):
                raise WireError("truncated OSC argument")
            args.append(struct.unpack_from(">" + tag, packet, offset)[0])
            offset += 4
        else:
            raise WireError("unsupported OSC type tag")
    if offset != len(packet):
        raise WireError("trailing bytes")
    return Message(address, types[1:], tuple(args))
