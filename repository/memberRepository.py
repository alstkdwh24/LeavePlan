from sqlalchemy.orm import Session
from models.members import Members
from models.role import Role
from models.userCredentials import UserCredentials
from models.authProviders import AuthProviders


class MemberRepository:
    def __init__(self, db: Session):
        self.db = db

    # 로그인 아이디로 회원 한명을 찾는 기능
    def get_by_login_id(self, member_id: str) -> Members | None:
        return self.db.query(Members).filter(Members.member_id == member_id).first()

    # pk 로 회원을 찾습니다. JWT의 sub에 이 pk가 들어가 있어서, 토큰 검증 후 토큰 주인이 누구인지 찾을 때 씁니다.
    def get_by_id(self, id: str) -> Members | None:
        return self.db.query(Members).get(id)

    # 구글 로그인 용 AuthProviders 테이블에서 구글이 주는 고유로 먼저 레코드를 찾고, 그 연동 레코드에 연결된 member를 반환
    def get_by_provider_id(self, provider_id: str) -> Members | None:
        ap = self.db.query(AuthProviders).filter(AuthProviders.provider_id == provider_id).first()
        return ap.member if ap else None

    # 일반 회원가입 처리입나다.
    # self는 객체를 가르기는 참조
    def create(self, member_id: str, name: str, hashed_pw: str, phone: int | None, gender: str | None = None,
               age: int | None = None) -> Members:
        member = Members(member_id=member_id, name=name, phone=phone, role=Role.USER, gender=gender, age=age)
        self.db.add(member)
        # 일단 먼저 DB에 일단 보내서 SQL을 실행시키는것
        self.db.flush()

        self.db.add(UserCredentials(member_id=member.id, user_pw=hashed_pw))
        self.db.commit()
        self.db.refresh(member)
        return member

# 구글로 처음 로그인한 사용자를 위한 가입 처리입니다.C:\courage3\pythonProject\portfolio_project\backend\LeavePlnner
    def create_google_member(self, email: str, name: str, provider_id: int | None) -> Members:
        member = Members(member_id=email, name=name, role=Role.USER)
        self.db.add(member)
        self.db.flush()
        self.db.add(AuthProviders(member_id=member.id, provider="google", provider_id=provider_id))
        self.db.commit()
        self.db.refresh(member)
        return member
