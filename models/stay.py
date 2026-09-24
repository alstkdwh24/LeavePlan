import uuid

from sqlalchemy import Column, String, Uuid

from config.database import Base


class Stay(Base):
    """공공데이터포털 '전국 숙박업 인허가 정보' 원본 데이터를 가공 없이 그대로 담는 staging 테이블.
    예약 가능한 숙소 목록(가격/평점 등)은 models/stay_listing.py의 StayListing을 따로 참고."""

    __tablename__ = "stay"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))

    local_gov_code = Column("localGovCode", String(20), comment="개방자치단체코드")
    management_number = Column("managementNumber", String(50), unique=True, index=True, comment="관리번호")
    license_date = Column("licenseDate", String(10), comment="인허가일자")
    business_status_name = Column("businessStatusName", String(20), comment="영업상태명")
    closure_date = Column("closureDate", String(10), comment="폐업일자")
    site_area = Column("siteArea", String(20), comment="소재지면적")
    site_zip_code = Column("siteZipCode", String(10), comment="소재지우편번호")
    road_zip_code = Column("roadZipCode", String(10), comment="도로명우편번호")
    business_name = Column("businessName", String(200), comment="사업장명")
    business_type_name = Column("businessTypeName", String(50), comment="업태구분명")
    data_update_type = Column("dataUpdateType", String(10), comment="데이터갱신구분")
    building_ownership_type = Column("buildingOwnershipType", String(20), comment="건물소유구분명")
    above_ground_floor_count = Column("aboveGroundFloorCount", String(10), comment="건물지상층수")
    below_ground_floor_count = Column("belowGroundFloorCount", String(10), comment="건물지하층수")
    male_worker_count = Column("maleWorkerCount", String(10), comment="남성종사자수")
    multi_use_facility_yn = Column("multiUseFacilityYn", String(2), comment="다중이용업소여부")
    data_update_datetime = Column("dataUpdateDatetime", String(20), comment="데이터갱신시점")
    road_address = Column("roadAddress", String(300), comment="도로명주소")
    jibun_address = Column("jibunAddress", String(300), comment="지번주소")
    use_end_above_ground_floor = Column("useEndAboveGroundFloor", String(10), comment="사용끝지상층")
    use_end_below_ground_floor = Column("useEndBelowGroundFloor", String(10), comment="사용끝지하층")
    use_start_above_ground_floor = Column("useStartAboveGroundFloor", String(10), comment="사용시작지상층")
    use_start_below_ground_floor = Column("useStartBelowGroundFloor", String(10), comment="사용시작지하층")
    detailed_business_status_name = Column("detailedBusinessStatusName", String(20), comment="상세영업상태명")
    detailed_business_status_code = Column("detailedBusinessStatusCode", String(10), comment="상세영업상태코드")
    western_room_count = Column("westernRoomCount", String(10), comment="양실수")
    female_worker_count = Column("femaleWorkerCount", String(10), comment="여성종사자수")
    business_status_code = Column("businessStatusCode", String(10), index=True, comment="영업상태코드")
    hygiene_business_type = Column("hygieneBusinessType", String(50), comment="위생업태명")
    conditional_license_start_date = Column("conditionalLicenseStartDate", String(10), comment="조건부허가시작일자")
    conditional_license_reason = Column("conditionalLicenseReason", String(500), comment="조건부허가신고사유")
    conditional_license_end_date = Column("conditionalLicenseEndDate", String(10), comment="조건부허가종료일자")
    phone_number = Column("phoneNumber", String(30), comment="전화번호")
    coord_x = Column("coordX", String(30), comment="좌표정보(X)")
    coord_y = Column("coordY", String(30), comment="좌표정보(Y)")
    korean_room_count = Column("koreanRoomCount", String(10), comment="한실수")
    last_modified_datetime = Column("lastModifiedDatetime", String(20), comment="최종수정시점")


# CSV 원본 컬럼 순서 그대로 (헤더 순서와 1:1 대응, import 스크립트에서 사용)
RAW_COLUMN_ORDER = [
    "local_gov_code", "management_number", "license_date", "business_status_name",
    "closure_date", "site_area", "site_zip_code", "road_zip_code", "business_name",
    "business_type_name", "data_update_type", "building_ownership_type",
    "above_ground_floor_count", "below_ground_floor_count", "male_worker_count",
    "multi_use_facility_yn", "data_update_datetime", "road_address", "jibun_address",
    "use_end_above_ground_floor", "use_end_below_ground_floor",
    "use_start_above_ground_floor", "use_start_below_ground_floor",
    "detailed_business_status_name", "detailed_business_status_code",
    "western_room_count", "female_worker_count", "business_status_code",
    "hygiene_business_type", "conditional_license_start_date",
    "conditional_license_reason", "conditional_license_end_date", "phone_number",
    "coord_x", "coord_y", "korean_room_count", "last_modified_datetime",
]
