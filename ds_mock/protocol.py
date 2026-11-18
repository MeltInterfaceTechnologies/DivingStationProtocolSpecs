# SPDX-License-Identifier: Apache-2.0
"""Wire layouts and limited semantic inspection against the pinned v2 spec.

This module is an implementation under test, never the source of fixture
expectations. It does not implement biomechanics, IK or client cache policy.
"""

import math
import re
from .wire import Message, WireError, encode

PREFIX = "/DS2/HC/"
NODES = (
    "wrist", "thumb_cmc", "thumb_mcp", "thumb_ip", "thumb_tip",
    "index_cmc", "index_mcp", "index_pip", "index_dip", "index_tip",
    "middle_cmc", "middle_mcp", "middle_pip", "middle_dip", "middle_tip",
    "ring_cmc", "ring_mcp", "ring_pip", "ring_dip", "ring_tip",
    "little_cmc", "little_mcp", "little_pip", "little_dip", "little_tip",
)
ROTATIONS = tuple(n for n in NODES if n != "wrist" and not n.endswith("_tip"))
ERGONOMICS = (
    "thumb_cmc", "thumb_mcp", "thumb_ip", "thumb_tilt",
    "index_mcp", "index_pip", "index_dip", "index_tilt",
    "middle_mcp", "middle_pip", "middle_dip", "middle_tilt",
    "ring_mcp", "ring_pip", "ring_dip", "ring_tilt",
    "little_mcp", "little_pip", "little_dip", "little_tilt",
)
SENSORS = ("thumb_sensor", "index_sensor", "middle_sensor", "ring_sensor", "little_sensor")
_UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", re.ASCII)
LAYOUTS = {
    "Device": ("ssiiiiiisi", (
        "id", "pair_id", "battery_percentage", "is_haptics", "is_left", "device_type",
        "color", "connected_state", "name", "is_external_power_present")),
    "Ergonomics": ("siiii" + "f" * 20, (
        "id", "is_left", "generated_at_ms_hi", "generated_at_ms_lo", "tracking_state", *ERGONOMICS)),
    "Controller": ("s" + "i" * 7 + "f" * 7, (
        "id", "is_left", "a", "b", "sys", "trigger_button", "joystick_button", "trackpad_button",
        "trigger", "grip_value", "grip_force", "joystick_x", "joystick_y", "trackpad_x", "trackpad_y")),
    "RawSensorTransforms": ("siii" + "f" * 35, (
        "id", "is_left", "generated_at_ms_hi", "generated_at_ms_lo",
        *(f"{sensor}_{part}_{axis}" for sensor in SENSORS
          for part, axes in (("p", "xyz"), ("q", "wxyz")) for axis in axes))),
}
for _kind, _prefix_types, _prefix_names in (
    ("HandSkeleton", "ssiiii", ("id", "profile_uuid", "is_left", "generated_at_ms_hi", "generated_at_ms_lo", "tracking_state")),
    ("HandSkeletonRaw", "siiii", ("id", "is_left", "generated_at_ms_hi", "generated_at_ms_lo", "tracking_state")),
):
    LAYOUTS[_kind] = (_prefix_types + "f" * 151, (
        *_prefix_names, *(f"{n}_p_{a}" for n in NODES for a in "xyz"),
        *(f"{n}_q_{a}" for n in ROTATIONS for a in "wxyz")))


def is_uuid(value: str) -> bool:
    return _UUID.fullmatch(value) is not None


def timestamp_words(timestamp_ms: int) -> tuple[int, int]:
    if type(timestamp_ms) is not int or not 0 <= timestamp_ms < 2**64:
        raise ValueError("timestamp must be an unsigned 64-bit integer")
    def signed(n):
        return n if n < 2**31 else n - 2**32
    return signed(timestamp_ms >> 32), signed(timestamp_ms & 0xffffffff)


def combine_timestamp(hi: int, lo: int) -> int:
    return ((hi & 0xffffffff) << 32) | (lo & 0xffffffff)


