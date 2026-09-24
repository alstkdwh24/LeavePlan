import uuid

from sqlalchemy import Column, String, Uuid

from config.database import Base


class Cafe(Base):
    """공공데이터포털 '전국 카페 표준데이터' 원본을 가공 없이 그대로 담는 테이블.
    기존에 있던 프로덕션용 Cafe(가격/평점/이미지 등)는 삭제하고 이 공공데이터 버전으로 대체함."""

    __tablename__ = "Cafe"

    id = Column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))

    business_name = Column("businessName", String(200), comment="사업장명")
    sido_name = Column("sidoName", String(20), comment="시도명")
    sigungu_name = Column("sigunguName", String(20), comment="시군구명")
    road_address = Column("roadAddress", String(300), comment="소재지도로명주소")
    jibun_address = Column("jibunAddress", String(300), comment="소재지지번주소")
    latitude = Column("latitude", String(30), comment="위도")
    longitude = Column("longitude", String(30), comment="경도")
    business_area = Column("businessArea", String(30), comment="사업장면적")
    phone_number = Column("phoneNumber", String(30), comment="전화번호")
    management_org_name = Column("managementOrgName", String(100), comment="관리기관명")
    management_org_phone = Column("managementOrgPhone", String(30), comment="관리기관전화번호")
    data_reference_date = Column("dataReferenceDate", String(10), comment="데이터기준일자")
    provider_org_code = Column("providerOrgCode", String(20), comment="제공기관코드")
    provider_org_name = Column("providerOrgName", String(100), comment="제공기관명")


# CSV 원본 컬럼 순서 그대로 (헤더 순서와 1:1 대응, import 스크립트에서 사용)
RAW_COLUMN_ORDER = [
    "business_name", "sido_name", "sigungu_name", "road_address", "jibun_address",
    "latitude", "longitude", "business_area", "phone_number", "management_org_name",
    "management_org_phone", "data_reference_date", "provider_org_code", "provider_org_name",
]