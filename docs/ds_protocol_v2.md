# DivingStationProtocol (v2)

[English](ds_protocol_v2_EN.md) | 日本語

## 概要

DivingStationProtocol とは、DivingStationを介してMelt Interface Technologies製デバイスとの通信を行うためのプロトコルです。
v2ではContactGlove3 Proに対応しています。通常のContactGlove3ではDivingStationProtocolを使用できません。

ContactGlove, ContactGlove2, ContactSheet との互換性はありません。

通信には、OSC (Open Sound Control) を使用しています。

プロトコルの送受信によって、以下のようなことが可能となります。

- ハンドトラッキングデバイスの関節位置・回転の取得
- ハンドトラッキングデバイスの指の曲げ・開きの取得
- コントローラー入力の取得
- デバイスのバッテリー残量の取得
- デバイスの振動の制御

v1との主な違いは以下の通りです。

- プロトコルバージョンは `2` です。
- OSCアドレスのprefixは `/DS2/HC` です。
- DivingStation側のデフォルト受信ポートは `25791` です。
- v1の `/DS/HC/Hand` は、`/DS2/HC/Ergonomics` に置き換わります。
- v1の `/DS/HC/HandQuat` は、`/DS2/HC/HandSkeleton` に置き換わります。
- `/DS2/HC/Device` はペア単位ではなく、グローブデバイス単位の情報を配信します。

## 対応ソフトウェア

- DivingStation v2.0.0以降

## 使用方法

DivingStationProtocolでは、OSC (Open Sound Control) を使用して通信を行います。
使用したい言語や環境に合わせて、OSCライブラリを選択してください。

最初に、DivingStation が起動していること、およびデバイスが接続されていることを確認してください。

::: warning LAN公開と許可セッション

既定では同一マシンからのみ接続できます。同一マシンのクライアントはDivingStationの受信先として `127.0.0.1` を使用してください。

LAN上のクライアントを利用する場合は、DivingStationの設定でプロトコルのLAN公開を明示的に有効化します。LANからのConnectの扱いはDivingStationで設定された接続承認ポリシーに従います。利用者の許可が必要な設定では、Connectは保留され、DivingStation上で利用者が許可するとデータ配信やデバイスへのコマンド送信が可能です。

許可セッションは暗号化または暗号学的な認証を提供しません。信頼できるLANでのみ使用してください。

:::

次に、DivingStation との接続を行います。
DivingStation（既定のポート番号: `25791`）に対し、以下の接続要求プロトコルを送信します。DivingStation側の受信ポートは設定で変更できます（変更する場合、古いポートを参照しているクライアントの接続先設定も同様に変更してください）。

- 例: クライアントの受信用ポート番号が 25788 である場合

```plaintext
/DS2/HC/Connect 25788
```

(`/DS2/HC/Connect` はOSCアドレスを、`25788` は引数を表します。)

接続に成功した場合、25788番ポートに対してDivingStation から各種データが送信されるようになります。

DivingStationの設定上LANクライアントの接続に許可が必要な場合、利用者が許可モーダルで承認するまでデータを受信しません。

すべてのv2クライアントは、接続承認の要否や接続元（localhost / LAN）にかかわらず、接続を維持する間は30秒ごとに`Connect`を再送しなければなりません。この再送はkeepaliveであり、許可待ちの間および承認後のいずれでも必要です。

SDKは、Connect、keepalive、Disconnect、Hapticsの送信に同一のUDP送信socketを継続して使用してください。`port_recv` はDivingStationからのデータを受信するポートであり、許可セッションはConnectの送信元endpointと `port_recv` の組み合わせに関連付けられます。

許可セッションは最後のConnectから90秒後に失効します。DivingStationは同時に許可するv2クライアント数を制限します。Connectの再試行が必要な場合も、1秒未満の間隔で送信してはいけません。

通信を終了する際は、切断要求プロトコルを送信します。

```plaintext
/DS2/HC/Disconnect 25788
```

切断に成功すると、DivingStation からのデータの受信が停止します。

## 構成

### アドレスと引数

