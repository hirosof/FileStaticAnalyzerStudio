# リポジトリ構成

> 状態：Phase 0 / 0.5 反映済み（生きた文書）。モノレポ。各ディレクトリは Phase 進行に応じて追加していく。

## 全体構成

```
FileStaticAnalyzerStudio/
├─ .gitignore / LICENSE / README.md
├─ docs/                              # VitePress 文書サイト（設計ドキュメントもここ）
│  └─ design/                         #   architecture.md / data-model.md / repo-structure.md
├─ backend/                           # Python（単一 poetry プロジェクト）
│  ├─ pyproject.toml / poetry.lock    #   正式パッケージ（package-mode=true, src レイアウト）
│  ├─ Dockerfile / .dockerignore      #   api・dispatcher 共用イメージ
│  ├─ config.toml                     #   設定（開発用。秘密は含めない）
│  ├─ config.docker.toml              #   設定（compose 用：valkey/postgres をサービス名で指定）
│  ├─ alembic/ / alembic.ini          #   マイグレーション
│  ├─ src/fsas/                       #   パッケージ名 fsas
│  │  ├─ config_store.py              #     設定の集約（TOML 読込＋秘密のみ env）
│  │  ├─ contracts/                   #     ジョブ JSON 契約（Pydantic）
│  │  ├─ models/                      #     SQLAlchemy モデル
│  │  ├─ db/                          #     engine/session、Alembic 連携
│  │  ├─ storage/                     #     検体ストレージ抽象IF（staging／cas）
│  │  ├─ queue.py                     #     Valkey 接続・STREAM/GROUP・enqueue
│  │  ├─ api/                         #     FastAPI アプリ（受付）         ← uvicorn fsas.api.app:app
│  │  ├─ dispatcher/                  #     常駐ディスパッチャ(supervisor)  ← python -m fsas.dispatcher.entry
│  │  ├─ processor/                   #     1ジョブ=1サブプロセスの実処理    ← python -m fsas.processor.entry
│  │  └─ analyzers/                   #     解析器＋種別判定＋レジストリ（PE→LNK→Office…）後で増える
│  │     ├─ registry.py               #       sniff で担当 analyzer を選ぶ dispatch table
│  │     ├─ detect.py                 #       種別判定（magika 主 / libmagic 従）= Basic 層
│  │     └─ pe.py                     #       PE analyzer（LIEF）。純粋関数 + sniff(=lief.is_pe)
│  └─ tests/
├─ frontend/                          # Vue SPA（Vite + PrimeVue）
│  ├─ Dockerfile                      #   多段：deps / dev(Vite) / build / prod(nginx)
│  ├─ nginx.conf                      #   静的配信＋/api 逆プロキシ
│  ├─ .dockerignore
│  └─ src/                            #   App.vue / api/client.ts / main.ts / router / stores
├─ services/
│  └─ reception-node/                 # Phase2：Fastify(Node) 受付
├─ infra/                             # Docker Compose（dev/prod 出し分け）
│  ├─ compose.yaml                    #   本番ベース（valkey/postgres/migrate/api/dispatcher/frontend）
│  ├─ compose.override.yaml           #   開発差分（bind-mount＋--reload＋Vite dev）
│  └─ .env                            #   秘密（FSAS_DB_USER/PASSWORD）※git 管理外
└─ fixtures/                          # テスト用検体（安全な自作ファイル）
```

## 各ディレクトリの役割

| パス | 役割 | 状態 |
|---|---|---|
| `docs/` | VitePress 文書サイト＋設計ドキュメント | 作成済み |
| `backend/` | 受付 API・ディスパッチャ・プロセッサ（同一コードベース、起動3系統） | Phase 0 完了 |
| `frontend/` | Vue SPA（PrimeVue） | Phase 0 完了 |
| `infra/` | Docker Compose（dev/prod） | Phase 0.5 完了 |
| `services/reception-node/` | Fastify(Node) 受付（言語非依存の実証） | Phase 2 |
| `fixtures/` | 安全な自作テスト検体 | Phase 1〜 |

