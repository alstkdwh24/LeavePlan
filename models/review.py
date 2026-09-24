import uuid

# import에 추가
from sqlalchemy import Column, Text, Numeric, DateTime, ForeignKey, Uuid, Enum as SAEnum
from config.database import Base
from models.itemType import ItemType




class Review(Base):
    __tablename__ = "Review"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    contents = Column(Text, comment="리뷰 내용")
    score = Column(Numeric, comment="평정")
    created_at = Column("createdAt", DateTime, comment="리뷰 생성시간")
    member_id = Column("memberId", Uuid(as_uuid=False), ForeignKey("Members.id"))
    plan_item_id = Column("planItemId", Uuid(as_uuid=False), ForeignKey("PlanItem.id"))
    item_type = Column("itemType", SAEnum(ItemType), nullable=False, comment="유형")
    item_id = Column("itemId", Uuid(as_uuid=False), nullable=False, index=True)