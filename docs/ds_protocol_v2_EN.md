# DivingStationProtocol (v2)

English | [日本語](ds_protocol_v2.md)

## Overview

DivingStationProtocol is a protocol for communicating with Melt Interface Technologies devices through DivingStation.
v2 supports ContactGlove3 Pro. The standard ContactGlove3 cannot use DivingStationProtocol.

It is not compatible with ContactGlove, ContactGlove2, or ContactSheet.

Communication uses OSC (Open Sound Control).

Sending and receiving protocol messages enables the following:

- Obtaining joint positions and rotations from hand tracking devices
- Obtaining finger bending and splay from hand tracking devices
- Obtaining controller input
- Obtaining device battery levels
- Controlling device vibration

The main differences from v1 are as follows.

- The protocol version is `2`.
- The OSC address prefix is `/DS2/HC`.
- The default receive port on the DivingStation side is `25791`.
- v1's `/DS/HC/Hand` is replaced by `/DS2/HC/Ergonomics`.
- v1's `/DS/HC/HandQuat` is replaced by `/DS2/HC/HandSkeleton`.
- `/DS2/HC/Device` distributes information per glove device rather than per pair.

## Supported software

- DivingStation v2.0.0 or later

## Usage

DivingStationProtocol uses OSC (Open Sound Control) for communication.
Choose an OSC library appropriate for your language and environment.

First, make sure DivingStation is running and your device is connected.

::: warning LAN access and authorized sessions

By default, only clients on the same machine can connect. For clients on the same machine, use `127.0.0.1` as the destination address for DivingStation.

To use clients on the LAN, explicitly enable LAN access for the protocol in the DivingStation settings. Connect requests from the LAN are handled according to the connection approval policy configured in DivingStation. If user approval is required, Connect is held pending; once the user grants approval in DivingStation, data delivery and commands to devices are enabled.

Authorized sessions do not provide encryption or cryptographic authentication. Use them only on a trusted LAN.

:::

Next, connect to DivingStation.
Send the following connection request to DivingStation (default port: `25791`). The receive port on the DivingStation side can be changed in its settings (if you change it, also update the destination settings of clients that still refer to the old port).

- Example: the client's receive port is 25788

```plaintext
/DS2/HC/Connect 25788
```

(`/DS2/HC/Connect` is the OSC address, and `25788` is the argument.)

Once the connection succeeds, DivingStation starts sending data to port 25788.

If the DivingStation settings require approval for LAN client connections, no data is received until the user approves the connection in the approval modal.

All v2 clients must resend `Connect` every 30 seconds while maintaining a connection, regardless of whether connection approval is required or whether the client connects from localhost or the LAN. This resend serves as a keepalive and is required both while approval is pending and after approval.

When implementing an SDK, continue using the same UDP sending socket for Connect, keepalive, Disconnect, and Haptics. `port_recv` is the port for receiving data from DivingStation; an authorized session is associated with the combination of the Connect source endpoint and `port_recv`.

An authorized session expires 90 seconds after the last Connect. DivingStation limits the number of simultaneously authorized v2 clients. Even when retrying Connect, clients must not send it at intervals shorter than 1 second.

To end communication, send a disconnection request.

```plaintext
/DS2/HC/Disconnect 25788
```

Once disconnection succeeds, data reception from DivingStation stops.

## Structure

### Addresses and arguments

Each protocol message in DivingStationProtocol consists of an OSC address and arguments.

The address identifies the type of protocol message.

The arguments are a sequence of values of type float, int, or string. Fields beginning with `is_` represent Boolean values: 0 (=False) or 1 (=True).

### Version and time

The first argument of each protocol message, `version`, is `2` in v2. Clients ignore messages whose `version` is not `2`.

`timestamp_ms` is a numeric value representing Unix time in milliseconds. Over OSC, it is split into two `int` values: `timestamp_ms_hi` and `timestamp_ms_lo`. Clients combine both as unsigned 32bit values.

For records containing `generated_at_ms_hi` and `generated_at_ms_lo`, use the combined value as the frame generation time. It is not the OSC message transmission time.

### Records and validation

`*` means zero or more repetitions of the immediately preceding parenthesized group.

