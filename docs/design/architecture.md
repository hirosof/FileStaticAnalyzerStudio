# アーキテクチャ

> 状態：設計第1版（生きた文書。各フェーズ開始時に見直す）

## 概要

PE / LNK / Office ファイルを対象とした **静的解析（実行せずに構造・内容を解析）** に特化した
Web アプリ。マルウェア解析・トリアージ用途を意識した「ファイル構造ビューア＋指標抽出ツール」。

- 動作形態：LAN 内の専用サーバ端末。組織／チーム内利用（不特定多数は想定しない）。
- セキュリティ前提：入力は実マルウェアであり得る前提で設計する。

## 全体構成

```
[Vue SPA]
   │  ① ファイルアップロード (HTTP)
   ▼
[受付API]  ── 受付は極薄（Phase0-1: FastAPI / Phase2: + Fastify(Node)）
   │  ② 実体をステージング保管(request_item_id) → DB行コミット
   │     → {schema_version, request_item_id} を XADD → nanoid 即返却
   ▼
[Valkey Stream (Consumer Group)]  ←─ 言語中立な自前ジョブ契約の置き場
   │  ③ ディスパッチャが XREADGROUP で取得（処理後に ACK）
   ▼
[ディスパッチャ(常駐/supervisor)]  ── ジョブ取得・子プロセス監視・ACK・失敗時の終端化
   │  ③' 1ジョブ＝1プロセッサ(サブプロセス)を起動
   ▼
[プロセッサ(使い捨て子プロセス)]  ── SHA256・種別判定・解析など重い処理を隔離実行
   │  ④ 状態・結果・イベントログを書き込み
   ▼
[結果ストア(SQLite→PostgreSQL)] / [検体ストレージ(SHA256内容アドレス)]
   ▲
   │  ⑤ フロントが request_item_id 単位で状態・結果・ログをポーリング取得（後に SSE）
[Vue SPA]
```

## コンポーネントと責務

### 受付 API（極薄）
- バイト受領 → **ステージング保管**（`request_item_id` をキー）→ **DB 行コミット** →
  Stream へ XADD → **nanoid を即返却**。
- **SHA256・種別判定・解析はしない**（CPU 仕事を非同期 API のイベントループから追い出す）。
- 受付を薄く保つことで、Phase2 の Fastify(Node) 受付が同一責務で対称になる。

### ディスパッチャ（常駐 / supervisor）
- Stream からジョブ取得 → **1ジョブ＝1プロセッサ（サブプロセス）を起動** → 子の終了コード／タイムアウトを
  監視 → 処理後に **ACK**。子が異常終了して自分で Error を記録できなかった場合は、
  **ディスパッチャが Item を Error に終端化**する。

### プロセッサ（使い捨て子プロセス）
- `--request_item_id` を受け、ステージングから検体読込 → **SHA256 算出** → **内容アドレス(SHA256)へ昇格** →
  **重複排除** → **種別判定** → **解析** → 指標算出 → 結果・イベント・状態を DB へ → 終了。
- 重く壊れやすい解析ライブラリ（LIEF 等）はプロセッサ側にのみ存在。
- **1ジョブ＝1プロセスなので、細工ファイルで segfault してもプロセッサ1個が死ぬだけ**（ディスパッチャは生存）。

### ブローカー（Valkey Stream / Consumer Group）
- 受付とディスパッチャをつなぐ配管。ジョブは言語中立な JSON。

### 結果ストア / 検体ストレージ
- 結果・状態・ログは RDBMS（SQLite で開始、後に PostgreSQL）。
- 検体実体は **SHA256 を内容アドレスとしたファイル保管**。DB は参照のみ。抽象インターフェース越し。

### フロント（Vue SPA）
- アップロード UI、状態・進捗・結果・ログ表示。状態取得は当面ポーリング（後に SSE）。

## ジョブ契約（言語中立・案A：薄い ID ポインタ）

