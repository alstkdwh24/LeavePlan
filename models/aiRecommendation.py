import uuid
from datetime import datetime

from sqlalchemy import Column, Text, DateTime, ForeignKey, Uuid

from config.database import Base


class AiRecommendation(Base):
    __tablename__ = "AiRecommendation"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    member_key = Column("memberKey", Uuid(as_uuid=False), ForeignKey("Members.id"))
    trip_id = Column("tripId", Uuid(as_uuid=False), ForeignKey("Trip.id"))
    prompt = Column(Text, comment="사용자가 요청한 내용")
    response = Column(Text, comment="AI가 답변한 내용")
    created_at = Column("createdAt", DateTime, default=datetime.utcnow)