import uuid

from sqlalchemy import Column, ForeignKey, String, Uuid
from sqlalchemy.orm import relationship

from config.database import Base


class AuthProviders(Base):
    __tablename__ = "AuthProviders"
    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id = Column(Uuid(as_uuid=False), ForeignKey("Members.id"), nullable=False)
    provider = Column(String(20), nullable=False, comment="google 등")
    provider_id = Column("providerId", String(255), nullable=False, unique=True, comment="구글 sub 값")

    member = relationship("Members", back_populates="auth_providers")