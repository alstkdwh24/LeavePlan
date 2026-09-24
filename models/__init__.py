# DB에 반영할 모든 모델을 등록한다 (Alembic / create_all 이 Base.metadata 로 읽어감)
from models.members import Members
from models.userCredentials import UserCredentials
from models.authProviders import AuthProviders
from models.refreshToken import RefreshTokenEntity

from models.trip import Trip
from models.dailyPlan import DailyPlan
from models.planItem import PlanItem
from models.conversation import Conversation
from models.message import Message

from models.stay import Stay
from models.stay_listing import StayListing
from models.room_type import RoomType
from models.cafe_model import Cafe
from models.cafe_listing import CafeListing
from models.cafe_menu_item import CafeMenuItem
from models.restaurant import Restaurant
from models.restaurant_listing import RestaurantListing
from models.restaurant_menu_item import RestaurantMenuItem
from models.tourist_spot import TouristSpot
from models.place import Place

from models.booking import Booking
from models.payment import Payment
from models.card import Card
from models.wishlist import Wishlist
from models.review import Review
from models.notifications import Notifications

# 삭제 예정이라 등록하지 않음: facility, aiRecommendation, models(빈 파일)