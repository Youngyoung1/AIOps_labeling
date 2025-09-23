#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PlantUML .puml -> .png 익스포트 스크립트 (서버 렌더링)
- Java/Graphviz 설치 없이 PlantUML 서버를 사용해 PNG 생성
- 서버 주소는 기본값(http://www.plantuml.com/plantuml) 사용, 필요 시 --server 옵션으로 변경

사용 예:
  python tools/plantuml_export.py anylabeling/services/roboflow/diagram.puml
  python tools/plantuml_export.py anylabeling/services/roboflow/diagram.puml --out anylabeling/services/roboflow/diagram.png
  python tools/plantuml_export.py diagram.puml --server http://www.plantuml.com/plantuml
"""

import argparse
import os
import sys
import zlib
from urllib.parse import urljoin
from urllib.request import urlopen, Request


def _encode6bit(b: int) -> str:
    if b < 10:
        return chr(48 + b)
    b -= 10
    if b < 26:
        return chr(65 + b)
    b -= 26
    if b < 26:
        return chr(97 + b)
    b -= 26
    if b == 0:
        return '-'
    if b == 1:
        return '_'
    return '?'  # should not happen


def _append3bytes(b1: int, b2: int, b3: int) -> str:
    c1 = (b1 >> 2) & 0x3F
    c2 = ((b1 & 0x3) << 4) | ((b2 >> 4) & 0xF)
    c3 = ((b2 & 0xF) << 2) | ((b3 >> 6) & 0x3)
    c4 = b3 & 0x3F
    return ''.join(_encode6bit(c) for c in (c1, c2, c3, c4))


def plantuml_encode(data: bytes) -> str:
    # raw deflate (no zlib header) + plantuml 6-bit encoding
    compressor = zlib.compressobj(level=9, wbits=-15)
    compressed = compressor.compress(data) + compressor.flush()

    res = []
    i = 0
    while i < len(compressed):
        b1 = compressed[i]
        b2 = compressed[i + 1] if (i + 1) < len(compressed) else 0
        b3 = compressed[i + 2] if (i + 2) < len(compressed) else 0
        res.append(_append3bytes(b1, b2, b3))
        i += 3
    return ''.join(res)


def export_png(puml_path: str, out_path: str = None, server: str = "http://www.plantuml.com/plantuml") -> str:
    if not os.path.exists(puml_path):
        raise FileNotFoundError(puml_path)

    with open(puml_path, 'rb') as f:
        content = f.read()

    encoded = plantuml_encode(content)
    # ensure server ends with '/'
    if not server.endswith('/'):
        server += '/'

    png_url = urljoin(server, 'png/' + encoded)

    req = Request(png_url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urlopen(req) as resp:
            data = resp.read()
    except Exception:
        # Fallback: some servers reject very long GET URLs. Try POSTing raw PUML to /png endpoint.
        post_url = urljoin(server, 'png')
        post_headers = {'User-Agent': 'Mozilla/5.0', 'Content-Type': 'text/plain'}
        req2 = Request(post_url, data=content, headers=post_headers)
        with urlopen(req2) as resp:
            data = resp.read()

    if not out_path:
        base, _ = os.path.splitext(puml_path)
        out_path = base + '.png'

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(data)

    return out_path


def main(argv=None):
    parser = argparse.ArgumentParser(description='Export PlantUML PUML to PNG via server')
    parser.add_argument('puml', help='Path to .puml file')
    parser.add_argument('--out', help='Output PNG path (default: same dir, same name with .png)', default=None)
    parser.add_argument('--server', help='PlantUML server base URL', default='http://www.plantuml.com/plantuml')

    args = parser.parse_args(argv)

    try:
        out = export_png(args.puml, args.out, args.server)
        print(out)
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
