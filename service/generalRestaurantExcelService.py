import csv
import logging
import time

from config.database import SessionLocal
from models.restaurant import Restaurant, RAW_COLUMN_ORDER

log = logging.getLogger(__name__)

FILE_PATH = r"C:\Users\JOMINSANG\OneDrive\Desktop\공공데이터\카페\식품_일반음식점.csv"
LOG_EVERY = 50_000  # 이 행 수마다 진행 상황 로그


def import_excel() -> int:
    db = SessionLocal()
    records: list[Restaurant] = []
    total_read = 0
    skipped = 0
    start = time.time()

    log.info("[일반음식점 엑셀 적재 시작] file=%s", FILE_PATH)

    try:
        with open(FILE_PATH, "r", encoding="cp949", errors="replace", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)  # 헤더 스킵

            for row in reader:
                total_read += 1

                if len(row) != len(RAW_COLUMN_ORDER):
                    skipped += 1
                    continue

                values = [v.strip() or None for v in row]
                data = dict(zip(RAW_COLUMN_ORDER, values))

                # 의미없는 데이터 필터링
                if not data["management_number"] or not data["business_name"]:
                    skipped += 1
                    continue

                records.append(Restaurant(**data))

                if total_read % LOG_EVERY == 0:
                    elapsed = time.time() - start
                    log.info("[읽는 중] %d행 읽음 / %d건 적재 대기 / %d건 스킵 (%.1fs 경과)",
                              total_read, len(records), skipped, elapsed)

        log.info("[DB 저장 시작] 총 %d건", len(records))
        db.bulk_save_objects(records)
        db.commit()

        elapsed = time.time() - start
        log.info("[일반음식점 엑셀 적재 완료] 건수=%d / 스킵=%d / %.1fs 소요", len(records), skipped, elapsed)
        return len(records)
    except Exception:
        log.exception("[일반음식점 엑셀 적재 실패]")
        raise
    finally:
        db.close()
