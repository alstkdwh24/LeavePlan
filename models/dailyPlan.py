import uuid

from sqlalchemy import Column, String, ForeignKey, Integer, Date, Uuid

from config.database import Base


class DailyPlan(Base):
    __tablename__ = "DailyPlan"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    region = Column(String(100), comment="지역")
    trip_id = Column("tripId", Uuid(as_uuid=False), ForeignKey("Trip.id"))
    day_number = Column("dayNumber", Integer, comment="1일차, 2일차")
    plan_date = Column("planDate", Date, comment="해당 날짜")
    theme = Column(String(100), comment="그날의 테마")
