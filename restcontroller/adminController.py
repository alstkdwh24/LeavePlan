from typing import Literal

from fastapi import APIRouter, BackgroundTasks

from scripts.import_general_restaurant import import_csv as import_general_restaurant_csv
from scripts.import_stay import import_csv as import_stay_csv
from scripts.import_tourist_spot import import_csv as import_tourist_spot_csv
from scripts.import_cafe import import_csv as import_cafe_csv
from scripts.enrich_stay_rooms import run as run_enrich_stay_rooms
from scripts.enrich_stay_rooms_from_csv import (
    run as run_enrich_stay_rooms_from_csv,
    DEFAULT_CSV_PATH as DEFAULT_STAY_ROOMS_CSV_PATH,
)
from scripts.enrich_listings import run as run_enrich_listings
from scripts.enrich_curated_regions import (
    run as run_enrich_curated_regions,
    DEFAULT_STATE_FILE as DEFAULT_CURATED_STATE_FILE,
    REGION_PLAN as CURATED_REGION_PLAN,
)

CURATED_REGION_NAMES = [row[0] for row in CURATED_REGION_PLAN]
from scripts.seed_generic_menus import run as run_seed_generic_menus
from scripts.seed_generic_rooms import run as run_seed_generic_rooms
from scripts.enrich_all_regions_listings import (
    run as run_enrich_all_regions_listings,
    DEFAULT_STATE_FILE as DEFAULT_ALL_LISTINGS_STATE_FILE,
)

router = APIRouter(prefix="/admin", tags=["admin"])

DEFAULT_GENERAL_RESTAURANT_CSV_PATH = r"C:\Users\JOMINSANG\OneDrive\Desktop\공공데이터\카페\식품_일반음식점.csv"
DEFAULT_STAY_CSV_PATH = r"C:\Users\JOMINSANG\OneDrive\Desktop\공공데이터\카페\문화_숙박업.csv"
DEFAULT_TOURIST_SPOT_CSV_PATH = r"C:\Users\JOMINSANG\OneDrive\Desktop\공공데이터\카페\전국관광지정보표준데이터.csv"
DEFAULT_CAFE_CSV_PATH = r"C:\Users\JOMINSANG\OneDrive\Desktop\공공데이터\카페\전국카페표준데이터.csv"

@router.post("/import/general-restaurant")
def import_general_restaurant(background_tasks: BackgroundTasks, csv_path: str = DEFAULT_GENERAL_RESTAURANT_CSV_PATH):
    """공공데이터 CSV(약 229만 행)를 Restaurant 테이블로 임포트한다.
    시간이 오래 걸리므로(로컬 MySQL 기준 수십 분) 백그라운드로 실행하고 즉시 응답한다.
    진행 상황은 서버(uvicorn) 콘솔 로그에 5000행 단위로 출력된다.

    ⚠️ 개인 로컬 관리용 엔드포인트입니다 — 운영 배포 시에는 인증(관리자 전용) 처리 후 노출하세요."""
    background_tasks.add_task(import_general_restaurant_csv, csv_path)
    return {
        "message": "임포트를 백그라운드로 시작했습니다. 서버 콘솔 로그에서 진행 상황을 확인하세요.",
        "csv_path": csv_path,
    }


@router.post("/import/stay")
def import_stay(background_tasks: BackgroundTasks, csv_path: str = DEFAULT_STAY_CSV_PATH):
    """공공데이터 CSV(약 5.9만 행, 숙박업 인허가 정보)를 Stay 테이블로 임포트한다.
    백그라운드로 실행하고 즉시 응답하며, 진행 상황은 서버(uvicorn) 콘솔 로그에 5000행 단위로 출력된다.

    ⚠️ 개인 로컬 관리용 엔드포인트입니다 — 운영 배포 시에는 인증(관리자 전용) 처리 후 노출하세요."""
    background_tasks.add_task(import_stay_csv, csv_path)
    return {
        "message": "임포트를 백그라운드로 시작했습니다. 서버 콘솔 로그에서 진행 상황을 확인하세요.",
        "csv_path": csv_path,
    }

@router.post("/import/tourist-spot")
def import_tourist_spot(background_tasks: BackgroundTasks, csv_path: str = DEFAULT_TOURIST_SPOT_CSV_PATH):
    """공공데이터 CSV(약 852행, 전국 관광지 정보)를 TouristSpot 테이블로 임포트한다."""
    background_tasks.add_task(import_tourist_spot_csv, csv_path)
    return {
        "message": "임포트를 백그라운드로 시작했습니다. 서버 콘솔 로그에서 진행 상황을 확인하세요.",
        "csv_path": csv_path,
    }


@router.post("/import/cafe")
def import_cafe(background_tasks: BackgroundTasks, csv_path: str = DEFAULT_CAFE_CSV_PATH):
    """공공데이터 CSV(약 8,604행, 전국 카페 표준데이터)를 Cafe 테이블로 임포트한다."""
    background_tasks.add_task(import_cafe_csv, csv_path)
    return {
        "message": "임포트를 백그라운드로 시작했습니다. 서버 콘솔 로그에서 진행 상황을 확인하세요.",
        "csv_path": csv_path,
    }


