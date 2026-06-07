import valkey

from fsas.config_store import config
from fsas.contracts import AnalysisJob

STREAM = config.stream
GROUP = config.group

client = valkey.Valkey(host=config.valkey_host, port=config.valkey_port, decode_responses=True)


def enqueue(job: AnalysisJob) -> str:
    """ジョブを Stream に積み、メッセージ ID を返す"""
    return client.xadd(STREAM, {"payload": job.to_payload()})