import uuid
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Numeric, Text, Boolean,
    Date, Time, DateTime, ForeignKey, JSON, Uuid, Enum as SAEnum
)
from config.database import Base
from models.itemType import PlaceType


class Wishlist(Base):
    __tablename__ = "Wishlist"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id = Column("memberId", Uuid(as_uuid=False), ForeignKey("Members.id"))
    item_type = Column("itemType", SAEnum(PlaceType), comment="STAY, CAFE, PLACE, RESTAURANT")
    item_id = Column("itemId", Uuid(as_uuid=False))
    check_in = Column("checkIn", Date, comment="숙소 체크인 날짜 (STAY만 사용)")
    check_out = Column("checkOut", Date, comment="숙소 체크아웃 날짜 (STAY만 사용)")
    travel_date = Column("travelDate", Date, comment="여행 갈 날짜 (CAFE, PLACE, RESTAURANT만 사용)")
    created_at = Column("createdAt", DateTime, default=datetime.utcnow)
    trip_id = Column("tripId", Uuid(as_uuid=False), ForeignKey("Trip.id"), nullable=True)
