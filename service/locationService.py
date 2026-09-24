import os

import httpx

# 카카오 로컬 API - 좌표(경도 x, 위도 y)를 주소로 변환
_COORD2ADDRESS_URL = "https://dapi.kakao.com/v2/local/geo/coord2address.json"


def coord_to_address(lat: float, lng: float) -> str | None:
    """위도/경도를 '인천 부평구 부평문화로 87' 같은 주소 문자열로 변환한다. 실패하면 None."""
    api_key = os.getenv("KAKAO_REST_API_KEY")
    if not api_key:
        print("KAKAO_REST_API_KEY가 설정되지 않았어요")
        return None

    try:
        res = httpx.get(
            _COORD2ADDRESS_URL,
            params={"x": lng, "y": lat},  # 카카오는 x=경도, y=위도 순서
            headers={"Authorization": f"KakaoAK {api_key}"},
            timeout=5,
        )
        res.raise_for_status()
    except httpx.HTTPError as e:
        print("카카오 주소 변환 실패:", e)
        return None

    documents = res.json().get("documents", [])
    if not documents:
        return None

    # 도로명 주소가 있으면 도로명, 없으면 지번 주소
    doc = documents[0]
    road = doc.get("road_address")
    if road:
        return road["address_name"]
    return doc["address"]["address_name"]
