import uuid

from sqlalchemy import Column, ForeignKey, String, Boolean, DateTime, Uuid
from sqlalchemy.orm import relationship

from config.database import Base


class RefreshTokenEntity(Base):
    __tablename__ = "RefreshTokens"
    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    token_hash = Column("tokenHash", String(64), unique=True, index=True, nullable=False)
    member_id = Column(Uuid(as_uuid=False), ForeignKey("Members.id"), nullable=False)
    family_id = Column("familyId", String(36), index=True, nullable=False)
    used = Column(Boolean, default=False)
    revoked = Column(Boolean, default=False)
    expires_at = Column("expiresAt", DateTime, nullable=False)

    member = relationship("Members", back_populates="refresh_tokens")