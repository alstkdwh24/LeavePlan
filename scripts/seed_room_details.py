"""
RoomType(숙소 방 종류) / RestaurantMenuItem·CafeMenuItem(식당·카페 메뉴)을
'비용 없이' 채우는 시드 스크립트. seed_listings.py와 같은 방식 — 외부 API를 호출하지 않고
이 앱이 원래부터 쓰던 데모 콘텐츠 성격의 가상 데이터를 채워 넣는다.

전제 조건:
    seed_listings.py를 먼저 실행해서 StayListing/RestaurantListing/CafeListing에
    이름이 존재해야 한다 (이 스크립트는 이름+지역으로 부모 행을 찾아 FK를 채운다).

사용법:
    python scripts/seed_room_details.py                    # room/restaurant-menu/cafe-menu 전부
    python scripts/seed_room_details.py --target room       # 하나만
    python scripts/seed_room_details.py --dry-run           # DB에 쓰지 않고 내용만 확인

재실행 안전성:
    같은 (부모 id, 이름) 조합이 이미 있으면 건너뛴다 — 여러 번 실행해도 중복 적재되지 않는다.
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
from models.stay_listing import StayListing
from models.restaurant_listing import RestaurantListing
from models.cafe_listing import CafeListing
from models.room_type import RoomType
from models.restaurant_menu_item import RestaurantMenuItem
from models.cafe_menu_item import CafeMenuItem

logging.config.dictConfig(LOGGING_CONFIG)
log = logging.getLogger(__name__)

# ── 시드 데이터 ──────────────────────────────────────────────────────────
# 키는 seed_listings.py의 STAY_SEEDS/CAFE_SEEDS/RESTAURANT_SEEDS와 동일한 (이름, 지역)이어야
# 부모 행을 찾아 FK를 채울 수 있다.

ROOM_TYPE_SEEDS = {
    ("오션뷰 풀빌라 안목", "강릉"): [
        dict(room_name="스탠다드 오션뷰룸", bed_type="더블베드 1개", base_capacity=2, max_capacity=3,
             price=248000, stock=2, description="바다 전망 스탠다드룸. 기본 조식 포함."),
        dict(room_name="프라이빗 풀빌라룸", bed_type="킹베드 1개", base_capacity=2, max_capacity=4,
             price=328000, stock=1, description="개별 프라이빗 풀이 딸린 최상위 룸."),
    ],
    ("오션뷰 룸텔과 한옥", "강릉"): [
        dict(room_name="한옥 온돌룸", bed_type="온돌 이불", base_capacity=2, max_capacity=4,
             price=248000, stock=3, description="전통 한옥 온돌 구조의 아늑한 방."),
        dict(room_name="룸텔 트윈룸", bed_type="트윈베드 2개", base_capacity=2, max_capacity=2,
             price=198000, stock=4, description="경포 해변 도보권 룸텔 트윈룸."),
    ],
    ("해솔 감성 독채 스테이", "제주"): [
        dict(room_name="독채 전체", bed_type="퀸베드 1개 + 소파베드 1개", base_capacity=2, max_capacity=4,
             price=175000, stock=1, description="건물 전체를 통째로 쓰는 독채형 스테이."),
    ],
    ("한옥 프리미엄 룸진", "경주"): [
        dict(room_name="프리미엄 한옥 스위트", bed_type="퀸베드 1개", base_capacity=2, max_capacity=3,
             price=232000, stock=2, description="불국사 인근 프리미엄 한옥 스위트룸."),
    ],
    ("제주대 파란 스위트", "부산"): [
        dict(room_name="오션뷰 스위트", bed_type="킹베드 1개", base_capacity=2, max_capacity=2,
             price=289000, stock=2, description="해운대 해변 도보권 신규 오픈 스위트룸."),
    ],
}

CAFE_MENU_SEEDS = {
    ("안목해변 감성 카페", "강릉"): [
        dict(menu_name="시그니처 오션뷰 라떼", category="음료", price=7500, is_signature=True,
             description="이 카페의 대표 메뉴. 통유리 오션뷰와 함께 즐기는 라떼."),
        dict(menu_name="아메리카노", category="커피", price=5000, is_signature=False, description="기본 아메리카노."),
        dict(menu_name="치즈 케이크", category="디저트", price=8000, is_signature=False, description="수제 치즈 케이크."),
    ],
    ("독채처럼 감성 카페", "동해"): [
        dict(menu_name="독채 브런치 플레이트", category="브런치", price=16000, is_signature=True,
             description="AI가 추천하는 동해시 감성 카페의 대표 브런치."),
        dict(menu_name="핸드드립 커피", category="커피", price=6500, is_signature=False, description="원두를 직접 내린 핸드드립."),
    ],
}

RESTAURANT_MENU_SEEDS = {
    ("강릉 회센터 물회", "강릉"): [
        dict(menu_name="강릉식 물회", category="메인", price=18000, is_signature=True,
             description="현지인이 추천하는 대표 물회 메뉴."),
        dict(menu_name="회덮밥", category="메인", price=16000, is_signature=False, description="신선한 회를 올린 덮밥."),
        dict(menu_name="소주", category="음료", price=5000, is_signature=False, description="곁들이 소주."),
    ],
    ("강릉 최선의 맛집", "강릉"): [
        dict(menu_name="강릉 한정식", category="메인", price=22000, is_signature=True,
             description="AI 일정에 자주 포함되는 강릉 현지 한정식."),
        dict(menu_name="된장찌개 정식", category="메인", price=13000, is_signature=False, description="집밥 스타일 정식."),
    ],
}

TARGETS = {
    "room": {
        "parent_model": StayListing, "parent_name_attr": "stayName", "parent_region_attr": "region",
        "child_model": RoomType, "fk_attr": "stay_id", "name_attr": "room_name", "seeds": ROOM_TYPE_SEEDS,
    },
    "cafe-menu": {
        "parent_model": CafeListing, "parent_name_attr": "cafe_name", "parent_region_attr": "region",
        "child_model": CafeMenuItem, "fk_attr": "cafe_id", "name_attr": "menu_name", "seeds": CAFE_MENU_SEEDS,
    },
    "restaurant-menu": {
        "parent_model": RestaurantListing, "parent_name_attr": "restaurant_name", "parent_region_attr": "region",
        "child_model": RestaurantMenuItem, "fk_attr": "restaurant_id", "name_attr": "menu_name", "seeds": RESTAURANT_MENU_SEEDS,
    },
}


def require_db_config() -> None:
    if not DB_USER or not DB_NAME:
        raise RuntimeError(
            f"DB 접속 정보가 비어있습니다 (DB_USER={DB_USER!r}, DB_HOST={DB_HOST!r}, DB_NAME={DB_NAME!r}). "
            "Run > Edit Configurations 에서 이 스크립트 설정에도 환경변수를 추가해주세요."
        )


def seed_one(target: str, dry_run: bool) -> None:
    spec = TARGETS[target]
    parent_model = spec["parent_model"]
    child_model = spec["child_model"]
    fk_attr = spec["fk_attr"]
    name_attr = spec["name_attr"]

    Base.metadata.create_all(bind=engine, tables=[child_model.__table__])

    session = SessionLocal()
    try:
        total_seeds = sum(len(rows) for rows in spec["seeds"].values())
        to_insert = []
        missing_parents = []
        already_exists_count = 0

        for (parent_name, parent_region), rows in spec["seeds"].items():
            parent = session.query(parent_model).filter(
                getattr(parent_model, spec["parent_name_attr"]) == parent_name,
                getattr(parent_model, spec["parent_region_attr"]) == parent_region,
            ).first()
            if parent is None:
                missing_parents.append((parent_name, parent_region))
                continue

            existing = {
                getattr(row, name_attr)
                for row in session.query(child_model).filter(getattr(child_model, fk_attr) == parent.id).all()
            }
            for row in rows:
                if row[name_attr] not in existing:
                    # RoomType/CafeMenuItem/RestaurantMenuItem 전부 isPlaceholder 컬럼이 있고,
                    # 여기서 넣는 값은 가상의 상호명에 붙인 가상 데이터라 True로 표시한다.
                    to_insert.append({**row, fk_attr: parent.id, "is_placeholder": True})
                else:
                    already_exists_count += 1

        skipped = already_exists_count

        if missing_parents:
            log.warning("[%s] 부모 행을 찾지 못해 건너뜀(먼저 seed_listings.py 실행 필요): %s", target, missing_parents)

        log.info("[%s] 시드 %d건 중 신규 %d건 / 이미 존재해서 건너뜀 %d건",
                  target, total_seeds, len(to_insert), skipped)

        if dry_run:
            for row in to_insert:
                log.info("  [--dry-run] %s", row)
            return

        if to_insert:
            session.bulk_save_objects([child_model(**row) for row in to_insert])
            session.commit()
    finally:
        session.close()

    if dry_run:
        return

    with engine.connect() as conn:
        real_count = conn.execute(text(f"SELECT COUNT(*) FROM {child_model.__table__.name}")).scalar()
        log.info("[검증] %s.%s 테이블 실제 행 수 = %s", DB_NAME, child_model.__table__.name, f"{real_count:,}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=list(TARGETS.keys()), default=None,
                         help="하나만 채우려면 지정 (기본: room/cafe-menu/restaurant-menu 전부)")
    parser.add_argument("--dry-run", action="store_true", help="DB에 쓰지 않고 결과만 로그로 확인")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        require_db_config()
        targets = [args.target] if args.target else list(TARGETS.keys())
        for t in targets:
            seed_one(t, args.dry_run)
    except Exception:
        log.exception("[시드 적재 실패]")
        raise
