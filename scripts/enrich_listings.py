"""
StayListing / RestaurantListing / CafeListing(예약·추천 화면에서 실제로 보여주는 도메인 테이블)을
채우는 스크립트.

공공데이터 인허가 CSV(Stay/Restaurant/Cafe)에는 상호명·주소·좌표만 있고 rating/price/imageUrl/
description 같은 필드가 없어서, 이 스크립트는 카카오 로컬 API로 후보를 찾고 네이버 지역 검색으로
같은 상호명이 실제로 존재하는지 교차검증만 한다.

    1) 카카오 로컬 API(키워드 검색)로 후보 업체의 상호명·주소·좌표·카테고리를 찾는다.
    2) 네이버 지역 검색 API로 같은 키워드를 검색해서, 카카오 후보 이름이 네이버 결과에도
       등장하는지 대조한다(교차검증 플래그만 남기고 DB에는 저장하지 않음 — 로그로만 확인).
    3) 카카오 결과를 StayListing / RestaurantListing / CafeListing에 저장한다.

※ 구글 Places API는 쓰지 않는다(유료). 그 결과 rating(평점)·image_url(사진)·price_range(가격대)는
   카카오/네이버 어느 쪽에도 무료로 제공하는 공식 API가 없어서 이 스크립트로는 채울 수 없고
   NULL로 남는다. 필요해지면 화면에서 카카오맵/네이버지도 링크로 연결하는 방식을 검토할 것.

사용법 (프로젝트 어느 위치에서 실행해도 됨):
    python scripts/enrich_listings.py --target stay --region 강릉 --keyword "강릉 오션뷰 풀빌라" --limit 10
    python scripts/enrich_listings.py --target cafe --region 강릉 --keyword "강릉 감성 카페" --limit 10
    python scripts/enrich_listings.py --target restaurant --region 강릉 --keyword "강릉 맛집" --limit 10 --dry-run

전제:
    - .env(또는 실행 환경변수)에 DB_USER/DB_PASSWORD/DB_HOST/DB_NAME이 채워져 있어야 함
    - KAKAO_REST_API_KEY: https://developers.kakao.com 에서 애플리케이션 생성 → REST API 키 발급
      (앱 설정 > 플랫폼에서 별도 등록 없이 REST API는 바로 씀. 카카오맵 사용 동의 필요할 수 있음)
    - NAVER_CLIENT_ID / NAVER_CLIENT_SECRET: https://developers.naver.com/apps 에서 애플리케이션
      등록 → "검색" API 사용 설정 → Client ID/Secret 발급 (무료, 결제 계정 불필요)
    - 이 키들은 계정 생성/발급이 필요해서 대신 만들어줄 수 없음 — 직접 발급 후 이 스크립트를
      실행하는 환경(예: PyCharm Run Configuration의 환경변수, 다른 env들과 같은 자리)에 추가할 것

주의:
    - 네이버 지역 검색 API는 한 번 호출에 최대 5건만 돌려준다(display 파라미터 상한). 그래서
      "네이버에서 못 찾음 = 교차검증 실패"가 실제로는 "네이버 상위 5건 안에 없었을 뿐"인 경우가
      섞여 있을 수 있다. 교차검증 실패(unconfirmed)는 삭제하지 않고 로그로만 표시하니, 결과를
      보고 의심스러운 항목은 사람이 직접 확인할 것.
    - 네이버 응답의 mapx/mapy는 좌표계가 불안정해 신뢰하지 않는다 — 좌표는 항상 카카오 값을 쓴다.
    - price(숙박 1박 가격)·rating·image_url·price_range 등은 이 스크립트로는 채울 수 없다.
      그대로 NULL로 남고, 별도 소스(TourAPI의 enrich_stay_rooms.py, 직접 입력 등)가 필요하다.
"""
import argparse
import html
import logging
import logging.config
import os
import re
import sys
import time

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
from models.restaurant_listing import RestaurantListing
from models.cafe_listing import CafeListing

logging.config.dictConfig(LOGGING_CONFIG)
log = logging.getLogger(__name__)

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

KAKAO_KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
NAVER_LOCAL_SEARCH_URL = "https://openapi.naver.com/v1/search/local.json"
NAVER_MAX_DISPLAY = 5  # 네이버 지역 검색 API의 display 파라미터 상한

# 카카오/네이버 사이 예의상 딜레이(초) — 둘 다 초당 호출수 제한이 있음
API_SLEEP = 0.15

_TAG_RE = re.compile(r"<[^>]+>")

