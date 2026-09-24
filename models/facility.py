import uuid

from sqlalchemy import Column, String, Uuid

from config.database import Base


class Facility(Base):
    __tablename__ = "facility"

    # 원본 DBML에 PK가 없어 매핑을 위해 임시로 id 추가
    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    wifi = Column(String(100), comment="와이파이")
    view = Column(String(100), comment="뷰")