```json
{ "schema_version": 1, "request_item_id": "<nanoid>" }
```

- 詳細は **DB が真実の源**。ジョブは「どの作業項目か」を指す ID のみ。
- 受付の順序：**DB 行コミット → ステージング保存 → XADD**（ワーカーが読む時に行が必ず存在）。
- `schema_version` で後方互換に進化（将来フィールドは版を上げて追加）。
- 受付が FastAPI でも Fastify でも、同じ JSON を投入できる。

## 障害対応・堅牢性

- **ACK は処理成功後のみ** → 途中でワーカーが落ちたジョブは pending に残る。
- **reclaim**：アイドル超過の pending を `XAUTOCLAIM` で別／再起動ワーカーが拾い直す。
- **リトライ上限＋デッドレター**：毎回確実に落ちる「毒ジョブ」を `attempts >= N` で打ち切り隔離。
- **解析本体のサブプロセス隔離（実装済み）**：ディスパッチャ（supervisor）が 1 ジョブごとにプロセッサ
  （子プロセス）を起動。細工ファイルで C 拡張パーサが segfault しても子のみで止まり、ディスパッチャは
  子の終了コード／タイムアウトを見て Item を Error に終端化して継続。防御的パース（サイズ上限・
  タイムアウト・メモリ上限）とセット。

## セキュリティ方針

- **絶対に実行・展開しない**：PE 実行しない／LNK のターゲットを解決しに行かない／VBA は取り出すだけ／
  OOXML 展開は zip 爆弾・パストラバーサル対策必須。
- **入力は全て敵性として扱う**（防御的パース）。再帰展開は深さ・数・総サイズに上限。
- **出力の無害化**：抽出文字列・パス・マクロ・ログの表示は信頼できないデータとしてエスケープ。
- **検体は不活性に保管**（直接配信／実行しない）。保管・削除ポリシー、ネットワークセグメント。
- **認証/認可**：認証＋投稿者記録（LAN 公開時に実装）。誤操作防止モードはセキュリティ境界にしない。

## 技術スタック

| 区分 | 採用 |
|---|---|
| 受付 API | FastAPI（Phase2 で Fastify(Node) を追加） |
| 解析（dispatcher / processor） | Python（LIEF / pefile / oletools / LnkParse3 / yara-python 等） |
| ブローカー | Valkey（Redis 互換）Stream |
| RDBMS | SQLite → PostgreSQL（SQLAlchemy + Alembic） |
| 検体ストレージ | 内容アドレス（SHA256）ファイル保管 |
| フロント | Vue（Vite + PrimeVue）SPA |
| コンテナ | Docker（Compose・dev/prod 出し分け） |

---

## 設定・実行構成

### 設定（config）
- 非秘密は **TOML**（`config.toml`＝開発／`config.docker.toml`＝compose。`FSAS_CONFIG_FILE` で選択、既定 `config.toml`）。
- **秘密のみ環境変数**（`FSAS_DB_USER` / `FSAS_DB_PASSWORD`）。TOML には書かない。
- `config_store.py` が集約し、`engine` / `storage` / `queue` / `dispatcher` はそこを参照。
- DB は **SQLite / PostgreSQL 両対応**（接続文字列で切替。dev=SQLite 可、compose=PostgreSQL）。

### 実行（Docker Compose・dev/prod）
- **prod**：`docker compose -f compose.yaml up` → nginx(:8080) が静的配信＋`/api` 逆プロキシ。ビルド済みイメージ。
- **dev**：`docker compose up`（`compose.override.yaml` 自動マージ）→ 全サービスをコンテナ内で起動し、
  ソース bind-mount＋ホットリロード（api=`uvicorn --reload` / dispatcher=`watchfiles` / frontend=Vite HMR、URL は :5173）。
- 同一ソースで配信方式（Vite or nginx）だけ切替。どちらも `/api` 同一オリジン経由＝**CORS 不要**。
