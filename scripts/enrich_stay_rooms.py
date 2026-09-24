"""
한국관광공사 TourAPI(공공데이터포털)로 실제 숙박업소 + 객실(방 종류) 정보를 가져와
StayListing / RoomType 테이블에 채우는 스크립트.

enrich_listings.py(카카오+구글)와 같은 역할이지만, 소스가 TourAPI 하나뿐이라 더 단순하다.
TourAPI는 이름/주소/좌표뿐 아니라 "객실 반복정보"(방이름/인원/요금/사진)까지 무료로 제공해서,
이 스크립트 하나로 StayListing과 RoomType을 함께 채울 수 있다.

    1) searchKeyword2로 키워드에 맞는 숙박업소 후보를 찾는다 (contentTypeId=32).
    2) 후보마다 detailInfo2로 객실 반복정보를 가져온다.
    3) 새 숙소면 StayListing에 추가하고, 그 방들을 RoomType에 추가한다.
       이미 있는 숙소(이름+지역 동일)면 StayListing은 건드리지 않고 RoomType만 보강한다.

사용법 (프로젝트 어느 위치에서 실행해도 됨):
    python scripts/enrich_stay_rooms.py --keyword "강릉 리조트" --region 강릉 --limit 5
    python scripts/enrich_stay_rooms.py --keyword "제주 풀빌라" --region 제주 --limit 5 --dry-run

전제:
    - .env(또는 실행 환경변수)에 DB_USER/DB_PASSWORD/DB_HOST/DB_NAME이 채워져 있어야 함
    - TOUR_API_KEY: data.go.kr에서 "한국관광공사_국문 관광정보 서비스_GW" 활용신청 후 발급받은
      일반 인증키(Decoding)를 그대로 사용. 계정/키 발급은 대신 만들어줄 수 없음 — 발급 후 이 스크립트를
      실행하는 환경(예: PyCharm Run Configuration의 환경변수, 다른 env들과 같은 자리)에 추가할 것

주의:
    - StayListing.rating은 이 스크립트로 채우지 않는다 — TourAPI에는 평점 필드가 없고,
      Google Places API의 rating은 약관상 저장(캐싱)이 금지돼 있어 DB 컬럼으로 두기 부적절하다고
      판단해 의도적으로 제외했다 (필요해지면 별도로 화면에서 라이브 호출하는 방식으로 다시 설계할 것).
    - StayListing.price(1박 가격)는 그 숙소의 방들 중 최저 비수기 요금으로 채운다. TourAPI가 요금을
      아예 안 주는 숙소는 price가 NULL로 남는다.
    - cancellationPolicy는 TourAPI에 없는 정보라 그대로 NULL로 남는다.
    - roomintro 등 일부 필드는 HTML 태그/엔티티가 섞여 오므로 간단히 정리해서 저장한다.
"""
import argparse
import html
import logging
import logging.config
import os
import re
import sys
import time
from urllib.parse import quote, urlencode

# 프로젝트 루트(LeavePlnner)를 sys.path에 추가 — `python scripts/xxx.py`로 직접 실행해도
# `from config...`, `from models...` 임포트가 되도록 함
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import httpx
from sqlalchemy import text

from config.database import Base, engine, SessionLocal, DB_USER, DB_HOST, DB_NAME
from config.logging_config import LOGGING_CONFIG
from models.stay_listing import StayListing
from models.room_type import RoomType

logging.config.dictConfig(LOGGING_CONFIG)
log = logging.getLogger(__name__)

TOUR_API_KEY = os.getenv("TOUR_API_KEY")

TOUR_API_BASE = "https://apis.data.go.kr/B551011/KorService2"
SEARCH_KEYWORD_URL = f"{TOUR_API_BASE}/searchKeyword2"
DETAIL_INFO_URL = f"{TOUR_API_BASE}/detailInfo2"
AREA_BASED_LIST_URL = f"{TOUR_API_BASE}/areaBasedList2"
AREA_CODE_URL = f"{TOUR_API_BASE}/areaCode2"

