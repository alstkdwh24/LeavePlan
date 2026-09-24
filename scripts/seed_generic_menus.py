"""
CafeMenuItem/RestaurantMenuItem이 하나도 없는 카페/식당(대부분 enrich_listings.py로 채운
실제 상호명들 — 무료 API로는 진짜 메뉴를 구할 방법이 없다)에, 카테고리별로 흔히 있을 법한
"예시 메뉴"를 채워 넣는다.

⚠️ 주의: 여기서 넣는 메뉴/가격은 그 가게의 실제 메뉴가 아니라 카테고리 평균 수준의 가상
데이터다. 실제 존재하는 상호명에 가상의 구체적 사실(메뉴/가격)을 붙이는 것이므로, 나중에
진짜 정보로 오인되지 않도록 description에 "예시 메뉴 — 실제와 다를 수 있습니다"를 항상
남긴다. is_signature는 실제로 확인된 바 없으므로 전부 False로 둔다 — "이 가게의 대표
메뉴"라는 더 구체적인 허위 주장은 하지 않기 위해서다.

사용법:
    python scripts/seed_generic_menus.py --dry-run     # 몇 곳에 몇 개 들어갈지 미리 확인
    python scripts/seed_generic_menus.py               # 실제 반영
    python scripts/seed_generic_menus.py --only cafe    # 카페만
"""
import argparse
import logging
import logging.config
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import text

from config.database import Base, engine, SessionLocal, DB_USER, DB_HOST, DB_NAME
from config.logging_config import LOGGING_CONFIG
from models.cafe_listing import CafeListing
from models.cafe_menu_item import CafeMenuItem
from models.restaurant_listing import RestaurantListing
from models.restaurant_menu_item import RestaurantMenuItem

logging.config.dictConfig(LOGGING_CONFIG)
log = logging.getLogger(__name__)

PLACEHOLDER_NOTE = "예시 메뉴 — 실제 메뉴와 다를 수 있습니다(정확한 정보는 매장에 확인해주세요)."

# 카페는 서브 카테고리(디저트카페/커피전문점 등)와 무관하게 대체로 겹치는 기본 라인업이라
# 하나의 공통 템플릿만 쓴다.
CAFE_TEMPLATE = [
    dict(menu_name="아메리카노", category="커피", price=4500),
    dict(menu_name="카페라떼", category="커피", price=5000),
    dict(menu_name="바닐라라떼", category="커피", price=5500),
    dict(menu_name="자몽에이드", category="음료", price=6000),
    dict(menu_name="치즈케이크", category="디저트", price=7000),
]

# 식당 category(카카오 카테고리 마지막 조각, 예: "한식"/"중식")의 키워드로 매칭.
# 못 찾으면 DEFAULT_RESTAURANT_TEMPLATE으로 대체.
RESTAURANT_TEMPLATES: dict[str, list[dict]] = {
    "한식": [
        dict(menu_name="된장찌개 정식", category="메인", price=9000),
        dict(menu_name="김치찌개 정식", category="메인", price=9000),
        dict(menu_name="공기밥 추가", category="사이드", price=1000),
    ],
    "중식": [
        dict(menu_name="짜장면", category="메인", price=7000),
        dict(menu_name="짬뽕", category="메인", price=8000),
        dict(menu_name="탕수육(소)", category="사이드", price=18000),
    ],
    "일식": [
        dict(menu_name="초밥 세트", category="메인", price=15000),
        dict(menu_name="우동", category="메인", price=9000),
        dict(menu_name="가라아게", category="사이드", price=8000),
    ],
    "양식": [
        dict(menu_name="토마토 파스타", category="메인", price=14000),
        dict(menu_name="크림 파스타", category="메인", price=15000),
        dict(menu_name="리조또", category="메인", price=13000),
    ],
    "고기": [
        dict(menu_name="삼겹살(1인분)", category="메인", price=15000),
        dict(menu_name="된장찌개", category="사이드", price=5000),
    ],
    "육류": [
        dict(menu_name="삼겹살(1인분)", category="메인", price=15000),
        dict(menu_name="된장찌개", category="사이드", price=5000),
    ],
    "분식": [
        dict(menu_name="떡볶이", category="메인", price=5000),
        dict(menu_name="순대", category="사이드", price=5000),
        dict(menu_name="튀김 모둠", category="사이드", price=6000),
    ],
    "카페": CAFE_TEMPLATE,
    "커피": CAFE_TEMPLATE,
}

DEFAULT_RESTAURANT_TEMPLATE = [
    dict(menu_name="오늘의 메뉴", category="메인", price=12000),
    dict(menu_name="사이드 메뉴", category="사이드", price=5000),
]


