import os
from datetime import datetime

from google import genai
from google.genai import types
from sqlalchemy.orm import Session

from config.config import GEMINI_API_KEY
from models.message import Message
from models.messageType import MessageType
from schemas.MessageRequest import TripConditions
from schemas.travelPlan import TravelPlan, ScheduleRequest, ScheduleResult

_MODEL ="gemini-3.5-flash-lite"
_SYSTEM_PROMPT = "너는 국내 여행 일정을 짜주는 플래너야. 숙소, 일정, 교통을 친절하고 간결하게 한국어로 안내해줘."
_client: genai.Client | None = None

def _get_client() -> genai.Client:
    #요청마다 새로 만들지 않고 한 번만 만 들어서 재사용
    # 전역변수에 값을 넣겠다.
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


# 조건이 있을 때 Gemini에게 주는 추가 지시 - 카드로 그릴 JSON(TravelPlan) 형식에 맞춰 채우게 한다
# 후보는 'AI 추천 결과' 페이지에서 사용자가 골라서 바꿀 수 있게 여러 개씩 받는다
_PLAN_INSTRUCTION = ("summary에는 일정을 소개하는 한 문장(이모지 하나 포함)을 넣어줘. "
                     "후보 목록은 조건에 가장 잘 맞는 순서로, 첫 번째가 가장 추천하는 것이야. "
                     "stays에는 숙소 후보 5개(tag는 '오션뷰 · 조용함'처럼 특징 2개, price는 1박 가격 '142,000원' 형식), "
                     "transports에는 여행지 안에서 쓸 교통 후보 4개(desc는 '공항 픽업 · 24시간'처럼 짧게, "
                     "price는 '65,000원/일', '기본 4,800원~' 형식), "
                     "cafes에는 카페 후보 5개(hours는 '09:00~21:00' 형식), "
                     "spots에는 관광지 후보 5개(distance는 '숙소에서 도보 5분', '차로 40분'처럼 첫 번째 숙소 기준), "
                     "days에는 각 후보 목록의 첫 번째 항목으로 짠 날짜별 일정을 'HH:MM' 시간순으로 넣고 "
                     "theme에는 '도착', '탐방', '여유 · 출발'처럼 그날의 성격을 짧게 적어줘. "
                     "교통 수단과 카페·관광지 취향을 일정에 반영해줘.")


def _schedule_prompt(req: ScheduleRequest) -> str:
    stays = ", ".join(f"{s.name}({s.nights}박)" for s in req.stays)
    cafes = ", ".join(c.name for c in req.cafes)
    spots = ", ".join(s.name for s in req.spots)
    return (f"{req.destination} {req.duration} 여행 일정을 짜줘.\n"
            f"- 숙소(적힌 순서대로 묵음): {stays}\n- 교통: {req.transport.name}\n"
            f"- 꼭 들를 카페: {cafes}\n- 꼭 갈 관광지: {spots}\n"
            "여기 적힌 숙소·카페·관광지를 모두 일정에 넣고, 체크인/체크아웃과 식사도 포함해서 "
            "날짜별로 'HH:MM' 시간순으로 짜줘. theme에는 '도착', '탐방', '여유 · 출발'처럼 그날의 성격을 짧게 적어줘.")


class LLMService:
    def __init__(self, db: Session):
        self.db = db

    def answerSave(self, tripId: str | None, memberId: str | None, text: str, origin: str | None = None,
                   conditions: TripConditions | None = None) -> dict:
        print(1)

        # 1. 사용자 메시지 저장
        user_msg = Message(trip_id=tripId, member_id=memberId, content=text,
                           type=MessageType.USER, created_at=datetime.now())
        self.db.add(user_msg)

        # 2. LLM 답변 (일단 고정 문구, 나중에 Gemini 호출로 교체)

        # 출발지가 있으면 system prompt에 추가 - 출발지 기준으로 이동 시간/교통을 고려하게 함
        system_prompt = _SYSTEM_PROMPT
        if origin:
            system_prompt += (f"\n사용자의 출발지는 '{origin}'이야. 일정은 이 출발지에서 출발하는 것으로 짜고, "
                              f"여행지까지의 이동 수단과 대략적인 소요 시간도 함께 안내해줘.")

        plan: dict | None = None
        try:
            if conditions:
                # 여행 조건이 있으면 숙소 카드 / DAY 일정 카드로 그릴 수 있게 JSON(TravelPlan)으로 받는다
                # (text에는 프론트가 모달에서 고른 조건을 이미 붙여서 보낸다)
                response = _get_client().models.generate_content(model=_MODEL,
                    contents=f"{text}\n\n{_PLAN_INSTRUCTION}",
                    config=types.GenerateContentConfig(system_instruction=system_prompt,
                                                       response_mime_type="application/json",
                                                       response_schema=TravelPlan),)
                plan = TravelPlan.model_validate_json(response.text).model_dump()
                answer = response.text  # DB에는 JSON 원문 그대로 저장
            else:
                response = _get_client().models.generate_content(model=_MODEL, contents=text,
                    config=types.GenerateContentConfig(system_instruction=system_prompt),)
                answer = response.text
            print(answer)
        except Exception as e:
            print("제미나이 호출 실패:", e)
            answer = "지금은 답변이 불가능해요. 잠시후 다시 시도해 주세요."
            plan = None

        # 3. LLM 답변 저장
        llm_msg = Message(trip_id=tripId, member_id=memberId, content=answer,
                          type=MessageType.LLM, created_at=datetime.now())
        self.db.add(llm_msg)
        self.db.commit()

        # plan이 있으면 프론트는 카드로, 없으면 answer를 말풍선으로 보여준다
        return {"id": user_msg.id, "text": text, "answer": plan["summary"] if plan else answer, "plan": plan}

    def schedule(self, req: ScheduleRequest) -> dict:
        # 'AI 추천 결과' 페이지에서 고른 숙소·교통·카페·관광지로 날짜별 일정을 다시 짠다
        response = _get_client().models.generate_content(model=_MODEL, contents=_schedule_prompt(req),
            config=types.GenerateContentConfig(system_instruction=_SYSTEM_PROMPT,
                                               response_mime_type="application/json",
                                               response_schema=ScheduleResult),)
        return ScheduleResult.model_validate_json(response.text).model_dump()
