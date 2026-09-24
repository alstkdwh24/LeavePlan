import uuid

from sqlalchemy import Column, String, Numeric, Text, Uuid, JSON, Integer

from config.database import Base


class Place(Base):
    __tablename__ = "Place"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    place = Column(String(100))
    region = Column(String(100))
    address = Column(String(200), comment="주소")
    lat = Column(Numeric(10, 7), comment="위도")
    lng = Column(Numeric(10, 7), comment="경도")
    rating = Column(Numeric(2, 1), comment="평점")
    description = Column(Text, comment="설명")
    image_url = Column("imageUrl", String(500), comment="대표 이미지")
    category = Column(String(50), comment="카테고리")
    opening_hours = Column("openingHours", String(100), comment="오픈시간")
    admission_fee = Column("admissionFee", String(100), comment="입장료")
    tags = Column(JSON, comment="태그")
    review_count = Column("reviewCount", Integer, default=0, comment="리뷰 숫자")