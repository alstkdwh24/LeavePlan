import uuid

from sqlalchemy import Column, String, Numeric, Text, Boolean, Uuid, Integer

from config.database import Base


class CafeListing(Base):
    """예약/추천 대상으로 쓰는 카페 목록 — 여행 플래너에서 실제로 보여주는 도메인 테이블.
    공공데이터 카페 표준데이터 원본은 models/cafe_model.py의 Cafe를 따로 참고."""

    __tablename__ = "CafeListing"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    cafe_name = Column("cafeName", String(100), nullable=False)
    region = Column(String(20))
    address = Column(String(200), comment="주소")
    lat = Column(Numeric(10, 7), comment="위도")
    lng = Column(Numeric(10, 7), comment="경도")
    category = Column(String(50), comment="디저트카페/브런치카페/북카페 등")
    price_range = Column("priceRange", String(50), comment="가격대")
    rating = Column(Numeric(2, 1), comment="평점")
    description = Column(Text, comment="설명")
    image_url = Column("imageUrl", String(500), comment="대표 이미지")
    is_placeholder = Column("isPlaceholder", Boolean, nullable=False, default=False,
                             comment="실제 업체가 아니라 seed_listings.py의 가상 데모 카페인지 여부")
    opening_hours = Column("openingHours", String(100))
    parking = Column(String(100))
    review_count = Column("reviewCount", Integer, default=0)