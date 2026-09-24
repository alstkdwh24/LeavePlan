import uuid

from config.database import Base
from sqlalchemy import (
    Column, Integer, String, Numeric, Text, Boolean,
    Date, Time, DateTime, ForeignKey, JSON, Uuid, Enum as SAEnum
)

from models.bookingStatus import BookingStatus


class Booking(Base):
    __tablename__ = "Booking"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    book_name = Column(String(100), comment="예약")
    created_at = Column(DateTime, comment="생성시간")
    member_id = Column(Uuid(as_uuid=False), ForeignKey("Members.id"))
    check_in = Column(DateTime, comment="체크인 날짜")
    check_out = Column(DateTime, comment="체크아웃 날짜")
    status = Column(SAEnum(BookingStatus), comment="상태")
    price = Column(Integer, comment="가격")
    stay_id = Column("stay_id", Uuid(as_uuid=False), ForeignKey("StayListing.id"))
    cancelled_at = Column("cancelledAt", DateTime, comment="취소 시각")
    cancel_reason = Column("cancelReason", String(200), comment="취소 사유")
    refund_amount = Column("refundAmount", Integer, comment="실제 환불된 금액")
    trip_id = Column("tripId", Uuid(as_uuid=False), ForeignKey("Trip.id"), comment="여행일정 관련 id")
    room_type_id = Column("roomTypeId",Uuid(as_uuid=False), ForeignKey("RoomType.id"), comment="룸타입관련 id")
    guest_count =Column("guestCount", Integer)
