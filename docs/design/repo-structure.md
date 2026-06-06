# リポジトリ構成

> 状態：設計第1版。モノレポ。各ディレクトリは Phase 進行に応じて追加していく。

## 全体構成

```
FileStaticAnalyzerStudio/
├─ .gitignore / LICENSE / README.md
├─ docs/                              # VitePress 文書サイト（設計ドキュメントもここ）
│  └─ design/                         #   architecture.md / data-model.md / repo-structure.md
├─ backend/                           # Python（単一 poetry プロジェクト）
│  ├─ pyproject.toml                  #   正式パッケージ（package-mode=true, src レイアウト）
│  ├─ src/fsas/                       #   パッケージ名 fsas
│  │  ├─ contracts/                   #     ジョブ JSON 契約（Pydantic）
│  │  ├─ models/                      #     SQLAlchemy モデル
│  │  ├─ db/                          #     engine/session、Alembic 連携
│  │  ├─ storage/                     #     検体ストレージ抽象IF（ステージング／内容アドレス）
│  │  ├─ api/                         #     FastAPI アプリ（受付）   ← uvicorn で起動
│  │  ├─ worker/                      #     解析ワーカー            ← python -m fsas.worker で起動
│  │  └─ analyzers/                   #     解析器（PE→LNK→Office…）後で増える
│  ├─ alembic/                        #   マイグレーション
│  ├─ alembic.ini
│  └─ tests/
├─ frontend/                          # Vue SPA（Vite）
├─ services/
│  └─ reception-node/                 # Phase2：Fastify(Node) 受付
├─ infra/                             # compose ファイル等（podman/docker 兼用）
└─ fixtures/                          # テスト用検体（安全な自作ファイル）
```

## 各ディレクトリの役割

| パス | 役割 | 追加時期 |
|---|---|---|
| `docs/` | VitePress 文書サイト＋設計ドキュメント | 作成済み |
| `backend/` | Python の受付 API と解析ワーカー（同一コードベース、起動2系統） | Phase 0 |
| `frontend/` | Vue SPA | Phase 0（当面は `/docs` で代用可） |
| `services/reception-node/` | Fastify(Node) 受付（言語非依存の実証） | Phase 2 |
| `infra/` | compose 等のインフラ定義 | Phase 0.5 |
| `fixtures/` | 安全な自作テスト検体 | Phase 1〜 |

## backend の方針

- **単一 poetry プロジェクト**。受付 API と解析ワーカーは `contracts` / `models` を共有するため
  コードベースは 1 つにまとめ、**起動プロセスを 2 つ**（uvicorn / worker）にする。
  デプロイ時は別コンテナでもソースは共有。
- **src レイアウト＋ `package-mode=true`**（import 可能な正式パッケージ）。
- **解析ライブラリの依存分離**（poetry の optional group 等）は **Phase 0.5（コンテナ化）で検討**。
  分離は可逆な設定なので、必要になってから「追加」で対応する。

## 命名

- パッケージ名：`fsas`（`from fsas.contracts import ...`）。
- 公開 ID は nanoid（`request_reception_id` / `request_item_id`）、検体の内容アドレスは SHA256。
