import os
import uuid
from datetime import datetime

from fastapi import HTTPException
from starlette import status
from starlette.requests import Request

from config.oauth import oauth
from config.security import hash_password, verify_password, revoke_access_token, create_refresh_token, decode_token, \
    create_access_token
from repository.memberRepository import MemberRepository
from repository.tokenRepository import TokenRepository
from schemas.auth import RegisterRequest, TokenPair


class AuthService:
    def __init__(self, member_repo: MemberRepository, token_repo: TokenRepository):
        self.member_repo = member_repo
        self.token_repo = token_repo

    def register(self, payload: RegisterRequest):
        if self.member_repo.get_by_login_id(payload.member_id):
            raise HTTPException(400, "이미 존재하는 아이디입니다.")
        return self.member_repo.create(payload.member_id, payload.name, hash_password(payload.password), payload.phone, payload.gender, payload.age)

    # 이 메서드의 목적 주어진 member_id 회원아이디와 password를 이용해 사용자를 인증한 후, 해당 사용자에게 토큰을 발급합니다.
    # 인증 실패 시 401 Unaunthorized HTTP 상태 코드를 반환하며 예외를 발생시킵니다.

    def login(self, member_id: str, password: str) -> TokenPair:
        member = self.member_repo.get_by_login_id(member_id)
        # 비밀번호 검증 사용자 존재 여부 확인 not member 사용자 자격 증명 확인 not member.credentials
        # 비밀번호 검증 not verify_password(password, member.credentials.user_pw)
        # 사용자가 입력한 비밀번호와 데이터 베이스에 저장된 해시화된 비밀번호를 비교합니다.
        if not member or not member.credentials or not verify_password(password, member.credentials.user_pw):
            # raise는 예외처리
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "아이디 또는 비밀번호가 틀렸습니다.")
        # 토큰 발급
        return self._issue_tokens(member.id, member.role.value, str(uuid.uuid4()))

    def refresh(self, refresh_token: str) -> TokenPair:
        stored = self.token_repo.find(refresh_token)
        if not stored or stored.expires_at < datetime.utcnow():
            raise HTTPException(401, "토큰이 유효하지 않습니다.")
        if stored.revoked or stored.used:
            self.token_repo.revoke_family(stored.family_id)
            raise HTTPException(401, "토큰 재사용이 감지되서 세션이 종료되었습니다. 다시 로그인 해주세요")


        self.token_repo.mark_used(stored)
        member = self.member_repo.get_by_id(stored.member_id)
        return self._issue_tokens(member.id, member.role.value, stored.family_id)

    def logout(self, refresh_token: str, access_jti: str | None = None ):
        stored = self.token_repo.find(refresh_token)
        if stored:
            self.token_repo.revoke_family(stored.family_id)
        # 토큰의 고유 식별자 access_jti
        if access_jti:
            revoke_access_token(access_jti)


    async def handle_google_callback(self, request: Request) -> str:
        token = await oauth.google.authorize_access_token(request)
        userinfo = token.get("userinfo")
        if not userinfo:
            raise HTTPException(400, "구글 사용자의 정보를 가져오지 못했습니다.")
    # 이메일이 아니라 provider_id로 조회
        member = self.member_repo.get_by_provider_id(userinfo["sub"])
        if not member:
            member = self.member_repo.create_google_member(userinfo["email"], userinfo.get("name", "구글사용자"), userinfo["sub"])

        tokens = self._issue_tokens(member.id, member.role.value, str(uuid.uuid4()))
        frontend = os.getenv("FRONTEND_URL")
        return f"{frontend}/login?token={tokens.access_token}&refresh_token={tokens.refresh_token}"

    def get_current_member(self, token:str):
        data = decode_token(token)
        if not data or data.get("type") != "access":
            raise HTTPException(401, "인증되지 않았습니다.")
        member = self.member_repo.get_by_id(data.get("sub"))
        if not member:
            raise HTTPException(401, "사용자를 찾을 수 없습니다.")
        return member

    def _issue_tokens(self, member_id:int, role:str, family_id:str) -> TokenPair:
        access_token = create_access_token(member_id, role)
        refresh_token, expires_at = create_refresh_token(member_id)
        self.token_repo.save(refresh_token, member_id, family_id, expires_at)
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    # 딕셔너리 dict는 Java의 Map과 거의 같은 개념입니다.
    # 키로 값을 찾아가는 자료구조