"""YOLO 추론 기반 자동 라벨 생성 스텁 (세그멘테이션).

현재 실제 YOLO 모델 추론을 수행하지 않고, (선택) 전달된 폴리곤 좌표를 활용하여
YOLO 세그멘테이션 형식(.txt) 라벨을 생성한다.

동작 요약:
1. `data/interim` 내 이미지 순회
2. 동일 stem 의 라벨파일이 이미 존재하면 건너뜀
3. polygon_coords 인자가 주어지면 해당 좌표를 이미지 크기에 맞게 (상대/절대 혼용 허용) 변환
4. 변환된 폴리곤을 YOLO 세그 텍스트 라인으로 저장

TODO (실제 구현 시):
- ultralytics YOLO 세그 모델 로드 후 예측 → 마스크 → 폴리곤 변환
- NMS / 점 단순화 / 클래스 매핑
- confidence threshold 적용
"""
from __future__ import annotations
from pathlib import Path
from ..common.logging_utils import get_logger
from ..common.io_utils import list_images, ensure_dir
from .convert import polygon_to_yolo_line, merge_lines
from PIL import Image

logger = get_logger(__name__)
INTERIM = Path("data/interim")
LABELS = Path("data/labels")

def run(config_path: str | None = None, polygon_coords: list[tuple[int, int]] | None = None):
    ensure_dir(LABELS)
    # 현재는 SAM 스텁과 유사하게 외부에서 좌표가 주어지지 않으면 아무 것도 생성하지 않음
    imgs = list_images(INTERIM)
    created = 0
    for img in imgs:
        txt = LABELS / (img.stem + ".txt")
        if txt.exists():
            continue
        # Use the actual image size
        with Image.open(img) as im:
            width, height = im.size

    # 폴리곤 좌표 미제공 시 기본/더미 라벨 생성하지 않고 skip
        if polygon_coords is None:
            logger.debug("폴리곤 좌표 미제공: %s (manual_bbox 모드일 수 있음)", img.name)
            continue

        # 폴리곤 구성: 상대좌표(0..1 float) 또는 절대 픽셀(int) 혼용 허용
        polygon: list[tuple[int, int]] = []
        for x, y in polygon_coords:
            # float 이거나 (작은 int 로 들어와 상대 좌표로 해석 가능한 경우) → 비율로 간주
            if isinstance(x, float) or isinstance(y, float) or (
                isinstance(x, int) and isinstance(y, int) and 0 <= x <= 1 and 0 <= y <= 1
            ):
                px = int(float(x) * width)
                py = int(float(y) * height)
            else:  # 절대 좌표
                px = int(x)
                py = int(y)
            polygon.append((px, py))

        line = polygon_to_yolo_line(0, polygon, width, height)
        txt.write_text(merge_lines([line]), encoding="utf-8")
        created += 1
    logger.info("YOLO infer 라벨 생성 누적: %d", created)
    return {"labels": created}