For data delivery protocols sent from DivingStation to clients, zero or more records of the same format follow `version`. Unless a protocol specifies a smaller limit, the maximum number of records per message is 8. Messages exceeding the maximum record count are treated as invalid messages.

If a message contains an invalid record, discard the entire message. Clients do not skip only the invalid record or fill in default values.

## 3D coordinate system

Positions are expressed in meters.
Quaternions are expressed in the order `w, x, y, z`.

In this specification, the hand coordinate system with `wrist` as its origin is called the "wrist-origin hand model coordinate system." Positions in `/DS2/HC/HandSkeleton` are coordinates in the retarget profile's hand model coordinate system. Positions in `/DS2/HC/HandSkeletonRaw` are coordinates in the source skeleton's hand model coordinate system. In both cases, the root node is `wrist`, and each node position is expressed in meters.

`/DS2/HC/HandSkeletonRaw` is the source skeleton obtained by applying IK and forward kinematics to calibrated EMF tracking results. It is not raw EMF values, device-local coordinates, or [`RawSensorTransforms`](#raw-sensor-transform). The retarget profile's `bind_points`, `bind_rotations`, `rest_alignment`, and model-space transformation are not applied.

Joint rotations are local quaternions relative to each corresponding node's parent, for the 19 nodes listed in [Skeleton rotation order](#skeleton-rotation-order). Rotations for `wrist` and each `*_tip` are not transmitted.

Communication frames do not include parent-child information; clients reconstruct the skeleton using the known fixed topology.

The wrist-origin hand model coordinate system is right-handed for both hands. Axis directions are as follows.

| Axis | Direction |
| --------- | ---- |
| +X | From the fingertips toward the wrist. The extended middle finger points approximately along -X from `wrist` |
| +Y | From the palm toward the back of the hand. The finger pad side is -Y; the nail and back-of-hand side is +Y |
| +Z | Across the hand. From the little finger side toward the thumb side for the right hand, and from the thumb side toward the little finger side for the left hand |

When comparing mirror-symmetric poses, the same anatomical points have equal X/Y coordinates and opposite Z signs between the right and left hands.

A local quaternion represents the current node orientation as a rotation relative to its parent node. In the reference pose (bind pose), HandSkeleton matches the retarget profile's bind local quaternion, and HandSkeletonRaw matches the source skeleton's fixed bind local quaternion.

## Protocol list (DivingStation to client)

### Device information

This protocol provides information about all hand tracking devices connected to DivingStation.

#### Address

`/DS2/HC/Device`

#### Arguments

`int version, (string id, string pair_id, int battery_percentage, int is_haptics, int is_left, int device_type, int color, int connected_state, string name, int is_external_power_present)*`

The argument count is 1+10n (where n is the number of devices).

| Argument | Type | Description |
| --------- | ---- | ----------- |
| version | int | Protocol version (=2) |
| id | string | Device ID |
| pair_id | string | ID of the paired glove; an empty string if there is no paired glove |
| battery_percentage | int | Battery level (an integer from 0 to 100, or -1; -1 indicates an invalid battery level estimate) |
| is_haptics | int | Whether the device has a vibration function |
| is_left | int | Whether the hand is left or right |
| device_type | int | Device type |
| color | int | Device display color setting |
| connected_state | int | Device connection state |
| name | string | Device name |
| is_external_power_present | int | Whether external power is detected |

The `device_type` values correspond to the following device types.

| device_type | Device type |
| --------- | ---- |
| 0 | ContactGlove |
| 1 | ContactSheet |
| 2 | ContactGlove2 |
| 3 | ContactGlove3 family |

v2 accepts only `3` for `device_type`. This value identifies the ContactGlove3 family; it does not indicate protocol support. Only ContactGlove3 Pro can use the protocol.

The `color` values correspond to the following colors.

| color | Color |
| --------- | ---- |
| 0 | Magenta |
| 1 | Red |
| 2 | Orange |
| 3 | Yellow |
| 4 | Green |
| 5 | Cyan |
| 6 | Blue |
| 7 | Achromatic |

The `connected_state` values correspond to the following connection states.

| connected_state | Connection state |
| --------- | ---- |
| 0 | Unknown |
| 1 | Connected |
| 2 | Disconnected |
| 3 | Attempting to connect |

::: info Battery level values

`battery_percentage` is an integer from 0 to 100 when the device can validly report its current battery level. `-1` is an invalid value, used when disconnected, when battery estimation has stopped due to external power, or in similar cases.

:::

### Finger bending and splay values

This protocol provides finger bending and splay values from a hand tracking device.

v1's `/DS/HC/Hand` is removed; use this protocol in v2.

#### Address

`/DS2/HC/Ergonomics`

#### Arguments

`int version, (string id, int is_left, int generated_at_ms_hi, int generated_at_ms_lo, int tracking_state, float thumb_cmc, float thumb_mcp, float thumb_ip, float thumb_tilt, float index_mcp, float index_pip, float index_dip, float index_tilt, ...)*`

The argument count is 1+25n (where n is the number of data records).

| Argument | Type | Description |
| --------- | ---- | ----------- |
| version | int | Protocol version (=2) |
| id | string | Device ID |
| is_left | int | Whether the hand is left or right |
| generated_at_ms_hi | int | Upper 32bit of the frame generation time |
| generated_at_ms_lo | int | Lower 32bit of the frame generation time |
| tracking_state | int | Tracking state |
| thumb_cmc | float | Bending angle of the thumb CMC joint |
| thumb_mcp | float | Bending angle of the thumb MCP joint |
| thumb_ip | float | Bending angle of the thumb IP joint |
| thumb_tilt | float | Thumb tilt angle |
| {finger}_mcp | float | Bending angle of the {finger} MCP joint |
| {finger}_pip | float | Bending angle of the {finger} PIP joint |
| {finger}_dip | float | Bending angle of the {finger} DIP joint |
| {finger}_tilt | float | Tilt angle of the {finger} |

Values are arranged in the order listed in [Ergonomics value order](#ergonomics-value-order).

All values are in degrees. Bending angles are relative to the extended state. Tilt angles use the default state as 0°.

The values and handling of `tracking_state` follow [Tracking states](#tracking-states).

### Controller input

This protocol provides controller input information.

#### Address

`/DS2/HC/Controller`

#### Arguments

`int version, (string id, int is_left, int a, int b, int sys, int trigger_button, int joystick_button, int trackpad_button, float trigger, float grip_value, float grip_force, float joystick_x, float joystick_y, float trackpad_x, float trackpad_y)*`

The argument count is 1+15n (where n is the number of controllers).

| Argument | Type | Description |
| --------- | ---- | ----------- |
| version | int | Protocol version (=2) |
| id | string | Device ID |
| is_left | int | Whether the hand is left or right |
| a | int | A button press state |
| b | int | B button press state |
| sys | int | System button press state |
| trigger_button | int | Trigger button press state |
| joystick_button | int | Joystick button press state |
| trackpad_button | int | Trackpad touch press state |
| trigger | float | Trigger value |
| grip_value | float | Grip value |
| grip_force | float | Grip force |
| joystick_x | float | Joystick X axis value |
| joystick_y | float | Joystick Y axis value |
| trackpad_x | float | Trackpad X axis value |
| trackpad_y | float | Trackpad Y axis value |

Button state values are defined as follows.

| Value | Description |
| --------- | ---- |
| 0 | Button is not pressed |
| 1 | Button is being touched |
| 2 | Button is pressed |

The ranges of the analog values are as follows.

| Argument | Range |
| --------- | ---- |
| trigger | 0.0–1.0 |
| grip_value | 0.0–1.0 |
| grip_force | 0.0–1.0 |
| joystick_x | -1.0–1.0 |
| joystick_y | -1.0–1.0 |
| trackpad_x | -1.0–1.0 |
| trackpad_y | -1.0–1.0 |

Analog values are sent after calibration and dead zone processing on the DivingStation side.

Messages containing out-of-range values or NaN/Inf are treated as invalid messages.

In the current ContactGlove3 Pro implementation, trackpad input is sent as `trackpad_x = 0.0` and one of `trackpad_y = -1.0, 0.0, 1.0`, rather than as continuous analog values.

### Hand skeleton (retargeted)

This protocol provides joint positions and rotations resulting from transforming a hand tracking device's hand skeleton with a retarget profile.

v1's `/DS/HC/HandQuat` is removed; use this protocol in v2.

#### Address

`/DS2/HC/HandSkeleton`

#### Arguments

`int version, string id, string profile_uuid, int is_left, int generated_at_ms_hi, int generated_at_ms_lo, int tracking_state, float wrist_p_x, float wrist_p_y, float wrist_p_z, ..., float little_tip_p_z, float thumb_cmc_q_w, float thumb_cmc_q_x, float thumb_cmc_q_y, float thumb_cmc_q_z, ..., float little_dip_q_z`

The argument count is 158. `/DS2/HC/HandSkeleton` always contains exactly 1 skeleton record. The left and right hands are sent as separate OSC messages.

| Argument | Type | Description |
| --------- | ---- | ----------- |
| version | int | Protocol version (=2) |
| id | string | Device ID |
| profile_uuid | string | Fixed UUID of the retarget profile |
| is_left | int | Whether the hand is left or right |
| generated_at_ms_hi | int | Upper 32bit of the frame generation time |
| generated_at_ms_lo | int | Lower 32bit of the frame generation time |
| tracking_state | int | Tracking state |
| {node_id}_p_x | float | X component of the joint position |
| {node_id}_p_y | float | Y component of the joint position |
| {node_id}_p_z | float | Z component of the joint position |
| {node_id}_q_w | float | w component of the joint rotation quaternion |
| {node_id}_q_x | float | x component of the joint rotation quaternion |
| {node_id}_q_y | float | y component of the joint rotation quaternion |
| {node_id}_q_z | float | z component of the joint rotation quaternion |

Joint positions are arranged for the 25 nodes listed in [Skeleton node order](#skeleton-node-order), with each node's components ordered as `x, y, z`.

Joint rotations are arranged for the 19 nodes listed in [Skeleton rotation order](#skeleton-rotation-order), with each node's components ordered as `w, x, y, z`.

Rotations are not included for `wrist` or any `*_tip` node.

Joint positions are skeleton node positions; their coordinate system, units, and origin follow [3D coordinate system](#3d-coordinate-system). Joint rotations are local quaternions relative to each corresponding node's parent.

DivingStation sends only frames containing all 25 node positions and all 19 joint rotations, with finite values for every position and quaternion component. Missing nodes, missing rotations, NaN, and Inf are not filled with 0 or an identity quaternion; frames containing missing values are not sent.

`profile_uuid` is a UUID-formatted string assigned by DivingStation when a profile is created. UUID format means a 36 byte string of ASCII hexadecimal digits and hyphens in the `8-4-4-4-12` format. It remains fixed throughout the profile's lifetime and must not be reused for another profile. A HandSkeleton record with an empty or non-UUID-formatted `profile_uuid` is invalid. DivingStation does not activate such a profile and must not send the corresponding HandSkeleton record. The profile's display name and description can be obtained through [Retarget profile information](#retarget-profile-information).

The values and handling of `tracking_state` follow [Tracking states](#tracking-states).

The datagram containing 1 record serialized in OSC must be no larger than 1200 bytes. DivingStation does not send records exceeding this limit and must not rely on IP fragmentation. `id` must be a UTF-8 string no larger than 64 bytes.

### Hand skeleton (raw)

This protocol provides joint positions and rotations of the hand skeleton obtained from a hand tracking device.
It is used to obtain raw skeleton values before transformation by a retarget profile.

#### Address

`/DS2/HC/HandSkeletonRaw`

#### Arguments

`int version, string id, int is_left, int generated_at_ms_hi, int generated_at_ms_lo, int tracking_state, float wrist_p_x, float wrist_p_y, float wrist_p_z, ..., float little_tip_p_z, float thumb_cmc_q_w, float thumb_cmc_q_x, float thumb_cmc_q_y, float thumb_cmc_q_z, ..., float little_dip_q_z`

The argument count is 157. `/DS2/HC/HandSkeletonRaw` always contains exactly 1 skeleton record. The left and right hands are sent as separate OSC messages.

| Argument | Type | Description |
| --------- | ---- | ----------- |
| version | int | Protocol version (=2) |
| id | string | Device ID |
| is_left | int | Whether the hand is left or right |
| generated_at_ms_hi | int | Upper 32bit of the frame generation time |
| generated_at_ms_lo | int | Lower 32bit of the frame generation time |
| tracking_state | int | Tracking state |
| {node_id}_p_x | float | X component of the joint position |
| {node_id}_p_y | float | Y component of the joint position |
| {node_id}_p_z | float | Z component of the joint position |
| {node_id}_q_w | float | w component of the joint rotation quaternion |
| {node_id}_q_x | float | x component of the joint rotation quaternion |
| {node_id}_q_y | float | y component of the joint rotation quaternion |
| {node_id}_q_z | float | z component of the joint rotation quaternion |

Joint positions are arranged for the 25 nodes listed in [Skeleton node order](#skeleton-node-order), with each node's components ordered as `x, y, z`.

Joint rotations are arranged for the 19 nodes listed in [Skeleton rotation order](#skeleton-rotation-order), with each node's components ordered as `w, x, y, z`.

Rotations are not included for `wrist` or any `*_tip` node.

Joint positions are skeleton node positions; their coordinate system, units, and origin follow [3D coordinate system](#3d-coordinate-system). Joint rotations are local quaternions relative to each corresponding node's parent.

DivingStation sends only frames containing all 25 node positions and all 19 joint rotations, with finite values for every position and quaternion component. Missing nodes, missing rotations, NaN, and Inf are not filled with 0 or an identity quaternion; frames containing missing values are not sent.

The values and handling of `tracking_state` follow [Tracking states](#tracking-states).

The datagram containing 1 record serialized in OSC must be no larger than 1200 bytes. DivingStation does not send records exceeding this limit and must not rely on IP fragmentation. `id` must be a UTF-8 string no larger than 64 bytes.

### Retarget profile information

This protocol provides display information for the `profile_uuid` included in `/DS2/HC/HandSkeleton`. The profile's coordinates and joint values themselves are included in the HandSkeleton message, so not having received a profile information response does not prevent interpretation of skeleton values.

#### Address

`/DS2/HC/HandSkeleton/Profile`

#### Arguments

`int version, int request_id, string profile_uuid, int status, string name, string description`

The argument count is 6.

| Argument | Type | Description |
| --------- | ---- | ----------- |
| version | int | Protocol version (=2) |
| request_id | int | Client-specified request identifier; the value from the request is returned unchanged |
| profile_uuid | string | Profile UUID according to `status` |
| status | int | Result of retrieving profile information |
| name | string | User-facing profile name; no larger than 128 bytes in UTF-8 |
| description | string | Profile description; no larger than 768 bytes in UTF-8 |

`status` values are defined as follows.

| status | Description |
| --------- | ---- |
| 0 | The profile exists. `name` and `description` can be used |
| 1 | The UUID format is valid, but the profile does not exist. `name` and `description` are empty strings |
| 2 | The query is invalid. `profile_uuid`, `name`, and `description` are empty strings |

`request_id` always returns the int value from the request unchanged, regardless of `status`. When `status` is 0, DivingStation includes the stored profile's `profile_uuid` unchanged in the response. When `status` is 1, it includes the `profile_uuid` from the request unchanged. When `status` is 2, the response's `profile_uuid` is an empty string. Upon receiving an unknown `profile_uuid`, a client can send a [Retarget profile information request](#retarget-profile-information-request) as needed and cache the result keyed by `profile_uuid`. Responses with undefined `status` values are treated as invalid messages.

The 128 byte limit for `name` and 768 byte limit for `description` count bytes encoded in UTF-8 (excluding the terminating NUL of the OSC string). DivingStation must validate these limits when creating, updating, or loading profiles and reject profiles exceeding them. Strings must not be truncated during transmission.

### Raw sensor Transform

This protocol provides raw sensor positions and rotations.

DivingStation sends the 5 sensor transforms for one hand as 1 record, which the client receives.

#### Address

`/DS2/HC/RawSensorTransforms`

#### Arguments

`int version, (string id, int is_left, int generated_at_ms_hi, int generated_at_ms_lo, float thumb_sensor_p_x, float thumb_sensor_p_y, float thumb_sensor_p_z, float thumb_sensor_q_w, float thumb_sensor_q_x, float thumb_sensor_q_y, float thumb_sensor_q_z, ..., float little_sensor_q_z)*`

The argument count is 1+39n (where n is the number of data records).

| Argument | Type | Description |
| --------- | ---- | ----------- |
| version | int | Protocol version (=2) |
| id | string | Device ID |
| is_left | int | Whether the hand is left or right |
| generated_at_ms_hi | int | Upper 32bit of the frame generation time |
| generated_at_ms_lo | int | Lower 32bit of the frame generation time |
| {sensor_id}_p_x | float | X component of the sensor position |
| {sensor_id}_p_y | float | Y component of the sensor position |
| {sensor_id}_p_z | float | Z component of the sensor position |
| {sensor_id}_q_w | float | w component of the sensor rotation quaternion |
| {sensor_id}_q_x | float | x component of the sensor rotation quaternion |
| {sensor_id}_q_y | float | y component of the sensor rotation quaternion |
| {sensor_id}_q_z | float | z component of the sensor rotation quaternion |

Sensor transforms are arranged for the 5 sensors listed in [Raw sensor Transform order](#raw-sensor-transform-order), with each sensor's components ordered as `p_x, p_y, p_z, q_w, q_x, q_y, q_z`.

Positions are expressed in meters. Quaternions are expressed in the order `w, x, y, z`.

The raw sensor transforms here are the transforms of each finger sensor estimated by DivingStation. They are not raw EMF values or device-local coordinates; the transmitted values are transformed into the same wrist-origin hand model coordinate system as `/DS2/HC/HandSkeleton`.

Positions are sensor center positions relative to `wrist` as the origin.

Rotations are quaternions representing the orientation from the sensor local frame to the wrist-origin hand model coordinate system. With an identity quaternion, the sensor local frame's X/Y/Z axes coincide with those of the wrist-origin hand model coordinate system.

Raw sensor transforms for the left hand are also expressed in the same right-handed wrist-origin hand model coordinate system as `/DS2/HC/HandSkeleton`. When comparing mirror-symmetric poses, corresponding sensor positions have equal X/Y coordinates and opposite Z signs.

## Protocol list (client to DivingStation)

### Connection request

This protocol sends a request to connect to DivingStation.

::: warning Ports

The client's receive port can be set freely using this protocol.

The default receive port on the DivingStation side is 25791 and can be changed in its settings.

:::

#### Address

`/DS2/HC/Connect`

#### Arguments

`int port_recv`

The argument count is 1.

| Argument | Type | Description |
| --------- | ---- | ----------- |
| port_recv | int | Client receive port number |

### Disconnection request

This protocol sends a request to disconnect from DivingStation.

#### Address

`/DS2/HC/Disconnect`

#### Arguments

`int port_recv`

The argument count is 1.

| Argument | Type | Description |
| --------- | ---- | ----------- |
| port_recv | int | Client receive port number |

DivingStation treats the combination of source IP address and `port_recv` as the client identifier. Connections using the same `port_recv` from different IP addresses are treated as separate clients; duplicate connections using the same IP address and the same `port_recv` are combined into 1 client.

When LAN access is enabled, DivingStation processes Connect as a request to create or update an authorized session for the combination of source UDP endpoint and `port_recv`. Client messages other than Connect from sources that are pending approval, expired, or unauthorized are not processed.

### Retarget profile information request

This request retrieves the display name and description corresponding to the `profile_uuid` in `/DS2/HC/HandSkeleton`. Only connected clients can send it. DivingStation responds with [Retarget profile information](#retarget-profile-information) to the client receive port registered by Connect.

#### Address

`/DS2/HC/HandSkeleton/Profile/Get`

#### Arguments

`int version, int request_id, string profile_uuid`

The argument count is 3.

| Argument | Type | Description |
| --------- | ---- | ----------- |
| version | int | Protocol version (=2) |
| request_id | int | Value used by the client to correlate the response |
| profile_uuid | string | Retarget profile UUID to query |

`profile_uuid` must be in UUID format. UUID format means a 36 byte string of ASCII hexadecimal digits and hyphens in the `8-4-4-4-12` format. Empty strings, strings other than 36 bytes, and strings not in UUID format are invalid. If the argument count, types, and `version` are correct and only `profile_uuid` is invalid, DivingStation returns [Retarget profile information](#retarget-profile-information) with the same `request_id` and `status = 2`. Messages with invalid argument counts, types, or `version` are discarded without a response.

DivingStation also responds when `profile_uuid` does not exist, setting the response's `status` to `1`.

### Vibration

This protocol triggers vibration on devices with a vibration module.

#### Address

`/DS2/HC/{id}/Haptics/Body`

Specify the device ID in id. The device ID can be obtained using the device information protocol.

#### Arguments

`int version, float frequency, float amplitude, float duration`

The argument count is 4.

| Argument | Type | Description |
| --------- | ---- | ----------- |
| version | int | Protocol version (=2) |
| frequency | float | Vibration frequency (Hz) |
| amplitude | float | Vibration amplitude |
| duration | float | Vibration duration (seconds) |

Specify `frequency` in the range 100.0 ~ 500.0.
Specify `amplitude` in the range 0.0 ~ 1.0.
Specify `duration` in the range 0.001 ~ 1.0.

Out-of-range values are rejected without clamping.

When LAN access is enabled, only messages from sources with authorized v2 sessions are processed. Haptics messages sent by clients pending approval, expired clients, or unauthorized clients are discarded.

## Tracking states

IK-derived records containing `tracking_state` use the following values.

| tracking_state | State | Handling of record values |
| --------- | ---- | ----------- |
| 0 | `Tracked` | Valid values obtained from the current IK processing |
| 1 | `IkFailed` | A frame for which the IK processing needed to generate the record was attempted but reported failure. Complete, finite position, rotation, and angle values can be used for display and diagnostics, but clients must not use them as inputs to control, velocity estimation, or interpolation |
| 2 | `NotAttempted` | A frame for which the IK processing needed to generate the record was not performed. This includes cases where an earlier processing failure or missing input prevented an attempt, as well as cases where pose calculation was deemed unnecessary, such as due to update interval control. Complete, finite position, rotation, and angle values can be used for display and diagnostics, but clients must not use them as inputs to control, velocity estimation, or interpolation |

Records with other values are treated as invalid records.

`NotAttempted` itself does not mean that IK processing failed. For example, it also includes cases where IK processing is skipped due to update interval control and an existing pose is reused.

Even when sending records with `IkFailed` or `NotAttempted`, DivingStation sends only complete, finite position, rotation, and angle values. Values must not be filled with 0 or an identity quaternion. If complete values are unavailable, the record is not sent.

The state of `/DS2/HC/HandSkeleton` represents the IK result of retargeting. `IkFailed` means retargeting was attempted and failed; `NotAttempted` means retargeting was not performed. This includes both cases where it could not be attempted due to source skeleton failure or similar causes and cases where pose calculation was deemed unnecessary. The states of `/DS2/HC/HandSkeletonRaw` and `/DS2/HC/Ergonomics` represent the IK result for obtaining the source skeleton before retargeting. States may differ across messages for the same time. For example, if only retargeting fails, only HandSkeleton may be `IkFailed`. If the IK for obtaining the source skeleton is attempted and fails, Raw Skeleton and Ergonomics may be `IkFailed`, while HandSkeleton, which uses them as input, may be `NotAttempted`. If processing fails before the IK for obtaining the source skeleton, all 3 may be `NotAttempted`.

## Skeleton definitions

`/DS2/HC/HandSkeleton` and `/DS2/HC/HandSkeletonRaw` transmit a skeleton with a fixed topology of 25 nodes.
Communication frames do not include parent-child information; clients reconstruct the skeleton using this known topology.

### Skeleton node order

Joint positions in `/DS2/HC/HandSkeleton` and `/DS2/HC/HandSkeletonRaw` are arranged in the following order.

| index | node_id | parent | child |
| --------- | ---- | ---- | ---- |
| 0 | `wrist` | - | `thumb_cmc`, `index_cmc`, `middle_cmc`, `ring_cmc`, `little_cmc` |
| 1 | `thumb_cmc` | `wrist` | `thumb_mcp` |
| 2 | `thumb_mcp` | `thumb_cmc` | `thumb_ip` |
| 3 | `thumb_ip` | `thumb_mcp` | `thumb_tip` |
| 4 | `thumb_tip` | `thumb_ip` | - |
| 5 | `index_cmc` | `wrist` | `index_mcp` |
| 6 | `index_mcp` | `index_cmc` | `index_pip` |
| 7 | `index_pip` | `index_mcp` | `index_dip` |
| 8 | `index_dip` | `index_pip` | `index_tip` |
| 9 | `index_tip` | `index_dip` | - |
| 10 | `middle_cmc` | `wrist` | `middle_mcp` |
| 11 | `middle_mcp` | `middle_cmc` | `middle_pip` |
| 12 | `middle_pip` | `middle_mcp` | `middle_dip` |
| 13 | `middle_dip` | `middle_pip` | `middle_tip` |
| 14 | `middle_tip` | `middle_dip` | - |
| 15 | `ring_cmc` | `wrist` | `ring_mcp` |
| 16 | `ring_mcp` | `ring_cmc` | `ring_pip` |
| 17 | `ring_pip` | `ring_mcp` | `ring_dip` |
| 18 | `ring_dip` | `ring_pip` | `ring_tip` |
| 19 | `ring_tip` | `ring_dip` | - |
| 20 | `little_cmc` | `wrist` | `little_mcp` |
| 21 | `little_mcp` | `little_cmc` | `little_pip` |
| 22 | `little_pip` | `little_mcp` | `little_dip` |
| 23 | `little_dip` | `little_pip` | `little_tip` |
| 24 | `little_tip` | `little_dip` | - |

### Skeleton rotation order

Joint rotations in `/DS2/HC/HandSkeleton` are arranged in the following order.

| index | node_id |
| --------- | ---- |
| 0 | `thumb_cmc` |
| 1 | `thumb_mcp` |
| 2 | `thumb_ip` |
| 3 | `index_cmc` |
| 4 | `index_mcp` |
| 5 | `index_pip` |
| 6 | `index_dip` |
| 7 | `middle_cmc` |
| 8 | `middle_mcp` |
| 9 | `middle_pip` |
| 10 | `middle_dip` |
| 11 | `ring_cmc` |
| 12 | `ring_mcp` |
| 13 | `ring_pip` |
| 14 | `ring_dip` |
| 15 | `little_cmc` |
| 16 | `little_mcp` |
| 17 | `little_pip` |
| 18 | `little_dip` |

## Ergonomics definitions

### Ergonomics value order

Values in `/DS2/HC/Ergonomics` are arranged in the following order.

| index | Name |
| --------- | ---- |
| 0 | `thumb_cmc` |
| 1 | `thumb_mcp` |
| 2 | `thumb_ip` |
| 3 | `thumb_tilt` |
| 4 | `index_mcp` |
| 5 | `index_pip` |
| 6 | `index_dip` |
| 7 | `index_tilt` |
| 8 | `middle_mcp` |
| 9 | `middle_pip` |
| 10 | `middle_dip` |
| 11 | `middle_tilt` |
| 12 | `ring_mcp` |
| 13 | `ring_pip` |
| 14 | `ring_dip` |
| 15 | `ring_tilt` |
| 16 | `little_mcp` |
| 17 | `little_pip` |
| 18 | `little_dip` |
| 19 | `little_tilt` |

## Raw sensor Transform definitions

### Raw sensor Transform order

Sensor transforms in `/DS2/HC/RawSensorTransforms` are arranged in the following order.

| index | sensor_id |
| --------- | ---- |
| 0 | `thumb_sensor` |
| 1 | `index_sensor` |
| 2 | `middle_sensor` |
| 3 | `ring_sensor` |
| 4 | `little_sensor` |

## Removed protocols

### Wrist

v2 does not define `/DS2/HC/Wrist`.

ContactGlove3 Pro does not have a function for obtaining wrist rotation, so the initial v2 specification does not define a standalone Wrist protocol. If future devices can obtain wrist rotation, integration into the `wrist` node of `/DS2/HC/HandSkeleton` will be considered.

### Haptics/Finger

v2 does not define a finger haptic command equivalent to v1's `/DS/HC/{id}/Haptics/Finger`.

### Hand, HandQuat

- v1's `/DS/HC/Hand` is replaced by `/DS2/HC/Ergonomics`.
- v1's `/DS/HC/HandQuat` is replaced by `/DS2/HC/HandSkeleton`.
