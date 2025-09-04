"""Conversion helpers: polygon mask -> YOLO segmentation txt format.

YOLOv8 segmentation txt 한 줄 형식:
class_id x1 y1 x2 y2 ...  (좌표는 0~1 정규화, 다각형 시계/반시계 허용)

여기서는 간단히 입력 polygon ([(x,y), ...])을 이미지 크기(width,height)로 정규화하여 라인 문자열 생성.
추후: mask -> polygon(external contour) 추출, 홀 처리 등 확장 가능.
"""
from __future__ import annotations
from typing import Sequence, Tuple


def polygon_to_yolo_line(cls_id: int, polygon: Sequence[Tuple[float, float]], width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        raise ValueError("Invalid image size")
    norm_coords = []
    for x, y in polygon:
        nx = min(max(x / width, 0.0), 1.0)
        ny = min(max(y / height, 0.0), 1.0)
        norm_coords.extend([f"{nx:.6f}", f"{ny:.6f}"])
    return f"{cls_id} " + " ".join(norm_coords)


def merge_lines(lines: list[str]) -> str:
    return "\n".join(lines) + ("\n" if lines else "")


__all__ = ["polygon_to_yolo_line", "merge_lines"]