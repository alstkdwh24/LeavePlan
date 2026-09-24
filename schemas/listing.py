from pydantic import BaseModel


class ListingOut(BaseModel):
    """StayListing/RestaurantListing/CafeListing 3개 테이블을 프론트엔드에서 하나의 그리드로
    보여줄 수 있도록 공통 모양으로 맞춘 응답 스키마. 원본 테이블마다 컬럼명이 달라서
    (stayName vs restaurantName vs cafeName 등) 라우터에서 각 모델을 이 모양으로 변환해 내려준다."""

    id: str
    category_type: str  # "stay" | "cafe" | "restaurant"
    name: str
    region: str | None = None
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    category: str | None = None       # 카페/식당의 세부 카테고리 (숙소는 없음)
    price: int | None = None          # 숙박 1박 가격 (원 단위) — 카페/식당은 None
    price_range: str | None = None    # 카페/식당 가격대 (예: "2만원대") — 숙박은 None
    rating: float | None = None
    description: str | None = None
    image_url: str | None = None
    is_placeholder: bool = False
