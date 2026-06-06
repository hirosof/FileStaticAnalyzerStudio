from collections.abc import Iterator

from sqlalchemy.orm import Session

from fsas.db.engine import SessionLocal


def get_db() -> Iterator[Session]:
    """リクエストごとに DB セッションを払い出し、終了時に閉じる"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()