@router.post("/enrich/stay-rooms")
def enrich_stay_rooms(
    background_tasks: BackgroundTasks,
    keyword: str,
    region: str,
    limit: int = 5,
    dry_run: bool = False,
):
    """TourAPI(한국관광공사)로 숙박업소+객실(방 종류) 실데이터를 가져와
    StayListing/RoomType을 채운다. TOUR_API_KEY는 서버 실행 환경(.env 또는 이 서버의
    Run Configuration 환경변수)에서 그대로 읽으므로 별도 스크립트 실행 설정이 필요 없다.

    ⚠️ 개인 로컬 관리용 엔드포인트입니다 — 운영 배포 시에는 인증(관리자 전용) 처리 후 노출하세요."""
    background_tasks.add_task(run_enrich_stay_rooms, keyword, region, limit, dry_run)
    return {
        "message": "TourAPI 객실정보 보강을 백그라운드로 시작했습니다. 서버 콘솔 로그에서 진행 상황을 확인하세요.",
        "keyword": keyword,
        "region": region,
        "limit": limit,
        "dry_run": dry_run,
    }


@router.post("/enrich/stay-rooms-from-csv")
def enrich_stay_rooms_from_csv(
    background_tasks: BackgroundTasks,
    csv_path: str = DEFAULT_STAY_ROOMS_CSV_PATH,
    dry_run: bool = False,
):
    """TourAPI/시드로도 RoomType이 하나도 안 채워진 StayListing에 한해, 숙박업 인허가 CSV의
    양실수/한실수로 "양실"/"한실" 두 종류만 간이 보완한다 (개별 방 이름·가격 정보는 없음).

    ⚠️ 개인 로컬 관리용 엔드포인트입니다 — 운영 배포 시에는 인증(관리자 전용) 처리 후 노출하세요."""
    background_tasks.add_task(run_enrich_stay_rooms_from_csv, csv_path, dry_run)
    return {
        "message": "CSV 기반 방 보완을 백그라운드로 시작했습니다. 서버 콘솔 로그에서 진행 상황을 확인하세요.",
        "csv_path": csv_path,
        "dry_run": dry_run,
    }


@router.post("/enrich/listing")
def enrich_listing(
    background_tasks: BackgroundTasks,
    target: Literal["stay", "restaurant", "cafe"],
    keyword: str,
    region: str,
    limit: int = 10,
    category_override: str | None = None,
    dry_run: bool = False,
):
    """카카오 로컬 검색으로 후보를 찾고 네이버 지역 검색으로 교차검증만 해서
    StayListing/RestaurantListing/CafeListing을 채운다 (구글 Places 미사용 — 유료라서 뺌).
    rating/imageUrl/price_range는 카카오/네이버 어느 쪽도 무료로 안 줘서 채워지지 않는다.
    KAKAO_REST_API_KEY/NAVER_CLIENT_ID/NAVER_CLIENT_SECRET은 서버 실행 환경(.env 또는 이 서버의
    Run Configuration 환경변수)에서 그대로 읽으므로 별도 스크립트 실행 설정이 필요 없다.

    ⚠️ 개인 로컬 관리용 엔드포인트입니다 — 운영 배포 시에는 인증(관리자 전용) 처리 후 노출하세요."""
    background_tasks.add_task(
        run_enrich_listings, target, keyword, region, limit, category_override, dry_run
    )
    return {
        "message": "카카오+네이버 리스팅 보강을 백그라운드로 시작했습니다. 서버 콘솔 로그에서 진행 상황을 확인하세요.",
        "target": target,
        "keyword": keyword,
        "region": region,
        "limit": limit,
        "dry_run": dry_run,
    }


@router.get("/enrich/curated-regions/plan")
def get_curated_regions_plan():
    """scripts/enrich_curated_regions.py의 REGION_PLAN에 지금 등록된 지역/키워드 목록을 그대로 보여준다."""
    return {
        "count": len(CURATED_REGION_PLAN),
        "regions": [
            {"region": region, "stay_keyword": stay_kw, "restaurant_keyword": rest_kw, "cafe_keyword": cafe_kw}
            for region, stay_kw, rest_kw, cafe_kw in CURATED_REGION_PLAN
        ],
    }


