import uuid

from sqlalchemy import (
    Column, Integer, String, Numeric, Text, Boolean,
    Date, Time, DateTime, ForeignKey, JSON, Uuid, Enum as SAEnum
)
from config.database import Base
from models.paymentMethod import PaymentMethod
from models.paymentStatus import PaymentStatus


class Payment(Base):
    __tablename__ = "Payment"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id = Column("memberId", Uuid(as_uuid=False), ForeignKey("Members.id"))
    payment_type = Column("paymentType", SAEnum(PaymentMethod), comment="결제방식")
    created_at = Column("createdAt", DateTime)
    price = Column(Integer)
    booking_id = Column("bookingId", Uuid(as_uuid=False), ForeignKey("Booking.id"))
    status = Column(SAEnum(PaymentStatus), comment="결제 상태")
    cancelled_at = Column("cancelledAt", DateTime, comment="결제 취소 시간")