STAY_CONTENT_TYPE_ID = 32  # TourAPI 콘텐츠 타입: 32=숙박

# TourAPI 사이 예의상 딜레이(초) — 초당 호출수 제한 있음
API_SLEEP = 0.2

_TAG_RE = re.compile(r"<[^>]+>")


def require_config() -> None:
    if not TOUR_API_KEY:
        raise RuntimeError(
            "환경변수 TOUR_API_KEY가 비어있습니다. data.go.kr에서 "
            "'한국관광공사_국문 관광정보 서비스_GW' 활용신청 후 발급받은 일반 인증키(Decoding)를 "
            "이 스크립트를 실행하는 환경(PyCharm Run Configuration 등, DB_HOST와 같은 자리)에 추가해주세요."
        )
    if not DB_USER or not DB_NAME:
        raise RuntimeError(
            f"DB 접속 정보가 비어있습니다 (DB_USER={DB_USER!r}, DB_HOST={DB_HOST!r}, DB_NAME={DB_NAME!r}). "
            "Run > Edit Configurations 에서 이 스크립트 설정에도 환경변수를 추가해주세요."
        )


def _clean_text(raw: str | None) -> str | None:
    """TourAPI 응답에 섞여오는 HTML 태그/엔티티를 걷어낸 순수 텍스트로 정리."""
    if not raw:
        return None
    text_only = _TAG_RE.sub(" ", raw)
    text_only = html.unescape(text_only)
    text_only = re.sub(r"\s+", " ", text_only).strip()
    return text_only or None


def _to_int(raw) -> int | None:
    """'50,000' 같은 문자열 요금을 정수로. 빈 값/파싱 불가 시 None."""
    if raw is None:
        return None
    digits = re.sub(r"[^\d]", "", str(raw))
    return int(digits) if digits else None


def _service_key_param() -> str:
    """data.go.kr 키는 '일반 인증키(Encoding)'와 '(Decoding)' 두 종류가 있는데, Encoding 키를
    httpx의 params=에 그대로 넘기면 httpx가 다시 URL-인코딩해서 이중 인코딩(인증 실패)이 된다.
    이미 %XX 형태로 인코딩된 값(Encoding 키)이면 그대로 쓰고, 아니면(Decoding 키) 직접 인코딩해서
    항상 serviceKey만 URL 문자열에 직접 박아 넣는다 — httpx가 다시 건드리지 않도록."""
    key = TOUR_API_KEY or ""
    return key if "%" in key else quote(key, safe="")


def _build_url(base: str, **extra) -> str:
    query = urlencode({"MobileOS": "ETC", "MobileApp": "leaveplan", "_type": "json", **extra})
    return f"{base}?serviceKey={_service_key_param()}&{query}"


MAX_429_RETRIES = 3
RETRY_BACKOFF_SECONDS = 5.0


def _get_with_retry(url: str) -> httpx.Response:
    """data.go.kr가 순간 트래픽 제한(HTTP 429)을 걸 때가 있어서, 잠깐 기다렸다가 재시도한다.
    (하루 호출 한도 자체를 넘긴 경우엔 재시도해도 계속 429가 나므로, 결국 예외가 올라가 호출부의
    circuit breaker가 잡는다.)"""
    for attempt in range(1, MAX_429_RETRIES + 1):
        resp = httpx.get(url, timeout=10)
        if resp.status_code != 429:
            resp.raise_for_status()
            return resp
        if attempt == MAX_429_RETRIES:
            resp.raise_for_status()
        log.warning("  [429 Too Many Requests] %d초 대기 후 재시도 (%d/%d)",
                    int(RETRY_BACKOFF_SECONDS * attempt), attempt, MAX_429_RETRIES)
        time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    raise RuntimeError("unreachable")  # pragma: no cover


