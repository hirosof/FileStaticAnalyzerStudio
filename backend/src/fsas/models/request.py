from datetime import datetime, timezone

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from fsas.db.base import Base


class AnalysisRequest(Base):
    __tablename__ = "analysis_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_reception_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )