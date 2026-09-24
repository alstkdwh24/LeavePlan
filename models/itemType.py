from enum import Enum as PyEnum


class ItemType(PyEnum):
    STAY = "STAY"
    CAFE = "CAFE"
    PLACE = "PLACE"
    RESTAURANT = "RESTAURANT"


PlaceType = ItemType  # PLACETYPE == ITEMTYPE 동일값이라 재사용