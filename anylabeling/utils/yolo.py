"""YOLO 형식(.txt) <-> 내부 Shape 변환 유틸.

YOLO txt 한 줄 형식:
 <class_id> <x_center> <y_center> <width> <height>
 - 모든 좌표는 0~1 정규화.
"""
from __future__ import annotations
from pathlib import Path
from typing import List, Sequence


def load_classes(classes_path: str | Path) -> List[str]:
    p = Path(classes_path)
    if not p.exists():
        return []
    lines = [l.strip() for l in p.read_text(encoding="utf-8").splitlines()]
    return [l for l in lines if l]


def parse_yolo_line(line: str):
    parts = line.strip().split()
    if len(parts) != 5:
        raise ValueError("Invalid YOLO line: " + line)
    cls = int(parts[0])
    x, y, w, h = map(float, parts[1:])
    return cls, x, y, w, h


def load_yolo_annotations(txt_path: str | Path, width: int, height: int, classes: Sequence[str]):
    """YOLO txt -> 내부용 bbox 리스트 반환.

    반환: [{label, x1,y1,x2,y2}]
    """
    p = Path(txt_path)
    if not p.exists():
        return []
    results = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            cls, x, y, w, h = parse_yolo_line(line)
        except Exception:
            continue
        x_c = x * width
        y_c = y * height
        bw = w * width
        bh = h * height
        x1 = max(0.0, x_c - bw / 2)
        y1 = max(0.0, y_c - bh / 2)
        x2 = min(float(width), x_c + bw / 2)
        y2 = min(float(height), y_c + bh / 2)
        label = classes[cls] if 0 <= cls < len(classes) else f"cls_{cls}"
        results.append({
            "label": label,
            "x1": x1, "y1": y1,
            "x2": x2, "y2": y2,
        })
    return results


def save_yolo_annotations(txt_path: str | Path, boxes: Sequence[dict], width: int, height: int, classes: Sequence[str]):
    """내부 bbox 딕셔너리 -> YOLO txt 저장.
    boxes: [{'label': str, 'x1':..,'y1':..,'x2':..,'y2':..}]
    """
    cls_to_idx = {c: i for i, c in enumerate(classes)}
    lines = []
    for b in boxes:
        x1, y1, x2, y2 = b['x1'], b['y1'], b['x2'], b['y2']
        bw = x2 - x1
        bh = y2 - y1
        if bw <= 0 or bh <= 0:
            continue
        x_c = x1 + bw / 2
        y_c = y1 + bh / 2
        cls_idx = cls_to_idx.get(b['label'], None)
        if cls_idx is None:
            # 새 클래스는 무시 (혹은 append 가능)
            continue
        lines.append(
            f"{cls_idx} {x_c/width:.6f} {y_c/height:.6f} {bw/width:.6f} {bh/height:.6f}"
        )
    Path(txt_path).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