## backend の方針

- **単一 poetry プロジェクト**。受付 API・ディスパッチャ・プロセッサは `contracts` / `models` を共有するため
  コードベースは 1 つにまとめ、**3 系統で起動**する：
  受付（`uvicorn fsas.api.app:app`）／ディスパッチャ（`python -m fsas.dispatcher.entry`）／
  プロセッサ（ディスパッチャが 1 ジョブごとに `python -m fsas.processor.entry --request_item_id=...` を起動）。
- **ディスパッチャ＝supervisor／プロセッサ＝使い捨て子プロセス**。1 ジョブ＝1 プロセスにすることで、
  細工ファイルでパーサが segfault してもプロセッサ 1 個が死ぬだけ（ディスパッチャは生存し、子の終了コード／
  タイムアウトを見て Item を Error 化）。
- **src レイアウト＋ `package-mode=true`**。コンテナでは `PYTHONPATH=/app/src` で import（prod=COPY／dev=bind-mount のどちらでも同形）。
- **解析ライブラリの依存分離**（poetry の optional group 等）は可逆なため未着手。必要になってから追加で対応。
  ※ PE は **LIEF を主**とし、**pefile は直接依存にしない**（imphash も LIEF の
  `get_imphash(..., IMPHASH_MODE.PEFILE)` で。pefile は dotnetfile 経由で .NET 対応時に推移的に入る）。
- **ファジーハッシュ ssdeep は純 Python の `ppdeep` を採用**（ssdeep 互換ダイジェスト）。ネイティブ
  ssdeep（3.4）は py3.14 でビルド不可（`pkg_resources` 撤去）だったため。これで **`libfuzzy-dev` は不要**。
- **解析の実行は worker（Linux コンテナ）**。worker イメージ（apt）に必要なのは：
  - `build-essential` … `py-tlsh` 等が cp314 wheel 未提供でソースビルドするため（将来 wheel 提供 or
    マルチステージ化で外せる）
  - `libmagic1` … python-magic(libmagic) の実行時依存（magika は onnxruntime 同梱で apt 依存ほぼ無し）

## 設定（config）

- 非秘密は **TOML**（`config.toml`＝開発／`config.docker.toml`＝compose）。読むファイルは `FSAS_CONFIG_FILE` で選択（既定 `config.toml`）。
- **秘密のみ環境変数**（`FSAS_DB_USER` / `FSAS_DB_PASSWORD`）。TOML には書かない（git に漏らさない）。
- `config_store.py` が集約し、`engine` / `storage` / `queue` / `dispatcher` はそこを参照（散らばった `os.environ` を排除）。
- DB は **SQLite / PostgreSQL 両対応**（接続文字列で切替。dev=SQLite 可、compose=PostgreSQL）。
  FK の参照先カラムは UNIQUE 制約で持つ（Postgres は一意インデックスだけでは FK を張れないため）。
- 実行時データは `data/` 配下に集約：`data/fsas.db`（SQLite 時）／`data/specimens/{staging,cas}`（検体 blob）。

## 実行構成（Docker Compose・dev/prod）

- **prod**：`docker compose -f compose.yaml up --build` → nginx(:8080) が静的配信＋`/api` 逆プロキシ。ビルド済みイメージ。
- **dev**：`docker compose up --build`（`compose.override.yaml` を自動マージ）→ 全サービスをコンテナ内で起動し、
  ソース bind-mount＋ホットリロード（api=`uvicorn --reload` / dispatcher=`watchfiles` / frontend=Vite HMR、URL は :5173）。
- 同一ソースで配信方式（Vite or nginx）だけ切替。どちらも `/api` 同一オリジン経由＝**CORS 不要**。
- コンテナランタイムは **Docker Desktop**（当初 Podman を使用したが、`\\.\pipe\docker_engine` の占有競合のため撤去）。

## 命名

- パッケージ名：`fsas`（`from fsas.contracts import ...`）。
- 公開 ID は nanoid（`request_reception_id` / `request_item_id`）、検体の内容アドレスは SHA256。