@router.post("/enrich/curated-regions")
def enrich_curated_regions(
    background_tasks: BackgroundTasks,
    only: Literal["stay", "restaurant", "cafe"] | None = None,
    regions: str | None = None,
    limit: int = 10,
    dry_run: bool = False,
):
    """scripts/enrich_curated_regions.py의 REGION_PLAN에 등록된 지역(개수/목록은 그 파일 참고 —
    지역 추가/삭제는 REGION_PLAN만 고치면 되고 이 엔드포인트는 안 건드려도 됨)에 대해 숙소+방
    (TourAPI) / 식당·카페(카카오+네이버)를 한 번의 호출로 전부 순회한다. 지역/카테고리 조합별로
    진행 상황을 scripts/_enrich_curated_state.json에 기록해 이어하기를 지원한다 — 중간에 API 한도
    등으로 멈춰도 다시 호출하면 이어서 처리된다. `regions`는 콤마로 구분(예: "강릉,제주"), 생략 시
    REGION_PLAN 전부. 실제 지역 개수/목록은 이 엔드포인트를 호출한 응답의 "regions" 필드나
    GET /admin/enrich/curated-regions/plan 으로 확인.

    ⚠️ 개인 로컬 관리용 엔드포인트입니다 — 운영 배포 시에는 인증(관리자 전용) 처리 후 노출하세요."""
    regions_filter = [r.strip() for r in regions.split(",")] if regions else None
    background_tasks.add_task(
        run_enrich_curated_regions, only, regions_filter, limit, dry_run, 0.5, 3,
        DEFAULT_CURATED_STATE_FILE, False,  # sleep_between, max_consecutive_failures, state_file, reset_state
    )
    return {
        "message": "큐레이션 지역 보강을 백그라운드로 시작했습니다. 서버 콘솔 로그에서 진행 상황을 확인하세요.",
        "only": only,
        "regions": regions_filter or f"전체({', '.join(CURATED_REGION_NAMES)})",
        "limit": limit,
        "dry_run": dry_run,
    }


@router.post("/enrich/generic-menus")
def enrich_generic_menus(
    background_tasks: BackgroundTasks,
    only: Literal["cafe", "restaurant"] | None = None,
    dry_run: bool = False,
):
    """CafeMenuItem/RestaurantMenuItem이 하나도 없는 카페/식당에 카테고리별 '예시 메뉴'를 채운다.
    실제 메뉴 데이터를 무료로 구할 방법이 없어서 만든 placeholder이며, 각 행의 description에
    "예시 메뉴 — 실제와 다를 수 있습니다"를 항상 남겨 진짜 정보로 오인되지 않게 한다.

    ⚠️ 개인 로컬 관리용 엔드포인트입니다 — 운영 배포 시에는 인증(관리자 전용) 처리 후 노출하세요."""
    background_tasks.add_task(run_seed_generic_menus, only, dry_run)
    return {
        "message": "예시 메뉴 채우기를 백그라운드로 시작했습니다. 서버 콘솔 로그에서 진행 상황을 확인하세요.",
        "only": only,
        "dry_run": dry_run,
    }


@router.post("/enrich/generic-rooms")
def enrich_generic_rooms(background_tasks: BackgroundTasks, dry_run: bool = False):
    """RoomType이 하나도 없는 StayListing에 '예시 방'(스탠다드/디럭스) 2종을 채운다.
    generic-menus와 동일하게 placeholder이며 description에 항상 안내 문구를 남긴다.

    ⚠️ 개인 로컬 관리용 엔드포인트입니다 — 운영 배포 시에는 인증(관리자 전용) 처리 후 노출하세요."""
    background_tasks.add_task(run_seed_generic_rooms, dry_run)
    return {
        "message": "예시 객실 채우기를 백그라운드로 시작했습니다. 서버 콘솔 로그에서 진행 상황을 확인하세요.",
        "dry_run": dry_run,
    }


@router.post("/enrich/all-regions-listings")
def enrich_all_regions_listings(
    background_tasks: BackgroundTasks,
    only: Literal["stay", "cafe", "restaurant"] | None = None,
    limit_per_region: int = 15,
    max_regions: int | None = None,
    dry_run: bool = False,
):
    """StayListing에 이미 들어있는 전국 모든 지역(시군구 단위, 약 213개)을 순회하며 숙소+방
    (TourAPI)/카페·식당(카카오+네이버)을 채운다. 카페·식당은 키워드 변형 5개씩(카페/로스터리/
    브런치카페 등)을 각각 검색해서 카카오의 "키워드당 최대 45건" 한계를 우회한다.
    (지역, 카테고리, 키워드변형) 조합별로 scripts/_enrich_all_listings_state.json에 진행 상황을
    기록해 이어하기를 지원 — 중간에 멈춰도 다시 호출하면 이어서 처리된다. 지역(213) x 카테고리
    (변형 포함 11개) 조합이 2천 건이 넘어 전체 실행은 오래 걸리니, 처음엔 max_regions로 소규모
    테스트를 권장한다 (예: max_regions=5).

    ⚠️ 개인 로컬 관리용 엔드포인트입니다 — 운영 배포 시에는 인증(관리자 전용) 처리 후 노출하세요."""
    background_tasks.add_task(
        run_enrich_all_regions_listings, only, limit_per_region, dry_run, max_regions,
        0.5, 5, DEFAULT_ALL_LISTINGS_STATE_FILE, False,
        # sleep_between, max_consecutive_failures, state_file, reset_state
    )
    return {
        "message": "전국 지역 리스팅 보강을 백그라운드로 시작했습니다. 서버 콘솔 로그에서 진행 상황을 확인하세요.",
        "only": only,
        "limit_per_region": limit_per_region,
        "max_regions": max_regions,
        "dry_run": dry_run,
    }
