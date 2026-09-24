# restcontroller의 실제 엔드포인트들을 모아서 app에 등록하는 조립부.
from fastapi import APIRouter
from restcontroller.generalRestaurantExcelController import router as excel_controller_router

router = APIRouter()
router.include_router(excel_controller_router)
