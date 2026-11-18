# 共通 mock と独立 fixture

[English / 詳細・対応表](mock-server.md) · [ケース一覧](../fixtures/v2/README.md) · [出典・ライセンス](mock-provenance.md)

DSProtocol v2 の共通試験基盤です。正とする仕様は v2 の commit
`745e3903dc17f51d3e30e18d9dfa61bca7f0781f` です。対象は ContactGlove3 Pro と
DivingStation 2.0.0 以降です。Python 3.10 以降の標準ライブラリだけで動きます。

## 固定 SHA で取得する

仕様・mock・fixture の commit SHA とファイルごとの SHA-256 は
[`conformance/revisions.json`](../conformance/revisions.json) に記録します。
利用側はこのファイルの `mock_commit` / `fixture_commit` の40桁 SHA を固定してください。
この版では mock と fixture を同じ commit に固定しています。期待値は mock の出力とは独立しています。

```sh
git clone https://github.com/MeltInterfaceTechnologies/DivingStationProtocolSpecs.git
cd DivingStationProtocolSpecs
git checkout <revisions.json の公開 mock_commit の40桁SHA>
python3 -m unittest discover -s tests -v
python3 tools/check_oracle_sensitivity.py
```

commit に自分自身の SHA を埋め込むことはできないため、固定情報は後続の証跡 commit に追加します。
固定情報を含む checkout では、次で Git オブジェクトと現在のファイルの両方を検証できます。

```sh
python3 tools/verify_snapshot.py
python3 tools/audit_public.py
```

mock の commit 自体を検証する場合は、固定情報を別に保存して
`python3 tools/verify_snapshot.py --lock /absolute/path/revisions.json` を実行してください。
検証には固定先の Git 履歴が必要です。ZIP や履歴不足の shallow clone だけでは Git オブジェクトの照合はできません。

## 決定的な試験

```sh
python3 -m unittest discover -s tests -v
python3 tools/check_oracle_sensitivity.py
python3 -m ds_mock.replay fixtures/v2/scenarios/delivery-faults.json
```

試験用コアは整数の仮想時刻を引数に取り、ソケット、sleep、実時間、乱数を使いません。
再生 CLI は実際の結果を表示し、期待値を書き換えません。シナリオ内の `expected` はテストだけが参照します。

- OSC の固定バイト列 4 件、不正・非対応パケット 10 件、時刻境界 8 件。
- 7 種の正常入力の全フィールド・バイト列、配置確認用 anchor 3 件、mock validator 向け回帰入力 88 件。
- profile と haptics を中心としたコマンド 39 件。
- 接続元の分離、keepalive、期限切れ、仮想承認、欠損・重複・逆順を含む時系列シナリオ 5 件。

期待値のフィールド名、値、判定は公開仕様から転記した静的な oracle です。
短い OSC バイト列は手書きし、大きい固定パケットは独立した `struct` ベースの手順で作成しました。
期待値の変更時は根拠となる仕様もレビューしてください。入力の反復・編集記法はケースの重複を減らすためのものです。

`check_oracle_sensitivity.py` は、時刻下位ワードの符号、骨格とセンサーの quaternion の w/x、ノード順序、Ergonomics 順序を故意に取り違え、
独立 fixture の試験が assertion failure になることと、予期しない error がゼロであることを確認します。
検出対象はこの5種類です。serializer と parser が共通の誤りを持つ場合の確認に使います。