# target 이름 -> (모델, 상호명 속성명, region 속성명, category 속성명 또는 None)
TARGETS = {
    "stay": {
        "model": StayListing,
        "name_attr": "stayName",
        "region_attr": "region",
        "category_attr": None,  # StayListing엔 category 컬럼이 없음
        "kakao_group_code": None,  # stay는 카카오를 안 씀(TourAPI 전용, enrich_stay_rooms.py)
    },
    "restaurant": {
        "model": RestaurantListing,
        "name_attr": "restaurant_name",
        "region_attr": "region",
        "category_attr": "category",
        "kakao_group_code": "FD6",  # 카카오 카테고리 그룹코드: 음식점
    },
    "cafe": {
        "model": CafeListing,
        "name_attr": "cafe_name",
        "region_attr": "region",
        "category_attr": "category",
        "kakao_group_code": "CE7",  # 카카오 카테고리 그룹코드: 카페
    },
}


def require_api_keys() -> None:
    missing = []
    if not KAKAO_REST_API_KEY:
        missing.append("KAKAO_REST_API_KEY")
    if not NAVER_CLIENT_ID:
        missing.append("NAVER_CLIENT_ID")
    if not NAVER_CLIENT_SECRET:
        missing.append("NAVER_CLIENT_SECRET")
    if missing:
        raise RuntimeError(
            f"다음 환경변수가 비어있습니다: {', '.join(missing)}. "
            "카카오는 https://developers.kakao.com, 네이버는 https://developers.naver.com/apps 에서 "
            "키를 발급한 뒤, 이 스크립트를 실행하는 환경(PyCharm Run Configuration 등, "
            "DB_HOST/REDIS_URL과 같은 자리)에 추가해주세요."
        )
    if not DB_USER or not DB_NAME:
        raise RuntimeError(
            f"DB 접속 정보가 비어있습니다 (DB_USER={DB_USER!r}, DB_HOST={DB_HOST!r}, DB_NAME={DB_NAME!r}). "
            "Run > Edit Configurations 에서 이 스크립트 설정에도 환경변수를 추가해주세요."
        )


