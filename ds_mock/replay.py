# SPDX-License-Identifier: Apache-2.0
"""Offline JSON replay. No sockets, wall clock, randomness, or fixture writes."""

import argparse
import json
import math
from pathlib import Path
from .core import Station
from .wire import Message, WireError, decode, encode


def packet_from(item):
    """Literal hex or explicit tags/values; never infer types or expected data."""
    if "packet_hex" in item:
        return bytes.fromhex(item["packet_hex"])
    message = item["message"]
    args = tuple(float(v["float"]) if isinstance(v, dict) and set(v) == {"float"} else v
                 for v in message["args"])
    return encode(Message(message["address"], message["types"], args))


def stream_from(items):
    return [(item["at_ms"], packet_from(item)) for item in items]


def describe(emissions):
    result = []
    for emission in emissions:
        item = {"target": list(emission.target)}
        try:
            message = decode(emission.packet)
            item["message"] = {"address": message.address, "types": message.types, "args": [
                {"float": "nan" if math.isnan(v) else "inf" if v > 0 else "-inf"}
                if type(v) is float and not math.isfinite(v) else v for v in message.args]}
        except WireError:
            item["packet_hex"] = emission.packet.hex()
        result.append(item)
    return result


def run(scenario):
    # Deliberately does not read scenario["expected"]. Tests own the oracle.
    config = scenario.get("config", {})
    if "haptics_limit" in config:
        raise ValueError("offline replay requires complete haptics history; haptics_limit is not supported")
    station = Station(**config, stream=stream_from(scenario.get("stream", [])))
    transcript = []
    for step in scenario["steps"]:
        at_ms, operation = step["at_ms"], step["op"]
        if operation == "receive":
            outcome, emissions = station.receive(packet_from(step), tuple(step["source"]), at_ms)
        elif operation == "approve":
            outcome, emissions = station.approve(tuple(step["source"]), step["receive_port"], at_ms)
        elif operation == "advance":
            outcome, emissions = "advanced", station.advance(at_ms)
        elif operation == "publish":
            outcome, emissions = "published", station.publish(packet_from(step), at_ms)
        else:
            raise ValueError(f"unknown replay operation: {operation}")
        transcript.append({"at_ms": at_ms, "outcome": outcome, "emissions": describe(emissions),
                           "sessions": station.state(), "haptics": list(station.haptics)})
    return transcript


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(json.loads(args.scenario.read_text(encoding="utf-8"))),
                     ensure_ascii=False, allow_nan=False, indent=2))


if __name__ == "__main__":
    main()
