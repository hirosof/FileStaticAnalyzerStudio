from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from fsas.db.base import Base


class SpecimenInformation(Base):
    __tablename__ = "specimen_informations"

    id: Mapped[int] = mapped_column(primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # 内容アドレス/重複排除
    size: Mapped[int] = mapped_column(Integer)
    analysis_state: Mapped[str] = mapped_column(String(16), default="Processing")  # 内容の解析状況
    file_type: Mapped[str] = mapped_column(String(16), default="Other")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )