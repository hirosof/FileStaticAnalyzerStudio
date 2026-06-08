from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SpecimenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # ORM から変換可能に

    sha256: str
    size: int
    analysis_state: str
    file_type: str
    # Phase1: Basic ハッシュ群
    md5: str | None = None
    sha1: str | None = None
    crc32: str | None = None
    ssdeep: str | None = None
    tlsh: str | None = None
    # Phase1: 種別判定（生結果 JSON）＋ 形式固有の詳細（JSON）
    type_detection: dict | None = None
    detail_data: dict | None = None
    has_detail_data: bool = False

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