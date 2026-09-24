from fastapi import APIRouter, HTTPException, Query

from service.locationService import coord_to_address

router = APIRouter(prefix="/api", tags=["location"])


@router.get("/location/address")
def location_address(lat: float = Query(...), lng: float = Query(...)):
    """브라우저에서 받은 현재 위치(위도/경도)를 주소로 변환 - 실제 경로: GET /api/location/address"""
    address = coord_to_address(lat, lng)
    if address is None:
        raise HTTPException(status_code=502, detail="주소를 가져오지 못했어요")
    return {"address": address}
