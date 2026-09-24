"""
TourAPI의 지역코드 기반 전체목록조회(areaBasedList2)로 전국 시군구를 순회하며 StayListing/RoomType을
보강하는 스크립트. enrich_all_regions_tour_api.py(searchKeyword2, 업체명에 지역명이 들어간 곳만
잡힘)보다 훨씬 넓게 잡힌다 — 지역코드로 그 지역에 등록된 숙박업소를 이름 상관없이 전부 가져오기
때문. 실제로 강릉시 하나만 테스트해도 이름검색 15건 vs 지역코드 156건으로 10배 차이가 났다.

동작:
    1) TourAPI areaCode2로 광역(17개) -> 시군구 코드 목록을 전부 가져온다.
    2) 시군구마다 areaBasedList2(contentTypeId=32)로 숙박업소 후보를 가져온다.
    3) 후보마다 detailInfo2로 객실 정보를 가져와 StayListing/RoomType에 반영한다
       (enrich_stay_rooms.py의 process_candidates 재사용 — 신규면 추가, 있으면 방 이름 기준으로
       업데이트).

지역명 매핑:
    TourAPI의 시군구명(예: "강릉시", "종로구")을 DB에 저장할 때는 import_stay_listings_from_csv.py와
    같은 규칙으로 "시" 접미사만 떼고("강릉시"->"강릉") "군"/"구"는 그대로 둔다("종로구"->"종로구").
    세종특별자치시처럼 하위 시군구가 없는 광역은 그 자체를 하나의 지역으로 취급한다.

트래픽 한도 대비 (enrich_all_regions_tour_api.py와 동일한 방식):
    - 완료한 (광역코드, 시군구코드)는 --state-file에 기록해서 다음 실행 때 건너뜀
    - 연속 실패(한도 초과 추정) --max-consecutive-failures번 나면 자동 중단
    - --reset-state로 처음부터 다시

사용법:
    python scripts/enrich_by_area_tour_api.py --dry-run --max-areas 5   # 테스트
    python scripts/enrich_by_area_tour_api.py --limit-per-area 50       # 실제 반영
    python scripts/enrich_by_area_tour_api.py --reset-state             # 처음부터 다시
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

from config.database import Base, engine, SessionLocal, DB_USER, DB_HOST, DB_NAME
from config.logging_config import LOGGING_CONFIG
from models.stay_listing import StayListing
from models.room_type import RoomType
from scripts.enrich_stay_rooms import (
    require_config, process_candidates, search_area,
    list_province_codes, list_sigungu_codes,
)

logging.config.dictConfig(LOGGING_CONFIG)
log = logging.getLogger(__name__)

DEFAULT_STATE_FILE = os.path.join(PROJECT_ROOT, "scripts", "_enrich_area_state.json")


def load_done(state_file: str) -> set[str]:
    if not os.path.exists(state_file):
        return set()
    with open(state_file, "r", encoding="utf-8") as f:
        return set(json.load(f))


def save_done(state_file: str, done: set[str]) -> None:
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(sorted(done), f, ensure_ascii=False, indent=2)


def to_region_label(sigungu_name: str) -> str:
    """TourAPI 시군구명을 DB region 라벨 규칙으로 변환 ('시' 접미사만 제거)."""
    return sigungu_name[:-1] if sigungu_name.endswith("시") else sigungu_name


def list_area_units() -> list[tuple[str, str, str, str]]:
    """(areaCode, sigunguCode, sigunguName, regionLabel) 튜플 전체 목록.
    하위 시군구가 없는 광역(세종 등)은 그 광역 자체를 sigunguCode=''(전체) 단위로 넣는다."""
    units: list[tuple[str, str, str, str]] = []
    provinces = list_province_codes()
    for prov in provinces:
        area_code = prov["code"]
        sigungus = list_sigungu_codes(area_code)
        if not sigungus:
            units.append((area_code, "", prov["name"], to_region_label(prov["name"])))
            continue
        for sg in sigungus:
            units.append((area_code, sg["code"], sg["name"], to_region_label(sg["name"])))
    return units


def require_db_config() -> None:
    if not DB_USER or not DB_NAME:
        raise RuntimeError(
            f"DB 접속 정보가 비어있습니다 (DB_USER={DB_USER!r}, DB_HOST={DB_HOST!r}, DB_NAME={DB_NAME!r}). "
            ".env 또는 Run Configuration에 환경변수를 채워주세요."
        )


def room_count() -> int:
    session = SessionLocal()
    try:
        return session.query(RoomType).count()
    finally:
        session.close()


def run(limit_per_area: int, dry_run: bool, max_areas: int | None,
        sleep_between: float, max_consecutive_failures: int,
        state_file: str, reset_state: bool) -> None:
    require_config()
    require_db_config()
    Base.metadata.create_all(bind=engine, tables=[StayListing.__table__, RoomType.__table__])

    if reset_state and os.path.exists(state_file):
        os.remove(state_file)
        log.info("[이어하기 상태 초기화] %s 삭제", state_file)

    done = load_done(state_file) if not dry_run else set()
    if done:
        log.info("[이어하기] 이전에 완료한 %d개 시군구는 건너뜁니다", len(done))

    log.info("[지역코드 조회 중] areaCode2로 전국 시군구 목록을 가져옵니다...")
    units = list_area_units()
    log.info("[전국 시군구] %d개", len(units))

    units = [u for u in units if f"{u[0]}:{u[1]}" not in done]
    if max_areas:
        units = units[:max_areas]
    log.info("[대상] %d개 시군구 (이어하기 제외 후)", len(units))

    before = room_count()
    consecutive_failures = 0
    processed = 0
    failed = 0
    total_candidates = 0
    total_new_stay = 0
    total_new_room = 0
    total_updated_room = 0

    session = SessionLocal()
    try:
        for i, (area_code, sigungu_code, sigungu_name, region_label) in enumerate(units, start=1):
            key = f"{area_code}:{sigungu_code}"
            log.info("[%d/%d] %s (region=%s)", i, len(units), sigungu_name, region_label)
            try:
                candidates, total_count = search_area(area_code, sigungu_code, limit_per_area)
                log.info("  [후보 %d건 수집 / 전체 %d건 중]", len(candidates), total_count)
                total_candidates += len(candidates)

                new_stay, new_room, updated_room = process_candidates(
                    session, candidates, region_label, dry_run
                )
                total_new_stay += new_stay
                total_new_room += new_room
                total_updated_room += updated_room

                if not dry_run:
                    session.commit()

                consecutive_failures = 0
                processed += 1
                if not dry_run:
                    done.add(key)
                    save_done(state_file, done)
            except Exception:
                session.rollback()
                failed += 1
                consecutive_failures += 1
                log.exception("  [실패] %s (연속 실패 %d회)", sigungu_name, consecutive_failures)
                if consecutive_failures >= max_consecutive_failures:
                    log.error(
                        "[중단] 연속 실패 %d회 - TourAPI 트래픽 한도 초과로 추정, 여기서 멈춥니다. "
                        "(처리 완료 %d개는 %s에 기록됨 / 나중에 다시 실행하면 이어서 처리됨)",
                        consecutive_failures, processed, state_file,
                    )
                    break
            time.sleep(sleep_between)
    finally:
        session.close()

    after = room_count()
    log.info(
        "[전체 요약] 처리 시도 %d개 시군구 / 실패 %d개 / 후보 %d건 / "
        "신규 숙소 %d건 / 신규 방 %d건 / 업데이트된 방 %d건 / RoomType %d -> %d / 누적 완료 %d개",
        processed + failed, failed, total_candidates,
        total_new_stay, total_new_room, total_updated_room,
        before, after, len(done),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit-per-area", type=int, default=50, help="시군구당 후보 최대 개수 (기본 50)")
    parser.add_argument("--dry-run", action="store_true", help="DB에 쓰지 않고 로그로만 확인")
    parser.add_argument("--max-areas", type=int, default=None, help="테스트용: 앞에서 N개 시군구만 처리")
    parser.add_argument("--sleep-between", type=float, default=0.5, help="시군구 사이 대기 시간(초)")
    parser.add_argument("--max-consecutive-failures", type=int, default=3,
                         help="연속 실패 시 중단 기준 (기본 3)")
    parser.add_argument("--state-file", default=DEFAULT_STATE_FILE,
                         help="이어하기 상태 파일 (기본: scripts/_enrich_area_state.json)")
    parser.add_argument("--reset-state", action="store_true", help="이어하기 상태를 지우고 처음부터")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        run(args.limit_per_area, args.dry_run, args.max_areas,
            args.sleep_between, args.max_consecutive_failures,
            args.state_file, args.reset_state)
    except Exception:
        log.exception("[지역코드 기반 전국 보강 실패]")
        raise
