from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from google.genai import errors as genai_errors
from config.database import get_db
from schemas.MessageRequest import MessageRequest
from schemas.travelPlan import ScheduleRequest
from service.llmService import LLMService

router = APIRouter(prefix="/api", tags=["message"])


def get_llm_service(db: Session = Depends(get_db)) -> LLMService:
    return LLMService(db)

def _raise_llm_error(e: Exception, fallback: str):
    if isinstance(e, genai_errors.ClientError) and e.code == 429:
        raise HTTPException(status_code=429, detail="AI 사용량 한도를 초과했어요. 잠시 후 다시 시도해 주세요.")
    print(f"{fallback}: {e}")
    raise HTTPException(status_code=502, detail=fallback) # 실제 에러 내용을 보여주는 것이다. api서버에서 내려오는
@router.post("/messages")
def messages(request: MessageRequest, service: LLMService = Depends(get_llm_service)):
    # conversationId가 아직 프론트 더미값('jeju' 등)이라 Trip.id(FK)와 맞지 않으므로 tripId는 None으로 저장
    return service.answerSave(tripId=None, memberId=None, text=request.text, origin=request.origin,
                              conditions=request.conditions)


@router.post("/messages/schedule")
def schedule(request: ScheduleRequest, service: LLMService = Depends(get_llm_service)):
    # 'AI 추천 결과' 페이지의 '일정 확정하기' - 고른 조합으로 날짜별 일정을 다시 짠다
    try:
        return service.schedule(request)
    except Exception as e:
        print("일정 생성 실패:", e)
        raise HTTPException(status_code=502, detail="일정을 만들지 못했어요")
