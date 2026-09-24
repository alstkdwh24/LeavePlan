"""
StayListing에 실제 존재하는 전국 모든 region(시군구 단위, 약 213개)을 순회하며 숙소(TourAPI)/
카페·식당(카카오+네이버)을 채우는 스크립트.

enrich_curated_regions.py는 프론트가 실제로 쓰는 5개 지역에 지역마다 손으로 고른 키워드
("강릉 감성 카페" 등) 1개씩만 쓰지만, 이 스크립트는:
    - 전국 지역 전부를 대상으로 하고
    - 카페/식당은 키워드 하나가 아니라 여러 변형(KEYWORD_VARIANTS)으로 돌려서 카카오의
      "키워드 하나당 최대 45건" 한계를 넘어 더 많은 후보를 모은다
      (예: "{지역} 카페" 뿐 아니라 "{지역} 로스터리", "{지역} 브런치카페" 등도 같이 검색)
    - 숙소는 enrich_all_regions_tour_api.py와 동일하게 TourAPI로 지역명 하나만 검색한다
      (TourAPI는 카카오 키워드 검색과 달리 관광콘텐츠 DB 전체를 지역코드로 조회하는 구조라
      카페/식당처럼 키워드를 여러 개 바꿔가며 늘릴 필요가 적다)

enrich_all_regions_tour_api.py와 같은 이어하기/연속실패중단 패턴을 그대로 쓴다. (지역, 카테고리,
키워드변형) 조합 단위로 이어하기 상태를 기록한다.

사용법:
    python scripts/enrich_all_regions_listings.py --dry-run                # 전체 지역, dry-run
    python scripts/enrich_all_regions_listings.py --limit-per-region 20    # 실제 반영 (이어하기 자동)
    python scripts/enrich_all_regions_listings.py --max-regions 10         # 테스트용: 상위 10개 지역만
    python scripts/enrich_all_regions_listings.py --only cafe              # 카페만
    python scripts/enrich_all_regions_listings.py --reset-state            # 처음부터 다시

주의:
    지역(약 213개) x 카테고리(3) x 키워드변형(카페/식당은 5개, 숙소는 1개) 조합이 꽤 많아
    (대략 213 x (1 + 5 + 5) = 2,343건) 전체를 다 돌리면 시간이 오래 걸린다(수십 분~한두 시간
    추정, --sleep-between으로 조절 가능). --max-regions로 먼저 소규모 테스트를 권장한다.
"""
import argparse
import json
import logging
import logging.config
import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import func

from config.database import Base, engine, SessionLocal, DB_USER, DB_HOST, DB_NAME
from config.logging_config import LOGGING_CONFIG
from models.stay_listing import StayListing
from models.room_type import RoomType
from models.cafe_listing import CafeListing
from models.restaurant_listing import RestaurantListing
from scripts.enrich_listings import run as run_enrich_one_listing
from scripts.enrich_stay_rooms import run as run_enrich_stay_rooms

logging.config.dictConfig(LOGGING_CONFIG)
log = logging.getLogger(__name__)

DEFAULT_STATE_FILE = os.path.join(PROJECT_ROOT, "scripts", "_enrich_all_listings_state.json")
CATEGORIES = ("stay", "cafe", "restaurant")

# 카테고리별 키워드 변형 목록. None 하나만 있으면 "{지역}" 그대로(변형 없음), 문자열이면
# "{지역} {변형}" 형태로 검색한다. 카페/식당은 5개씩 둬서 카카오 45건/키워드 한계를 우회한다.
KEYWORD_VARIANTS: dict[str, list[str | None]] = {
    "stay": [None],  # TourAPI는 지역명 자체로 검색 — 변형 불필요
    "cafe": ["카페", "로스터리", "브런치카페", "디저트카페", "커피"],
    "restaurant": ["맛집", "한식", "중식", "일식", "고깃집"],
}


def load_done(state_file: str) -> set[str]:
    if not os.path.exists(state_file):
        return set()
    with open(state_file, "r", encoding="utf-8") as f:
        return set(json.load(f))


def save_done(state_file: str, done: set[str]) -> None:
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(sorted(done), f, ensure_ascii=False, indent=2)


def require_db_config() -> None:
    if not DB_USER or not DB_NAME:
        raise RuntimeError(
            f"DB 접속 정보가 비어있습니다 (DB_USER={DB_USER!r}, DB_HOST={DB_HOST!r}, DB_NAME={DB_NAME!r})."
        )


def list_regions_by_impact() -> list[tuple[str, int]]:
    """StayListing 건수가 많은 지역부터 내림차순으로 — enrich_all_regions_tour_api.py와 동일 기준."""
    session = SessionLocal()
    try:
        rows = (
            session.query(StayListing.region, func.count(StayListing.id))
            .filter(StayListing.region.isnot(None))
            .group_by(StayListing.region)
            .order_by(func.count(StayListing.id).desc())
            .all()
        )
        return [(region, count) for region, count in rows]
    finally:
        session.close()


