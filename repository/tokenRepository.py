import hashlib
from datetime import datetime

from sqlalchemy.orm import Session

from models.refreshToken import RefreshTokenEntity


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class TokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, token: str, member_id: str, family_id: str, expires_at: datetime):
        entity = RefreshTokenEntity(
            token_hash=hash_token(token), member_id=member_id,
            family_id=family_id, expires_at=expires_at
        )
        self.db.add(entity)
        self.db.commit()

    def find(self, token: str) -> RefreshTokenEntity | None:
        # self.db는 SQLAlchemy Session 객체로 보이고, RefreshTokenEntity 테이블을 대상으로 쿼리를 만듭니다.
        # hash_token(token)부분이 db에 저장되 해시값을 해시한뒤 해시값으로 where token_hash = ... 조건을 걸어 비교합니다.
        # .first()로 조건에 맞는 척 번째 행 하나만 가져오고, 없으면 None을 반환합니다.
        return self.db.query(RefreshTokenEntity).filter(
            RefreshTokenEntity.token_hash == hash_token(token)
        ).first()

    # RefreshTokenEntity의 used 필드를 True 로 설정하고, 데이터베이스에 해당 변경 사항을 저장합니다.
    def mark_used(self, entity: RefreshTokenEntity):
        entity.used = True
        self.db.commit()

    # self: 이 메서드는 클래스 내부의 메서드이므로 , self는 클래스 인스턴스를 참조
    # family_id: str:
    # family_id는 문자열로, 리프레시 토큰을 특정 그룹 또는 "패밀리"로 묶는 기준이 되는 값입니다.
    # 그러니까 family_id는 여러 장치의 토큰을 하나로 묶는 것이라고 생각을 하면 됩니다.
    # 그리고 이 메서드는 family_id에 해당하는 모든 토큰을 한번에 "무효화"하는 역할을 합니다.
    # self.db 는 SQLAlchemy ORM 세션 객체 이다. 그러니까 데이터베이스와의 연결을 관리한다.
    # query(RefreshTokenEntity) 데이터베이스 내 RefreshTokenEntity 테이블을 조회할 준비를 합니다.
    # self.db.commit()
    # 데이터 베이스에 변경 사항을 저장합니다.
    def revoke_family(self, family_id: str):
        self.db.query(RefreshTokenEntity).filter(RefreshTokenEntity.family_id == family_id).update({"revoked": True})
        self.db.commit()
