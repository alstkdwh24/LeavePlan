"""
공공데이터포털 '전국 숙박업 인허가 정보' CSV를 Stay 테이블에 그대로 적재한다.

사용법 (프로젝트 어느 위치에서 실행해도 됨):
    python scripts/import_stay.py "C:\\Users\\JOMINSANG\\OneDrive\\Desktop\\공공데이터\\카페\\문화_숙박업.csv"

전제:
    - .env(또는 실행 환경변수)에 DB_USER/DB_PASSWORD/DB_HOST/DB_NAME이 실제 값으로 채워져 있어야 함
    - 파일 인코딩은 cp949(euc-kr), 컬럼 순서는 models.stay.RAW_COLUMN_ORDER와 1:1 대응
    - 총 약 5.9만 행 — 배치 커밋으로 처리
"""
import csv
import logging
import logging.config
import os
import sys
import time

# 프로젝트 루트(LeavePlnner)를 sys.path에 추가 — `python scripts/xxx.py`로 직접 실행해도
# `from config...`, `from models...` 임포트가 되도록 함
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import text
from sqlalchemy.dialects.mysql import insert as mysql_insert

from config.database import Base, engine, DB_USER, DB_HOST, DB_NAME
from config.logging_config import LOGGING_CONFIG
from models.stay import Stay, RAW_COLUMN_ORDER

# attribute명(snake_case) -> 실제 DB 컬럼명(camelCase) 매핑. Stay 모델 정의에서 그대로 뽑아 쓴다
# (손으로 다시 옮겨적지 않음 — 이전에 이 매핑을 손으로 잘못 옮겨서 전부 NULL로 들어간 적이 있었다).
COLUMN_NAME_MAP = {prop.key: prop.columns[0].name for prop in Stay.__mapper__.column_attrs}

# main.py를 거치지 않고 이 스크립트를 단독 실행할 때도(PyCharm Run 등) 같은 로그 포맷이 나오도록
# 여기서도 직접 로깅 설정을 적용한다.
logging.config.dictConfig(LOGGING_CONFIG)
log = logging.getLogger(__name__)

BATCH_SIZE = 5000
EXPECTED_COLUMNS = len(RAW_COLUMN_ORDER)
LOG_EVERY_BATCHES = 1  # 배치(5000행)마다 로그 — 필요시 늘려서 로그 양 줄이기


def build_row_dict(raw_row: list[str]) -> dict:
    values = [v.strip() or None for v in raw_row]
    return dict(zip(RAW_COLUMN_ORDER, values))


def import_csv(csv_path: str) -> None:
    # 환경변수가 비어있으면(=이 실행 설정엔 DB 접속 정보가 안 잡혀있으면) 여기서 바로 죽게 만든다.
    if not DB_USER or not DB_NAME:
        raise RuntimeError(
            f"DB 접속 정보가 비어있습니다 (DB_USER={DB_USER!r}, DB_HOST={DB_HOST!r}, DB_NAME={DB_NAME!r}). "
            "이 스크립트를 PyCharm에서 새로 Run 하면 별도의 실행 설정(Run Configuration)이 만들어지는데, "
            "거기엔 main 앱 실행 설정의 환경변수(DB_USER/DB_PASSWORD/DB_HOST/DB_NAME)가 없을 수 있습니다. "
            "Run > Edit Configurations 에서 이 스크립트 설정에도 동일한 환경변수를 추가해주세요."
        )
    log.info("[DB 접속 대상] host=%s, db=%s, user=%s", DB_HOST, DB_NAME, DB_USER)

    # 테이블이 없으면 생성 (있으면 그대로 사용)
    Base.metadata.create_all(bind=engine, tables=[Stay.__table__])

    table = Stay.__table__
    start = time.time()
    total_read = 0
    total_inserted = 0
    skipped = 0
    batch: list[dict] = []

    log.info("[숙박업 CSV 적재 시작] file=%s", csv_path)

    non_key_db_columns = [
        db_name for attr, db_name in COLUMN_NAME_MAP.items() if attr != "management_number"
    ]

    def flush(rows: list[dict]) -> None:
        if not rows:
            return
        # UPSERT: managementNumber(관리번호)가 이미 있으면 나머지 컬럼을 최신 값으로 갱신하고,
        # 없으면 새로 삽입한다. 재실행해도 중복이 안 쌓이도록 하기 위함
        # (예전엔 순수 INSERT만 해서 같은 CSV를 두 번 돌리면 그대로 2배로 쌓였음).
        # dict 키는 attribute명(snake_case)이므로 실제 DB 컬럼명(camelCase)으로 변환해서 넣는다.
        db_rows = [
            {COLUMN_NAME_MAP[k]: v for k, v in row.items()}
            for row in rows
        ]
        # 배치마다 독립된 트랜잭션으로 커밋 — 중간에 실패해도 그 전까지 적재분은 DB에 남는다.
        with engine.begin() as conn:
            stmt = mysql_insert(Stay.__table__).values(db_rows)
            update_values = {col: stmt.inserted[col] for col in non_key_db_columns}
            stmt = stmt.on_duplicate_key_update(**update_values)
            conn.execute(stmt)

    with open(csv_path, "r", encoding="cp949", errors="replace", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)  # 헤더 스킵

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

    # 실제로 DB에 들어갔는지 이 자리에서 바로 재확인 (다른 도구로 따로 확인 안 해도 되게)
    with engine.connect() as conn:
        real_count = conn.execute(text(f"SELECT COUNT(*) FROM {table.name}")).scalar()
        log.info("[검증] %s.%s 테이블 실제 행 수 = %s", DB_NAME, table.name, f"{real_count:,}")


DEFAULT_CSV_PATH = r"C:\Users\JOMINSANG\OneDrive\Desktop\공공데이터\카페\문화_숙박업.csv"

if __name__ == "__main__":
    # PyCharm에서 인자 없이 그냥 Run 버튼만 눌러도 되도록 기본 경로 사용.
    # 다른 파일을 넣고 싶으면: python scripts/import_stay.py <csv경로>
    csv_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV_PATH
    try:
        import_csv(csv_path)
    except Exception:
        log.exception("[숙박업 CSV 적재 실패]")
        raise
