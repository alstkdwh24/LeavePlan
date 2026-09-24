import uuid
from datetime import datetime

from sqlalchemy import (
    Column, BigInteger, Integer, String, Numeric, Text, Boolean,
    Date, Time, DateTime, ForeignKey, JSON, Uuid, Enum as SAEnum
)
from sqlalchemy.orm import relationship

from config.database import Base
from models.role import Role



class Members(Base):
    __tablename__ = "Members"
    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id = Column("memberId", String(50), nullable=False, unique=True, comment="로그인 ID")
    name = Column(String(50), nullable=False, comment="이름")
    phone = Column(String(20), comment="핸드폰 번호")
    role = Column(SAEnum(Role), default=Role.USER, nullable=False, comment="역할")
    gender = Column(String(10), comment="성별")
    age = Column(Integer, comment="나이")
    extra_settings = Column("extraSettings", JSON, comment="추가 설정 리스트 (JSON)")
    created_at = Column("createdAt", DateTime, default=datetime.utcnow, comment="생성시간")

    credentials = relationship("UserCredentials", back_populates="member", uselist=False)
    auth_providers = relationship("AuthProviders", back_populates="member")

    refresh_tokens = relationship("RefreshTokenEntity", back_populates="member")
    profile_image_url = Column("profileImageUrl", String(500), comment="프로필 사진")