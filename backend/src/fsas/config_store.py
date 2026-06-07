import os
import tomllib
from pathlib import Path


class ConfigStore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        path = os.environ.get("FSAS_CONFIG_FILE", "config.toml")  # 唯一の選択用 env（任意）
        with open(path, "rb") as f:
            toml = tomllib.load(f)

        st = toml["storage"]
        self.data_dir = Path(st["data_dir"])
        self.specimen_dir_name = st["specimen_dir_name"]
        self.staging_dir_name = st["staging_dir_name"]
        self.cas_dir_name = st["cas_dir_name"]

        vk = toml["valkey"]
        self.valkey_host, self.valkey_port = vk["host"], int(vk["port"])
        self.stream, self.group = vk["stream"], vk["group"]

        self.processor_timeout = int(toml["processor"]["timeout_seconds"])
        self.database_url = self._resolve_db_url(toml["database"])

    def _resolve_db_url(self, db: dict) -> str:
        if db.get("type", "sqlite").lower() == "postgresql":
            pg = db["postgresql"]
            pg_user = os.environ["FSAS_DB_USER"]  # 秘密だけ env
            pg_password = os.environ["FSAS_DB_PASSWORD"]  # 秘密だけ env
            return (f"postgresql+psycopg://{pg_user}:{pg_password}"
                    f"@{pg['host']}:{pg['port']}/{pg['db']}")
        sqlite = db["sqlite"]
        return f"sqlite:///{(self.data_dir / sqlite['file_name']).as_posix()}"


config = ConfigStore()