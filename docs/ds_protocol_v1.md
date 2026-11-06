# DivingStationProtocol (v1)

[English](ds_protocol_v1_EN.md) | 日本語

## 概要

DivingStationProtocol とは、DivingStationを介してMelt Interface Technologies製デバイスとの通信を行うためのプロトコルです。
現在は ContactGlove, ContactGlove2, ContactSheet に対応しています。

通信には、OSC (Open Sound Control) を使用しています。

プロトコルの送受信によって、以下のようなことが可能となります。

- ハンドトラッキングデバイスの指の曲げの取得
- デバイスのバッテリー残量の取得
- デバイスの振動の制御

## 対応ソフトウェア

- DivingStation v1.5.6以降

## 使用方法

DivingStationProtocolでは、OSC (Open Sound Control) を使用して通信を行います。
使用したい言語や環境に合わせて、OSCライブラリを選択してください。

最初に、DivingStation が起動していること、およびデバイスが接続されていることを確認してください。

次に、DivingStation との接続を行います。
DivingStation（既定のポート番号: `25790`）に対し、以下の接続要求プロトコルを送信します。DivingStation側の受信ポートは設定で変更できます。

- 例: クライアントの受信用ポート番号が 25788 である場合

```plaintext
/DS/HC/Connect 25788
```

(`/DS/HC/Connect` はOSCアドレスを、`25788` は引数を表します。)

接続に成功した場合、25788番ポートに対してDivingStation から各種データが送信されるようになります。

通信を終了する際は、切断要求プロトコルを送信します。

```plaintext
/DS/HC/Disconnect 25788
```

切断に成功すると、DivingStation からのデータの受信が停止します。

Unity用SDKのVer1.1.0以降は、DivingStationProtocolを使用して実装されています。実装の際の参考にしてください。

## 構成

DivingStationProtocolに含まれる各プロトコルは、OSCのアドレスと引数の組み合わせで構成されています。

アドレスによって、プロトコルの種類を識別します。

引数は、float, int, stringのいずれかの型を持つ値の組です。`is_`で始まるフィールドは0 (=False) または1 (=True) の値を取り、真偽値を表します。

## プロトコル一覧 (受信側)

### デバイス情報

DivingStation に接続されている全てのハンドトラッキングデバイスの情報を取得するプロトコルです。

#### アドレス

`/DS/HC/Device`

#### 引数

`int version, (string id, int is_main, int device_type, string name, int color, float ping, int is_left_connected, int left_battery, float left_ping, int is_right_connected, int right_battery, float right_ping)*`

`*`は直前のカッコ内の0回以上の繰り返しを表します。

引数長は 1+12n (nは接続デバイスの数) となります。

| 引数名 | 型 | 説明 |
| --------- | ---- | ----------- |
| version | int | プロトコルバージョン (=1) |
| id | string | デバイスID |
| is_main | int | メインデバイスかどうか |
| device_type | int | デバイスの種類 |
| name | string | デバイス名 |
| color | int | デバイスのLEDカラー |
| ping | float | ドングルとの通信遅延 |
| is_left_connected | int | 左手デバイスが接続されているか |
| left_battery | int | 左手デバイスのバッテリー残量 |
| left_ping | float | 左手デバイスとの通信遅延 |
| is_right_connected | int | 右手デバイスが接続されているか |
| right_battery | int | 右手デバイスのバッテリー残量 |
| right_ping | float | 右手デバイスとの通信遅延 |

メインデバイスは、SteamVR等で使用されているデバイスを表します。

`device_type`の値と、対応するデバイスの種類は以下の通りです。

| device_type | デバイスの種類 |
| --------- | ---- |
| 0 | ContactGlove |
| 1 | ContactSheet |
| 2 | ContactGlove2 |

`color`の値と、対応する色は以下の通りです。

| color | 色 |
| --------- | ---- |
| 0 | マゼンタ |
| 1 | 赤 |
| 2 | オレンジ |
| 3 | 黄色 |
| 4 | 緑 |
| 5 | シアン |
| 6 | 青 |
| 7 | 無彩色 |

### 指の曲げ・傾き値

ハンドトラッキングデバイスの指の曲げ値と傾き値を取得するプロトコルです。

#### アドレス

`/DS/HC/Hand`

#### 引数

`int version, string id, int is_left, float thumb_cmc, float thumb_mcp, float thumb_ip, float thumb_tilt, float index_mcp, float index_pip, float index_dip, float index_tilt, ...`

引数長は 23 となります。

| 引数名 | 型 | 説明 |
| --------- | ---- | ----------- |
| version | int | プロトコルバージョン (=1) |
| id | string | デバイスID |
| is_left | int | 左手か右手か |
| thumb_cmc | float | 親指のCMC関節の曲げ値 |
| thumb_mcp | float | 親指のMCP関節の曲げ値 |
| thumb_ip | float | 親指のIP関節の曲げ値 |
| thumb_tilt | float | 親指の傾き |
| {指名}_mcp | float | {指名}のMCP関節の曲げ値 |
| {指名}_pip | float | {指名}のPIP関節の曲げ値 |
| {指名}_dip | float | {指名}のDIP関節の曲げ値 |
| {指名}_tilt | float | {指名}の傾き |

各関節は、指の付け根から先端に向かってMCP, PIP, DIP の順番 (親指は CMC, MCP, IP の順番) で並んでいます。

指は、`thumb`(親指), `index`(人差し指), `middle`(中指), `ring`(薬指), `little`(小指) の順番で並んでいます。

曲げ値は、0.0 ~ 1.0 の範囲で表され、0.0 が伸びた状態、1.0 が曲げた状態となります。
傾きは、デフォルト状態を0°とした角度で表されます。

