import uuid

from sqlalchemy import Column, ForeignKey, String, Uuid
from sqlalchemy.orm import relationship

from config.database import Base


class UserCredentials(Base):
    __tablename__ = "UserCredentials"
    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id = Column(Uuid(as_uuid=False), ForeignKey("Members.id"), comment="1:1 관계")
    user_pw = Column("userPw", String(255), nullable=False, comment="비밀번호")

    member = relationship("Members", back_populates="credentials")