DivingStationProtocolに含まれる各プロトコルは、OSCのアドレスと引数の組み合わせで構成されています。

アドレスによって、プロトコルの種類を識別します。

引数は、float, int, stringのいずれかの型を持つ値の組です。`is_`で始まるフィールドは0 (=False) または1 (=True) の値を取り、真偽値を表します。

### バージョンと時刻

各プロトコルの先頭引数 `version` は、v2では `2` です。クライアントは `version` が `2` ではないmessageを無視します。

`timestamp_ms` はUnixタイムをミリ秒単位で表す数値です。OSC上では `timestamp_ms_hi` と `timestamp_ms_lo` の2つの `int` に分割して送信します。クライアントはどちらも unsigned 32bit として結合します。

`generated_at_ms_hi` と `generated_at_ms_lo` を持つrecordでは、結合した値をフレーム生成時刻として使用します。これはOSC messageの送信時刻ではありません。

### recordと検証

`*`は直前のカッコ内の0回以上の繰り返しを表します。

DivingStationからクライアントへ送信するデータ配信プロトコルでは、`version` の後ろに同一形式のrecordを0回以上並べます。各プロトコルがより小さい上限を定めない限り、1 messageあたりの最大record数は8です。最大record数を超えるmessageは不正なmessageとして扱います。

不正なrecordを含むmessageは、message全体を破棄します。クライアントは、不正recordのみのskipやdefault値の補完を行いません。

## 3次元座標系
位置はメートル単位で表します。
クォータニオンは `w, x, y, z` の順番で表します。

この仕様では、`wrist` を原点とする手の座標系を「手首を原点とする手モデル座標系」と呼びます。`/DS2/HC/HandSkeleton` の位置はretarget profileの手モデル座標系における座標です。`/DS2/HC/HandSkeletonRaw` の位置はsource skeletonの手モデル座標系における座標です。どちらもroot nodeは `wrist` であり、各node位置はメートル単位で表します。

