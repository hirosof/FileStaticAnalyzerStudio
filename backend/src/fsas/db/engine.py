import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 接続文字列は環境変数で差し替え可能（将来 Postgres へはここだけ変える＝移行のシーム）
DATABASE_URL = os.environ.get("FSAS_DATABASE_URL", "sqlite:///fsas.db")

# echo=True にすると SQL が見える（デバッグ用）
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)