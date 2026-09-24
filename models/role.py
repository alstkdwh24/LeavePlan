from enum import Enum as PyEnum


from sqlalchemy.orm import declarative_base
Base = declarative_base()

class Role(PyEnum):
    USER = "USER"
    ADMIN = "ADMIN"
    GUEST = "GUEST"