`delivery.json` schema 2 の `mock_expectation` は mock validator の回帰試験向けです。この corpus は SDK の仕様適合の合否を割り当てません。SDK の試験は既公開仕様に従う必要があり、[不正な record を含むメッセージは全体を破棄する総則](ds_protocol_v2_EN.md#records-and-validation) を維持します。

64 byte の骨格 ID、1200 byte の datagram、profile 文字列の上限と総則を、各境界入力の SDK の合否へどう適用するかは、この作業では未解決です。`unspecified` は corpus が判定を割り当てていないという意味であり、その入力の受入れが仕様上許されると決めたものではありません。SDK の実際の挙動も、仕様適合の結論とは区別して記録します。

骨格・センサーの正常入力は `(1, 2, 4, 10) / 11` の符号付き順列を用い、w/x/y/z と関節・センサーの順序を識別できます。二乗和は整数設計で 1、OSC float32 では丸め誤差の範囲です。既存の配置確認用データは `layout-sentinels.json` に保持しています。`normal-stream.json` は ID `L` の 6 種のデータを一度送り、polling 用の inventory を保持します。合成データであり、解剖学的な姿勢や順運動学の正しさを評価するデータではありません。詳細は [fixture の形式と用途](../fixtures/v2/README.md) を参照してください。

## UDP とデモを別に実行する

```sh
# loopback UDP の動作確認
python3 -m unittest discover -s integration_tests -v
# 固定パケットを各接続に1回だけ再生
python3 -m ds_mock.server --port 25791 --stream fixtures/v2/normal-stream.json
# 実時間の合成モーションを継続配信するデモ
python3 -m ds_mock.demo --port 25791
```

UDP は `127.0.0.1` にだけ bind します。`--port 0` なら空きポートを選び、先頭の JSON 行に表示します。
クライアントは受信用ポートを Connect に渡し、Connect、keepalive、profile、haptics、Disconnect に同じ送信ソケットを使ってください。
終了は Ctrl+C です。DivingStation と同じポートで同時に起動しないでください。

固定ストリームの時刻は、その接続が承認された時点からの相対ミリ秒です。keepalive で先頭には戻りません。
予定時刻を過ぎたパケットは列挙順に送り、生成時刻による並べ替えをしません。欠損パケットも補いません。
UDP の到着時刻や欠損は OS の動作に依存するため、決定的な判定はオフライン試験で行います。

デモは Device、Ergonomics、Controller、RawSensorTransforms、HandSkeleton、HandSkeletonRaw を送ります。
デバイス ID は `MOCK-L` / `MOCK-R`、profile UUID は末尾 `0001` / `0002` の固定値です。
値は説明用の合成データで、実測、較正、IK、retarget 処理の結果ではありません。
haptics は範囲検証と記録だけを行い、物理的な振動は発生しません。
ライブ CLI の診断履歴は最新1024件を保持します。試験用エンジンは既定で全件を保持し、オフライン再生での保持数制限は拒否します。

## 自動試験

GitHub Actions は Ubuntu / Python 3.10・3.12・3.13 で fixture・mutation と別コマンドの UDP 試験を実行します。
初回payloadのlock不在と、後続revisionでのlock必須化は[検証手順](../conformance/validation.md#automated-checks)に記載しています。
実時間のdemoは手動で確認してください。

## 対応範囲と制約

詳細は [English 版の対応表](mock-server.md#coverage-and-limits) にあります。
7 種の v2 配送形式、完全な record、型と件数、上限、UUID、UTF-8 バイト数、tracking_state、生成時刻、profile 応答、
haptics の値域と接続状態を扱います。不正 record を含むメッセージは全体を破棄し、欠損を 0 や identity quaternion で埋めません。
tracking_state 1/2 の有限な値は表示用に残しますが、制御・速度推定・補間の入力には使用できません。

同時接続上限は承認待ちを含めて既定 8、1 秒未満の Connect は期限を延ばさず無視します。
これらの数値や応答は mock の方針です。仕様は上限の数値や短すぎる再送に対するサーバー応答を定めていません。
同じ送信 endpoint が複数の受信ポートを登録した場合、profile 応答はその送信元に結び付く各ポートに送ります。この多重化は本体互換を主張しません。
RawSensorTransforms の非有限値と未登録の合成 ID への haptics の拒否も mock 独自の方針です。

検証対象は静的なプロトコルケースと loopback adapter です。実機、SDK 相互接続、LAN 設定・承認 UI・セキュリティ、負荷、姿勢の幾何学的な正しさは利用先の環境で確認してください。
OSC bundle、他の OSC 型、パターン展開、v1、Wrist、Hand/HandQuat、指 haptics、通常の CG3 には対応しません。
仕様にない stale/duplicate 判定やクライアントの timeout 規則は追加していません。
