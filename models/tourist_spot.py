import uuid

from sqlalchemy import Column, Uuid, String, Text

from config.database import Base


class TouristSpot(Base):
    """공공데이터포털 '전국 관광지 정보 표준데이터' 원본을 가공 없이 그대로 담는 staging 테이블.
    실제 서비스에서 쓰는 관광지 / 장소 목록은 models/place.py의 Place를 따로 참고."""

    __tablename__ = "TouristSpot"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    spot_name = Column("spotName", String(200), comment="관광지명")
    spot_type = Column("spotType", String(50), comment="관광지구분")
    road_address = Column("roadAddress", String(300), comment="소재지도로명주소")
    jibun_address = Column("jibunAddress", String(300), comment="소재지지번주소")
    latitude = Column("latitude", String(30), comment="위도")
    longitude = Column("longitude", String(30), comment="경도")
    area = Column("area", String(30), comment="면적")
    public_facility_info = Column("publicFacilityInfo", String(500), comment="공공편익시설정보")
    lodging_facility_info = Column("lodgingFacilityInfo", String(500), comment="숙박시설정보")
    sports_facility_info = Column("sportsFacilityInfo", String(500), comment="운동및오락시설정보")
    culture_facility_info = Column("cultureFacilityInfo", String(500), comment="휴양및문화시설정보")
    hospitality_facility_info = Column("hospitalityFacilityInfo", String(500), comment="접객시설정보")
    support_facility_info = Column("supportFacilityInfo", String(500), comment="지원시설정보")
    designation_date = Column("designationDate", String(10), comment="지정일자")
    capacity = Column("capacity", String(20), comment="수용인원수")
    parking_capacity = Column("parkingCapacity", String(20), comment="주차가능수")
    description = Column("description", Text, comment="관광지소개")
    management_org_phone = Column("managementOrgPhone", String(30), comment="관리기관전화번호")
    management_org_name = Column("managementOrgName", String(100), comment="관리기관명")
    data_reference_date = Column("dataReferenceDate", String(10), comment="데이터기준일자")
    provider_org_code = Column("providerOrgCode", String(20), comment="제공기관코드")
    provider_org_name = Column("providerOrgName", String(100), comment="제공기관명")


# csv 원본 컬럼 순서 그대로 (헤더 순서와 1:1 대응, import 스크립트에서 사용)
RAW_COLUMN_ORDER = [
    "spot_name", "spot_type", "road_address", "jibun_address", "latitude", "longitude",
    "area", "public_facility_info", "lodging_facility_info", "sports_facility_info",
    "culture_facility_info", "hospitality_facility_info", "support_facility_info",
    "designation_date", "capacity", "parking_capacity", "description",
    "management_org_phone", "management_org_name", "data_reference_date",
    "provider_org_code", "provider_org_name",
]