def search_keyword(keyword: str, limit: int) -> list[dict]:
    """숙박업소 후보를 이름/주소/좌표/사진과 함께 가져온다."""
    url = _build_url(
        SEARCH_KEYWORD_URL,
        keyword=keyword, contentTypeId=STAY_CONTENT_TYPE_ID,
        numOfRows=limit, pageNo=1,
    )
    resp = _get_with_retry(url)
    body = resp.json().get("response", {}).get("body", {})
    items = body.get("items")
    if not items:
        return []
    item_list = items.get("item", [])
    return item_list if isinstance(item_list, list) else [item_list]


def search_area(area_code: str, sigungu_code: str, num_of_rows: int, page_no: int = 1) -> tuple[list[dict], int]:
    """지역코드(광역+시군구)에 등록된 숙박업소를 이름 상관없이 전부 가져온다 (searchKeyword2보다
    훨씬 넓게 잡힘 — 업체명에 지역명이 안 들어간 곳도 빠짐없이 잡힌다).
    반환값: (이번 페이지 후보 목록, 전체 건수 totalCount)."""
    url = _build_url(
        AREA_BASED_LIST_URL,
        areaCode=area_code, sigunguCode=sigungu_code, contentTypeId=STAY_CONTENT_TYPE_ID,
        numOfRows=num_of_rows, pageNo=page_no,
    )
    resp = _get_with_retry(url)
    body = resp.json().get("response", {}).get("body", {})
    total_count = body.get("totalCount", 0)
    items = body.get("items")
    if not items:
        return [], total_count
    item_list = items.get("item", [])
    return (item_list if isinstance(item_list, list) else [item_list]), total_count


def list_province_codes() -> list[dict]:
    """광역 지역코드(서울/강원특별자치도 등 17개) 목록."""
    url = _build_url(AREA_CODE_URL, numOfRows=30, pageNo=1)
    resp = _get_with_retry(url)
    body = resp.json().get("response", {}).get("body", {})
    items = body.get("items", {})
    item_list = items.get("item", []) if items else []
    return item_list if isinstance(item_list, list) else [item_list]


def list_sigungu_codes(area_code: str) -> list[dict]:
    """광역 지역코드 하나 밑의 시군구 코드 목록."""
    url = _build_url(AREA_CODE_URL, areaCode=area_code, numOfRows=100, pageNo=1)
    resp = _get_with_retry(url)
    body = resp.json().get("response", {}).get("body", {})
    items = body.get("items", {})
    item_list = items.get("item", []) if items else []
    return item_list if isinstance(item_list, list) else [item_list]


def fetch_room_types(content_id: str) -> list[dict]:
    """숙소 하나의 객실 반복정보(방이름/인원/요금/사진)를 가져온다."""
    url = _build_url(DETAIL_INFO_URL, contentId=content_id, contentTypeId=STAY_CONTENT_TYPE_ID)
    resp = _get_with_retry(url)
    body = resp.json().get("response", {}).get("body", {})
    items = body.get("items")
    if not items:
        return []
    item_list = items.get("item", [])
    return item_list if isinstance(item_list, list) else [item_list]


def room_item_to_kwargs(room: dict) -> dict:
    off_season = _to_int(room.get("roomoffseasonminfee1")) or _to_int(room.get("roomoffseasonminfee2"))
    peak_season = _to_int(room.get("roompeakseasonminfee1")) or _to_int(room.get("roompeakseasonminfee2"))
    return dict(
        room_name=room.get("roomtitle") or "객실",
        base_capacity=_to_int(room.get("roombasecount")),
        max_capacity=_to_int(room.get("roommaxcount")),
        price=off_season or peak_season,
        description=_clean_text(room.get("roomintro")),
        image_url=room.get("roomimg1") or None,
    )


