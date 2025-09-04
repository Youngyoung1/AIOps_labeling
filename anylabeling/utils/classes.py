"""클래스 텍스트/JSON 변환 유틸.

형식:
- classes.txt : 한 줄당 하나의 클래스 이름
- classes.json : {
    "version": 1,
    "classes": [ {"id":0,"name":"cls"}, ... ]
  }
"""
from __future__ import annotations
from pathlib import Path
import json
from typing import List

__all__ = [
    "read_classes_txt",
    "write_classes_txt",
    "write_classes_json",
    "convert_txt_to_json",
]


def read_classes_txt(path: str | Path) -> List[str]:
    p = Path(path)
    if not p.exists():
        return []
    lines = [l.strip() for l in p.read_text(encoding="utf-8").splitlines()]
    # 공백/중복 제거, 순서 유지
    seen = set()
    result: List[str] = []
    for name in lines:
        if not name:
            continue
        if name in seen:
            continue
        seen.add(name)
        result.append(name)
    return result


def write_classes_txt(path: str | Path, classes: List[str]):
    Path(path).write_text("\n".join(classes) + "\n", encoding="utf-8")


def write_classes_json(path: str | Path, classes: List[str]):
    data = {
        "version": 1,
        "classes": [
            {"id": i, "name": c} for i, c in enumerate(classes)
        ],
    }
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def convert_txt_to_json(txt_path: str | Path, json_path: str | Path | None = None) -> dict:
    """classes.txt → classes.json 변환.

    반환: {"count": N, "txt": "...", "json": "..."}
    """
    txt_p = Path(txt_path)
    if json_path is None:
        json_path = txt_p.with_suffix(".json")
    json_p = Path(json_path)
    classes = read_classes_txt(txt_p)
    if not classes:
        return {"count": 0, "txt": str(txt_p), "json": str(json_p)}
    write_classes_json(json_p, classes)
    return {"count": len(classes), "txt": str(txt_p), "json": str(json_p)}
