from pydantic import BaseModel, Field

CURRENT_SCHEMA_VERSION = 1


class AnalysisJob(BaseModel):
    """Valkey Stream に積む言語中立なジョブ（案A：薄いIDポインタ）。"""

    schema_version: int = Field(default=CURRENT_SCHEMA_VERSION)
    request_item_id: str

    def to_payload(self) -> str:
        """Stream の payload フィールドに入れる JSON 文字列へ"""
        return self.model_dump_json()

    @classmethod
    def from_payload(cls, payload: str) -> "AnalysisJob":
        """payload(JSON文字列) から復元"""
        return cls.model_validate_json(payload)