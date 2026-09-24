"""
RoomType이 하나도 없는 StayListing(TourAPI/CSV 어느 쪽으로도 방 정보가 안 채워진 소수 잔여분)에
"예시 방" 2종(스탠다드/디럭스)을 채운다. seed_generic_menus.py와 같은 방식 — 무료로 구할 수 있는
실제 객실 데이터 소스가 없어서 만든 placeholder이며, description에 항상 "예시 정보" 문구를 남겨
진짜 정보로 오인되지 않게 한다.

사용법:
    python scripts/seed_generic_rooms.py --dry-run     # 몇 곳에 몇 개 들어갈지 미리 확인
    python scripts/seed_generic_rooms.py               # 실제 반영
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
from models.room_type import RoomType

logging.config.dictConfig(LOGGING_CONFIG)
log = logging.getLogger(__name__)

PLACEHOLDER_NOTE = "예시 객실 정보 — 실제 객실 구성/가격과 다를 수 있습니다(정확한 정보는 숙소에 확인해주세요)."

ROOM_TEMPLATE = [
    dict(room_name="스탠다드룸", bed_type="더블베드 1개", base_capacity=2, max_capacity=2, price=90000, stock=3),
    dict(room_name="디럭스룸", bed_type="퀸베드 1개", base_capacity=2, max_capacity=3, price=130000, stock=2),
]


def require_db_config() -> None:
    if not DB_USER or not DB_NAME:
        raise RuntimeError(
            f"DB 접속 정보가 비어있습니다 (DB_USER={DB_USER!r}, DB_HOST={DB_HOST!r}, DB_NAME={DB_NAME!r})."
        )


def run(dry_run: bool) -> None:
    require_db_config()
    Base.metadata.create_all(bind=engine, tables=[RoomType.__table__])

    session = SessionLocal()
    try:
        all_stays = session.query(StayListing).all()
        has_room_ids = {row[0] for row in session.query(RoomType.stay_id).distinct().all()}
        targets = [s for s in all_stays if s.id not in has_room_ids]

        log.info("[room] 전체 %d곳 중 방 정보 없는 곳 %d곳", len(all_stays), len(targets))

        inserted = 0
        for stay in targets:
            rows = [
                dict(stay_id=stay.id, room_name=item["room_name"], bed_type=item["bed_type"],
                     base_capacity=item["base_capacity"], max_capacity=item["max_capacity"],
                     price=item["price"], stock=item["stock"], description=PLACEHOLDER_NOTE,
                     is_placeholder=True)
                for item in ROOM_TEMPLATE
            ]
            if dry_run:
                log.info("  [--dry-run] %s -> %s", stay.stayName, [r["room_name"] for r in rows])
            else:
                session.bulk_save_objects([RoomType(**r) for r in rows])
            inserted += len(rows)

        if dry_run:
            log.info("[--dry-run] DB에 쓰지 않고 종료합니다. (%d곳 / %d행 예정)", len(targets), inserted)
            return

        session.commit()
    finally:
        session.close()

    with engine.connect() as conn:
        room_count = conn.execute(text(f"SELECT COUNT(*) FROM {RoomType.__table__.name}")).scalar()
        log.info("[검증] RoomType 행 수 = %s", f"{room_count:,}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="DB에 쓰지 않고 로그로만 확인")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        run(args.dry_run)
    except Exception:
        log.exception("[예시 객실 시드 실패]")
        raise
