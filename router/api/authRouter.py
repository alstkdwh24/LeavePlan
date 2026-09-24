# restcontroller의 실제 엔드포인트들을 모아서 app에 등록하는 조립부.
# 이미 restcontroller와 router 폴더를 나눠두신 구조라, 여기선 include만 담당합니다.
from fastapi import APIRouter
from restcontroller.authController import router as auth_controller_router

router = APIRouter()
router.include_router(auth_controller_router)