`/DS2/HC/HandSkeletonRaw` は、校正済みのEMF追跡結果に対してIKおよびforward kinematicsを適用したsource skeletonです。EMFの生値、device-local座標、または[`RawSensorTransforms`](#raw-sensor-transform)ではありません。retarget profileの `bind_points`、`bind_rotations`、`rest_alignment`、model-space変換は適用しません。

関節回転は、[スケルトン回転順序](#スケルトン回転順序) に記載された19個のnodeについて、対応nodeの親nodeに対するlocal quaternionです。`wrist` と各 `*_tip` の回転は送信しません。

通信フレームには親子情報を含めず、クライアントが固定topologyを知っている前提で復元します。

手首を原点とする手モデル座標系は、左右どちらの手でも右手系座標です。軸方向は以下の通りです。

| 軸 | 向き |
| --------- | ---- |
| +X | 指先から手首へ向かう方向。伸ばした中指は `wrist` から見ておおむね -X へ伸びます |
| +Y | 手のひらから手の甲へ向かう方向。指腹側は -Y、爪・手の甲側は +Y です |
| +Z | 手幅方向。右手では小指側から親指側へ向かい、左手では親指側から小指側に向かいます |

左右対称な姿勢を比較すると、同じ解剖学的な点は右手と左手でX/Yが同じ、Zの符号が反転した位置になります。

local quaternion は現在姿勢のnode orientationを親nodeから見た回転として表します。基準姿勢（bind pose）では、HandSkeletonはretarget profileのbind local quaternion、HandSkeletonRawはsource skeletonの固定bind local quaternionと一致します。

## プロトコル一覧 (DivingStationからクライアント)

### デバイス情報

DivingStation に接続されている全てのハンドトラッキングデバイスの情報を取得するプロトコルです。

#### アドレス

`/DS2/HC/Device`

#### 引数

`int version, (string id, string pair_id, int battery_percentage, int is_haptics, int is_left, int device_type, int color, int connected_state, string name, int is_external_power_present)*`

引数長は 1+10n (nはデバイス数) となります。

| 引数名 | 型 | 説明 |
| --------- | ---- | ----------- |
| version | int | プロトコルバージョン (=2) |
| id | string | デバイスID |
| pair_id | string | ペアとなっているグローブのID。存在しない場合は空文字列 |
| battery_percentage | int | バッテリー残量（0から100の整数値あるいは-1。-1は残量推定値の無効を表す） |
| is_haptics | int | 振動機能を持つかどうか |
| is_left | int | 左手か右手か |
| device_type | int | デバイスの種類 |
| color | int | デバイスの表示色設定 |
| connected_state | int | デバイスの接続状況 |
| name | string | デバイス名 |
| is_external_power_present | int | 外部電源が検出されているか |

`device_type`の値と、対応するデバイスの種類は以下の通りです。

| device_type | デバイスの種類 |
| --------- | ---- |
| 0 | ContactGlove |
| 1 | ContactSheet |
| 2 | ContactGlove2 |
| 3 | ContactGlove3シリーズ |

v2で扱う`device_type`は`3`のみです。この値はContactGlove3シリーズを識別し、Protocolへの対応を示すものではありません。Protocolを利用できるのはContactGlove3 Proのみです。

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

`connected_state`の値と、対応する接続状況は以下の通りです。

| connected_state | 接続状況 |
| --------- | ---- |
| 0 | 状況不明 |
| 1 | 接続 |
| 2 | 未接続 |
| 3 | 接続試行中 |

::: info バッテリー残量の値

`battery_percentage` は、デバイスが現在の残量を有効に報告できる場合は0から100の整数値です。`-1` は無効値であり、未接続、外部電源によって残量推定を停止した場合などに使用します。

:::

### 指の曲げ・開き値

ハンドトラッキングデバイスの指の曲げ値と開き値を取得するプロトコルです。

v1の `/DS/HC/Hand` は廃止し、v2ではこのプロトコルを使用します。

#### アドレス

`/DS2/HC/Ergonomics`

#### 引数

`int version, (string id, int is_left, int generated_at_ms_hi, int generated_at_ms_lo, int tracking_state, float thumb_cmc, float thumb_mcp, float thumb_ip, float thumb_tilt, float index_mcp, float index_pip, float index_dip, float index_tilt, ...)*`

引数長は 1+25n (nはデータ数) となります。

| 引数名 | 型 | 説明 |
| --------- | ---- | ----------- |
| version | int | プロトコルバージョン (=2) |
| id | string | デバイスID |
| is_left | int | 左手か右手か |
| generated_at_ms_hi | int | フレーム生成時刻の上位32bit |
| generated_at_ms_lo | int | フレーム生成時刻の下位32bit |
| tracking_state | int | 追跡状態 |
| thumb_cmc | float | 親指のCMC関節の曲げ角度 |
| thumb_mcp | float | 親指のMCP関節の曲げ角度 |
| thumb_ip | float | 親指のIP関節の曲げ角度 |
| thumb_tilt | float | 親指の傾き角度 |
| {指名}_mcp | float | {指名}のMCP関節の曲げ角度 |
| {指名}_pip | float | {指名}のPIP関節の曲げ角度 |
| {指名}_dip | float | {指名}のDIP関節の曲げ角度 |
| {指名}_tilt | float | {指名}の傾き角度 |

値は、[Ergonomics値順序](#ergonomics値順序) に記載された順番で並びます。

各値は度単位です。曲げ角度は伸びた状態を基準とした角度として扱います。傾き角度はデフォルト状態を0°とした角度として扱います。

`tracking_state` の値と扱いは[追跡状態](#追跡状態)に従います。

### コントローラー入力

コントローラーの入力情報を取得するプロトコルです。

#### アドレス

`/DS2/HC/Controller`

#### 引数

`int version, (string id, int is_left, int a, int b, int sys, int trigger_button, int joystick_button, int trackpad_button, float trigger, float grip_value, float grip_force, float joystick_x, float joystick_y, float trackpad_x, float trackpad_y)*`

引数長は 1+15n (nはコントローラー数) となります。

| 引数名 | 型 | 説明 |
| --------- | ---- | ----------- |
| version | int | プロトコルバージョン (=2) |
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

各アナログ値の範囲は以下の通りです。

| 引数名 | 範囲 |
| --------- | ---- |
| trigger | 0.0〜1.0 |
| grip_value | 0.0〜1.0 |
| grip_force | 0.0〜1.0 |
| joystick_x | -1.0〜1.0 |
| joystick_y | -1.0〜1.0 |
| trackpad_x | -1.0〜1.0 |
| trackpad_y | -1.0〜1.0 |

各アナログ値はDivingStation側でキャリブレーションおよびデッドゾーン処理済みの値を送信します。

範囲外の値またはNaN/Infを含むmessageは不正なmessageとして扱います。

ContactGlove3 Proの現在の実装では、トラックパッド入力は連続アナログ値ではなく、`trackpad_x = 0.0`、`trackpad_y = -1.0, 0.0, 1.0` のいずれかとして送信されます。

### 手のスケルトン（Retarget済み）

ハンドトラッキングデバイスで得られた手のスケルトンをRetarget profileで変換した結果の関節位置と回転を取得するプロトコルです。

v1の `/DS/HC/HandQuat` は廃止し、v2ではこのプロトコルを使用します。

#### アドレス

`/DS2/HC/HandSkeleton`

#### 引数

`int version, string id, string profile_uuid, int is_left, int generated_at_ms_hi, int generated_at_ms_lo, int tracking_state, float wrist_p_x, float wrist_p_y, float wrist_p_z, ..., float little_tip_p_z, float thumb_cmc_q_w, float thumb_cmc_q_x, float thumb_cmc_q_y, float thumb_cmc_q_z, ..., float little_dip_q_z`

引数長は 158 となります。`/DS2/HC/HandSkeleton` では、Skeleton recordの数は常に1です。左右の手は別々のOSC messageとして送信します。

| 引数名 | 型 | 説明 |
| --------- | ---- | ----------- |
| version | int | プロトコルバージョン (=2) |
| id | string | デバイスID |
| profile_uuid | string | retarget profile の固定UUID |
| is_left | int | 左手か右手か |
| generated_at_ms_hi | int | フレーム生成時刻の上位32bit |
| generated_at_ms_lo | int | フレーム生成時刻の下位32bit |
| tracking_state | int | 追跡状態 |
| {node_id}_p_x | float | 関節位置のX成分 |
| {node_id}_p_y | float | 関節位置のY成分 |
| {node_id}_p_z | float | 関節位置のZ成分 |
| {node_id}_q_w | float | 関節回転クォータニオンのw成分 |
| {node_id}_q_x | float | 関節回転クォータニオンのx成分 |
| {node_id}_q_y | float | 関節回転クォータニオンのy成分 |
| {node_id}_q_z | float | 関節回転クォータニオンのz成分 |

関節位置は、[スケルトンノード順序](#スケルトンノード順序) に記載された25個のnodeについて、各nodeごとに `x, y, z` の順番で並びます。

関節回転は、[スケルトン回転順序](#スケルトン回転順序) に記載された19個のnodeについて、各nodeごとに `w, x, y, z` の順番で並びます。

`wrist` と各 `*_tip` node には、回転を含めません。

関節位置はスケルトンのnode位置であり、座標系、単位、原点は[3次元座標系](#3次元座標系)に従います。関節回転は対応nodeの親nodeに対するlocal quaternionです。

DivingStationは、25個すべてのnode位置と19個すべての関節回転を持ち、各position成分とquaternion成分が有限値であるframeだけを送信します。欠損node、欠損rotation、NaN、Infは0またはidentity quaternionで補完せず、欠損値を含むframeは送信しません。

`profile_uuid` はprofile作成時にDivingStationが割り当てるUUID形式の文字列です。UUID形式とは、ASCIIの16進数とハイフンによる `8-4-4-4-12` 形式の36 byte文字列を指します。profileの生存期間を通じて固定であり、別のprofileに再利用してはいけません。空文字列またはUUID形式でない `profile_uuid` を含むHandSkeleton recordは不正です。DivingStationはそのようなprofileを有効化せず、該当するHandSkeleton recordを送信してはいけません。profileの表示名と説明は[retarget profile情報](#retarget-profile情報)で取得できます。

`tracking_state` の値と扱いは[追跡状態](#追跡状態)に従います。

1 recordをOSCでシリアライズしたdatagramは1200 byte以下でなければなりません。DivingStationは上限を超えるrecordを送信せず、IP fragmentationに依存してはいけません。`id` は64 byte以下のUTF-8文字列でなければなりません。

### 手のスケルトン（Raw）

ハンドトラッキングデバイスで得られた手のスケルトンの関節位置と回転を取得するプロトコルです。
Retarget profileで変換する前の生のスケルトン値を取得するために使用します。

#### アドレス

`/DS2/HC/HandSkeletonRaw`

#### 引数

`int version, string id, int is_left, int generated_at_ms_hi, int generated_at_ms_lo, int tracking_state, float wrist_p_x, float wrist_p_y, float wrist_p_z, ..., float little_tip_p_z, float thumb_cmc_q_w, float thumb_cmc_q_x, float thumb_cmc_q_y, float thumb_cmc_q_z, ..., float little_dip_q_z`

引数長は157となります。`/DS2/HC/HandSkeletonRaw` ではSkeleton recordの数は常に1です。左右の手は別々のOSC messageとして送信します。

| 引数名 | 型 | 説明 |
| --------- | ---- | ----------- |
| version | int | プロトコルバージョン (=2) |
| id | string | デバイスID |
| is_left | int | 左手か右手か |
| generated_at_ms_hi | int | フレーム生成時刻の上位32bit |
| generated_at_ms_lo | int | フレーム生成時刻の下位32bit |
| tracking_state | int | 追跡状態 |
| {node_id}_p_x | float | 関節位置のX成分 |
| {node_id}_p_y | float | 関節位置のY成分 |
| {node_id}_p_z | float | 関節位置のZ成分 |
| {node_id}_q_w | float | 関節回転クォータニオンのw成分 |
| {node_id}_q_x | float | 関節回転クォータニオンのx成分 |
| {node_id}_q_y | float | 関節回転クォータニオンのy成分 |
| {node_id}_q_z | float | 関節回転クォータニオンのz成分 |

関節位置は、[スケルトンノード順序](#スケルトンノード順序) に記載された25個のnodeについて、各nodeごとに `x, y, z` の順番で並びます。

関節回転は、[スケルトン回転順序](#スケルトン回転順序) に記載された19個のnodeについて、各nodeごとに `w, x, y, z` の順番で並びます。

`wrist` と各 `*_tip` node には、回転を含めません。

関節位置はスケルトンのnode位置であり、座標系、単位、原点は[3次元座標系](#3次元座標系)に従います。関節回転は対応nodeの親nodeに対するlocal quaternionです。

DivingStationは、25個すべてのnode位置と19個すべての関節回転を持ち、各position成分とquaternion成分が有限値であるframeだけを送信します。欠損node、欠損rotation、NaN、Infは0またはidentity quaternionで補完せず、欠損値を含むframeは送信しません。

`tracking_state` の値と扱いは[追跡状態](#追跡状態)に従います。

1 recordをOSCでシリアライズしたdatagramは1200 byte以下でなければなりません。DivingStationは上限を超えるrecordを送信せず、IP fragmentationに依存してはいけません。`id` は64 byte以下のUTF-8文字列でなければなりません。

### retarget profile情報

`/DS2/HC/HandSkeleton` に含まれる `profile_uuid` の表示用情報を取得するプロトコルです。profileそのものの座標や関節値はHandSkeleton messageに含まれるため、profile情報の応答を受信していないことはスケルトン値の解釈を妨げません。

#### アドレス

`/DS2/HC/HandSkeleton/Profile`

#### 引数

`int version, int request_id, string profile_uuid, int status, string name, string description`

引数長は6となります。

| 引数名 | 型 | 説明 |
| --------- | ---- | ----------- |
| version | int | プロトコルバージョン (=2) |
| request_id | int | requestを識別するクライアント指定の値。要求時の値をそのまま返す |
| profile_uuid | string | `status` に応じたprofile UUID |
| status | int | profile情報の取得結果 |
| name | string | 利用者向けのprofile名。UTF-8で128 byte以下 |
| description | string | profileの説明。UTF-8で768 byte以下 |

`status` の値は以下の通りです。

| status | 説明 |
| --------- | ---- |
| 0 | profileが存在する。`name` と `description` を使用できる |
| 1 | UUID形式は正しいがprofileが存在しない。`name` と `description` は空文字列 |
| 2 | 問い合わせが不正。`profile_uuid`、`name`、`description` は空文字列 |

`request_id` は、`status` にかかわらず要求時のint値をそのまま返します。`status` が0の場合、DivingStationは保存されているprofileの `profile_uuid` をそのまま応答に含めます。`status` が1の場合、要求で渡された `profile_uuid` をそのまま応答に含めます。`status` が2の場合、応答の `profile_uuid` は空文字列です。クライアントは未知の `profile_uuid` を受信したとき、必要に応じて[retarget profile情報要求](#retarget-profile情報要求)を送信し、`profile_uuid` をキーに結果をキャッシュできます。定義されていない `status` の応答は不正なmessageとして扱います。

`name` の128 byteおよび `description` の768 byteは、UTF-8でエンコードしたバイト数です（OSC文字列の終端NULは含めません）。DivingStationはprofileの作成、更新、または読み込み時にこの上限を検証し、超過するprofileを拒否しなければなりません。送信時に文字列を途中で切断してはいけません。

### Raw sensor Transform

raw sensor の位置・回転を取得するプロトコルです。

DivingStationが片手分の5個のsensor Transformを1 recordとして送信し、クライアントが受信します。

#### アドレス

`/DS2/HC/RawSensorTransforms`

#### 引数

`int version, (string id, int is_left, int generated_at_ms_hi, int generated_at_ms_lo, float thumb_sensor_p_x, float thumb_sensor_p_y, float thumb_sensor_p_z, float thumb_sensor_q_w, float thumb_sensor_q_x, float thumb_sensor_q_y, float thumb_sensor_q_z, ..., float little_sensor_q_z)*`

引数長は 1+39n (nはデータ数) となります。

| 引数名 | 型 | 説明 |
| --------- | ---- | ----------- |
| version | int | プロトコルバージョン (=2) |
| id | string | デバイスID |
| is_left | int | 左手か右手か |
| generated_at_ms_hi | int | フレーム生成時刻の上位32bit |
| generated_at_ms_lo | int | フレーム生成時刻の下位32bit |
| {sensor_id}_p_x | float | sensor位置のX成分 |
| {sensor_id}_p_y | float | sensor位置のY成分 |
| {sensor_id}_p_z | float | sensor位置のZ成分 |
| {sensor_id}_q_w | float | sensor回転クォータニオンのw成分 |
| {sensor_id}_q_x | float | sensor回転クォータニオンのx成分 |
| {sensor_id}_q_y | float | sensor回転クォータニオンのy成分 |
| {sensor_id}_q_z | float | sensor回転クォータニオンのz成分 |

sensor Transformは、[Raw sensor Transform順序](#raw-sensor-transform順序) に記載された5個のsensorについて、各sensorごとに `p_x, p_y, p_z, q_w, q_x, q_y, q_z` の順番で並びます。

位置はメートル単位で表します。クォータニオンは `w, x, y, z` の順番で表します。

ここでの raw sensor Transform は、DivingStation が推定した各指sensorのTransformです。EMF raw値やdevice-local座標ではなく、`/DS2/HC/HandSkeleton` と同じ手首を原点とする手モデル座標系に変換した値を送信します。

位置は `wrist` を原点としたsensor中心位置です。

回転はsensor local frameから手首を原点とする手モデル座標系への向きを表すクォータニオンです。identity quaternion の場合、sensor local frame のX/Y/Z軸は手首を原点とする手モデル座標系のX/Y/Z軸と一致します。

左手の raw sensor Transform も、`/DS2/HC/HandSkeleton` と同じ右手系の手首を原点とする手モデル座標系で表します。左右対称な姿勢を比較すると、対応するsensor位置はX/Yが同じでZの符号が反転します。

## プロトコル一覧 (クライアントからDivingStation)

### 接続要求

DivingStation に接続するための要求を送信するプロトコルです。

::: warning ポートについて

クライアントの受信用ポート番号はこのプロトコルを用いて自由に設定することができます。

DivingStation側のデフォルト受信ポートは 25791 で、設定にて変更可能です。

:::

#### アドレス

`/DS2/HC/Connect`

#### 引数

`int port_recv`

引数長は 1 となります。

| 引数名 | 型 | 説明 |
| --------- | ---- | ----------- |
| port_recv | int | クライアントの受信用ポート番号 |

### 切断要求

DivingStation から切断するための要求を送信するプロトコルです。

#### アドレス

`/DS2/HC/Disconnect`

#### 引数

`int port_recv`

引数長は 1 となります。

| 引数名 | 型 | 説明 |
| --------- | ---- | ----------- |
| port_recv | int | クライアントの受信用ポート番号 |

DivingStation は、送信元IPアドレスと `port_recv` の組み合わせをクライアント識別子として扱います。複数IPから同じ `port_recv` で接続された場合は別クライアントとして扱い、同一IPアドレス・同一 `port_recv` の重複接続は1つにまとめます。

LAN公開が有効な場合、DivingStationはConnectを、送信元UDP endpointと `port_recv` の組み合わせに対する許可済みセッションの作成または更新の要求として処理します。許可待ち、期限切れ、または未許可の送信元からのConnect以外のクライアントmessageは処理しません。

### retarget profile情報要求

`/DS2/HC/HandSkeleton` の `profile_uuid` に対応する表示名と説明を取得する要求です。接続済みのクライアントだけが送信できます。DivingStationは、Connectで登録されたクライアント受信用ポートへ[retarget profile情報](#retarget-profile情報)を応答します。

#### アドレス

`/DS2/HC/HandSkeleton/Profile/Get`

#### 引数

`int version, int request_id, string profile_uuid`

引数長は3となります。

| 引数名 | 型 | 説明 |
| --------- | ---- | ----------- |
| version | int | プロトコルバージョン (=2) |
| request_id | int | クライアントがresponseとの対応付けに使用する値 |
| profile_uuid | string | 問い合わせるretarget profile UUID |

`profile_uuid` はUUID形式でなければなりません。UUID形式とは、ASCIIの16進数とハイフンによる `8-4-4-4-12` 形式の36 byte文字列を指します。空文字列、36 byte以外の文字列、またはUUID形式でない文字列は不正です。引数の数と型および `version` が正しいrequestで `profile_uuid` だけが不正な場合、DivingStationは同じ `request_id` と `status = 2` の[retarget profile情報](#retarget-profile情報)を返します。引数の数・型または `version` が不正なmessageは破棄し、応答しません。

存在しない `profile_uuid` でもDivingStationは応答を返し、応答の `status` を `1` とします。

### 振動

振動モジュールを持つデバイスの振動を発生させるためのプロトコルです。

#### アドレス

`/DS2/HC/{id}/Haptics/Body`

id にはデバイスIDを指定します。デバイスIDは、デバイス情報プロトコルで取得できます。

#### 引数

`int version, float frequency, float amplitude, float duration`

引数長は 4 となります。

| 引数名 | 型 | 説明 |
| --------- | ---- | ----------- |
| version | int | プロトコルバージョン (=2) |
| frequency | float | 振動の周波数 (Hz) |
| amplitude | float | 振動の振幅 |
| duration | float | 振動の持続時間 (秒) |

`frequency` は 100.0 ~ 500.0 の範囲で指定します。
`amplitude` は 0.0 ~ 1.0 の範囲で指定します。
`duration` は 0.001 ~ 1.0 の範囲で指定します。

範囲外の値は受理せず、clampは行いません。

LAN公開時は、許可済みv2セッションの送信元から受信したmessageだけを処理します。許可待ち、期限切れ、または未許可のクライアントから送信されたHaptics messageは破棄します。

## 追跡状態

`tracking_state` を持つIK由来のrecordは、以下の値を使用します。

| tracking_state | 状態 | record値の扱い |
| --------- | ---- | ----------- |
| 0 | `Tracked` | 現在のIK処理から得た有効な値 |
| 1 | `IkFailed` | recordの生成に必要なIK処理を実行したが、失敗を報告したframe。完全で有限な位置・回転・角度値は表示・診断に使用できるが、クライアントは制御、速度推定、補間の入力として使用してはいけない |
| 2 | `NotAttempted` | recordの生成に必要なIK処理を実施しなかったframe。前段階の処理失敗や入力欠損で試行できなかった場合に加え、更新間隔の制御などにより姿勢計算の実施が不要と判断された場合を含む。完全で有限な位置・回転・角度値は表示・診断に使用できるが、クライアントは制御、速度推定、補間の入力として使用してはいけない |

他の値を持つrecordは不正なrecordとして扱います。

`NotAttempted` 自体はIK処理の失敗を意味しません。例えば、更新間隔の制御によりIK処理を間引き、既存の姿勢を再利用する場合も含まれます。

`IkFailed` または `NotAttempted` のrecordを送信する場合も、DivingStationは完全で有限な位置・回転・角度値だけを送信します。0またはidentity quaternionによる補完を行ってはいけません。完全な値を用意できない場合はrecordを送信しません。

`/DS2/HC/HandSkeleton` の状態はretarget処理のIK結果を表します。`IkFailed` はretarget処理を試行して失敗したこと、`NotAttempted` はretarget処理を実施しなかったことを表します。source skeletonの失敗などにより試行できなかった場合だけでなく、姿勢計算の実施が不要と判断された場合も含みます。`/DS2/HC/HandSkeletonRaw` と `/DS2/HC/Ergonomics` の状態は、retarget前のsource skeletonを求めるIK結果を表します。同一時刻の各messageで状態が異なることがあり、例えばretarget処理だけが失敗した場合はHandSkeletonだけが `IkFailed` になり得ます。source skeletonを求めるIKを試行して失敗した場合はRaw SkeletonとErgonomicsが `IkFailed`、それを入力とするHandSkeletonが `NotAttempted` になり得ます。source skeletonを求めるIKの前段階で失敗した場合は、3つすべてが `NotAttempted` になり得ます。

## スケルトン定義

`/DS2/HC/HandSkeleton` と `/DS2/HC/HandSkeletonRaw` は、25個の固定topologyを持つスケルトンを送信します。
通信フレームには親子情報を含めず、クライアントがこのtopologyを知っている前提で復元します。

### スケルトンノード順序

`/DS2/HC/HandSkeleton` と `/DS2/HC/HandSkeletonRaw` の関節位置は、以下の順番で並びます。

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

### スケルトン回転順序

`/DS2/HC/HandSkeleton` の関節回転は、以下の順番で並びます。

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

## Ergonomics定義

### Ergonomics値順序

`/DS2/HC/Ergonomics` の値は、以下の順番で並びます。

| index | 名前 |
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

## Raw sensor Transform定義

### Raw sensor Transform順序

`/DS2/HC/RawSensorTransforms` のsensor Transformは、以下の順番で並びます。

| index | sensor_id |
| --------- | ---- |
| 0 | `thumb_sensor` |
| 1 | `index_sensor` |
| 2 | `middle_sensor` |
| 3 | `ring_sensor` |
| 4 | `little_sensor` |

## 廃止プロトコル

### Wrist

v2では `/DS2/HC/Wrist` を定義しません。

ContactGlove3 ProはWrist回転を取得する機能を持たないため、v2初期仕様ではWrist単独プロトコルを定義しません。将来のデバイスでWrist回転を取得できる場合は、`/DS2/HC/HandSkeleton` の `wrist` nodeに統合する方針を検討します。

### Haptics/Finger

v2では、v1の `/DS/HC/{id}/Haptics/Finger` 相当の指触覚コマンドは定義しません。

### Hand, HandQuat
- v1の `/DS/HC/Hand` は、`/DS2/HC/Ergonomics` に置き換わります。
- v1の `/DS/HC/HandQuat` は、`/DS2/HC/HandSkeleton` に置き換わります。
