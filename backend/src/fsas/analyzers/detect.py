"""種別判定（Basic 層）: magika（主）+ python-magic=libmagic（従）。DB は触らない純粋関数。"""
import magic  # python-magic (libmagic)
from magika import Magika

_magika: Magika | None = None


def _get_magika() -> Magika:
    global _magika
    if _magika is None:
        _magika = Magika()  # モデルロードは高コスト→遅延 & プロセス内1回
    return _magika


def detect(data: bytes) -> dict:
    """magika + libmagic の生結果を JSON 構造で返す（type_detection 列にそのまま入れる）。"""
    result: dict = {"magika": None, "libmagic": None}
    try:
        r = _get_magika().identify_bytes(data)
        if r.ok:
            o = r.output
            result["magika"] = {
                "label": o.label,
                "score": float(r.score),
                "mime_type": o.mime_type,
                "group": o.group,
                "description": o.description,
                "is_text": o.is_text,
                "extensions": list(o.extensions),
            }
    except Exception:
        pass  # 検出器の失敗は致命ではない
    try:
        result["libmagic"] = {
            "mime": magic.from_buffer(data, mime=True),
            "description": magic.from_buffer(data),
        }
    except Exception:
        pass
    return result