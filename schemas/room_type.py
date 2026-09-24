from pydantic import BaseModel


class RoomTypeOut(BaseModel):
    """StayListing 하나에 딸린 개별 방 종류 응답 스키마."""

    id: str
    stay_id: str
    room_name: str
    bed_type: str | None = None
    base_capacity: int | None = None
    max_capacity: int | None = None
    price: int | None = None
    stock: int | None = None
    description: str | None = None
    image_url: str | None = None
    is_placeholder: bool = False
