"""
'전국 숙박업 인허가 정보' CSV(영업중인 곳 전부)를 실제 StayListing(+RoomType)으로 적재하는 스크립트.

import_stay.py는 이 CSV를 원본 그대로 Stay(staging) 테이블에 적재하는 용도였는데, 이 스크립트는
한 단계 더 나아가 실제 앱이 쓰는 예약 대상 테이블(StayListing/RoomType)까지 채운다.

CSV에는 없는 정보(가격, 방 이름, 평점)는 채우지 않는다 — 방은 양실수/한실수 "개수"만으로
"양실"/"한실" 두 종류만 만든다. 가격/방이름까지 채우려면 이 스크립트 실행 후
enrich_stay_rooms.py(TourAPI)를 지역별로 돌려서 보강해야 한다 (매칭되는 곳만 실데이터 방이 추가로
붙는다 — 이 스크립트가 만든 양실/한실을 지우진 않고 같이 남겨둔다).

좌표계 주의:
    CSV의 '좌표정보(X)/(Y)'는 위경도가 아니라 EPSG:5174(TM 중부원점, Bessel) 좌표다.
    StayListing.lat/lng는 위경도(WGS84, EPSG:4326)를 기대하므로 pyproj로 변환해서 저장한다.
    (서울 종로구 샘플 좌표로 변환 검증 완료 — 실제 주소와 근사치 일치.)

지역(region) 추출:
    주소 문자열에서 '~시/~군/~구' 단위를 정규식으로 뽑는다. 기존 데모/TourAPI 데이터가
    "강릉"(시 접미사 제거)처럼 쓰길래 '시' 단위는 접미사를 떼고, '군'/'구'는 그대로 둔다
    (예: "강릉시"->"강릉", "종로구"->"종로구"). 주소 형식이 특이해 못 뽑으면 region=NULL로
    남기고 개수만 로그로 집계한다 (StayListing.region은 nullable이라 에러는 아님).

사용법:
    python scripts/import_stay_listings_from_csv.py                # 기본 CSV 경로 사용
    python scripts/import_stay_listings_from_csv.py --dry-run       # DB에 쓰지 않고 통계만 확인
    python scripts/import_stay_listings_from_csv.py --limit 100     # 앞에서 N건만(테스트용)

재실행 안전성:
    (stayName, region)이 이미 StayListing에 있으면 새로 만들지 않고, 그 기존 행의 address/lat/lng와
    양실/한실 RoomType의 stock을 이번 CSV 값으로 업데이트한다 (덮어쓰기) — 여러 번 실행해도 중복
    적재는 안 되고, 대신 최신 CSV 값으로 계속 갱신된다.
"""
import argparse
import csv
import logging
import logging.config
import os
import re
import sys
import time
import uuid

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pyproj import Transformer

from config.database import Base, engine, SessionLocal, DB_USER, DB_HOST, DB_NAME
from config.logging_config import LOGGING_CONFIG
from models.stay_listing import StayListing
from models.room_type import RoomType
from scripts.enrich_stay_rooms_from_csv import _to_int  # 재사용: "50,000" 같은 문자열 -> int

logging.config.dictConfig(LOGGING_CONFIG)
log = logging.getLogger(__name__)

DEFAULT_CSV_PATH = r"C:\Users\JOMINSANG\OneDrive\Desktop\공공데이터\카페\문화_숙박업.csv"
BATCH_SIZE = 5000

_KOREA_TM_TO_WGS84 = Transformer.from_crs("EPSG:5174", "EPSG:4326", always_xy=True)

# "OO시/OO군/OO구" 단위를 뽑는다 — 그 앞의 광역 단위(특별시/광역시/특별자치시/특별자치도/도)는 건너뛴다.
_REGION_RE = re.compile(r"(?:특별시|광역시|특별자치시|특별자치도|도)\s+(\S+?)(시|군|구)\b")
# 세종특별자치시처럼 그 밑에 시/군/구 하위단위가 아예 없는 경우의 fallback
_SEJONG_RE = re.compile(r"^(\S+?)특별자치시\b")


