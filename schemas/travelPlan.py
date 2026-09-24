from pydantic import BaseModel


# Gemini 구조화 출력(response_schema)용 - 채팅 카드 + 'AI 추천 결과' 페이지에서 고를 후보들
class PlanStay(BaseModel):
    name: str   # 숙소 이름
    tag: str    # 특징 (예: "오션뷰·조용함")
    price: str  # 1박 가격 (예: "142,000원")


class PlanTransport(BaseModel):
    name: str   # "렌터카"
    desc: str   # "공항 픽업 · 24시간"
    price: str  # "65,000원/일"


class PlanCafe(BaseModel):
    name: str   # "애월 오션뷰 카페"
    tag: str    # "오션뷰 · 루프탑"
    hours: str  # "09:00~21:00"


class PlanSpot(BaseModel):
    name: str      # "협재해수욕장"
    tag: str       # "해변 · 스노클링"
    distance: str  # "숙소에서 도보 5분"


class PlanItem(BaseModel):
    time: str      # "14:00"
    activity: str  # "애월 오션뷰 카페"


class PlanDay(BaseModel):
    day: int
    theme: str  # "도착", "탐방", "여유 · 출발"
    items: list[PlanItem]


class TravelPlan(BaseModel):
    summary: str  # 첫 말풍선 문구 (예: "오션뷰 숙소와 카페 투어 중심으로 짜봤어요 👋")
    stays: list[PlanStay]            # 후보 5개 - 첫 번째가 가장 추천
    transports: list[PlanTransport]  # 후보 4개 - 첫 번째가 가장 추천
    cafes: list[PlanCafe]            # 후보 5개
    spots: list[PlanSpot]            # 후보 5개
    days: list[PlanDay]              # 추천 조합(각 목록의 첫 번째)으로 짠 일정


class ScheduleResult(BaseModel):
    days: list[PlanDay]


# 'AI 추천 결과' 페이지에서 고른 조합으로 일정을 다시 짜는 요청
class StaySelection(BaseModel):
    name: str
    tag: str
    price: str
    nights: int


class ScheduleRequest(BaseModel):
    destination: str
    duration: str  # "2박3일"
    stays: list[StaySelection]
    transport: PlanTransport
    cafes: list[PlanCafe]
    spots: list[PlanSpot]
