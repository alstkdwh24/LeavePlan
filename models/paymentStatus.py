from models.bookingStatus import PyEnum


class PaymentStatus(PyEnum):
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"
    CANCELLED = "CANCELLED"