def extract_region(address: str | None) -> str | None:
    if not address:
        return None
    m = _REGION_RE.search(address)
    if m:
        name, suffix = m.group(1), m.group(2)
        return name if suffix == "시" else f"{name}{suffix}"
    m = _SEJONG_RE.match(address)
    return m.group(1) if m else None


def require_db_config() -> None:
    if not DB_USER or not DB_NAME:
        raise RuntimeError(
            f"DB 접속 정보가 비어있습니다 (DB_USER={DB_USER!r}, DB_HOST={DB_HOST!r}, DB_NAME={DB_NAME!r}). "
            ".env 또는 Run Configuration에 환경변수를 채워주세요."
        )


def to_wgs84(x: float, y: float) -> tuple[float, float]:
    lng, lat = _KOREA_TM_TO_WGS84.transform(x, y)
    return lat, lng


def run(csv_path: str, dry_run: bool, limit: int | None) -> None:
    require_db_config()
    Base.metadata.create_all(bind=engine, tables=[StayListing.__table__, RoomType.__table__])

    session = SessionLocal()
    try:
        existing: dict[tuple[str, str | None], str] = {
            (row.stayName, row.region): row.id
            for row in session.query(StayListing.stayName, StayListing.region, StayListing.id)
        }
        log.info("[기존 StayListing] %s건 (중복이면 업데이트 대상)", f"{len(existing):,}")

        # 기존 양실/한실 RoomType만 미리 인덱싱 — 중복 stay를 다시 만나면 stock을 갱신하기 위함
        # (실제 방이름이 있는 RoomType은 이 스크립트가 손대지 않는다).
        room_index: dict[tuple[str, str], str] = {
            (r.stay_id, r.room_name): r.id
            for r in session.query(RoomType.stay_id, RoomType.room_name, RoomType.id)
            .filter(RoomType.room_name.in_(["양실", "한실"]))
        }
        log.info("[기존 양실/한실 RoomType] %s건 (중복이면 stock 갱신 대상)", f"{len(room_index):,}")

        total_read = 0
        active = 0
        no_coords = 0
        no_region = 0
        duplicates = 0
        inserted = 0
        rooms_created = 0
        stays_updated = 0
        rooms_updated = 0

        stay_batch: list[StayListing] = []
        room_batch: list[RoomType] = []
        stay_update_batch: list[dict] = []
        room_update_batch: list[dict] = []
        start = time.time()

        def flush():
            nonlocal stay_batch, room_batch, stay_update_batch, room_update_batch
            if dry_run:
                stay_batch.clear()
                room_batch.clear()
                stay_update_batch.clear()
                room_update_batch.clear()
                return
            if stay_batch:
                session.bulk_save_objects(stay_batch)
            if room_batch:
                session.bulk_save_objects(room_batch)
            if stay_update_batch:
                session.bulk_update_mappings(StayListing, stay_update_batch)
            if room_update_batch:
                session.bulk_update_mappings(RoomType, room_update_batch)
            session.commit()
            stay_batch = []
            room_batch = []
            stay_update_batch = []
            room_update_batch = []

        with open(csv_path, "r", encoding="cp949", errors="replace", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_read += 1
                if limit and active >= limit:
                    break

                name = (row.get("사업장명") or "").strip()
                status = (row.get("영업상태명") or "").strip()
                if not name or not status.startswith("영업"):
                    continue
                active += 1

                x = _to_float(row.get("좌표정보(X)"))
                y = _to_float(row.get("좌표정보(Y)"))
                if not x or not y:
                    no_coords += 1
                    continue
                lat, lng = to_wgs84(x, y)

                address = (row.get("도로명주소") or row.get("지번주소") or "").strip() or None
                region = extract_region(address)
                if region is None:
                    no_region += 1

                western = _to_int(row.get("양실수"))
                korean = _to_int(row.get("한실수"))

                key = (name, region)
                existing_stay_id = existing.get(key)
                if existing_stay_id is not None:
                    duplicates += 1
                    stays_updated += 1
                    stay_update_batch.append({
                        "id": existing_stay_id, "address": address,
                        "lat": round(lat, 7), "lng": round(lng, 7),
                    })
                    for room_name, count in (("양실", western), ("한실", korean)):
                        if not count:
                            continue
                        existing_room_id = room_index.get((existing_stay_id, room_name))
                        if existing_room_id is not None:
                            room_update_batch.append({"id": existing_room_id, "stock": count})
                            rooms_updated += 1
                        else:
                            room_batch.append(RoomType(
                                stay_id=existing_stay_id, room_name=room_name, stock=count,
                                description="공공데이터(전국 숙박업 인허가 정보) 기준 "
                                             f"{room_name} 객실 수. 개별 방 이름/가격/인원 정보는 제공되지 않음.",
                            ))
                            rooms_created += 1
                    if len(stay_update_batch) + len(room_update_batch) >= BATCH_SIZE:
                        flush()
                    continue

                stay_id = str(uuid.uuid4())
                existing[key] = stay_id  # 같은 실행 안에서 CSV 자체 중복도 다음부터는 업데이트로 처리
                stay_batch.append(StayListing(
                    id=stay_id, stayName=name, region=region, address=address,
                    lat=round(lat, 7), lng=round(lng, 7),
                ))
                inserted += 1

                for room_name, count in (("양실", western), ("한실", korean)):
                    if not count:
                        continue
                    room_batch.append(RoomType(
                        stay_id=stay_id, room_name=room_name, stock=count,
                        description="공공데이터(전국 숙박업 인허가 정보) 기준 "
                                     f"{room_name} 객실 수. 개별 방 이름/가격/인원 정보는 제공되지 않음.",
                    ))
                    rooms_created += 1

                if len(stay_batch) >= BATCH_SIZE:
                    flush()
                    elapsed = time.time() - start
                    log.info("%s건 적재 완료 (%.1fs 경과)", f"{inserted:,}", elapsed)

            flush()

        log.info(
            "[요약] CSV %s행 읽음 / 영업중 %s건 / 좌표없음 %s건 / 지역파싱실패 %s건 / "
            "중복(업데이트) %s건(StayListing %s건 갱신 / RoomType %s건 갱신) / "
            "신규 StayListing %s건 / 신규 RoomType %s건",
            f"{total_read:,}", f"{active:,}", f"{no_coords:,}", f"{no_region:,}",
            f"{duplicates:,}", f"{stays_updated:,}", f"{rooms_updated:,}",
            f"{inserted:,}", f"{rooms_created:,}",
        )

        if dry_run:
            log.info("[--dry-run] DB에 쓰지 않고 종료합니다.")
            session.rollback()
            return
    finally:
        session.close()

    if dry_run:
        return

    with engine.connect() as conn:
        from sqlalchemy import text
        stay_count = conn.execute(text(f"SELECT COUNT(*) FROM {StayListing.__table__.name}")).scalar()
        room_count = conn.execute(text(f"SELECT COUNT(*) FROM {RoomType.__table__.name}")).scalar()
        log.info("[검증] StayListing 테이블 행 수 = %s, RoomType 테이블 행 수 = %s",
                 f"{stay_count:,}", f"{room_count:,}")


def _to_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default=DEFAULT_CSV_PATH, help="숙박업 인허가 정보 CSV 경로")
    parser.add_argument("--dry-run", action="store_true", help="DB에 쓰지 않고 통계만 확인")
    parser.add_argument("--limit", type=int, default=None, help="테스트용: 앞에서 N건(영업중 기준)만 처리")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        run(args.csv, args.dry_run, args.limit)
    except Exception:
        log.exception("[CSV 기반 StayListing 적재 실패]")
        raise