def pick_restaurant_template(category: str | None) -> list[dict]:
    if category:
        for keyword, template in RESTAURANT_TEMPLATES.items():
            if keyword in category:
                return template
    return DEFAULT_RESTAURANT_TEMPLATE


def require_db_config() -> None:
    if not DB_USER or not DB_NAME:
        raise RuntimeError(
            f"DB 접속 정보가 비어있습니다 (DB_USER={DB_USER!r}, DB_HOST={DB_HOST!r}, DB_NAME={DB_NAME!r})."
        )


def seed_cafe_menus(session, dry_run: bool) -> tuple[int, int]:
    """메뉴가 하나도 없는 CafeListing에 공통 템플릿을 채운다. 반환값: (대상 가게 수, 삽입한 메뉴 행 수)."""
    all_cafes = session.query(CafeListing).all()
    existing_cafe_ids = {row[0] for row in session.query(CafeMenuItem.cafe_id).distinct().all()}
    targets = [c for c in all_cafes if c.id not in existing_cafe_ids]

    log.info("[cafe] 전체 %d곳 중 메뉴 없는 곳 %d곳", len(all_cafes), len(targets))

    inserted = 0
    for cafe in targets:
        rows = [
            dict(cafe_id=cafe.id, menu_name=item["menu_name"], category=item["category"],
                 price=item["price"], is_signature=False, description=PLACEHOLDER_NOTE,
                 is_placeholder=True)
            for item in CAFE_TEMPLATE
        ]
        if dry_run:
            log.info("  [--dry-run] %s -> %s", cafe.cafe_name, [r["menu_name"] for r in rows])
        else:
            session.bulk_save_objects([CafeMenuItem(**r) for r in rows])
        inserted += len(rows)

    return len(targets), inserted


def seed_restaurant_menus(session, dry_run: bool) -> tuple[int, int]:
    all_restaurants = session.query(RestaurantListing).all()
    existing_ids = {row[0] for row in session.query(RestaurantMenuItem.restaurant_id).distinct().all()}
    targets = [r for r in all_restaurants if r.id not in existing_ids]

    log.info("[restaurant] 전체 %d곳 중 메뉴 없는 곳 %d곳", len(all_restaurants), len(targets))

    inserted = 0
    for restaurant in targets:
        template = pick_restaurant_template(restaurant.category)
        rows = [
            dict(restaurant_id=restaurant.id, menu_name=item["menu_name"], category=item["category"],
                 price=item["price"], is_signature=False, description=PLACEHOLDER_NOTE,
                 is_placeholder=True)
            for item in template
        ]
        if dry_run:
            log.info("  [--dry-run] %s (%s) -> %s", restaurant.restaurant_name, restaurant.category,
                      [r["menu_name"] for r in rows])
        else:
            session.bulk_save_objects([RestaurantMenuItem(**r) for r in rows])
        inserted += len(rows)

    return len(targets), inserted


def run(only: str | None, dry_run: bool) -> None:
    require_db_config()
    Base.metadata.create_all(bind=engine, tables=[CafeMenuItem.__table__, RestaurantMenuItem.__table__])

    session = SessionLocal()
    try:
        if only in (None, "cafe"):
            cafe_targets, cafe_rows = seed_cafe_menus(session, dry_run)
        else:
            cafe_targets = cafe_rows = 0

        if only in (None, "restaurant"):
            rest_targets, rest_rows = seed_restaurant_menus(session, dry_run)
        else:
            rest_targets = rest_rows = 0

        if dry_run:
            log.info("[--dry-run] DB에 쓰지 않고 종료합니다. (카페 %d곳/%d행, 식당 %d곳/%d행 예정)",
                      cafe_targets, cafe_rows, rest_targets, rest_rows)
            return

        session.commit()
    finally:
        session.close()

    with engine.connect() as conn:
        cafe_menu_count = conn.execute(text(f"SELECT COUNT(*) FROM {CafeMenuItem.__table__.name}")).scalar()
        rest_menu_count = conn.execute(text(f"SELECT COUNT(*) FROM {RestaurantMenuItem.__table__.name}")).scalar()
        log.info("[검증] CafeMenuItem 행 수 = %s, RestaurantMenuItem 행 수 = %s",
                  f"{cafe_menu_count:,}", f"{rest_menu_count:,}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=["cafe", "restaurant"], default=None,
                         help="카페 또는 식당 하나만 (기본: 둘 다)")
    parser.add_argument("--dry-run", action="store_true", help="DB에 쓰지 않고 로그로만 확인")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        run(args.only, args.dry_run)
    except Exception:
        log.exception("[예시 메뉴 시드 실패]")
        raise
