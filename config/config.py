import os
from dotenv import load_dotenv

load_dotenv()

PRIVATE_KEY = open(os.getenv("SECRET_PRIVATE_KEY_PATH")).read()
PUBLIC_KEY = open(os.getenv("SECRET_PUBLIC_KEY_PATH")).read()

JWT_ISSUER = os.getenv("JWT_ISSUER")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE")
ALGORITHM = "RS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 14

SESSION_SECRET = os.getenv("SESSION_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL")
REDIS_URL = os.getenv("REDIS_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
