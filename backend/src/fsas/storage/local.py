import shutil
from pathlib import Path
from typing import BinaryIO

from fsas.config_store import config
from fsas.storage.base import Storage


class LocalFileStorage(Storage):
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or config.data_dir
        specimen_root = self.base_dir / config.specimen_dir_name
        self.staging_dir = specimen_root / config.staging_dir_name
        self.cas_dir = specimen_root / config.cas_dir_name

    def staged_path(self, request_item_id: str) -> Path:
        return self.staging_dir / request_item_id

    def stage(self, request_item_id: str, source: BinaryIO) -> Path:
        dest = self.staged_path(request_item_id)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as f:
            shutil.copyfileobj(source, f, length=1024 * 1024)  # 1MiB ずつコピー
        return dest

    def content_path(self, sha256: str) -> Path:
        # 例: data/cas/ab/cd/abcd...  （ハッシュで分散配置）
        return self.cas_dir / sha256[:2] / sha256[2:4] / sha256

    def exists(self, sha256: str) -> bool:
        return self.content_path(sha256).exists()

    def promote(self, request_item_id: str, sha256: str) -> Path:
        staged = self.staged_path(request_item_id)
        dest = self.content_path(sha256)
        if dest.exists():
            # 重複: 既に同一内容がある → ステージングを破棄し、既存を使う
            staged.unlink(missing_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            staged.replace(dest)  # 同一FS内なら原子的に移動
        return dest