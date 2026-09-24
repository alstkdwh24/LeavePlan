from models.bookingStatus import PyEnum


class PaymentMethod(PyEnum):
    CASH = "CASH"
    CREDIT_CARD = "CREDIT_CARD"
    SAMSUNG_PAY = "SAMSUNG_PAY"
    APPLE_PAY = "APPLE_PAY"
    NAVER_PAY = "NAVER_PAY"
    KAKAO_PAY = "KAKAO_PAY"