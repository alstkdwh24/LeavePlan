import calendar
import json
import os
import uuid
from _pydatetime import timedelta, datetime

from jose import jwt, JWTError
from passlib.context import CryptContext

from config.redis_client import redis_client
PRIVATE_KEY = open(os.getenv("SECRET_PRIVATE_KEY_PATH", "keys/private.pem")).read()
PUBLIC_KEY = open(os.getenv("SECRET_PUBLIC_KEY_PATH", "keys/public.pem")).read()
ALGORITHM = "RS256"
ISSUER = os.getenv("JWT_ISSUER")
AUDIENCE = os.getenv("JWT_AUDIENCE")
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 14

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(member_id: str, role: str) -> str:
    jti = str(uuid.uuid4())
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub" : str(member_id), "role": role, "type": "access", "jti" : jti, "iss": ISSUER, "aud": AUDIENCE,
        "exp": calendar.timegm(expire.utctimetuple())
    }
    token = jwt.encode(payload, PRIVATE_KEY, algorithm=ALGORITHM)

    # 발급된 access token을 Redis에 "활성 토큰"으로 등록 (여기 없으면 서명이 멀쩡해도 무효)
    redis_client.setex(
        f"access:{jti}",
        ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        json.dumps({"member_id": member_id, "role": role}),
    )
    return token

def create_refresh_token(member_id: str) -> tuple[str, datetime]:
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(member_id), "type": "refresh", "jti": str(uuid.uuid4()),
        "iss": ISSUER, "aud": AUDIENCE, "exp": calendar.timegm(expires_at.utctimetuple()),
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm=ALGORITHM), expires_at

def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM], audience=AUDIENCE, issuer=ISSUER)
    except JWTError:
        return None

    jti = payload.get("jti")
    if payload.get("type") == "access":
        # 화이트리스트 체크 — 서명이 멀쩡해도 Redis에 없으면(=로그아웃/폐기됨) 무효
        if not jti or not redis_client.exists(f"access:{jti}"):
            return None

    return payload

def revoke_access_token(jti: str):
    """로그아웃/탈취 신고 시 즉시 무효화 — 키를 지우는 순간 그 토큰은 바로 끝"""
    redis_client.delete(f"access:{jti}")