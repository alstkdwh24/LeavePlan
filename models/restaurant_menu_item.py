import uuid

from sqlalchemy import Column, String, Integer, Text, Boolean, ForeignKey, Uuid

from config.database import Base


class RestaurantMenuItem(Base):
    """RestaurantListing(식당) 하나에 딸린 개별 메뉴 항목 — 메뉴명/가격 등 세부 정보.
    식당 하나에 메뉴가 여러 개 있을 수 있어 restaurant_id로 RestaurantListing과 1:N 관계."""

    __tablename__ = "RestaurantMenuItem"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    restaurant_id = Column("restaurantId", Uuid(as_uuid=False), ForeignKey("RestaurantListing.id"), nullable=False, index=True)
    menu_name = Column("menuName", String(100), nullable=False, comment="메뉴명")
    category = Column(String(50), comment="메인/사이드/음료 등 메뉴 분류")
    price = Column(Integer, comment="가격")
    is_signature = Column("isSignature", Boolean, default=False, comment="대표(시그니처) 메뉴 여부")
    description = Column(Text, comment="설명")
    image_url = Column("imageUrl", String(500), comment="메뉴 사진")
    is_placeholder = Column("isPlaceholder", Boolean, nullable=False, default=False,
                             comment="실제 확인된 메뉴가 아니라 자동 생성된 예시 데이터인지 여부")
