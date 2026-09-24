"""
StayListing / RestaurantListing / CafeListing을 '비용 없이' 채우는 시드 스크립트.

scripts/enrich_listings.py(카카오+구글 Places API)는 실제 평점/사진까지 가져오지만
구글 Places API가 유료(결제 계정 필수)라서, 결제 없이 바로 쓸 수 있는 대안으로 이 스크립트를 쓴다.

외부 API를 아예 호출하지 않는다. 대신:
    - 상호명/설명/평점/가격은 이 프로젝트 프론트엔드(MainPage/MapSchedulePage/StayDetailPage)에
      이미 등장하는 데모 콘텐츠를 그대로 재사용한다 — 실제 존재하는 특정 업체에 임의로 평점·가격을
      지어붙이는 게 아니라, 원래부터 이 앱이 "실습용 데모"로 쓰던 가상의 상호명이다
      (MainPage.tsx 하단 문구: "본 웹사이트 서비스는 실습용으로 실제 서비스가 아닙니다").
    - 위치만 실제 지명(안목해변, 경포대, 서귀포, 불국사, 해운대, 동해시 등) 근처의 대략적인 위도/경도를
      써서 지도에 자연스럽게 찍히게 한다. (Airbnb 데모 데이터가 실제 동네에 가상 매물을 배치하는 것과 같은 방식)

이미지(imageUrl)는 이 스크립트로 채우지 않는다 — 프론트엔드도 아직 실제 <img>가 아니라 색깔 블록
placeholder로 렌더링하고 있어서(MapSchedulePage/StayDetailPage 참고) 지금 단계에서는 NULL로 둬도
화면에 문제가 없다. 실제 사진이 필요해지면 enrich_listings.py(유료) 또는 직접 촬영/구매한 이미지를
스토리지에 올리는 방식을 나중에 추가하면 된다.

사용법:
    python scripts/seed_listings.py                 # stay/restaurant/cafe 전부
    python scripts/seed_listings.py --target stay    # 하나만
    python scripts/seed_listings.py --dry-run        # DB에 쓰지 않고 내용만 확인

재실행 안전성:
    같은 (테이블, 이름, 지역) 조합이 이미 있으면 건너뛴다 — 여러 번 실행해도 중복 적재되지 않는다.
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

logging.config.dictConfig(LOGGING_CONFIG)
log = logging.getLogger(__name__)

# ── 시드 데이터 ──────────────────────────────────────────────────────────
# 프론트엔드에 이미 등장하는 데모 콘텐츠 그대로 재사용 (MainPage.tsx의 spots/tlItems,
# MapSchedulePage.tsx/StayDetailPage.tsx의 scheduleItems·오션뷰 풀빌라 안목 등).
# lat/lng는 실제 지명의 대략적인 위경도(소수점 셋째자리 수준의 근사치).

STAY_SEEDS = [
    dict(stayName="오션뷰 풀빌라 안목", region="강릉", address="강릉시 안목해변 인근",
         lat=37.7807, lng=128.9480, price=248000, rating=4.9,
         description="강릉 안목해변 바로 앞 프라이빗 풀빌라. 전면 통창으로 바다가 한눈에 들어온다."),
    dict(stayName="오션뷰 룸텔과 한옥", region="강릉", address="강릉시 경포 인근",
         lat=37.7959, lng=128.8969, price=248000, rating=4.9,
         description="경포 해변가 오션뷰 룸텔. AI 일정에 가장 많이 담긴 숙소."),
    dict(stayName="해솔 감성 독채 스테이", region="제주", address="서귀포시 인근",
         lat=33.2541, lng=126.5601, price=175000, rating=4.9,
         description="서귀포 독채 스테이. 감성 인테리어와 조용한 위치가 특징."),
    dict(stayName="한옥 프리미엄 룸진", region="경주", address="경주시 불국사 인근",
         lat=35.7898, lng=129.3320, price=232000, rating=5.0,
         description="불국사 인근 프리미엄 한옥. 전통과 현대적 편의시설을 함께 갖췄다."),
    dict(stayName="제주대 파란 스위트", region="부산", address="해운대구 인근",
         lat=35.1587, lng=129.1604, price=289000, rating=4.8,
         description="해운대 해변 도보권 스위트룸. 신규 오픈 숙소."),
]

CAFE_SEEDS = [
    dict(cafe_name="안목해변 감성 카페", region="강릉", address="강릉시 안목해변 인근",
         lat=37.7810, lng=128.9485, category="디저트카페", price_range="1만원대",
         rating=4.7, description="통유리 오션뷰가 있는 감성 카페. 시그니처 라떼가 대표 메뉴."),
    dict(cafe_name="독채처럼 감성 카페", region="동해", address="동해시 인근",
         lat=37.5247, lng=129.1143, category="브런치카페", price_range="1만원대",
         rating=4.6, description="AI가 추천하는 동해시 감성 카페. 독채 느낌의 아늑한 공간."),
]

RESTAURANT_SEEDS = [
    dict(restaurant_name="강릉 회센터 물회", region="강릉", address="강릉시 안목해변 인근",
         lat=37.7805, lng=128.9478, category="한식", price_range="2만원대",
         rating=4.7, description="현지인이 추천하는 물회 맛집. 안목해변에서 도보 7분."),
    dict(restaurant_name="강릉 최선의 맛집", region="강릉", address="강릉시 인근",
         lat=37.7515, lng=128.8761, category="한식", price_range="2만원대",
         rating=4.6, description="AI 일정에 자주 포함되는 강릉 현지 맛집."),
]

TARGETS = {
    "stay": {"model": StayListing, "seeds": STAY_SEEDS, "name_attr": "stayName", "region_attr": "region",
             "placeholder_attr": "isPlaceholder"},
    "cafe": {"model": CafeListing, "seeds": CAFE_SEEDS, "name_attr": "cafe_name", "region_attr": "region",
             "placeholder_attr": "is_placeholder"},
    "restaurant": {"model": RestaurantListing, "seeds": RESTAURANT_SEEDS, "name_attr": "restaurant_name",
                   "region_attr": "region", "placeholder_attr": "is_placeholder"},
}


def require_db_config() -> None:
    if not DB_USER or not DB_NAME:
        raise RuntimeError(
            f"DB 접속 정보가 비어있습니다 (DB_USER={DB_USER!r}, DB_HOST={DB_HOST!r}, DB_NAME={DB_NAME!r}). "
            "Run > Edit Configurations 에서 이 스크립트 설정에도 환경변수를 추가해주세요."
        )


def seed_one(target: str, dry_run: bool) -> None:
    spec = TARGETS[target]
    model = spec["model"]
    name_attr = spec["name_attr"]
    region_attr = spec["region_attr"]

    Base.metadata.create_all(bind=engine, tables=[model.__table__])

    session = SessionLocal()
    try:
        existing = {
            (getattr(row, name_attr), getattr(row, region_attr))
            for row in session.query(model).all()
        }
        to_insert = [
            seed for seed in spec["seeds"]
            if (seed[name_attr], seed[region_attr]) not in existing
        ]
        skipped = len(spec["seeds"]) - len(to_insert)

        log.info("[%s] 시드 %d건 중 신규 %d건 / 이미 존재해서 건너뜀 %d건",
                  target, len(spec["seeds"]), len(to_insert), skipped)

        if dry_run:
            for seed in to_insert:
                log.info("  [--dry-run] %s", seed)
            return

        if to_insert:
            placeholder_attr = spec["placeholder_attr"]
            session.bulk_save_objects(
                [model(**seed, **{placeholder_attr: True}) for seed in to_insert]
            )
            session.commit()
    finally:
        session.close()

    if dry_run:
        return

    with engine.connect() as conn:
        real_count = conn.execute(text(f"SELECT COUNT(*) FROM {model.__table__.name}")).scalar()
        log.info("[검증] %s.%s 테이블 실제 행 수 = %s", DB_NAME, model.__table__.name, f"{real_count:,}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=list(TARGETS.keys()), default=None,
                         help="하나만 채우려면 지정 (기본: stay/cafe/restaurant 전부)")
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
