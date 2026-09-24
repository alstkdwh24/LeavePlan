import uuid

from sqlalchemy import (
    Column, Integer, String, Numeric, Text, Boolean,
    Date, Time, DateTime, ForeignKey, JSON, Uuid, Enum as SAEnum
)
from config.database import Base
from models.itemType import ItemType


class PlanItem(Base):
    __tablename__ = "PlanItem"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    region = Column(String(100), comment="지역")
    item_type = Column("itemType", SAEnum(ItemType), comment="장소 유형")
    item_id = Column("itemId", Uuid(as_uuid=False), comment="stay/cafe/place/restaurant의 id")
    daily_plan_id = Column("dailyPlanId", Uuid(as_uuid=False), ForeignKey("DailyPlan.id"))
    visit_order = Column("visitOrder", Integer, comment="방문 순서")
    start_time = Column("startTime", Time, comment="방문 시작 시간")
    end_time = Column("endTime", Time, comment="방문 종료 시간")
    memo = Column(Text, comment="메모")
    stay_id = Column("stayId", Uuid(as_uuid=False), ForeignKey("StayListing.id"))
    place_id = Column("placeId", Uuid(as_uuid=False), ForeignKey("Place.id"))
    cafe_id = Column("cafeId", Uuid(as_uuid=False), ForeignKey("CafeListing.id"))
    restaurant_id = Column("restaurantId", Uuid(as_uuid=False), ForeignKey("RestaurantListing.id"))