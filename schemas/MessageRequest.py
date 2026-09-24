from pydantic import BaseModel


class TripConditions(BaseModel):
    # 프론트의 여행 조건 모달에서 고른 값 - 사용자가 채팅에 이미 적은 항목은 None
    duration: str | None = None        # 예: "2박 3일"
    stayType: str | None = None        # 예: "펜션·독채"
    stayTheme: str | None = None       # 예: "오션뷰"
    cafeMood: str | None = None        # 예: "루프탑 오션뷰"
    spotType: str | None = None        # 예: "해변 드라이브"
    toDestination: str | None = None   # 출발지 → 여행지 교통 (예: "비행기")
    localTransport: str | None = None  # 현지 이동 수단 (예: "렌터카")


class MessageRequest(BaseModel):
    conversationId: str
    text: str
    origin: str | None = None  # 출발지 주소 (예: "인천 부평구 부평문화로 87") - 위치 권한이 없으면 None
    conditions: TripConditions | None = None  # 있으면 일정을 카드용 JSON(plan)으로 받아온다
