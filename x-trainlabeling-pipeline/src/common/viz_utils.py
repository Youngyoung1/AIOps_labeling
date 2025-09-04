"""경량 시각화(placeholder) 유틸 함수 모음."""
from __future__ import annotations
from pathlib import Path
from typing import Sequence
import cv2

def overlay_masks(image_path: str | Path, masks: Sequence, colors=None):  # TODO: 실제 마스크 오버레이 구현
    img = cv2.imread(str(image_path))
    if img is None:
        return None
    # TODO: 마스크를 이미지 위에 색상으로 덧씌우는 로직 구현 예정
    return img
