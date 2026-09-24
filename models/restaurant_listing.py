import uuid

from sqlalchemy import Column, String, Numeric, Text, Boolean, Uuid

from config.database import Base


class RestaurantListing(Base):
    """예약/추천 대상으로 쓰는 식당 목록 — 여행 플래너에서 실제로 보여주는 도메인 테이블.
    공공데이터 일반음식점 인허가 원본 데이터는 models/restaurant.py의 Restaurant을 따로 참고."""

    __tablename__ = "RestaurantListing"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    restaurant_name = Column("restaurantName", String(100), nullable=False)
    region = Column(String(100))
    address = Column(String(200), comment="주소")
    lat = Column(Numeric(10, 7), comment="위도")
    lng = Column(Numeric(10, 7), comment="경도")
    category = Column(String(50), comment="한식/양식/일식 등 음식 카테고리")
    price_range = Column("priceRange", String(50), comment="가격대 (예: 1만원대, 3만원대~)")
    rating = Column(Numeric(2, 1), comment="평점")
    description = Column(Text, comment="설명")
    image_url = Column("imageUrl", String(500), comment="대표 이미지")
    website = Column(String(200), comment="사이트")
    is_placeholder = Column("isPlaceholder", Boolean, nullable=False, default=False,
                             comment="실제 업체가 아니라 seed_listings.py의 가상 데모 식당인지 여부")
