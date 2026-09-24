from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from config.database import get_db
from models.stay_listing import StayListing
from models.restaurant_listing import RestaurantListing
from models.cafe_listing import CafeListing
from models.room_type import RoomType
from models.restaurant_menu_item import RestaurantMenuItem
from models.cafe_menu_item import CafeMenuItem
from schemas.listing import ListingOut
from schemas.room_type import RoomTypeOut
from schemas.menu_item import MenuItemOut

# prefix="/listings" -> 이 라우터의 모든 경로 앞에 /listings가 붙음
router = APIRouter(prefix="/listings", tags=["listings"])


def _stay_to_out(row: StayListing) -> ListingOut:
    return ListingOut(
        id=row.id, category_type="stay", name=row.stayName, region=row.region,
        address=row.address, lat=float(row.lat) if row.lat is not None else None,
        lng=float(row.lng) if row.lng is not None else None,
        price=row.price, rating=float(row.rating) if row.rating is not None else None,
        description=row.description, image_url=row.imageUrl,
        is_placeholder=bool(row.isPlaceholder),
    )


def _restaurant_to_out(row: RestaurantListing) -> ListingOut:
    return ListingOut(
        id=row.id, category_type="restaurant", name=row.restaurant_name, region=row.region,
        address=row.address, lat=float(row.lat) if row.lat is not None else None,
        lng=float(row.lng) if row.lng is not None else None,
        category=row.category, price_range=row.price_range,
        rating=float(row.rating) if row.rating is not None else None,
        description=row.description, image_url=row.image_url,
        is_placeholder=bool(row.is_placeholder),
    )


def _cafe_to_out(row: CafeListing) -> ListingOut:
    return ListingOut(
        id=row.id, category_type="cafe", name=row.cafe_name, region=row.region,
        address=row.address, lat=float(row.lat) if row.lat is not None else None,
        lng=float(row.lng) if row.lng is not None else None,
        category=row.category, price_range=row.price_range,
        rating=float(row.rating) if row.rating is not None else None,
        description=row.description, image_url=row.image_url,
        is_placeholder=bool(row.is_placeholder),
    )


# StayListing이 전국 공공데이터 임포트로 3만 건이 넘어서(카페/식당은 아직 소량), region 필터 +
# limit/offset 페이지네이션을 셋 다 공통으로 지원한다 — 프론트가 한 번에 전부 그리드로 렌더링하면
# 브라우저가 버거워지므로 기본 limit(60)을 둔다.
@router.get("/stay", response_model=list[ListingOut])
def get_stay_listings(
    region: str | None = None,
    limit: int = Query(60, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(StayListing)
    if region:
        query = query.filter(StayListing.region == region)
    rows = query.offset(offset).limit(limit).all()
    return [_stay_to_out(r) for r in rows]


@router.get("/stay/{stay_id}", response_model=ListingOut)
def get_stay_listing(stay_id: str, db: Session = Depends(get_db)):
    row = db.query(StayListing).filter(StayListing.id == stay_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="숙소를 찾을 수 없습니다.")
    return _stay_to_out(row)


@router.get("/restaurant", response_model=list[ListingOut])
def get_restaurant_listings(
    region: str | None = None,
    limit: int = Query(60, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(RestaurantListing)
    if region:
        query = query.filter(RestaurantListing.region == region)
    rows = query.offset(offset).limit(limit).all()
    return [_restaurant_to_out(r) for r in rows]


@router.get("/cafe", response_model=list[ListingOut])
def get_cafe_listings(
    region: str | None = None,
    limit: int = Query(60, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(CafeListing)
    if region:
        query = query.filter(CafeListing.region == region)
    rows = query.offset(offset).limit(limit).all()
    return [_cafe_to_out(r) for r in rows]


def _room_type_to_out(row: RoomType) -> RoomTypeOut:
    return RoomTypeOut(
        id=row.id, stay_id=row.stay_id, room_name=row.room_name, bed_type=row.bed_type,
        base_capacity=row.base_capacity, max_capacity=row.max_capacity, price=row.price,
        stock=row.stock, description=row.description, image_url=row.image_url,
        is_placeholder=bool(row.is_placeholder),
    )


def _restaurant_menu_to_out(row: RestaurantMenuItem) -> MenuItemOut:
    return MenuItemOut(
        id=row.id, owner_id=row.restaurant_id, menu_name=row.menu_name, category=row.category,
        price=row.price, is_signature=bool(row.is_signature), description=row.description,
        image_url=row.image_url, is_placeholder=bool(row.is_placeholder),
    )


def _cafe_menu_to_out(row: CafeMenuItem) -> MenuItemOut:
    return MenuItemOut(
        id=row.id, owner_id=row.cafe_id, menu_name=row.menu_name, category=row.category,
        price=row.price, is_signature=bool(row.is_signature), description=row.description,
        image_url=row.image_url, is_placeholder=bool(row.is_placeholder),
    )


@router.get("/stay/{stay_id}/rooms", response_model=list[RoomTypeOut])
def get_room_types(stay_id: str, db: Session = Depends(get_db)):
    rows = db.query(RoomType).filter(RoomType.stay_id == stay_id).all()
    return [_room_type_to_out(r) for r in rows]


@router.get("/restaurant/{restaurant_id}/menu", response_model=list[MenuItemOut])
def get_restaurant_menu(restaurant_id: str, db: Session = Depends(get_db)):
    rows = db.query(RestaurantMenuItem).filter(RestaurantMenuItem.restaurant_id == restaurant_id).all()
    return [_restaurant_menu_to_out(r) for r in rows]


@router.get("/cafe/{cafe_id}/menu", response_model=list[MenuItemOut])
def get_cafe_menu(cafe_id: str, db: Session = Depends(get_db)):
    rows = db.query(CafeMenuItem).filter(CafeMenuItem.cafe_id == cafe_id).all()
    return [_cafe_menu_to_out(r) for r in rows]
