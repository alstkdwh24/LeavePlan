"""
'전국 숙박업 인허가 정보' CSV(양실수/한실수)로 RoomType을 간이 버전으로 보완하는 스크립트.

enrich_stay_rooms.py(TourAPI)는 방 이름/침대타입/가격까지 실데이터로 채워주지만 검색 범위 밖의
숙소는 놓친다. 이 스크립트는 그렇게 RoomType이 하나도 없는 StayListing만 대상으로, CSV의
양실수/한실수(개수만 있고 이름·가격·인원 정보는 없음)로 "양실"/"한실" 두 종류만 최소한으로
채워 넣는 보완용(fallback)이다 — TourAPI로 이미 방이 채워진 숙소는 절대 건드리지 않는다.

전제:
    - .env에 DB_USER/DB_PASSWORD/DB_HOST/DB_NAME이 채워져 있어야 함 (config/database.py가 자동 로드)
    - CSV 인코딩은 cp949(euc-kr), scripts/import_stay.py와 같은 파일
    - StayListing.stayName과 CSV의 사업장명이 '완전히 같아야' 매칭된다 (실무 데모 수준의 단순 매칭 —
      상호명 앞뒤 공백/괄호 표기 차이 등으로 매칭이 안 될 수 있음). 후보가 여러 곳이면 StayListing.region이
      도로명주소/지번주소에 포함되는 쪽을 우선한다.
    - 폐업한 곳(영업상태명이 '영업'으로 시작하지 않음)은 매칭 후보에서 제외한다.

사용법:
    python scripts/enrich_stay_rooms_from_csv.py                # 기본 CSV 경로 사용
    python scripts/enrich_stay_rooms_from_csv.py --dry-run       # DB에 쓰지 않고 결과만 로그로 확인
    python scripts/enrich_stay_rooms_from_csv.py --csv "다른경로.csv"

재실행 안전성:
    RoomType이 이미 1개 이상 있는 StayListing은 건너뛴다 (TourAPI/seed로 채워졌든, 이 스크립트로
    이전에 채워졌든 상관없이) — 여러 번 실행해도 중복 적재되지 않는다.
"""
import argparse
import csv
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

DEFAULT_CSV_PATH = r"C:\Users\JOMINSANG\OneDrive\Desktop\공공데이터\카페\문화_숙박업.csv"


def require_db_config() -> None:
    if not DB_USER or not DB_NAME:
        raise RuntimeError(
            f"DB 접속 정보가 비어있습니다 (DB_USER={DB_USER!r}, DB_HOST={DB_HOST!r}, DB_NAME={DB_NAME!r}). "
            ".env 또는 Run Configuration에 환경변수를 채워주세요."
        )


def _to_int(raw: str | None) -> int | None:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        value = int(float(raw))
    except ValueError:
        return None
    return value if value > 0 else None


def load_csv_index(csv_path: str) -> dict[str, list[dict]]:
    """사업장명 -> [해당 CSV row(주소/양실수/한실수)...] 인덱스. 폐업 업소는 제외."""
    index: dict[str, list[dict]] = {}
    total = 0
    active = 0
    with open(csv_path, "r", encoding="cp949", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            name = (row.get("사업장명") or "").strip()
            status = (row.get("영업상태명") or "").strip()
            if not name or not status.startswith("영업"):
                continue
            active += 1
            entry = {
                "address": (row.get("도로명주소") or row.get("지번주소") or "").strip(),
                "western_rooms": _to_int(row.get("양실수")),
                "korean_rooms": _to_int(row.get("한실수")),
            }
            index.setdefault(name, []).append(entry)
    log.info("[CSV 로드 완료] 전체 %s행 / 영업중 %s행 / 고유 상호명 %s개",
             f"{total:,}", f"{active:,}", f"{len(index):,}")
    return index


def pick_best_match(candidates: list[dict], region: str | None) -> dict | None:
    if not candidates:
        return None
    if region:
        for cand in candidates:
            if region in cand["address"]:
                return cand
    return candidates[0]


def run(csv_path: str, dry_run: bool) -> None:
    require_db_config()
    Base.metadata.create_all(bind=engine, tables=[StayListing.__table__, RoomType.__table__])

    csv_index = load_csv_index(csv_path)

    session = SessionLocal()
    matched = 0
    unmatched = 0
    new_room_count = 0
    try:
        stays_without_rooms = [
            stay for stay in session.query(StayListing).all()
            if session.query(RoomType).filter_by(stay_id=stay.id).first() is None
        ]
        log.info("[대상] RoomType이 없는 StayListing %d건", len(stays_without_rooms))

        for stay in stays_without_rooms:
            candidates = csv_index.get(stay.stayName.strip())
            best = pick_best_match(candidates, stay.region) if candidates else None
            if best is None:
                unmatched += 1
                log.info("  [매칭 실패] %s (%s)", stay.stayName, stay.region)
                continue

            matched += 1
            rooms_to_add = []
            if best["western_rooms"]:
                rooms_to_add.append(dict(
                    room_name="양실", stock=best["western_rooms"],
                    description="공공데이터(전국 숙박업 인허가 정보) 기준 양실 객실 수. "
                                 "개별 방 이름/가격/인원 정보는 제공되지 않음.",
                ))
            if best["korean_rooms"]:
                rooms_to_add.append(dict(
                    room_name="한실", stock=best["korean_rooms"],
                    description="공공데이터(전국 숙박업 인허가 정보) 기준 한실 객실 수. "
                                 "개별 방 이름/가격/인원 정보는 제공되지 않음.",
                ))

            if not rooms_to_add:
                unmatched += 1
                log.info("  [매칭됐지만 방 개수 정보 없음] %s", stay.stayName)
                continue

            log.info("  [매칭] %s -> %s", stay.stayName,
                     ", ".join(f"{r['room_name']} {r['stock']}실" for r in rooms_to_add))
            new_room_count += len(rooms_to_add)
            if not dry_run:
                for r in rooms_to_add:
                    session.add(RoomType(stay_id=stay.id, **r))

        log.info("[요약] 매칭 %d건 / 매칭 실패(또는 방 정보 없음) %d건 / 신규 RoomType %d건",
                 matched, unmatched, new_room_count)

        if dry_run:
            log.info("[--dry-run] DB에 쓰지 않고 종료합니다.")
            session.rollback()
            return

        session.commit()
    finally:
        session.close()

    if dry_run:
        return

    with engine.connect() as conn:
        room_count = conn.execute(text(f"SELECT COUNT(*) FROM {RoomType.__table__.name}")).scalar()
        log.info("[검증] %s 테이블 실제 행 수 = %s", RoomType.__table__.name, f"{room_count:,}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default=DEFAULT_CSV_PATH, help="숙박업 인허가 정보 CSV 경로")
    parser.add_argument("--dry-run", action="store_true", help="DB에 쓰지 않고 결과만 로그로 확인")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        run(args.csv, args.dry_run)
    except Exception:
        log.exception("[CSV 기반 방 보완 실패]")
        raise
