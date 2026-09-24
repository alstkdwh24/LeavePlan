import uuid
from datetime import datetime

from sqlalchemy import Column, ForeignKey, String, Text, Boolean, DateTime, Uuid

from config.database import Base


class Notifications(Base):
    __tablename__ = "Notifications"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()), comment="Primary Key")
    user_id = Column(Uuid(as_uuid=False), ForeignKey("Members.id"), nullable=False, comment="User FK")
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False, comment="일정 생성 완료 알림, 숙박 예약 완료 알림, 메시지 알림")
    type = Column(String(20), nullable=False, comment="EMAIL, SNS, PUSH, IN_APP")
    status = Column(String(20), default="UNREAD", comment="UNREAD, READ, DELETE")
    is_read = Column(Boolean, default=False)
    priority = Column(String(20), default="NORMAL", comment="LOW, NORMAL, HIGH, URGENT")
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)

    # 원본 인덱스: user_id, created_at, status
    __table_args__ = ()

