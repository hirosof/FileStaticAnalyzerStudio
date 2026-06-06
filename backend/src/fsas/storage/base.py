from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO


class Storage(ABC):
    """検体ストレージの抽象。将来 MinIO/S3 等へ差し替え可能にするための境界。"""

    @abstractmethod
    def stage(self, request_item_id: str, source: BinaryIO) -> Path:
        """受信バイトを request_item_id をキーにステージング保存"""

    @abstractmethod
    def staged_path(self, request_item_id: str) -> Path:
        """ステージング上のパス"""

    @abstractmethod
    def content_path(self, sha256: str) -> Path:
        """内容アドレス（SHA256）上のパス"""

    @abstractmethod
    def exists(self, sha256: str) -> bool:
        """その内容が既に内容アドレスに存在するか（重複排除の判定）"""

    @abstractmethod
    def promote(self, request_item_id: str, sha256: str) -> Path:
        """ステージング → 内容アドレスへ昇格（既存なら破棄して既存を使う）"""