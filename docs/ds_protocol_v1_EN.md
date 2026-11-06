# DivingStationProtocol (v1)

English | [日本語](ds_protocol_v1.md)

## Overview

DivingStationProtocol is a protocol for communicating with Melt Interface Technologies devices through DivingStation.
It currently supports ContactGlove, ContactGlove2, and ContactSheet.

Communication uses OSC (Open Sound Control).

Sending and receiving protocol messages enables the following:

- Obtaining finger bending values from hand tracking devices
- Obtaining device battery levels
- Controlling device vibration

## Supported software

- DivingStation v1.5.6 or later

## Usage

DivingStationProtocol uses OSC (Open Sound Control) for communication.
Choose an OSC library appropriate for your language and environment.

First, make sure DivingStation is running and your device is connected.

Next, connect to DivingStation.
Send the following connection request to DivingStation (default port: `25790`). The receive port on the DivingStation side can be changed in its settings.

- Example: the client's receive port is 25788

```plaintext
/DS/HC/Connect 25788
```

(`/DS/HC/Connect` is the OSC address, and `25788` is the argument.)

Once the connection succeeds, DivingStation starts sending data to port 25788.

To end communication, send a disconnection request.

```plaintext
/DS/HC/Disconnect 25788
```

Once disconnection succeeds, data reception from DivingStation stops.

Version 1.1.0 and later of the Unity SDK are implemented using DivingStationProtocol. Refer to the SDK when implementing your client.

## Structure

Each protocol message in DivingStationProtocol consists of an OSC address and arguments.

The address identifies the type of protocol message.

The arguments are a sequence of values of type float, int, or string. Fields beginning with `is_` represent Boolean values: 0 (=False) or 1 (=True).

## Protocol list (receiving side)

### Device information

This protocol provides information about all hand tracking devices connected to DivingStation.

#### Address

`/DS/HC/Device`

#### Arguments

`int version, (string id, int is_main, int device_type, string name, int color, float ping, int is_left_connected, int left_battery, float left_ping, int is_right_connected, int right_battery, float right_ping)*`

`*` means zero or more repetitions of the immediately preceding parenthesized group.

The argument count is 1+12n (where n is the number of connected devices).

| Argument | Type | Description |
| --------- | ---- | ----------- |
| version | int | Protocol version (=1) |
| id | string | Device ID |
| is_main | int | Whether this is the main device |
| device_type | int | Device type |
| name | string | Device name |
| color | int | Device LED color |
| ping | float | Communication latency with the dongle |
| is_left_connected | int | Whether the left hand device is connected |
| left_battery | int | Battery level of the left hand device |
| left_ping | float | Communication latency with the left hand device |
| is_right_connected | int | Whether the right hand device is connected |
| right_battery | int | Battery level of the right hand device |
| right_ping | float | Communication latency with the right hand device |

The main device is the device used in SteamVR or similar software.

The `device_type` values correspond to the following device types.

| device_type | Device type |
| --------- | ---- |
| 0 | ContactGlove |
| 1 | ContactSheet |
| 2 | ContactGlove2 |

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

### Finger bending and tilt values

This protocol provides finger bending and tilt values from a hand tracking device.

#### Address

`/DS/HC/Hand`

#### Arguments

`int version, string id, int is_left, float thumb_cmc, float thumb_mcp, float thumb_ip, float thumb_tilt, float index_mcp, float index_pip, float index_dip, float index_tilt, ...`

The argument count is 23.

| Argument | Type | Description |
| --------- | ---- | ----------- |
| version | int | Protocol version (=1) |
| id | string | Device ID |
| is_left | int | Whether the hand is left or right |
| thumb_cmc | float | Bending value of the thumb CMC joint |
| thumb_mcp | float | Bending value of the thumb MCP joint |
| thumb_ip | float | Bending value of the thumb IP joint |
| thumb_tilt | float | Thumb tilt |
| {finger}_mcp | float | Bending value of the {finger} MCP joint |
| {finger}_pip | float | Bending value of the {finger} PIP joint |
| {finger}_dip | float | Bending value of the {finger} DIP joint |
| {finger}_tilt | float | Tilt of the {finger} |

Joints are ordered from the base of the finger toward its tip: MCP, PIP, DIP (CMC, MCP, IP for the thumb).

