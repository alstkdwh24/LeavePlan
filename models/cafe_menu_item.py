import uuid

from sqlalchemy import Column, String, Integer, Text, Boolean, ForeignKey, Uuid

from config.database import Base


class CafeMenuItem(Base):
    """CafeListing(카페) 하나에 딸린 개별 메뉴 항목 — 메뉴명/가격 등 세부 정보.
    카페 하나에 메뉴가 여러 개 있을 수 있어 cafe_id로 CafeListing과 1:N 관계."""

    __tablename__ = "CafeMenuItem"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    cafe_id = Column("cafeId", Uuid(as_uuid=False), ForeignKey("CafeListing.id"), nullable=False, index=True)
    menu_name = Column("menuName", String(100), nullable=False, comment="메뉴명")
    category = Column(String(50), comment="커피/음료/디저트 등 메뉴 분류")
    price = Column(Integer, comment="가격")
    is_signature = Column("isSignature", Boolean, default=False, comment="대표(시그니처) 메뉴 여부")
    description = Column(Text, comment="설명")
    image_url = Column("imageUrl", String(500), comment="메뉴 사진")
    is_placeholder = Column("isPlaceholder", Boolean, nullable=False, default=False,
                             comment="실제 확인된 메뉴가 아니라 자동 생성된 예시 데이터인지 여부")
