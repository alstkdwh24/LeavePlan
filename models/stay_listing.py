import enum
import uuid

from sqlalchemy import Column, String, Numeric, Text, Integer, Boolean, Uuid, Enum, JSON, Time

from config.database import Base


class StayStatus(str, enum.Enum):
    """숙소 예약 상태"""
    CONFIRMED = "예약 확정"
    PENDING = "대기"
    COMPLETED = "이용완료"
    CANCELLED = "취소"


class StayListing(Base):
    """예약 가능한 숙소(호텔 등) 목록 — 여행 플래너에서 예약 대상으로 쓰는 도메인 테이블.
    공공데이터 숙박업 인허가 원본 데이터는 models/stay.py의 Stay(테이블 stay)를 따로 참고."""

    __tablename__ = "StayListing"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    stayName = Column(String(100), nullable=False)
    region = Column(String(20))
    address = Column(String(200), comment="주소")
    lat = Column(Numeric(10, 7), comment="위도")
    lng = Column(Numeric(10, 7), comment="경도")
    price = Column(Integer, comment="1박 가격")
    rating = Column(Numeric(2, 1), comment="평점")
    description = Column(Text, comment="설명")
    imageUrl = Column(String(500), comment="대표 이미지")
    status = Column(Enum(StayStatus), comment="예약 확정, 대기, 이용완료, 취소")
    cancellationPolicy = Column(
        String(500),
        comment="취소 규정 (예: '3일 전 100%, 1일 전 50%, 당일 환불불가')",
    )
    isPlaceholder = Column(Boolean, nullable=False, default=False,
                            comment="실제 업체가 아니라 seed_listings.py의 가상 데모 숙소인지 여부")
    check_in_time = Column("checkInTime", Time)
    check_out_time = Column("checkOutTime", Time)
    amenities = Column(JSON)          # facility.py 대체
    review_count = Column("reviewCount", Integer, default=0)