Fingers are ordered as `thumb`, `index`, `middle`, `ring`, and `little`.

Bending values range from 0.0 ~ 1.0: 0.0 is extended, and 1.0 is bent.
Tilt is expressed as an angle with the default state at 0°.

### Joint quaternions

This protocol provides the quaternion of each joint of a hand tracking device.

#### Address

`/DS/HC/HandQuat`

#### Arguments

`int version, string id, int is_left, float thumb_cmc_w, float thumb_cmc_x, float thumb_cmc_y, float thumb_cmc_z, ..., float index_mcp_w, ...`

The argument count is 63.

| Argument | Type | Description |
| --------- | ---- | ----------- |
| version | int | Protocol version (=1) |
| id | string | Device ID |
| is_left | int | Whether the hand is left or right |
| {finger}_{joint}_w | float | w component of the quaternion of the {finger} {joint} |
| {finger}_{joint}_x | float | x component of the quaternion of the {finger} {joint} |
| {finger}_{joint}_y | float | y component of the quaternion of the {finger} {joint} |
| {finger}_{joint}_z | float | z component of the quaternion of the {finger} {joint} |

Fingers are ordered as `thumb`, `index`, `middle`, `ring`, and `little`.

For the thumb, joints are ordered as `cmc` (base), `mcp` (middle), and `ip` (tip). For the other fingers, they are ordered as `mcp` (base), `pip` (middle), and `dip` (tip).

### Wrist rotation

This protocol provides the wrist rotation of a hand tracking device.

#### Address

`/DS/HC/Wrist`

#### Arguments

`int version, string id, int is_left, float w, float x, float y, float z`

The argument count is 7.

| Argument | Type | Description |
| --------- | ---- | ----------- |
| version | int | Protocol version (=1) |
| id | string | Device ID |
| is_left | int | Whether the hand is left or right |
| w | float | w component of the quaternion |
| x | float | x component of the quaternion |
| y | float | y component of the quaternion |
| z | float | z component of the quaternion |

### Controller input

This protocol provides controller input information.

#### Address

`/DS/HC/Controller`

#### Arguments

`int version, string id, int is_left, int a, int b, int sys, int trigger_button, int joystick_button, int trackpad_button, float trigger, float grip_value, float grip_force, float joystick_x, float joystick_y, float trackpad_x, float trackpad_y`

The argument count is 16.

| Argument | Type | Description |
| --------- | ---- | ----------- |
| version | int | Protocol version (=1) |
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

## Protocol list (sending side)

### Connection request

This protocol sends a request to connect to DivingStation.

::: warning Ports

The client's receive port can be set freely using this protocol.

The default receive port on the DivingStation side is 25790. The port can be changed in the DivingStation settings.

:::

#### Address

`/DS/HC/Connect`

#### Arguments

`int port_recv`

The argument count is 1.

| Argument | Type | Description |
| --------- | ---- | ----------- |
| port_recv | int | Receive port number |

### Disconnection request

This protocol sends a request to disconnect from DivingStation.

#### Address

`/DS/HC/Disconnect`

#### Arguments

`int port_recv`

The argument count is 1.

| Argument | Type | Description |
| --------- | ---- | ----------- |
| port_recv | int | Receive port number |

### Vibration

This protocol triggers vibration on devices with a vibration module.

#### Address

`/DS/HC/{id}/Haptics/Body`

Specify the device ID in id. The device ID can be obtained using the device information protocol.

#### Arguments

`int version, int is_left, float frequency, float amplitude, float duration`

The argument count is 5.

| Argument | Type | Description |
| --------- | ---- | ----------- |
| version | int | Protocol version (=1) |
| is_left | int | Whether the hand is left or right |
| frequency | float | Vibration frequency |
| amplitude | float | Vibration amplitude |
| duration | float | Vibration duration (seconds) |

Specify `ampitude` in the range 0.0 ~ 1.0.

### Finger haptics

This protocol triggers haptics on devices with finger haptic modules.

#### Address

`/DS/HC/{id}/Haptics/Finger`

Specify the device ID in id. The device ID can be obtained using the device information protocol.

#### Arguments

`int version, int is_left, int thumb, int index, int middle, int ring, int force`

The argument count is 7.
