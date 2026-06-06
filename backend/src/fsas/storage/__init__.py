from fsas.storage.base import Storage
from fsas.storage.local import LocalFileStorage

# 既定のストレージ実装（将来ここを差し替えるだけで MinIO/S3 等へ）
storage: Storage = LocalFileStorage()

__all__ = ["Storage", "LocalFileStorage", "storage"]