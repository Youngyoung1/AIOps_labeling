"""로깅 설정 유틸리티 모듈."""
from __future__ import annotations
import logging
import sys

_DEF_FORMAT = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"  # 기본 로그 포맷

def setup_logging(level: str = "INFO") -> None:
    if logging.getLogger().handlers:
        return
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=_DEF_FORMAT,
        stream=sys.stdout,
    )

def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
