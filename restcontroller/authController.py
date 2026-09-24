from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from schemas.auth import RegisterRequest, MemberOut, TokenPair, RefreshRequest
from repository.memberRepository import MemberRepository
from repository.tokenRepository import TokenRepository
from service.authService import AuthService
from config.oauth import oauth
import os

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(MemberRepository(db), TokenRepository(db))


def get_current_member(token: str = Depends(oauth2_scheme), service: AuthService = Depends(get_auth_service)):
    return service.get_current_member(token)

# MemberOut은 보통 회원 정보를 응답으로 내보낼때 쓰는 Pydantic 응답 스키마 이름입니다.
@router.post("/register", response_model=MemberOut, status_code=201)
def register(payload: RegisterRequest, service: AuthService = Depends(get_auth_service)):
    return service.register(payload)

@router.post("/login", response_model=TokenPair)
def login(form: OAuth2PasswordRequestForm = Depends(), service: AuthService = Depends(get_auth_service)):
    return service.login(form.username, form.password)

@router.post("/refresh",response_model=TokenPair)
def refresh(payload: RefreshRequest, service: AuthService = Depends(get_auth_service)):
    return service.refresh(payload.refresh_token)


@router.post("/logout")
def logout(payload: RefreshRequest, service: AuthService = Depends(get_auth_service)):
    service.logout(payload.refresh_token)
    return {"message": "Logout successful"}

@router.get("/google/login")
async def google_login(request: Request):
    return await oauth.google.authorize_redirect(request, os.getenv("GOOGLE_REDIRECT_URI"))

@router.get("/google/callback")
async def google_callback(request: Request, service: AuthService = Depends(get_auth_service)):
    return RedirectResponse(await service.handle_google_callback(request))

@router.get("/me", response_model=MemberOut)
def me(member=Depends(get_current_member)):
    return member