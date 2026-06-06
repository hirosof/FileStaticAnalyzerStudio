import valkey

from fsas.contracts import AnalysisJob
from fsas.queue import client, STREAM, GROUP

import subprocess
from typing import Any

CONSUMER = "fsas-be-dispatcher"

def ensure_group() -> None:
    # id="0" で作ると、既存メッセージも未配信扱いで拾える（先に積んだジョブも処理される）
    try:
        client.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except valkey.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


def processor_execute(job: AnalysisJob , msg_id : Any) -> None:
    try:
        proc = subprocess.run(["poetry","run","python.exe" , "-m",  "fsas.processor.entry" , "--request_item_id" , job.request_item_id] ,  capture_output=True, text=True)
        print(proc)
    except Exception as e:
        print(f"[worker] unexpected error on {job.request_item_id}: {e}")
    finally:
        client.xack(STREAM, GROUP, msg_id)

def entry() -> None:
    ensure_group()
    print(f"[worker] {CONSUMER} waiting on {STREAM} (Ctrl+C to stop)")
    try:
        while True:
            resp = client.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=1, block=5000)
            if not resp:
                continue
            for _stream, messages in resp:
                for msg_id, fields in messages:
                    processor_execute(AnalysisJob.from_payload(fields["payload"]) , msg_id)
    except KeyboardInterrupt:
        print("[worker] shutting down...")


if __name__ == "__main__":
    entry()
