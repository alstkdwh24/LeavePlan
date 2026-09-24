import uuid

from sqlalchemy import Column, String, Integer, Text, Boolean, ForeignKey, Uuid

from config.database import Base


class RoomType(Base):
    """StayListing(숙소) 하나에 딸린 개별 방 종류 — 방 이름/인원/1박 가격 등 예약 단위의 세부 정보.
    숙소 하나에 방 종류가 여러 개 있을 수 있어 stay_id로 StayListing과 1:N 관계."""

    __tablename__ = "RoomType"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    stay_id = Column("stayId", Uuid(as_uuid=False), ForeignKey("StayListing.id"), nullable=False, index=True)
    room_name = Column("roomName", String(100), nullable=False, comment="방 이름 (예: 디럭스 더블룸)")
    bed_type = Column("bedType", String(50), comment="침대 타입 (예: 더블베드 1개, 트윈베드 2개)")
    base_capacity = Column("baseCapacity", Integer, comment="기준 인원")
    max_capacity = Column("maxCapacity", Integer, comment="최대 인원")
    price = Column(Integer, comment="1박 가격")
    stock = Column(Integer, comment="예약 가능 객실 수(재고)")
    description = Column(Text, comment="설명")
    image_url = Column("imageUrl", String(500), comment="대표 이미지")
    is_placeholder = Column("isPlaceholder", Boolean, nullable=False, default=False,
                             comment="실제 확인된 객실 정보가 아니라 자동 생성된 예시 데이터인지 여부")
