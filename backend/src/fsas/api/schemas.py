from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SpecimenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # ORM から変換可能に

    sha256: str
    size: int
    analysis_state: str
    file_type: str


class ItemStatusOut(BaseModel):
    request_item_id: str
    request_reception_id: str
    original_name: str | None
    process_state: str
    current_phase: str | None
    error_type: str | None
    sha256: str | None
    specimen: SpecimenOut | None = None


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ts: datetime
    level: str
    phase: str | None
    message: str