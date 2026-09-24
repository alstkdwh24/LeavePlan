"""
프론트엔드(MainPage.tsx)가 실제로 보여주는 5개 지역(강릉/제주/경주/부산/동해)에 대해,
숙소+방(TourAPI) / 식당(카카오+네이버) / 카페(카카오+네이버)를 한 번의 명령으로 순회 실행한다.

enrich_stay_rooms.py, enrich_listings.py를 지역마다 하나씩 손으로 호출하는 대신 이 스크립트
하나로 15콜(5지역 x 3카테고리)을 순서대로 처리한다.

사용법:
    python scripts/enrich_curated_regions.py --dry-run          # 전체, DB에 안 쓰고 로그만 확인
    python scripts/enrich_curated_regions.py                    # 실제 반영 (이어하기 자동)
    python scripts/enrich_curated_regions.py --only stay        # 카테고리 하나만
    python scripts/enrich_curated_regions.py --regions 강릉,제주  # 지역 일부만
    python scripts/enrich_curated_regions.py --reset-state      # 처음부터 다시

전제:
    TOUR_API_KEY(.env)와 KAKAO_REST_API_KEY/NAVER_CLIENT_ID/NAVER_CLIENT_SECRET(.env, PyCharm
    Run Configuration 등)이 실행 환경에 채워져 있어야 함. 네이버는 실패해도 enrich_listings.py가
    자동으로 건너뛰고 계속 진행한다(교차검증은 참고용이라 필수 아님).

이어하기:
    (지역, 카테고리) 조합 단위로 --state-file(기본: scripts/_enrich_curated_state.json)에 완료
    기록을 남긴다. 중간에 API 한도 초과 등으로 멈춰도 다시 실행하면 이어서 처리된다.
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

from config.logging_config import LOGGING_CONFIG
from scripts.enrich_stay_rooms import run as run_stay_rooms
from scripts.enrich_listings import run as run_listing

logging.config.dictConfig(LOGGING_CONFIG)
log = logging.getLogger(__name__)

DEFAULT_STATE_FILE = os.path.join(PROJECT_ROOT, "scripts", "_enrich_curated_state.json")

# 지역 라벨은 seed_listings.py의 STAY_SEEDS/CAFE_SEEDS/RESTAURANT_SEEDS와 동일하게 맞춘다
# (region 컬럼 값이 일치해야 프론트/기존 데모 데이터와 같은 그룹으로 묶인다).
REGION_PLAN = [
    # (region 라벨, stay 키워드, restaurant 키워드, cafe 키워드)
    ("강릉", "강릉 리조트", "강릉 맛집", "강릉 감성 카페"),
    ("제주", "서귀포 풀빌라", "서귀포 맛집", "서귀포 카페"),
    ("경주", "경주 한옥스테이", "경주 불국사 맛집", "경주 카페"),
    ("부산", "해운대 호텔", "해운대 맛집", "해운대 카페"),
    ("동해", "동해 펜션", "동해 맛집", "동해 감성 카페"),
    ("삼척", "삼척 펜션", "삼척 맛집", "삼척 카페"),
    ("여수", "여수 오션뷰 숙소", "여수 밤바다 맛집", "여수 카페"),
    ("서울", "서울 호텔", "서울 맛집", "서울 감성 카페"),
]

CATEGORIES = ("stay", "restaurant", "cafe")


def load_done(state_file: str) -> set[str]:
    if not os.path.exists(state_file):
        return set()
    with open(state_file, "r", encoding="utf-8") as f:
        return set(json.load(f))


def save_done(state_file: str, done: set[str]) -> None:
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(sorted(done), f, ensure_ascii=False, indent=2)


def run(only: str | None, regions_filter: list[str] | None, limit: int, dry_run: bool,
        sleep_between: float, max_consecutive_failures: int,
        state_file: str, reset_state: bool) -> None:
    if reset_state and os.path.exists(state_file):
        os.remove(state_file)
        log.info("[이어하기 상태 초기화] %s 삭제", state_file)

    done = load_done(state_file) if not dry_run else set()
    if done:
        log.info("[이어하기] 이전에 완료한 %d개 조합은 건너뜁니다", len(done))

    plan = REGION_PLAN
    if regions_filter:
        plan = [row for row in plan if row[0] in regions_filter]
    categories = (only,) if only else CATEGORIES

    tasks = []  # (region, category, keyword)
    for region, stay_kw, restaurant_kw, cafe_kw in plan:
        keyword_by_cat = {"stay": stay_kw, "restaurant": restaurant_kw, "cafe": cafe_kw}
        for cat in categories:
            task_key = f"{region}:{cat}"
            if task_key in done:
                continue
            tasks.append((region, cat, keyword_by_cat[cat]))

    log.info("[대상] %d개 조합 (지역 %d개 x 카테고리 %d개, 이어하기 제외 후)",
              len(tasks), len(plan), len(categories))

    processed = 0
    failed = 0
    consecutive_failures = 0

    for i, (region, cat, keyword) in enumerate(tasks, start=1):
        log.info("[%d/%d] region=%s category=%s keyword=%s", i, len(tasks), region, cat, keyword)
        try:
            if cat == "stay":
                run_stay_rooms(keyword=keyword, region=region, limit=limit, dry_run=dry_run)
            else:
                run_listing(target=cat, keyword=keyword, region=region, limit=limit,
                            category_override=None, dry_run=dry_run)
            consecutive_failures = 0
            processed += 1
            if not dry_run:
                done.add(f"{region}:{cat}")
                save_done(state_file, done)
        except Exception:
            failed += 1
            consecutive_failures += 1
            log.exception("  [실패] region=%s category=%s (연속 실패 %d회)", region, cat, consecutive_failures)
            if consecutive_failures >= max_consecutive_failures:
                log.error(
                    "[중단] 연속 실패 %d회 - API 한도 초과 등으로 추정, 여기서 멈춥니다. "
                    "(처리 완료 %d건은 %s에 기록됨 / 나중에 다시 실행하면 이어서 처리됨)",
                    consecutive_failures, processed, state_file,
                )
                break
        time.sleep(sleep_between)

    log.info("[전체 요약] 시도 %d건 / 성공 %d건 / 실패 %d건 / 누적 완료 %d건",
              processed + failed, processed, failed, len(done))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=list(CATEGORIES), default=None,
                         help="카테고리 하나만 처리 (기본: stay/restaurant/cafe 전부)")
    parser.add_argument("--regions", default=None,
                         help='지역 일부만 콤마로 지정, 예: "강릉,제주" (기본: 5개 전부)')
    parser.add_argument("--limit", type=int, default=10, help="지역당 후보 최대 개수 (기본 10)")
    parser.add_argument("--dry-run", action="store_true", help="DB에 쓰지 않고 로그로만 확인")
    parser.add_argument("--sleep-between", type=float, default=0.5, help="조합 사이 대기 시간(초), 기본 0.5")
    parser.add_argument("--max-consecutive-failures", type=int, default=3,
                         help="연속 실패 시 중단 기준 횟수 (기본 3)")
    parser.add_argument("--state-file", default=DEFAULT_STATE_FILE,
                         help="이어하기 상태 파일 경로")
    parser.add_argument("--reset-state", action="store_true", help="이어하기 상태를 지우고 처음부터")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    regions_filter = [r.strip() for r in args.regions.split(",")] if args.regions else None
    try:
        run(args.only, regions_filter, args.limit, args.dry_run,
            args.sleep_between, args.max_consecutive_failures,
            args.state_file, args.reset_state)
    except Exception:
        log.exception("[큐레이션 지역 전체 보강 실패]")
        raise
