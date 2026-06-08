import hashlib
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from fsas.db.engine import SessionLocal
from fsas.models import AnalysisRequestItem, JobEvent, SpecimenInformation
from fsas.storage import storage

import zlib
import tlsh
import ppdeep

from fsas.analyzers.detect import detect
from fsas.analyzers.registry import select_analyzer, RESULT_SCHEMA_VERSION

import argparse

def _now() -> datetime:
    return datetime.now(timezone.utc)


def log_event(db: Session, request_item_id: str, message: str,
              level: str = "info", phase: str | None = None) -> None:
    db.add(JobEvent(request_item_id=request_item_id, level=level, phase=phase, message=message))
    db.commit()


def compute_hashes(data: bytes) -> dict:
    th = tlsh.hash(data)
    return {
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "md5": hashlib.md5(data).hexdigest(),
        "sha1": hashlib.sha1(data).hexdigest(),
        "crc32": format(zlib.crc32(data) & 0xFFFFFFFF, "08x"),  # 32bit を 16進8桁
        "ssdeep": ppdeep.hash(data) or None,
        "tlsh": None if th == "TNULL" else th,                  # 小/低エントロピーは null
    }

def process(request_item_id: str):
    with SessionLocal() as db:
        item = db.scalar(
            select(AnalysisRequestItem).where(
                AnalysisRequestItem.request_item_id == request_item_id
            )
        )
        if item is None:
            print(f"[worker] item not found: {request_item_id}")
            return

        try:
            # 1) 処理開始
            item.process_state = "Processing"
            item.current_phase = "ハッシュ算出中"
            item.started_at = _now()
            db.commit()
            log_event(db, item.request_item_id, "解析開始", phase="ハッシュ算出中")

            # 2) ステージングを 1 回読み、Basic ハッシュ群を算出
            #    ※ 全読み込み。サイズ上限ガードは後段の防御的パース段階で追加（今は安全な自作検体前提）
            data = storage.staged_path(item.request_item_id).read_bytes()
            h = compute_hashes(data)
            sha256 = h["sha256"]

            # 3) 内容アドレスへ昇格（重複なら破棄して既存を使う）
            storage.promote(item.request_item_id, sha256)

            # 4) Specimen を get-or-create（重複排除）
            spec = db.scalar(
                select(SpecimenInformation).where(SpecimenInformation.sha256 == sha256)
            )
            if spec is None:
                # 種別判定（Basic）
                item.current_phase = "種別判定中"
                db.commit()
                log_event(db, item.request_item_id, "種別判定中", phase="種別判定中")
                td = detect(data)

                # 形式別解析：registry の sniff で担当 analyzer を決定
                cas_path = storage.content_path(sha256)
                file_type = "Other"
                detail_data = None
                has_detail = False
                analyzer = select_analyzer(cas_path)
                if analyzer is not None:
                    file_type = analyzer.file_type  # sniff が通った＝正準カテゴリ確定
                    item.current_phase = f"{file_type} 解析中"
                    db.commit()
                    log_event(db, item.request_item_id, f"{file_type} 解析中", phase=f"{file_type} 解析中")
                    try:
                        detail = analyzer.analyze(cas_path)
                        detail_data = {"result_schema_version": RESULT_SCHEMA_VERSION,
                                       analyzer.result_key: detail}
                        has_detail = True
                    except Exception as e:
                        # 壊れた構造でも Basic は活かす（部分結果＋warn・防御的パース層5）
                        log_event(db, item.request_item_id,
                                  f"{file_type} 解析失敗（Basic のみ保存）: {e}",
                                  level="warn", phase=f"{file_type} 解析中")

                spec = SpecimenInformation(
                    sha256=sha256, size=h["size"],
                    md5=h["md5"], sha1=h["sha1"], crc32=h["crc32"],
                    ssdeep=h["ssdeep"], tlsh=h["tlsh"],
                    type_detection=td,
                    file_type=file_type,
                    detail_data=detail_data,
                    has_detail_data=has_detail,
                    analysis_state="Completed",
                )
                db.add(spec)
            else:
                spec.analysis_state = "Completed"  # 既存=同一内容、解析済み
            db.commit()

            # 5) Item に紐づけて完了
            item.sha256 = sha256
            item.process_state = "Completed"
            item.current_phase = None
            item.finished_at = _now()
            db.commit()
            log_event(db, item.request_item_id, f"完了 sha256={sha256}", phase="完了")

        except Exception as e:
            # Phase0: 失敗は terminal 扱い（reclaim/retry/デッドレターは後フェーズ）
            db.rollback()
            item = db.scalar(
                select(AnalysisRequestItem).where(
                    AnalysisRequestItem.request_item_id == request_item_id
                )
            )
            if item is not None:
                item.process_state = "Error"
                item.error_type = type(e).__name__
                item.attempts = (item.attempts or 0) + 1
                item.finished_at = _now()
                db.commit()
                log_event(db, item.request_item_id, f"エラー: {e}", level="error")

def entry() -> None:

    parser = argparse.ArgumentParser()
    parser.add_argument("--request_item_id")

    args = parser.parse_args()

    if (args.request_item_id is not None) and (len(args.request_item_id)>0):
        process(request_item_id=args.request_item_id)



if __name__ == "__main__":
    entry()
