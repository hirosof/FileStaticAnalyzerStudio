from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, Boolean, Float, JSON, false
from sqlalchemy.orm import Mapped, mapped_column

from fsas.db.base import Base


class SpecimenInformation(Base):
    __tablename__ = "specimen_informations"

    id: Mapped[int] = mapped_column(primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), unique=True)  # 内容アドレス/重複排除
    size: Mapped[int] = mapped_column(Integer)
    analysis_state: Mapped[str] = mapped_column(String(16), default="Processing")  # 内容の解析状況
    file_type: Mapped[str] = mapped_column(String(16), default="Other")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)  
    )

        # --- Phase1: ハッシュ群（基本指標・形式非依存） ---
    md5: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sha1: Mapped[str | None] = mapped_column(String(40), nullable=True)
    crc32: Mapped[str | None] = mapped_column(String(8), nullable=True)   # 32bit を 16進8桁で保存
    ssdeep: Mapped[str | None] = mapped_column(String, nullable=True)     # ppdeep（ssdeep 互換）
    tlsh: Mapped[str | None] = mapped_column(String(72), nullable=True)   # 最小サイズ未満は null

    # --- Phase1: 種別判定（Basic 層・magika+libmagic の生結果を JSON で）---
    type_detection: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # --- Phase1: 形式固有の詳細結果（JSON）＋補助 ---
    detail_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)          # result_schema_version + pe{...}
    has_detail_data: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())  # 既存行も false で backfill
    last_analyze_log_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 完了サマリ（任意）