"""(비활성화) SAM 기반 자동 세그멘테이션 라벨러 래퍼.

현재 파이프라인에서는 SAM 을 사용하지 않으므로 아무 작업도 하지 않는다.
향후 통합 시 구현 가이드:
1. 모델 가중치 로드 (메모리 캐시 / lazy load)
2. 이미지 → 마스크/폴리곤 추론
3. 소형 객체 제거 / 다각형 단순화 / 병합 등 후처리
4. YOLO 세그멘테이션 TXT 혹은 COCO JSON 저장
5. 기존 라벨 존재 시 정책 (skip / overwrite / merge) 적용
"""
from __future__ import annotations
from pathlib import Path
from ..common.logging_utils import get_logger
from ..common.io_utils import list_images, ensure_dir
from .convert import polygon_to_yolo_line, merge_lines

logger = get_logger(__name__)
INTERIM = Path("data/interim")
LABELS = Path("data/labels")


def run(config_path: str | None = None):  # 현재 비활성화된 스텁
    ensure_dir(LABELS)
    imgs = list_images(INTERIM)
    created = 0
    for img in imgs:
        txt = LABELS / (img.stem + ".txt")
        if txt.exists():
            continue
        # 아무 작업도 하지 않고 다음 이미지로 넘어감.
        continue
    logger.info("SAM wrapper produced %d labels", created)
    return {"labels": created}
