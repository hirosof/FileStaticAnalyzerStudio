from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from fsas.db.base import Base


class AnalysisRequestItem(Base):
    __tablename__ = "analysis_request_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_item_id: Mapped[str] = mapped_column(String(32), unique=True)  # 公開ID/ジョブに載る
    request_reception_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("analysis_requests.request_reception_id"), index=True
    )
    parent_request_item_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("analysis_request_items.request_item_id"), nullable=True
    )  # ツリーのシーム（Phase0 は null）
    register_type: Mapped[str] = mapped_column(String(16), default="User")  # User/System
    original_name: Mapped[str | None] = mapped_column(String, nullable=True)
    process_state: Mapped[str] = mapped_column(String(16), default="Pending", index=True)  # 制御用状態
    current_phase: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 表示用ラベル
    error_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sha256: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("specimen_informations.sha256"), nullable=True, index=True
    )  # Worker がハッシュ確定後に紐づけ
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # ソフトデリート