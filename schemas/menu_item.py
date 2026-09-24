from pydantic import BaseModel


class MenuItemOut(BaseModel):
    """RestaurantMenuItem/CafeMenuItem 2개 테이블을 프론트엔드에서 같은 모양으로 쓸 수 있도록
    맞춘 응답 스키마. 컬럼명이 같아서(menu_name/price 등) listing.py의 ListingOut과 달리
    변환 없이 그대로 재사용 가능."""

    id: str
    owner_id: str  # 소속 식당/카페 id (restaurant_id 또는 cafe_id)
    menu_name: str
    category: str | None = None
    price: int | None = None
    is_signature: bool = False
    description: str | None = None
    image_url: str | None = None
    is_placeholder: bool = False
