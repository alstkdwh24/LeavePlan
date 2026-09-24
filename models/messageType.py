from enum import Enum as PyEnum


class MessageType(PyEnum):
    USER = "USER"
    LLM = "LLM"