# restcontroller의 실제 엔드포인트들을 모아서 app에 등록하는 조립부.
from fastapi import APIRouter
from restcontroller.adminController import router as admin_controller_router

router = APIRouter()
router.include_router(admin_controller_router)
