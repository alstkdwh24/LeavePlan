"""
CafeMenuItem/RestaurantMenuItem/RoomType/StayListing/CafeListing/RestaurantListing에
isPlaceholder 컬럼을 추가하는 1회성 마이그레이션.

이 프로젝트엔 alembic 같은 마이그레이션 도구가 없고 SQLAlchemy의 Base.metadata.create_all()은
"없는 테이블"만 만들지 "이미 있는 테이블에 컬럼 추가"는 안 해주기 때문에, 이미 데이터가 잔뜩 들어간
기존 테이블에 새 컬럼을 넣으려면 이렇게 직접 ALTER TABLE을 실행해야 한다.

동작 — 메뉴/방 테이블(FULL_PLACEHOLDER_TABLES):
    1) 컬럼이 이미 있으면 건너뜀 (재실행 안전)
    2) 없으면 ALTER TABLE ... ADD COLUMN isPlaceholder TINYINT(1) NOT NULL DEFAULT 0
    3) 지금까지 들어간 모든 행은 seed_room_details.py(가상 상호명+가상 메뉴)나
       seed_generic_menus.py/seed_generic_rooms.py(실제 상호명+가상 메뉴/방) 어느 쪽으로 들어왔든
       "실제로 확인된 정보"는 하나도 없으므로, 기존 행 전부를 isPlaceholder=1로 백필한다.

동작 — 리스팅 테이블(LISTING_SEED_MATCHES):
    가게(Listing) 자체는 대부분(카카오/TourAPI) 실제 업체라서 기본값 0을 그대로 두고,
    seed_listings.py에 있는 가상의 데모 상호명(이름+지역 일치)만 콕 집어 1로 백필한다.

사용법:
    python scripts/migrate_add_is_placeholder.py
"""
import logging
import logging.config
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import text

from config.database import engine, DB_USER, DB_HOST, DB_NAME
from config.logging_config import LOGGING_CONFIG

logging.config.dictConfig(LOGGING_CONFIG)
log = logging.getLogger(__name__)

FULL_PLACEHOLDER_TABLES = ["CafeMenuItem", "RestaurantMenuItem", "RoomType"]

# 리스팅 테이블 이름 -> (이름 컬럼, 지역 컬럼, seed_listings.py의 (이름, 지역) 목록).
# 이 목록에 있는 (이름, 지역) 조합만 isPlaceholder=1로 백필하고 나머지는 기본값 0(실제 업체) 그대로 둔다.
LISTING_SEED_MATCHES: dict[str, tuple[str, str, list[tuple[str, str]]]] = {
    "StayListing": ("stayName", "region", [
        ("오션뷰 풀빌라 안목", "강릉"),
        ("오션뷰 룸텔과 한옥", "강릉"),
        ("해솔 감성 독채 스테이", "제주"),
        ("한옥 프리미엄 룸진", "경주"),
        ("제주대 파란 스위트", "부산"),
    ]),
    "CafeListing": ("cafeName", "region", [
        ("안목해변 감성 카페", "강릉"),
        ("독채처럼 감성 카페", "동해"),
    ]),
    "RestaurantListing": ("restaurantName", "region", [
        ("강릉 회센터 물회", "강릉"),
        ("강릉 최선의 맛집", "강릉"),
    ]),
}


def require_db_config() -> None:
    if not DB_USER or not DB_NAME:
        raise RuntimeError(
            f"DB 접속 정보가 비어있습니다 (DB_USER={DB_USER!r}, DB_HOST={DB_HOST!r}, DB_NAME={DB_NAME!r})."
        )


def column_exists(conn, table: str, column: str) -> bool:
    row = conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = :table AND column_name = :column"
        ),
        {"schema": DB_NAME, "table": table, "column": column},
    ).scalar()
    return bool(row)


def add_column_if_missing(conn, table: str) -> bool:
    """컬럼을 추가했으면 True, 이미 있어서 건너뛰었으면 False."""
    if column_exists(conn, table, "isPlaceholder"):
        log.info("[%s] isPlaceholder 컬럼 이미 있음 — 건너뜀", table)
        return False
    log.info("[%s] isPlaceholder 컬럼 추가", table)
    conn.execute(text(
        f"ALTER TABLE `{table}` ADD COLUMN `isPlaceholder` TINYINT(1) NOT NULL DEFAULT 0"
    ))
    return True


def run() -> None:
    require_db_config()
    with engine.begin() as conn:
        for table in FULL_PLACEHOLDER_TABLES:
            added = add_column_if_missing(conn, table)
            if not added:
                continue
            # 지금까지 들어간 행은 전부 예시 데이터이므로 백필한다 (신규 컬럼 기본값 0으로 들어갔던 걸 1로).
            result = conn.execute(text(f"UPDATE `{table}` SET `isPlaceholder` = 1"))
            log.info("[%s] 기존 %d행을 isPlaceholder=1로 백필", table, result.rowcount)

        for table, (name_col, region_col, seeds) in LISTING_SEED_MATCHES.items():
            added = add_column_if_missing(conn, table)
            # 컬럼이 이미 있었더라도(재실행), 데모 이름 매칭 백필은 멱등이라 매번 다시 해도 안전하다.
            matched = 0
            for name, region in seeds:
                result = conn.execute(
                    text(f"UPDATE `{table}` SET `isPlaceholder` = 1 "
                         f"WHERE `{name_col}` = :name AND `{region_col}` = :region"),
                    {"name": name, "region": region},
                )
                matched += result.rowcount
            log.info("[%s] 데모 상호명 %d건 매칭 -> isPlaceholder=1 (나머지는 실제 업체로 0 유지)",
                      table, matched)

    log.info("[마이그레이션 완료]")


if __name__ == "__main__":
    try:
        run()
    except Exception:
        log.exception("[마이그레이션 실패]")
        raise
