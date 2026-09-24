"""
StayListing에 실제 존재하는 모든 region(시군구 단위)을 순회하며 enrich_stay_rooms.py(TourAPI)를
돌려서, 가능한 곳은 방 이름/가격까지 채우는 스크립트.

import_stay_listings_from_csv.py로 전국 데이터를 이미 넣었지만 그건 방 이름/가격이 없는
"양실"/"한실" 개수뿐이다. 이 스크립트는 지역명을 검색어로 TourAPI를 돌려서, 실제로 이름이 매칭되는
숙소에 한해 진짜 방 이름/가격을 추가로 붙인다 (기존 양실/한실은 지우지 않고 같이 남겨둔다 —
enrich_stay_rooms.py가 이미 있는 방 이름과 겹치지만 않으면 추가하는 방식이라서).

트래픽 한도 대비:
    data.go.kr 무료 키는 순간 트래픽 제한(HTTP 429, enrich_stay_rooms.py가 자동 재시도함)과
    별개로 일일 호출 한도가 있을 수 있다. 지역 수가 많아 호출이 누적되므로:
    - StayListing 건수가 많은 지역부터 우선 처리 (한도 다 쓰기 전에 임팩트 큰 지역부터)
    - 연속 실패(예: 한도 초과로 추정)가 --max-consecutive-failures 번 나면 자동 중단
    - 지역 사이 --sleep-between 초 대기
    - 처리 완료한 지역은 --state-file(기본: scripts/_enrich_regions_state.json)에 기록해두고,
      다음 실행 때 자동으로 건너뛴다 — 한도 초과로 중단됐다가 나중에 다시 실행해도 이어서 처리됨.
      처음부터 다시 하고 싶으면 --reset-state를 붙인다.

사용법:
    python scripts/enrich_all_regions_tour_api.py --dry-run                 # 전체 지역, dry-run
    python scripts/enrich_all_regions_tour_api.py --limit-per-region 30     # 실제 반영 (이어하기 자동)
    python scripts/enrich_all_regions_tour_api.py --max-regions 10         # 테스트용: 상위 10개 지역만
    python scripts/enrich_all_regions_tour_api.py --reset-state            # 처음부터 다시
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
from scripts.enrich_stay_rooms import run as run_enrich_one_region

logging.config.dictConfig(LOGGING_CONFIG)
log = logging.getLogger(__name__)

DEFAULT_STATE_FILE = os.path.join(PROJECT_ROOT, "scripts", "_enrich_regions_state.json")


def load_done_regions(state_file: str) -> set[str]:
    if not os.path.exists(state_file):
        return set()
    with open(state_file, "r", encoding="utf-8") as f:
        return set(json.load(f))


def save_done_regions(state_file: str, done: set[str]) -> None:
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(sorted(done), f, ensure_ascii=False, indent=2)


def require_db_config() -> None:
    if not DB_USER or not DB_NAME:
        raise RuntimeError(
            f"DB 접속 정보가 비어있습니다 (DB_USER={DB_USER!r}, DB_HOST={DB_HOST!r}, DB_NAME={DB_NAME!r}). "
            ".env 또는 Run Configuration에 환경변수를 채워주세요."
        )


def list_regions_by_impact() -> list[tuple[str, int]]:
    """StayListing 건수가 많은 지역부터 내림차순으로."""
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


def room_count() -> int:
    session = SessionLocal()
    try:
        return session.query(RoomType).count()
    finally:
        session.close()


def run(limit_per_region: int, dry_run: bool, max_regions: int | None,
        sleep_between: float, max_consecutive_failures: int,
        state_file: str, reset_state: bool) -> None:
    require_db_config()
    Base.metadata.create_all(bind=engine, tables=[StayListing.__table__, RoomType.__table__])

    if reset_state and os.path.exists(state_file):
        os.remove(state_file)
        log.info("[이어하기 상태 초기화] %s 삭제", state_file)

    done_regions = load_done_regions(state_file) if not dry_run else set()
    if done_regions:
        log.info("[이어하기] 이전에 완료한 %d개 지역은 건너뜁니다", len(done_regions))

    regions = list_regions_by_impact()
    regions = [(r, c) for r, c in regions if r not in done_regions]
    if max_regions:
        regions = regions[:max_regions]

    log.info("[대상 지역] %d개 (건수 많은 순, 이어하기 제외 후)", len(regions))

    before = room_count()
    consecutive_failures = 0
    processed = 0
    failed = 0

    for i, (region, stay_count) in enumerate(regions, start=1):
        log.info("[%d/%d] region=%s (StayListing %d건)", i, len(regions), region, stay_count)
        try:
            run_enrich_one_region(keyword=region, region=region, limit=limit_per_region, dry_run=dry_run)
            consecutive_failures = 0
            processed += 1
            if not dry_run:
                done_regions.add(region)
                save_done_regions(state_file, done_regions)
        except Exception:
            failed += 1
            consecutive_failures += 1
            log.exception("  [실패] region=%s (연속 실패 %d회)", region, consecutive_failures)
            if consecutive_failures >= max_consecutive_failures:
                log.error(
                    "[중단] 연속 실패 %d회 - TourAPI 트래픽 한도 초과로 추정, 여기서 멈춥니다. "
                    "(처리 완료 %d개 지역은 %s에 기록됨 / 나중에 다시 실행하면 이어서 처리됨)",
                    consecutive_failures, processed, state_file,
                )
                break
        time.sleep(sleep_between)

    after = room_count()
    log.info(
        "[전체 요약] 처리 시도 %d개 지역 / 실패 %d개 / RoomType %d -> %d (신규 %d건) / "
        "누적 완료 지역 %d개",
        processed + failed, failed, before, after, after - before, len(done_regions),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit-per-region", type=int, default=50, help="지역당 TourAPI 후보 최대 개수 (기본 50)")
    parser.add_argument("--dry-run", action="store_true", help="DB에 쓰지 않고 로그로만 확인")
    parser.add_argument("--max-regions", type=int, default=None, help="테스트용: 상위 N개 지역만 처리")
    parser.add_argument("--sleep-between", type=float, default=0.5, help="지역 사이 대기 시간(초), 기본 0.5")
    parser.add_argument("--max-consecutive-failures", type=int, default=3,
                         help="연속 실패 시 중단하는 기준 횟수 (기본 3, 트래픽 한도 초과 대비)")
    parser.add_argument("--state-file", default=DEFAULT_STATE_FILE,
                         help="이어하기 상태 파일 경로 (기본: scripts/_enrich_regions_state.json)")
    parser.add_argument("--reset-state", action="store_true", help="이어하기 상태를 지우고 처음부터 다시 시작")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        run(args.limit_per_region, args.dry_run, args.max_regions,
            args.sleep_between, args.max_consecutive_failures,
            args.state_file, args.reset_state)
    except Exception:
        log.exception("[전지역 TourAPI 보강 실패]")
        raise
