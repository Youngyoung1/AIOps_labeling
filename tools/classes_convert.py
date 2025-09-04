#!/usr/bin/env python
"""CLI: classes.txt -> classes.json 변환

사용:
  python tools/classes_convert.py --txt path/to/classes.txt [--json out.json]
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

# 상대 import 대비: repo 루트 기준 실행 가정
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from anylabeling.utils.classes import convert_txt_to_json  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Convert classes.txt to classes.json")
    ap.add_argument("--txt", required=True, help="classes.txt 경로")
    ap.add_argument("--json", required=False, help="출력 json 경로 (옵션)")
    args = ap.parse_args()

    res = convert_txt_to_json(args.txt, args.json)
    if res["count"] == 0:
        print(f"[WARN] 클래스가 비어있거나 파일이 없음: {res['txt']}")
    else:
        print(f"[OK] {res['count']}개 클래스 변환 -> {res['json']}")


if __name__ == "__main__":
    main()
