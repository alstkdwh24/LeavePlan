"""
공공데이터포털 '전국 카페 표준데이터' csv를 Cafe 테이블에 그대로 적재한다.

사용법:
    python scripts/import_cafe.py "C:\\Users\\JOMINSANG\\OneDrive\\Desktop\\공공데이터\\카페\\전국카페표준데이터.csv"

전제:
    - .env에 DB_USER/DB_PASSWORD/DB_HOST/DB_NAME이 채워져 있어야 함
    - 파일 인코딩은 cp949(euc-kr), 컬럼 순서는 models.cafe_model.RAW_COLUMN_ORDER와 1:1 대응
    - 총 약 8,604행
"""
import csv
import logging.config
import os
import sys
import time

# 현재 파이썬 파일을 기준으로 프로젝트의 상위 디렉터리를 구하는 코드
# Python이 파일 경로를 자동으로 프로젝트 기준으로 잡아주는 구조가 아니기 때문입니다.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import text

from config.database import Base, engine, SessionLocal, DB_USER, DB_HOST, DB_NAME
from config.logging_config import LOGGING_CONFIG
from models.cafe_model import Cafe, RAW_COLUMN_ORDER

logging.config.dictConfig(LOGGING_CONFIG)
log = logging.getLogger(__name__)

BATCH_SIZE = 2000
EXPECTED_COLUMNS = len(RAW_COLUMN_ORDER)


def build_row_dict(raw_row: list[str]) -> dict:
    values = [v.strip() or None for v in raw_row]
    return dict(zip(RAW_COLUMN_ORDER, values))


def import_csv(csv_path: str) -> int:
    if not DB_USER or not DB_NAME:
        raise RuntimeError(
            f"DB 접속 정보가 비어 있습니다 "
            f"(DB_USER={DB_USER!r}, DB_HOST={DB_HOST!r}, DB_NAME={DB_NAME!r}). "
            f"Run > Edit Configurations 에서 이 스크립트 설정에도 환경변수를 추가해주세요."
        )
    log.info("[DB 접속 대상] host=%s, db=%s, user=%s", DB_HOST, DB_NAME, DB_USER)

    Base.metadata.create_all(bind=engine, tables=[Cafe.__table__])

    table = Cafe.__table__
    start = time.time()
    total_read = 0
    total_inserted = 0
    skipped = 0
    batch: list[dict] = []

    log.info("[카페 CSV 적재 시작] file=%s", csv_path)

    def flush(rows: list[dict]) -> None:
        if not rows:
            return
        session = SessionLocal()
        try:
            session.bulk_save_objects([Cafe(**row) for row in rows])
            session.commit()
        finally:
            session.close()

    with open(csv_path, "r", encoding="cp949", errors="replace", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            total_read += 1
            if len(row) != EXPECTED_COLUMNS:
                skipped += 1
                continue
            batch.append(build_row_dict(row))
            if len(batch) >= BATCH_SIZE:
                flush(batch)
                total_inserted += len(batch)
                batch.clear()
                elapsed = time.time() - start
                log.info("%s행 적재 완료 (%.1fs 경과, 스킵 %d건)", f"{total_inserted:,}", elapsed, skipped)
        flush(batch)
        total_inserted += len(batch)

    elapsed = time.time() - start
    log.info("[적재 완료] 총 %s행 읽음 / %s행 적재 / %d행 스킵(컬럼 수 불일치) / %.1f초 소요",
             f"{total_read:,}", f"{total_inserted:,}", skipped, elapsed)

    with engine.connect() as conn:
        real_count = conn.execute(text(f"SELECT COUNT(*) FROM {table.name}")).scalar()
        log.info("[검증] %s.%s 테이블 실제 행 수 = %s", DB_NAME, table.name, f"{real_count:,}")

    return total_inserted


DEFAULT_CSV_PATH = r"C:\Users\JOMINSANG\OneDrive\Desktop\공공데이터\카페\전국카페표준데이터.csv"

if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV_PATH
    try:
        import_csv(csv_path)
    except Exception:
        log.exception("[카페 CSV 적재 실패]")
        raise