def listing_counts() -> dict[str, int]:
    session = SessionLocal()
    try:
        return {
            "stay": session.query(StayListing).count(),
            "room": session.query(RoomType).count(),
            "cafe": session.query(CafeListing).count(),
            "restaurant": session.query(RestaurantListing).count(),
        }
    finally:
        session.close()


def run(only: str | None, limit_per_region: int, dry_run: bool, max_regions: int | None,
        sleep_between: float, max_consecutive_failures: int,
        state_file: str, reset_state: bool) -> None:
    require_db_config()
    Base.metadata.create_all(bind=engine, tables=[
        StayListing.__table__, RoomType.__table__, CafeListing.__table__, RestaurantListing.__table__,
    ])

    if reset_state and os.path.exists(state_file):
        os.remove(state_file)
        log.info("[이어하기 상태 초기화] %s 삭제", state_file)

    done = load_done(state_file) if not dry_run else set()
    if done:
        log.info("[이어하기] 이전에 완료한 %d개 조합은 건너뜁니다", len(done))

    regions = list_regions_by_impact()
    if max_regions:
        regions = regions[:max_regions]
    categories = (only,) if only else CATEGORIES

    tasks = []  # (region, category, keyword, task_key)
    for region, stay_count in regions:
        for cat in categories:
            for variant in KEYWORD_VARIANTS[cat]:
                task_key = f"{region}:{cat}:{variant or '_'}"
                if task_key in done:
                    continue
                keyword = f"{region} {variant}" if variant else region
                tasks.append((region, cat, keyword, task_key))

    log.info("[대상] %d개 조합 (지역 %d개, 이어하기 제외 후)", len(tasks), len(regions))

    before = listing_counts()
    processed = 0
    failed = 0
    consecutive_failures = 0

    for i, (region, cat, keyword, task_key) in enumerate(tasks, start=1):
        log.info("[%d/%d] region=%s category=%s keyword=%s", i, len(tasks), region, cat, keyword)
        try:
            if cat == "stay":
                run_enrich_stay_rooms(keyword=keyword, region=region, limit=limit_per_region, dry_run=dry_run)
            else:
                run_enrich_one_listing(target=cat, keyword=keyword, region=region, limit=limit_per_region,
                                        category_override=None, dry_run=dry_run)
            consecutive_failures = 0
            processed += 1
            if not dry_run:
                done.add(task_key)
                save_done(state_file, done)
        except Exception:
            failed += 1
            consecutive_failures += 1
            log.exception("  [실패] region=%s category=%s keyword=%s (연속 실패 %d회)",
                           region, cat, keyword, consecutive_failures)
            if consecutive_failures >= max_consecutive_failures:
                log.error(
                    "[중단] 연속 실패 %d회 - API 한도 초과 등으로 추정, 여기서 멈춥니다. "
                    "(처리 완료 %d건은 %s에 기록됨 / 나중에 다시 실행하면 이어서 처리됨)",
                    consecutive_failures, processed, state_file,
                )
                break
        time.sleep(sleep_between)

    after = listing_counts()
    log.info(
        "[전체 요약] 시도 %d건 / 성공 %d건 / 실패 %d건 / "
        "StayListing %d->%d / RoomType %d->%d / CafeListing %d->%d / RestaurantListing %d->%d / 누적 완료 %d건",
        processed + failed, processed, failed,
        before["stay"], after["stay"], before["room"], after["room"],
        before["cafe"], after["cafe"], before["restaurant"], after["restaurant"], len(done),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=list(CATEGORIES), default=None,
                         help="stay/cafe/restaurant 중 하나만 (기본: 셋 다)")
    parser.add_argument("--limit-per-region", type=int, default=15, help="조합당 후보 최대 개수 (기본 15)")
    parser.add_argument("--dry-run", action="store_true", help="DB에 쓰지 않고 로그로만 확인")
    parser.add_argument("--max-regions", type=int, default=None, help="테스트용: 상위 N개 지역만 처리")
    parser.add_argument("--sleep-between", type=float, default=0.5, help="조합 사이 대기 시간(초), 기본 0.5")
    parser.add_argument("--max-consecutive-failures", type=int, default=5,
                         help="연속 실패 시 중단 기준 횟수 (기본 5)")
    parser.add_argument("--state-file", default=DEFAULT_STATE_FILE, help="이어하기 상태 파일 경로")
    parser.add_argument("--reset-state", action="store_true", help="이어하기 상태를 지우고 처음부터")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        run(args.only, args.limit_per_region, args.dry_run, args.max_regions,
            args.sleep_between, args.max_consecutive_failures,
            args.state_file, args.reset_state)
    except Exception:
        log.exception("[전지역 리스팅 보강 실패]")
        raise
