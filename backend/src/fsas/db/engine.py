from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from fsas.config_store import config

DATABASE_URL = config.database_url
_is_sqlite = DATABASE_URL.startswith("sqlite")
_connect_args = {"timeout": 30} if _is_sqlite else {}

if _is_sqlite:
    config.data_dir.mkdir(parents=True, exist_ok=True)

engine = create_engine(DATABASE_URL, echo=False, connect_args=_connect_args)

if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=30000")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SessionLocal = sessionmaker(bind=engine)