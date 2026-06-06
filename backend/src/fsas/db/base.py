from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """全モデルの基底クラス（メタデータの集約点）"""
    pass