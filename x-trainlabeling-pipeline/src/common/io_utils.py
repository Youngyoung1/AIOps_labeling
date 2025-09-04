"""파일 입출력 및 데이터셋 구성에 사용되는 공용 유틸 함수 모음."""
from __future__ import annotations
import json
import shutil
from pathlib import Path
from typing import Any, Iterable

def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p

def write_json(obj: Any, path: str | Path, indent: int = 2) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    with p.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)

def read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)

def symlink_or_copy(src: str | Path, dst: str | Path) -> None:
    src_p, dst_p = Path(src), Path(dst)
    ensure_dir(dst_p.parent)
    if dst_p.exists():
        return
    try:
        dst_p.symlink_to(src_p)
    except OSError:
        if src_p.is_dir():
            shutil.copytree(src_p, dst_p)
        else:
            shutil.copy2(src_p, dst_p)


def list_images(root: str | Path, exts: Iterable[str] = (".jpg", ".png", ".jpeg")) -> list[Path]:
    root_p = Path(root)
    files = []
    for ext in exts:
        files.extend(root_p.rglob(f"*{ext}"))
    return files
