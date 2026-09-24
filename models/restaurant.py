import uuid

from sqlalchemy import Column, String, Uuid

from config.database import Base

# 공공데이터포털 '전국 일반음식점 인허가 정보' CSV 컬럼 순서와 1:1 대응
# (scripts/import_general_restaurant.py 가 이 순서 그대로 zip 해서 적재함)
RAW_COLUMN_ORDER = [
    "local_government_code",              # 개방자치단체코드
    "management_number",                  # 관리번호
    "permit_date",                        # 인허가일자
    "business_status_name",               # 영업상태명
    "closure_date",                       # 폐업일자
    "site_area",                          # 소재지면적
    "site_postal_code",                   # 소재지우편번호
    "road_postal_code",                   # 도로명우편번호
    "business_name",                      # 사업장명
    "business_type_name",                 # 업태구분명
    "data_update_type",                   # 데이터갱신구분
    "building_ownership_type",            # 건물소유구분명
    "factory_office_staff_count",         # 공장사무직직원수
    "factory_production_staff_count",     # 공장생산직직원수
    "factory_sales_staff_count",          # 공장판매직직원수
    "water_supply_type",                  # 급수시설구분명
    "male_worker_count",                  # 남성종사자수
    "multi_use_facility_flag",            # 다중이용업소여부
    "data_update_time",                   # 데이터갱신시점
    "road_address",                       # 도로명주소
    "grade_type",                         # 등급구분명
    "deposit_amount",                     # 보증액
    "hq_staff_count",                     # 본사직원수
    "detailed_business_status_name",      # 상세영업상태명
    "detailed_business_status_code",      # 상세영업상태코드
    "facility_total_scale",               # 시설총규모
    "female_worker_count",                # 여성종사자수
    "business_status_code",               # 영업상태코드
    "surrounding_area_type",              # 영업장주변구분명
    "monthly_rent",                       # 월세액
    "sanitation_business_type_name",      # 위생업태명
    "traditional_business_main_food",     # 전통업소주된음식
    "traditional_business_designation_number",  # 전통업소지정번호
    "phone_number",                       # 전화번호
    "coord_x",                            # 좌표정보(X)
    "coord_y",                            # 좌표정보(Y)
    "lot_address",                        # 지번주소
    "website",                            # 홈페이지
    "last_modified_time",                 # 최종수정시점
]


class Restaurant(Base):
    """공공데이터포털 CSV를 가공 없이 그대로 적재하는 테이블.

    모든 컬럼을 문자열로 받는다 — 여기서는 타입 변환/정제를 하지 않고,
    필요한 가공은 이 테이블을 읽어가는 후속 단계에서 한다.
    """

    __tablename__ = "Restaurant"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    local_government_code = Column(String(20))
    management_number = Column(String(50))
    permit_date = Column(String(20))
    business_status_name = Column(String(50))
    closure_date = Column(String(20))
    site_area = Column(String(50))
    site_postal_code = Column(String(20))
    road_postal_code = Column(String(20))
    business_name = Column(String(200))
    business_type_name = Column(String(100))
    data_update_type = Column(String(20))
    building_ownership_type = Column(String(50))
    factory_office_staff_count = Column(String(20))
    factory_production_staff_count = Column(String(20))
    factory_sales_staff_count = Column(String(20))
    water_supply_type = Column(String(50))
    male_worker_count = Column(String(20))
    multi_use_facility_flag = Column(String(10))
    data_update_time = Column(String(30))
    road_address = Column(String(300))
    grade_type = Column(String(50))
    deposit_amount = Column(String(50))
    hq_staff_count = Column(String(20))
    detailed_business_status_name = Column(String(50))
    detailed_business_status_code = Column(String(20))
    facility_total_scale = Column(String(50))
    female_worker_count = Column(String(20))
    business_status_code = Column(String(20))
    surrounding_area_type = Column(String(50))
    monthly_rent = Column(String(50))
    sanitation_business_type_name = Column(String(100))
    traditional_business_main_food = Column(String(100))
    traditional_business_designation_number = Column(String(50))
    phone_number = Column(String(30))
    coord_x = Column(String(50))
    coord_y = Column(String(50))
    lot_address = Column(String(300))
    website = Column(String(300))
    last_modified_time = Column(String(30))
