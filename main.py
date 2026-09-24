import logging.config

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
import os

from config.logging_config import LOGGING_CONFIG

# uvicorn이 어떤 방식으로 실행되든(PyCharm FastAPI 실행 설정, CLI --reload 등)
# 여기서 강제로 Spring Boot 스타일 로그 포맷을 적용한다.
# --log-config CLI 옵션에 의존하지 않으므로 실행 방식과 무관하게 항상 적용됨.
logging.config.dictConfig(LOGGING_CONFIG)

from config.database import Base, engine
from router.api.authRouter import router as auth_router
from router.api.admin_router import router as admin_router
from router.api.excel_router import router as excel_router
from router.api.listing_router import router as listing_router
from router.api.llmRouter import router as llm_router
from router.api.locationRouter import router as location_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="LeavePlanner Security")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET"))  # noqa
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(excel_router)
app.include_router(listing_router)
app.include_router(llm_router)
app.include_router(location_router)