import uuid
from datetime import datetime

from sqlalchemy import Column, Integer, Uuid, ForeignKey, String, DateTime

from config.database import Base


class Conversation(Base):
    __tablename__ = "Conversation"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id = Column("memberId", Uuid(as_uuid=False), ForeignKey("Members.id"))
    trip_id = Column("tripId", Uuid(as_uuid=False), ForeignKey("Trip.id"))
    title = Column(String(100))
    created_at = Column("createdAt", DateTime, default=datetime.utcnow)
    updated_at = Column("updatedAt", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)