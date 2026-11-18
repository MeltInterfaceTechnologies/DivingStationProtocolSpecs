# SPDX-License-Identifier: Apache-2.0
"""Illustrative wall-clock demo; never used to create fixture expectations."""

import argparse
import json
import math
import time
from .core import DEVICES, LEFT_PROFILE, RIGHT_PROFILE
from .protocol import ERGONOMICS, NODES, ROTATIONS, SENSORS, delivery, timestamp_words
from .server import UDPServer
from .wire import encode


def frame(timestamp_ms, phase):
    """Complete synthetic values in metres, degrees and parent-local wxyz.

    This is a numerical illustration, not measured data, IK, calibration or
    retargeting. Raw and retargeted skeletons intentionally share the pose.
    """
    hi, lo = timestamp_words(timestamp_ms)
    devices, ergonomics, controllers, sensors, skeletons = [], [], [], [], []
    flex = (math.sin(phase) + 1.0) * 0.6
    for device_id, profile, left, mirror in (
        (DEVICES[0], LEFT_PROFILE, 1, -1.0), (DEVICES[1], RIGHT_PROFILE, 0, 1.0)
    ):
        devices.append(dict(id=device_id, pair_id=DEVICES[left], battery_percentage=80,
                            is_haptics=1, is_left=left, device_type=3, color=4 if left else 6,
                            connected_state=1, name="Synthetic left" if left else "Synthetic right",
                            is_external_power_present=0))
        timed = dict(id=device_id, is_left=left, generated_at_ms_hi=hi, generated_at_ms_lo=lo)
        ergo = dict(timed, tracking_state=0)
        ergo.update({key: 0.0 if key.endswith("tilt") else math.degrees(flex) for key in ERGONOMICS})
        ergonomics.append(ergo)
        controllers.append(dict(id=device_id, is_left=left, a=0, b=0, sys=0, trigger_button=0,
                                joystick_button=0, trackpad_button=0, trigger=0.0, grip_value=0.0,
                                grip_force=0.0, joystick_x=0.0, joystick_y=0.0, trackpad_x=0.0, trackpad_y=0.0))
        skeleton = dict(timed, tracking_state=0)
        skeleton.update({"wrist_p_x": 0.0, "wrist_p_y": 0.0, "wrist_p_z": 0.0})
        for finger, across, count in (("thumb", .040, 4), ("index", .020, 5),
                                     ("middle", .0, 5), ("ring", -.020, 5), ("little", -.040, 5)):
            chain = [node for node in NODES if node.startswith(finger + "_")]
            x, y, z = -0.015, 0.0, mirror * across
            for index, node in enumerate(chain):
                if index:
                    angle = flex * index / count
                    x -= .023 * math.cos(angle)
                    y -= .023 * math.sin(angle)
                skeleton.update({f"{node}_p_x": x, f"{node}_p_y": y, f"{node}_p_z": z})
        for node in ROTATIONS:
            skeleton.update({f"{node}_q_w": math.cos(flex / 6), f"{node}_q_x": 0.0,
                             f"{node}_q_y": 0.0, f"{node}_q_z": math.sin(flex / 6)})
        raw = dict(skeleton)
        skeleton["profile_uuid"] = profile
        skeletons.extend((delivery("HandSkeleton", [skeleton]), delivery("HandSkeletonRaw", [raw])))
        sensor = dict(timed)
        for name in SENSORS:
            node = name.replace("_sensor", "_mcp")
            for axis in "xyz":
                sensor[f"{name}_p_{axis}"] = skeleton[f"{node}_p_{axis}"]
            sensor.update({f"{name}_q_w": 1.0, f"{name}_q_x": 0.0,
                           f"{name}_q_y": 0.0, f"{name}_q_z": 0.0})
        sensors.append(sensor)
    messages = [delivery("Device", devices), delivery("Ergonomics", ergonomics),
                delivery("Controller", controllers), delivery("RawSensorTransforms", sensors), *skeletons]
    return [encode(message) for message in messages]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=25791)
    parser.add_argument("--frames", type=int, help="stop after N demo frames; default loops until Ctrl+C")
    args = parser.parse_args()
    if args.frames is not None and args.frames < 1:
        parser.error("--frames must be positive")
    server = UDPServer(port=args.port)
    print(json.dumps({"listening": list(server.address), "mode": "illustrative demo"}), flush=True)
    start, epoch = time.monotonic_ns(), time.time_ns() // 1_000_000
    count = 0
    try:
        while args.frames is None or count < args.frames:
            now_ms = (time.monotonic_ns() - start) // 1_000_000
            server.poll(now_ms, timeout=0.005)
            if now_ms >= count * 20:
                for packet in frame(epoch + now_ms, now_ms * math.pi / 2000):
                    server._send(server.station.publish(packet, now_ms))
                count += 1
    except KeyboardInterrupt:
        pass
    finally:
        server.close()


if __name__ == "__main__":
    main()
