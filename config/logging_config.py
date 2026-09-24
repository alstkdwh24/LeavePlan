import logging
import os
import datetime

RESET   = "\033[0m"
FAINT   = "\033[2m"
BOLD    = "\033[1m"
GREEN   = "\033[32m"
YELLOW  = "\033[33m"
RED     = "\033[31m"
CYAN    = "\033[36m"
MAGENTA = "\033[35m"

LEVEL_COLORS = {
    "DEBUG":    CYAN   + BOLD,
    "INFO":     GREEN  + BOLD,
    "WARNING":  YELLOW + BOLD,
    "ERROR":    RED    + BOLD,
    "CRITICAL": RED    + BOLD,
}

class SpringBootFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        now       = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        level     = record.levelname
        pid       = os.getpid()
        thread    = record.threadName[:15].center(15)
        logger    = record.name[:36].ljust(36)
        message   = record.getMessage()

        level_color = LEVEL_COLORS.get(level, RESET)
        level_str   = f"{level_color}{level:<5}{RESET}"

        line = (
            f"{FAINT}{now}{RESET}  "
            f"{level_str} "
            f"{MAGENTA}{pid}{RESET} --- "
            f"[{FAINT}{thread}{RESET}] "
            f"{CYAN}{logger}{RESET} : "
            f"{message}"
        )

        # log.exception(...)이나 uvicorn의 "Exception in ASGI application"처럼
        # exc_info가 실린 레코드는 기본 logging.Formatter라면 스택 트레이스를 이어붙여주는데,
        # 이 포매터는 그 로직 없이 message만 반환하고 있어서 트레이스백이 통째로 사라졌었다.
        # (원인 파악이 안 되던 근본 원인 — 여기서 표준 Formatter와 동일하게 붙여준다.)
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            line = line + "\n" + record.exc_text
        if record.stack_info:
            line = line + "\n" + self.formatStack(record.stack_info)

        return line


# 로그 파일 경로 — PyCharm 콘솔을 캡처해서 옮겨 적는 대신, 파일을 직접 열어서 확인할 수 있도록.
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE_PATH = os.path.join(LOG_DIR, "app.log")


class PlainSpringBootFormatter(SpringBootFormatter):
    """SpringBootFormatter와 내용은 같지만 ANSI 색상 코드를 안 넣는다 — 색상 코드가 낀 채로
    파일에 저장되면 텍스트 에디터/grep에서 알아보기 힘들어지기 때문에 파일 핸들러 전용으로 쓴다."""

    def format(self, record: logging.LogRecord) -> str:
        now    = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        level  = record.levelname
        pid    = os.getpid()
        thread = record.threadName[:15].center(15)
        logger = record.name[:36].ljust(36)
        message = record.getMessage()

        line = f"{now}  {level:<5} {pid} --- [{thread}] {logger} : {message}"

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            line = line + "\n" + record.exc_text
        if record.stack_info:
            line = line + "\n" + self.formatStack(record.stack_info)

        return line


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "spring": {
            "()": SpringBootFormatter,
        },
        "plain": {
            "()": PlainSpringBootFormatter,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "spring",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.FileHandler",
            "formatter": "plain",
            "filename": LOG_FILE_PATH,
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "uvicorn":          {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        "uvicorn.error":    {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        "uvicorn.access":   {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        "fastapi":          {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
}
