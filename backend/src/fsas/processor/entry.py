import hashlib
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from fsas.db.engine import SessionLocal
from fsas.models import AnalysisRequestItem, JobEvent, SpecimenInformation
from fsas.storage import storage

import sys
import argparse

def _now() -> datetime:
    return datetime.now(timezone.utc)


def log_event(db: Session, request_item_id: str, message: str,
              level: str = "info", phase: str | None = None) -> None:
    db.add(JobEvent(request_item_id=request_item_id, level=level, phase=phase, message=message))
    db.commit()


def hash_file(path: Path) -> tuple[str, int]:
    sha = hashlib.sha256()
    size = 0
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):  # 1MiB ずつ（ストリーミングハッシュ）
            size += len(chunk)
            sha.update(chunk)
    return sha.hexdigest(), size


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

            # 2) ステージングを読んで SHA256 + サイズ（Phase0 の“解析”はこれだけ）
            sha256, size = hash_file(storage.staged_path(item.request_item_id))

            # 3) 内容アドレスへ昇格（重複なら破棄して既存を使う）
            storage.promote(item.request_item_id, sha256)

            # 4) Specimen を get-or-create（重複排除）
            spec = db.scalar(
                select(SpecimenInformation).where(SpecimenInformation.sha256 == sha256)
            )
            if spec is None:
                spec = SpecimenInformation(
                    sha256=sha256, size=size, analysis_state="Completed", file_type="Other"
                )
                db.add(spec)
            else:
                spec.analysis_state = "Completed"
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

#    print(args.request_item_id)

    if (args.request_item_id is not None) and (len(args.request_item_id)>0):
        process(request_item_id=args.request_item_id)



if __name__ == "__main__":
    entry()
