# データモデル

> 状態：設計第1版（Phase 0 で使う最小サブセット ＋ 将来のシーム）

## 方針

- **後で変えづらい関係性（シーム）は最初から正しく**、**個々のカラムは段階的に追加**する。
- 区分表記：**【動】** Phase 0 で使う／**【種】** シームとして置くが当面未使用／**【後】** 後フェーズで追加。

## 階層

```
Tickets（案件/グルーピング）              ※ Phase0 では作らない（後で nullable FK 追加）
  └─ AnalysisRequests（受付＝Submission。1回のリクエスト）
       └─ AnalysisRequestItem（解析対象＝作業単位。parent で親子ツリー）
            └─ SHA256 ─→ SpecimenInformations（検体の事実。SHA256 ユニーク＝重複排除）
```

最終的な想定：
- 1 チケットは複数のリクエストを持てる。
- 1 リクエスト（1 回の依頼）で複数の検体（アイテム）の解析を依頼できる。
- アイテムは展開等で子アイテムを派生（親子ツリー）。
- 同一内容の検体は SHA256 で重複排除（`SpecimenInformations` は SHA256 ユニーク）。

## テーブル定義（Phase 0 最小サブセット）

### `analysis_requests`（受付＝Submission）
| カラム | 区分 | 備考 |
|---|---|---|
| id (int PK) | 【動】 | |
| request_reception_id (nanoid, unique) | 【動】 | 受付単位の公開 ID |
| created_at | 【動】 | |
| ticket 連携 / max_child_depth / 共通展開PW / 判定モード / owner | 【後】 | 横展開・認証フェーズ |

### `analysis_request_items`（解析対象＝作業単位。中核）
| カラム | 区分 | 備考 |
|---|---|---|
| id (int PK) | 【動】 | |
| request_item_id (nanoid, unique) | 【動】 | **公開 ID。ジョブに載る／呼び出し元へ返す** |
| request_reception_id (FK→requests) | 【動】 | 所属する受付 |
| parent_request_item_id (nullable, 自己FK) | 【種】 | **ツリーのシーム**（Phase0 は top-level=null） |
| register_type (default "User") | 【種】 | User / System（Phase0 は User 固定） |
| original_name | 【動】 | 元ファイル名 |
| process_state (default "Pending") | 【動】 | 制御用：Pending/Processing/Completed/Error（Extracting は後） |
| current_phase (nullable) | 【動】 | 表示用ラベル（"ハッシュ算出中" 等） |
| error_type (nullable) | 【種】 | timeout/segfault/parse-error 等 |
| sha256 (nullable, FK→specimens) | 【動】 | ワーカーがハッシュ確定後に紐づけ |
| attempts (default 0) | 【種】 | リトライ／reclaim 用 |
| created_at / updated_at | 【動】 | |
| started_at / finished_at (nullable) | 【動】 | |
| deleted_at (nullable) | 【種】 | ソフトデリート |
| child_depth_count / is_container / 展開PW / is_reanalyze_request 等 | 【後】 | 展開フェーズ |

> ステージングの場所はカラムを足さず `request_item_id` から規約で導出（例：`staging/<request_item_id>`）。

### `specimen_informations`（検体の事実。SHA256 で重複排除）
| カラム | 区分 | 備考 |
|---|---|---|
| id (int PK) | 【動】 | |
| sha256 (unique, index) | 【動】 | **内容アドレス／重複排除キー** |
| size | 【動】 | |
| analysis_state | 【動】 | **検体（内容）の解析状況** Processing/Completed/Error |
| file_type (default "Other") | 【動】 | PE/LNK/Office/Other（Phase0 は Other） |
| created_at | 【動】 | |
| md5/sha1/crc32 / mime_type / detail_data / has_detail_data / last_analyze_log_data | 【後】 | Phase1（PE解析） |

### `job_events`（ジョブイベントログ＝append-only）
| カラム | 区分 | 備考 |
|---|---|---|
| id (int PK) | 【動】 | |
| request_item_id (FK, index) | 【動】 | どの作業項目のログか |
| ts | 【動】 | |
| level (info/warn/error) | 【動】 | |
| phase (nullable) | 【動】 | どの段階で起きたか |
| message | 【動】 | 本文（フロント表示時はエスケープ） |

## 状態の二層化

| 状態 | 置き場 | 意味 |
|---|---|---|
| `process_state` | Item | この 1 リクエスト分の作業ライフサイクル（制御用・粗く安定） |
| `current_phase` | Item | 表示用の細かい進捗ラベル（自由に増やせる・制御に影響しない） |
| `analysis_state` | Specimen | **内容そのものの解析状況**。ハッシュ問い合わせに「解析中／完了」を返せる |

例：item A が SHA256=X を解析中 → specimen X は `analysis_state=Processing`。
別 item B が同じ X を問い合わせ → 「今 X は解析中」と即答（B は待つ／結果を共有）。

## 重複排除

- `specimen_informations.sha256` を UNIQUE にし、同一内容は 1 レコードに集約。
- アプリは get-or-create（あれば再利用、なければ登録）。並行時は `INSERT ... ON CONFLICT DO NOTHING`
  等で堅牢化（マルチワーカー＝PostgreSQL を検討する理由の一つ）。

## マイグレーション

- SQLAlchemy（2.0 スタイル）＋ Alembic で版管理。`create_all` ではなく差分マイグレーションで進化。
- カラム追加は nullable かデフォルト＋backfill（既存行に入れる値が必要なため）。
