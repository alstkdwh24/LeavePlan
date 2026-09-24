import uuid
from datetime import datetime

from sqlalchemy import Column, String, ForeignKey, Date, DateTime, Uuid, Integer, JSON

from config.database import Base


class Trip(Base):
    __tablename__ = "Trip"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    member_key = Column("memberKey", Uuid(as_uuid=False), ForeignKey("Members.id"))
    title = Column(String(100), comment="여행 제목")
    region = Column(String(20), comment="여행 지역")
    start_date = Column("startDate", Date, comment="여행 시작일")
    end_date = Column("endDate", Date, comment="여행 종료일")
    created_at = Column("createdAt", DateTime, default=datetime.utcnow)
    people = Column(Integer, comment="인원수")
    status = Column(String(20), default="DRAFT", comment="DRAFT / CONFIRMED")
    tags = Column(JSON, comment='["바다","힐링"]')