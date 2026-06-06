import os

import valkey

from fsas.contracts import AnalysisJob

VALKEY_HOST = os.environ.get("FSAS_VALKEY_HOST", "localhost")
VALKEY_PORT = int(os.environ.get("FSAS_VALKEY_PORT", "6379"))

STREAM = "fsas:jobs"
GROUP = "fsas-workers"

client = valkey.Valkey(host=VALKEY_HOST, port=VALKEY_PORT, decode_responses=True)


def enqueue(job: AnalysisJob) -> str:
    """ジョブを Stream に積み、メッセージ ID を返す"""
    return client.xadd(STREAM, {"payload": job.to_payload()})