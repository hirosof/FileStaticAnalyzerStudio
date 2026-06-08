"""解析器レジストリ：各 analyzer の sniff を順に試して担当を決める dispatch table。
将来 LNK/Office は ANALYZERS に1行追加するだけ（既存を作り直さない）。"""
from pathlib import Path
from typing import Protocol, runtime_checkable

from fsas.analyzers.pe import PEAnalyzer

RESULT_SCHEMA_VERSION = 1  # detail_data の結果スキーマ版（後方互換に進化）


@runtime_checkable
class Analyzer(Protocol):
    file_type: str           # 正準カテゴリ（PE/LNK/Office...）
    result_key: str          # detail_data 内のキー（"pe" 等）
    def sniff(self, path: Path) -> bool: ...     # 自分が扱えるか（native lib で判定）
    def analyze(self, path: Path) -> dict: ...   # 純粋関数：path→結果dict（DB 非依存）


ANALYZERS: list[Analyzer] = [
    PEAnalyzer(),
]


def select_analyzer(path: Path) -> Analyzer | None:
    """登録順に sniff を試し、最初に名乗り出た analyzer を返す（無ければ None）。"""
    for a in ANALYZERS:
        try:
            if a.sniff(path):
                return a
        except Exception:
            continue  # sniff が落ちても他を試す
    return None