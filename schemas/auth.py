from pydantic import BaseModel


class RegisterRequest(BaseModel):


    member_id: str
    name: str
    password: str
    phone: str | None = None
    gender: str | None = None
    age: int | None = None

class MemberOut(BaseModel):
    id: str
    member_id: str
    name: str
    role: str
    phone: str | None = None
    gender: str | None = None
    age: int | None = None
    class Config:
        from_attributes = True

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str