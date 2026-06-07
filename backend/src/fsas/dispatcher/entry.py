import subprocess
import sys
from typing import Any

from sqlalchemy import select

import valkey
from fsas.contracts import AnalysisJob
from fsas.db.engine import SessionLocal
from fsas.models import AnalysisRequestItem, JobEvent
from fsas.queue import client, STREAM, GROUP

CONSUMER = "fsas-be-dispatcher"
PROCESSOR_TIMEOUT = 300  # 秒（暫定）


def ensure_group() -> None:
    # id="0" で作ると、既存メッセージも未配信扱いで拾える（先に積んだジョブも処理される）
    try:
        client.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except valkey.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

def _mark_error(request_item_id: str, message: str) -> None:
    """子が自分で Error を記録できずに死んだ場合に、親が終端化する"""
    with SessionLocal() as db:
        item = db.scalar(
            select(AnalysisRequestItem).where(
                AnalysisRequestItem.request_item_id == request_item_id
            )
        )
        if item is None or item.process_state in ("Completed", "Error"):
            return  # 既に終端なら触らない
        item.process_state = "Error"
        item.error_type = "ProcessorFailure"
        item.attempts = (item.attempts or 0) + 1
        db.add(JobEvent(request_item_id=request_item_id, level="error",
                        phase="dispatcher", message=message))
        db.commit()

def processor_execute(job: AnalysisJob, msg_id: Any) -> None:
    try:

        cmdline_items = [sys.executable, 
                         "-m", 
                         "fsas.processor.entry",
                         f"--request_item_id={job.request_item_id}"]

        print("[dispatcher] Call to {0}".format(subprocess.list2cmdline(cmdline_items)))

        proc = subprocess.run(
           cmdline_items,
            capture_output=True, text=True, timeout=PROCESSOR_TIMEOUT,
        )
        if proc.returncode != 0:
            _mark_error(job.request_item_id,
                        f"processor abnormal exit (code={proc.returncode}): {proc.stderr[-500:]}")
    except subprocess.TimeoutExpired:
        _mark_error(job.request_item_id, f"processor timeout ({PROCESSOR_TIMEOUT}s)")
    except Exception as e:
        _mark_error(job.request_item_id, f"dispatcher error: {e}")
    finally:
        client.xack(STREAM, GROUP, msg_id)


def entry() -> None:
    ensure_group()
    print(f"[dispatcher] {CONSUMER} waiting on {STREAM} (Ctrl+C to stop)")
    try:
        while True:
            resp = client.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=1, block=5000)
            if not resp:
                continue
            for _stream, messages in resp:
                for msg_id, fields in messages:
                    processor_execute(AnalysisJob.from_payload(fields["payload"]) , msg_id)
    except KeyboardInterrupt:
        print("[dispatcher] shutting down...")


if __name__ == "__main__":
    entry()