def kakao_keyword_search(keyword: str, limit: int) -> list[dict]:
    """카카오 로컬 키워드 검색 — 상호명/주소/좌표/카테고리 후보를 가져온다."""
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    results: list[dict] = []
    page = 1
    while len(results) < limit:
        size = min(15, limit - len(results))  # 카카오 한 페이지 최대 15건
        resp = httpx.get(
            KAKAO_KEYWORD_URL,
            headers=headers,
            params={"query": keyword, "page": page, "size": size},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        documents = data.get("documents", [])
        results.extend(documents)
        if data.get("meta", {}).get("is_end", True) or not documents:
            break
        page += 1
        time.sleep(API_SLEEP)
    return results[:limit]


def naver_local_search(keyword: str) -> list[dict]:
    """네이버 지역 검색 — 카카오 후보와 이름을 대조하는 교차검증 용도로만 쓴다.
    평점/사진은 안 주고, 한 번에 최대 5건까지만 온다. 좌표(mapx/mapy)는 불안정해서 안 쓴다."""
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    resp = httpx.get(
        NAVER_LOCAL_SEARCH_URL,
        headers=headers,
        params={"query": keyword, "display": NAVER_MAX_DISPLAY},
        timeout=10,
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    cleaned = []
    for item in items:
        title = html.unescape(_TAG_RE.sub("", item.get("title", "")))
        cleaned.append({
            "title": title,
            "address": item.get("roadAddress") or item.get("address") or "",
        })
    return cleaned


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", "", name).lower()


def cross_validate(kakao_name: str, naver_candidates: list[dict]) -> bool:
    """카카오 후보 이름이 네이버 지역검색 결과에도 등장하는지 확인하는 참고용 플래그.
    네이버 쪽 recall이 최대 5건뿐이라, False라고 해서 실제로 없는 업체라는 뜻은 아니다."""
    target = _normalize_name(kakao_name)
    for cand in naver_candidates:
        cand_name = _normalize_name(cand["title"])
        if target == cand_name or target in cand_name or cand_name in target:
            return True
    return False


def build_candidate(kakao_doc: dict, naver_candidates: list[dict]) -> dict:
    """카카오 후보 1건 + 네이버 교차검증 결과를 공통 필드 dict로 반환한다."""
    name = kakao_doc["place_name"]
    address = kakao_doc.get("road_address_name") or kakao_doc["address_name"]
    return {
        "name": name,
        "address": address,
        "lat": float(kakao_doc["y"]),
        "lng": float(kakao_doc["x"]),
        "category_name": kakao_doc.get("category_name", ""),
        "naver_confirmed": cross_validate(name, naver_candidates),
    }


def to_model_kwargs(target: str, region: str, category_override: str | None, candidate: dict) -> dict:
    spec = TARGETS[target]
    kwargs = {
        spec["name_attr"]: candidate["name"],
        spec["region_attr"]: region,
        "address": candidate["address"],
        "lat": candidate["lat"],
        "lng": candidate["lng"],
    }
    if spec["category_attr"]:
        kwargs[spec["category_attr"]] = category_override or candidate["category_name"].split(" > ")[-1]
    return kwargs


def run(target: str, keyword: str, region: str, limit: int, category_override: str | None, dry_run: bool) -> None:
    require_api_keys()
    spec = TARGETS[target]
    model = spec["model"]

    Base.metadata.create_all(bind=engine, tables=[model.__table__])

    log.info("[카카오 검색] keyword=%s limit=%d", keyword, limit)
    kakao_candidates = kakao_keyword_search(keyword, limit)
    log.info("[카카오 후보 %d건 수집 완료]", len(kakao_candidates))

    # 카카오 키워드 검색은 이름/설명에 "카페"류 단어만 있으면 느슨하게 매칭해서, 실제론 카페가 아닌
    # 업체(인테리어점, 잡화점 등)가 섞여 들어올 수 있다. 카카오가 결과마다 정확히 분류해서 주는
    # category_group_code(카페=CE7, 음식점=FD6)로 걸러서 오탐을 줄인다.
    group_code = spec["kakao_group_code"]
    if group_code:
        before_filter = len(kakao_candidates)
        mismatched = [c for c in kakao_candidates if c.get("category_group_code") != group_code]
        kakao_candidates = [c for c in kakao_candidates if c.get("category_group_code") == group_code]
        if mismatched:
            log.info("[카테고리 불일치로 %d건 제외] %s",
                      len(mismatched), ", ".join(f"{c['place_name']}({c.get('category_name')})" for c in mismatched))
        log.info("[카테고리 필터링] %d건 -> %d건", before_filter, len(kakao_candidates))

    log.info("[네이버 교차검증용 검색] keyword=%s (최대 %d건)", keyword, NAVER_MAX_DISPLAY)
    try:
        naver_candidates = naver_local_search(keyword)
    except httpx.HTTPStatusError as e:
        # 네이버는 어디까지나 참고용 교차검증이라, 이게 실패했다고 카카오 결과까지 버릴 필요는 없다.
        # (키 미설정/권한 미승인 등으로 401이 나는 경우가 흔해서, 여기서 끊기지 않게 한다.)
        log.warning("[네이버 교차검증 실패 — 건너뜀] %s: %s", type(e).__name__, e)
        naver_candidates = []
    time.sleep(API_SLEEP)

    session = SessionLocal()
    try:
        existing_names = {
            getattr(row, spec["name_attr"])
            for row in session.query(model).filter(getattr(model, spec["region_attr"]) == region).all()
        }

        rows: list[dict] = []
        confirmed_count = 0
        skipped_duplicate = 0
        for i, doc in enumerate(kakao_candidates, start=1):
            candidate = build_candidate(doc, naver_candidates)
            if candidate["name"] in existing_names:
                log.info("[%d/%d] %s — 이미 존재해서 건너뜀", i, len(kakao_candidates), candidate["name"])
                skipped_duplicate += 1
                continue
            status = "네이버 교차검증 O" if candidate["naver_confirmed"] else "네이버 교차검증 X(직접 확인 권장)"
            log.info("[%d/%d] %s — %s", i, len(kakao_candidates), candidate["name"], status)
            if candidate["naver_confirmed"]:
                confirmed_count += 1
            kwargs = to_model_kwargs(target, region, category_override, candidate)
            rows.append(kwargs)
            existing_names.add(candidate["name"])  # 같은 실행 안에서 카카오가 중복 후보를 주는 경우도 방지

        log.info("[요약] 총 %d건 처리 / 신규 %d건 / 이미 존재해서 건너뜀 %d건 / 네이버 교차검증 성공 %d건",
                  len(kakao_candidates), len(rows), skipped_duplicate, confirmed_count)

        if dry_run:
            log.info("[--dry-run] DB에 쓰지 않고 종료합니다.")
            return

        if rows:
            session.bulk_save_objects([model(**row) for row in rows])
            session.commit()
    finally:
        session.close()

    with engine.connect() as conn:
        real_count = conn.execute(text(f"SELECT COUNT(*) FROM {model.__table__.name}")).scalar()
        log.info("[검증] %s.%s 테이블 실제 행 수 = %s", DB_NAME, model.__table__.name, f"{real_count:,}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, choices=list(TARGETS.keys()))
    parser.add_argument("--keyword", required=True, help='카카오/네이버 검색어, 예: "강릉 오션뷰 풀빌라"')
    parser.add_argument("--region", required=True, help='DB에 저장할 지역 라벨, 예: "강릉"')
    parser.add_argument("--limit", type=int, default=10, help="가져올 카카오 후보 수 (기본 10)")
    parser.add_argument("--category-override", default=None, help="카카오 카테고리 대신 강제로 쓸 카테고리명")
    parser.add_argument("--dry-run", action="store_true", help="DB에 쓰지 않고 결과만 로그로 확인")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        run(args.target, args.keyword, args.region, args.limit, args.category_override, args.dry_run)
    except Exception:
        log.exception("[리스팅 보강 실패]")
        raise
