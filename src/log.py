import logging
import uvicorn
import os
import sys
from src.config import settings

LOG_DIR = settings.LOG_DIR
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "unified": {
            "()": uvicorn.logging.DefaultFormatter,
            "format": "%(asctime)s | %(name)-18s | %(levelname)-5s | %(message)s",
            "use_colors": False,
        },
    },
    "handlers": {
        "console": {
            "class": logging.StreamHandler,
            "formatter": "unified",
            "stream": sys.stdout,
        },
        "file": {
            "class": logging.handlers.RotatingFileHandler,
            "formatter": "unified",
            "filename": f"{LOG_DIR}/app.log",
            "mode": "a",
            "encoding": "utf-8",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
        },
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["console", "file"],
            "level": settings.LOG_LEVEL,
            "propagate": False,
        },
        "watchfiles": {
            "handlers": ["console"],
            "level": settings.LOG_LEVEL,
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": settings.LOG_LEVEL,
    },
}
