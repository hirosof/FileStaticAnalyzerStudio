# FileStaticAnalyzerStudio — プロジェクト指示書

PE / LNK / Office ファイルの **静的解析（実行せず構造・内容を解析）** に特化した Web アプリ。
マルウェア解析・トリアージ用途。LAN 内のチーム利用想定。**入力は実マルウェアであり得る前提**で設計する。

> 設計の正典は `docs/design/`（`architecture.md` / `data-model.md` / `repo-structure.md`）。
> 迷ったらまずそこを読む。本ファイルはオリエンテーション＋規約＋ハマりどころの要約。

## 作業分担・進め方（最重要）
- **コードを書くのは開発者（人間）**。Claude の役割は「**何を・なぜ・どう**書くか」の説明・提案・レビュー・伴走。
  **勝手に実装（一括編集）しない**。コードは提示（スニペット/差分）し、**適用・実行は開発者が手で行う**。
- **実装前に方針を相談**（議論優先）。選択肢があれば提示して選んでもらう。依頼していない機能を勝手に足さない。
- **小さなステップで進め、各段階で確認**を取る。
- 例外：明示的に「これは君が書いて／適用して」と言われた場合のみ、Claude がファイルを編集・作成する。
- 設計ドキュメント（`docs/design/`）や本 CLAUDE.md の更新は、Claude が代行してよい（依頼ベース）。

## 構成（モノレポ）
- `backend/` … Python 単一 poetry プロジェクト（`src/fsas/`）。受付 API・dispatcher・processor を **同一コードベース**で。
- `frontend/` … Vue（Vite + PrimeVue）SPA。
- `infra/` … Docker Compose（dev/prod 出し分け）。
- `services/reception-node/` … Phase2 で Fastify(Node) 受付（未着手）。
- `fixtures/` … テスト用検体（安全な自作）。

## アーキテクチャ（要約）
```
[Vue] -(/api)-> [受付API(FastAPI,極薄)] -(Valkey Stream)-> [dispatcher(supervisor)] -(子プロセス)-> [processor]
                      | DB行+ステージング保存                         | SHA256/種別判定/解析
                      +----------- 結果ストア(SQLite/PostgreSQL) -----+
```
- **受付は極薄**：バイト受領 → ステージング保存 → DB 行コミット → `{schema_version, request_item_id}` を Stream 投入 → nanoid 即返却。SHA256/解析はしない。
- **dispatcher**：Stream consumer。1ジョブ=1 processor サブプロセス起動・監視・ACK。子が異常終了したら Item を Error 化。
- **processor**：`--request_item_id=...` を受け、SHA256 → 内容アドレス昇格 → 重複排除 → 種別判定 → 解析 → DB 更新 → 終了。
- **ジョブ契約は薄い ID ポインタ**（詳細は DB が真実の源）。

## 実行（Docker Desktop / `infra/` で）
- dev（全コンテナ＋ホットリロード、URL **:5173**）：`docker compose up --build`
- prod（nginx **:8080**＋/api 逆プロキシ）：`docker compose -f compose.yaml up --build`
- 秘密は `infra/.env`（`FSAS_DB_USER` / `FSAS_DB_PASSWORD`、git 管理外）。
- Swagger は api 直の `http://localhost:8000/docs`（nginx 経由では出ない）。

## 規約・ハマりどころ（重要）
- **設定**：非秘密は TOML（`config.toml`=dev / `config.docker.toml`=compose、`FSAS_CONFIG_FILE` で選択）。
  **秘密のみ env**。`config_store.py` に集約し、各モジュールはそこを参照（`os.environ` を散らさない）。
- **DB 両対応**（SQLite/PostgreSQL を接続文字列で切替）。**FK の参照先カラムは UNIQUE 制約で持つ**
  （`unique=True`。`index=True` だけだと PostgreSQL で FK を張れない）。
- **subprocess は必ずリスト＋`--opt=value`**：`subprocess.run([sys.executable, "-m", "fsas.processor.entry", f"--request_item_id={id}"])`。
  文字列で渡すと Linux で壊れる。nanoid は `-` 始まりがあり得るので `=value` 形式が必須（スペース区切りは argparse が誤認）。
- **コンテナの import** は `PYTHONPATH=/app/src`（パッケージはインストールせず src 直参照。prod=COPY / dev=bind-mount 共通）。
- **解析の実行は Linux コンテナ前提**。ssdeep / pyimpfuzzy は Windows 不可、Linux で `libfuzzy-dev` を入れれば可。
  3.14 wheel 確認済：LIEF / oletools / dotnetfile / lnkparse3 / magika / yara-python / py-tlsh は OK。
- **出力の無害化**：抽出文字列/ログ等は信頼できないデータ。フロントは `{{ }}` で自動エスケープ（`v-html` 禁止）。
- 公開 ID は nanoid（`request_reception_id` / `request_item_id`）、検体の内容アドレスは SHA256。

## 状態（2層）
- Item `process_state`（作業のライフサイクル：Pending/Processing/Completed/Error）＋ `current_phase`（表示用ラベル）。
- Specimen `analysis_state`（内容そのものの解析状況。ハッシュ問い合わせ用）。

## DB / マイグレーション
- SQLAlchemy 2.0（`Mapped`/`mapped_column`）＋ Alembic。`create_all` 不使用、差分マイグレーションで進化。
- カラム追加は nullable かデフォルト＋backfill。`render_as_batch` は SQLite 時のみ。

## 現在地 → 次
- **Phase 0（歩く骨格）／Phase 0.5（コンテナ化）完了**。
- 次：**Phase 1 = PE 解析の中身**（LIEF/pefile）。ハッシュ群 → ヘッダ → セクション+エントロピー →
  imports/exports → リソース → 署名、を段階追加。防御的パース（サイズ上限/タイムアウト/メモリ上限）。
  アプリ側アップロード上限（nginx 暫定 100m と整合）も整備。

## 注意
- 秘密（DB 認証情報等）は TOML/コードに書かない（env のみ）。
- 大きめの仕様変更・新機能は、実装前に方針を相談する（グローバル方針：議論優先）。