def process_candidates(session, candidates: list[dict], region: str, dry_run: bool) -> tuple[int, int, int]:
    """후보(숙박업소) 목록을 순회하며 StayListing/RoomType을 채운다 (신규 추가 또는 업데이트).
    search_keyword든 search_area든, 후보 dict 모양(title/contentid/addr1/mapx/mapy/firstimage)이
    같아서 이 함수 하나로 공용 처리한다. 반환값: (신규 숙소, 신규 방, 업데이트된 방) 건수."""
    new_stay_count = 0
    new_room_count = 0
    updated_room_count = 0

    for i, cand in enumerate(candidates, start=1):
        name = cand.get("title")
        content_id = cand.get("contentid")
        if not name or not content_id:
            continue

        log.info("[%d/%d] 객실정보 조회 중: %s", i, len(candidates), name)
        rooms = fetch_room_types(content_id)
        time.sleep(API_SLEEP)

        room_prices = [r["price"] for r in (room_item_to_kwargs(rm) for rm in rooms) if r["price"]]
        representative_price = min(room_prices) if room_prices else None

        stay = session.query(StayListing).filter_by(stayName=name, region=region).first()
        is_new_stay = stay is None
        if is_new_stay:
            stay = StayListing(
                stayName=name, region=region,
                address=cand.get("addr1"),
                lat=float(cand["mapy"]) if cand.get("mapy") else None,
                lng=float(cand["mapx"]) if cand.get("mapx") else None,
                price=representative_price,
                imageUrl=cand.get("firstimage") or None,
            )
            if not dry_run:
                session.add(stay)
                session.flush()  # stay.id 확보
            new_stay_count += 1

        existing_rooms_by_name = {}
        if not is_new_stay:
            existing_rooms_by_name = {
                r.room_name: r for r in session.query(RoomType).filter_by(stay_id=stay.id).all()
            }

        for rm in rooms:
            kwargs = room_item_to_kwargs(rm)
            existing_room = existing_rooms_by_name.get(kwargs["room_name"])
            if existing_room is not None:
                log.info("  -> 방 업데이트: %s (%s원)", kwargs["room_name"], kwargs["price"])
                updated_room_count += 1
                if not dry_run:
                    for field, value in kwargs.items():
                        if field == "room_name":
                            continue
                        setattr(existing_room, field, value)
                continue
            log.info("  -> 방 추가: %s (%s원)", kwargs["room_name"], kwargs["price"])
            new_room_count += 1
            if not dry_run:
                session.add(RoomType(stay_id=stay.id, **kwargs))

    return new_stay_count, new_room_count, updated_room_count


def run(keyword: str, region: str, limit: int, dry_run: bool) -> None:
    require_config()

    Base.metadata.create_all(bind=engine, tables=[StayListing.__table__, RoomType.__table__])

    log.info("[TourAPI 검색] keyword=%s limit=%d", keyword, limit)
    candidates = search_keyword(keyword, limit)
    log.info("[숙박업소 후보 %d건 수집 완료]", len(candidates))

    session = SessionLocal()
    try:
        new_stay_count, new_room_count, updated_room_count = process_candidates(
            session, candidates, region, dry_run
        )

        log.info("[요약] 신규 숙소 %d건 / 신규 방 종류 %d건 / 업데이트된 방 %d건",
                 new_stay_count, new_room_count, updated_room_count)

        if dry_run:
            log.info("[--dry-run] DB에 쓰지 않고 종료합니다.")
            session.rollback()
            return

        session.commit()
    finally:
        session.close()

    with engine.connect() as conn:
        stay_count = conn.execute(text(f"SELECT COUNT(*) FROM {StayListing.__table__.name}")).scalar()
        room_count = conn.execute(text(f"SELECT COUNT(*) FROM {RoomType.__table__.name}")).scalar()
        log.info("[검증] %s 테이블 행 수 = %s, %s 테이블 행 수 = %s",
                  StayListing.__table__.name, f"{stay_count:,}", RoomType.__table__.name, f"{room_count:,}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keyword", required=True, help='TourAPI 검색어, 예: "강릉 리조트"')
    parser.add_argument("--region", required=True, help='DB에 저장할 지역 라벨, 예: "강릉"')
    parser.add_argument("--limit", type=int, default=5, help="가져올 숙박업소 후보 수 (기본 5)")
    parser.add_argument("--dry-run", action="store_true", help="DB에 쓰지 않고 결과만 로그로 확인")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        run(args.keyword, args.region, args.limit, args.dry_run)
    except Exception:
        log.exception("[객실정보 보강 실패]")
        raise