### 各関節のクォータニオン

ハンドトラッキングデバイスの各関節のクォータニオンを取得するプロトコルです。

#### アドレス

`/DS/HC/HandQuat`

#### 引数

`int version, string id, int is_left, float thumb_cmc_w, float thumb_cmc_x, float thumb_cmc_y, float thumb_cmc_z, ..., float index_mcp_w, ...`

引数長は 63 となります。

| 引数名 | 型 | 説明 |
| --------- | ---- | ----------- |
| version | int | プロトコルバージョン (=1) |
| id | string | デバイスID |
| is_left | int | 左手か右手か |
| {指名}_{関節名}_w | float | {指名}の{関節名}のクォータニオンのw成分 |
| {指名}_{関節名}_x | float | {指名}の{関節名}のクォータニオンのx成分 |
| {指名}_{関節名}_y | float | {指名}の{関節名}のクォータニオンのy成分 |
| {指名}_{関節名}_z | float | {指名}の{関節名}のクォータニオンのz成分 |

指は、`thumb`(親指), `index`(人差し指), `middle`(中指), `ring`(薬指), `little`(小指) の順番で並んでいます。

関節は、親指は `cmc`(付け根), `mcp`(中心), `ip`(指先), それ以外の指は `mcp`(付け根), `pip`(中心), `dip`(指先) の順番で並んでいます。

### 手首の回転

ハンドトラッキングデバイスの手首の回転を取得するプロトコルです。

#### アドレス

`/DS/HC/Wrist`

#### 引数

`int version, string id, int is_left, float w, float x, float y, float z`

引数長は 7 となります。

| 引数名 | 型 | 説明 |
| --------- | ---- | ----------- |
| version | int | プロトコルバージョン (=1) |
| id | string | デバイスID |
| is_left | int | 左手か右手か |
| w | float | クォータニオンのw成分 |
| x | float | クォータニオンのx成分 |
| y | float | クォータニオンのy成分 |
| z | float | クォータニオンのz成分 |

### コントローラー入力

コントローラーの入力情報を取得するプロトコルです。

#### アドレス

`/DS/HC/Controller`

#### 引数

`int version, string id, int is_left, int a, int b, int sys, int trigger_button, int joystick_button, int trackpad_button, float trigger, float grip_value, float grip_force, float joystick_x, float joystick_y, float trackpad_x, float trackpad_y`

引数長は 16 となります。

| 引数名 | 型 | 説明 |
| --------- | ---- | ----------- |
| version | int | プロトコルバージョン (=1) |
| id | string | デバイスID |
| is_left | int | 左手か右手か |
| a | int | Aボタンの押下状態 |
| b | int | Bボタンの押下状態 |
| sys | int | システムボタンの押下状態 |
| trigger_button | int | トリガーボタンの押下状態 |
| joystick_button | int | ジョイスティックボタンの押下状態 |
| trackpad_button | int | トラックパッドタッチの押下状態 |
| trigger | float | トリガーの値 |
| grip_value | float | グリップの値 |
| grip_force | float | グリップの力量 |
| joystick_x | float | ジョイスティックのX軸の値 |
| joystick_y | float | ジョイスティックのY軸の値 |
| trackpad_x | float | トラックパッドのX軸の値 |
| trackpad_y | float | トラックパッドのY軸の値 |

各ボタンの押下状態の値は以下の通りです。

| 値 | 説明 |
| --------- | ---- |
| 0 | ボタンが押されていない |
| 1 | ボタンに触れている |
| 2 | ボタンが押されている |

## プロトコル一覧 (送信側)

### 接続要求

DivingStation に接続するための要求を送信するプロトコルです。

::: warning ポートについて

クライアントの受信用ポート番号はこのプロトコルを用いて自由に設定することができます。

DivingStation側の既定受信ポートは25790です。ポート番号はDivingStationの設定で変更できます。

:::

#### アドレス

`/DS/HC/Connect`

#### 引数

`int port_recv`

引数長は 1 となります。

| 引数名 | 型 | 説明 |
| --------- | ---- | ----------- |
| port_recv | int | 受信側のポート番号 |

### 切断要求

DivingStation から切断するための要求を送信するプロトコルです。

#### アドレス

`/DS/HC/Disconnect`

#### 引数

`int port_recv`

引数長は 1 となります。

| 引数名 | 型 | 説明 |
| --------- | ---- | ----------- |
| port_recv | int | 受信側のポート番号 |

### 振動

振動モジュールを持つデバイスの振動を発生させるためのプロトコルです。

#### アドレス

`/DS/HC/{id}/Haptics/Body`

id にはデバイスIDを指定します。デバイスIDは、デバイス情報プロトコルで取得できます。

#### 引数

`int version, int is_left, float frequency, float amplitude, float duration`

引数長は 5 となります。

| 引数名 | 型 | 説明 |
| --------- | ---- | ----------- |
| version | int | プロトコルバージョン (=1) |
| is_left | int | 左手か右手か |
| frequency | float | 振動の周波数 |
| amplitude | float | 振動の振幅  |
| duration | float | 振動の持続時間 (秒) |

`ampitude` は 0.0 ~ 1.0 の範囲で指定します。

### 指への触覚誘引

指への触覚モジュールを持つデバイスの触覚を発生させるためのプロトコルです。

#### アドレス

`/DS/HC/{id}/Haptics/Finger`

id にはデバイスIDを指定します。デバイスIDは、デバイス情報プロトコルで取得できます。

#### 引数

`int version, int is_left, int thumb, int index, int middle, int ring, int force`

引数長は 7 となります。
