from fastapi import APIRouter

from service.generalRestaurantExcelService import import_excel

router = APIRouter(prefix="/excel", tags=["excel"])


@router.post("/import")
def import_excel_endpoint():
    count = import_excel()
    return {"message": f"{count}건 저장 완료"}
