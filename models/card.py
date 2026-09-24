import uuid

from sqlalchemy import Column, String, Integer, Uuid, ForeignKey

from config.database import Base


class Card(Base):
    __tablename__ = "card"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    card_name = Column(String(100), comment="카드 이름")
    card_last4 = Column("cardLast4", String(4), comment="카드 번호 끝 4자리 (표시용)")
    card_company = Column(String(100), comment="카드사")
    members_id = Column("membersId", Uuid(as_uuid=False) ,ForeignKey("Members.id"), nullable=False)