def _valid_record(kind: str, record: dict) -> bool:
    if any(type(v) is float and not math.isfinite(v) for v in record.values()):
        return False
    for key in ("is_left", "is_haptics", "is_external_power_present"):
        if key in record and record[key] not in (0, 1):
            return False
    if "tracking_state" in record and record["tracking_state"] not in (0, 1, 2):
        return False
    if kind == "Device":
        return (record["battery_percentage"] in range(-1, 101)
                and record["device_type"] == 3 and record["color"] in range(8)
                and record["connected_state"] in range(4))
    if kind == "Controller":
        return (all(record[k] in (0, 1, 2) for k in (
            "a", "b", "sys", "trigger_button", "joystick_button", "trackpad_button"))
            and all(0.0 <= record[k] <= 1.0 for k in ("trigger", "grip_value", "grip_force"))
            and all(-1.0 <= record[k] <= 1.0 for k in (
                "joystick_x", "joystick_y", "trackpad_x", "trackpad_y")))
    if kind in ("HandSkeleton", "HandSkeletonRaw"):
        return (len(record["id"].encode("utf-8")) <= 64
                and (kind != "HandSkeleton" or is_uuid(record["profile_uuid"])))
    return True


def inspect(message: Message) -> dict:
    """Return accept/ignore/reject/unsupported with named, whole-message records.

    Unknown versions are ignored. No partial records, default filling, stale
    frame filtering or cross-address state merging takes place here.
    """
    kind = message.address.removeprefix(PREFIX)
    if not message.address.startswith(PREFIX) or kind not in (*LAYOUTS, "HandSkeleton/Profile"):
        return {"verdict": "unsupported"}
    if not message.args or not message.types.startswith("i"):
        return {"verdict": "reject"}
    if message.args[0] != 2:
        return {"verdict": "ignore"}
    try:
        packet = encode(message)  # checks Python values against explicit wire tags
    except (WireError, UnicodeError):
        return {"verdict": "reject"}
    if kind == "HandSkeleton/Profile":
        if message.types != "iisiss":
            return {"verdict": "reject"}
        version, request, uuid, status, name, description = message.args
        valid = (len(name.encode("utf-8")) <= 128 and len(description.encode("utf-8")) <= 768)
        valid &= ((status == 0 and is_uuid(uuid))
                  or (status == 1 and is_uuid(uuid) and name == description == "")
                  or (status == 2 and uuid == name == description == ""))
        if not valid:
            return {"verdict": "reject"}
        return {"verdict": "accept", "records": [{"request_id": request, "profile_uuid": uuid,
                "status": status, "name": name, "description": description}]}
    types, names = LAYOUTS[kind]
    width = len(types)
    count, remainder = divmod(len(message.args) - 1, width)
    if (remainder or message.types != "i" + types * count or count > 8
            or (kind in ("HandSkeleton", "HandSkeletonRaw") and (count != 1 or len(packet) > 1200))):
        return {"verdict": "reject"}
    records = []
    for start in range(1, len(message.args), width):
        record = dict(zip(names, message.args[start:start + width]))
        if not _valid_record(kind, record):
            return {"verdict": "reject"}
        if "generated_at_ms_hi" in record:
            record["generated_at_ms"] = combine_timestamp(record["generated_at_ms_hi"], record["generated_at_ms_lo"])
        if "tracking_state" in record:
            record["usable_for_control"] = record["tracking_state"] == 0
        records.append(record)
    return {"verdict": "accept", "records": records}


def delivery(kind: str, records: list[dict]) -> Message:
    """Serialize complete named records; missing fields raise, never default."""
    types, fields = LAYOUTS[kind]
    message = Message(PREFIX + kind, "i" + types * len(records),
                      (2, *(record[field] for record in records for field in fields)))
    if inspect(message)["verdict"] != "accept":
        raise ValueError("invalid delivery record/message")
    return message
