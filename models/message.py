import uuid

from config.database import Base
from sqlalchemy import (
    Column, Integer, String, Numeric, Text, Boolean,
    Date, Time, DateTime, ForeignKey, JSON, Uuid, Enum as SAEnum
)

from models.messageType import MessageType
# ForeignKey("Members.id"), ForeignKey("Trip.id")가 가리키는 테이블을 SQLAlchemy가 찾을 수 있도록 등록
import models.members  # noqa: F401
import models.trip  # noqa: F401


class Message(Base):
    __tablename__ = "Message"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()), comment="id 키")
    member_id = Column("memberId", Uuid(as_uuid=False), ForeignKey("Members.id"))
    trip_id = Column("tripId", Uuid(as_uuid=False), ForeignKey("Trip.id"))
    content = Column(Text)
    type = Column(SAEnum(MessageType), comment="메시지 발신자")
    created_at = Column("createdAt", DateTime, comment="생성시간")
    conversation_id = Column("conversationId", Uuid(as_uuid=False), ForeignKey("Conversation.id"), index=True, comment="대화 번호")