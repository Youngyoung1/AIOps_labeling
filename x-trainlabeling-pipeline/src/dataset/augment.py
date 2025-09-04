"""No-op augmentation module (disabled).

구성 파일(augmentation.enabled)이 true 로 변경되면 실제 증강 로직을 다시 구현하거나
이전 버전 히스토리를 참고하여 복원할 수 있습니다.
"""
from __future__ import annotations

from ..common.logging_utils import get_logger

logger = get_logger(__name__)


def run(config_path: str | None = None):  # noqa: D401
    logger.info("Augmentation disabled (no-op)")
    return {"augmented": 0, "disabled": True}

