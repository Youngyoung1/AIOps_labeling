"""액티브 러닝 루프 스텁.

개념:
1. 낮은 confidence / 높은 불확실성 샘플 선별
2. 라벨링 큐(또는 재검수 디렉터리)로 재할당
3. 일정 누적 후 재학습 트리거

현재는 구현되지 않았으며 선택 샘플 수 0 을 반환한다.
확장 아이디어:
- 예측 결과(JSON)에서 confidence quantile 기반 필터링
- 다양성(embedding clustering) + 불확실성 결합 스코어
- 재라벨 우선순위 점수 계산 및 로그 저장
"""
from __future__ import annotations
from pathlib import Path
import json
from ..common.logging_utils import get_logger
from ..common.io_utils import ensure_dir

logger = get_logger(__name__)
INFER = Path("data/inference")
LABELS = Path("data/labels")
MANUAL_JSON_DEFAULT = Path("data/manual_bboxes.json")

def _load_manual_bbox_json(path: Path) -> list[dict]:
    if not path.exists():
        logger.warning("수동 bbox JSON 이 존재하지 않음: %s", path)
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        logger.warning("수동 bbox JSON 루트가 list 아님: %s", type(data))
        return []
    except Exception as e:  # pragma: no cover
        logger.error("수동 bbox JSON 로드 실패: %s", e)
        return []

def _bbox_to_yolo_line(cls_id: int, x_min: int, y_min: int, w: int, h: int, img_w: int, img_h: int) -> str:
    # YOLO bbox: class cx cy w h (모두 0~1)
    cx = (x_min + w / 2) / img_w
    cy = (y_min + h / 2) / img_h
    nw = w / img_w
    nh = h / img_h
    return f"{cls_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}"

def _write_yolo_bbox_label(image_path: Path, lines: list[str]):
    ensure_dir(LABELS)
    label_path = LABELS / f"{image_path.stem}.txt"
    if label_path.exists():
        # append? 여기서는 overwrite (수동 라벨이 우선)
        pass
    label_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return label_path

def run(config_path: str | None = None):  # 수동 bbox -> YOLO 변환 + (미구현) AL 로직
    INFER.mkdir(parents=True, exist_ok=True)
    # 1) 수동 BBox JSON 로드
    json_candidates = [MANUAL_JSON_DEFAULT]
    manual_records: list[dict] = []
    for cand in json_candidates:
        manual_records = _load_manual_bbox_json(cand)
        if manual_records:
            break
    converted = 0
    skipped = 0
    from PIL import Image
    for rec in manual_records:
        # 기대 형식 예시: {"image": "data/interim/xxx.jpg", "bboxes": [{"cls":0, "x":100, "y":50, "w":200, "h":120}]}
        img_path = Path(rec.get("image", ""))
        bboxes = rec.get("bboxes", [])
        if not img_path.exists() or not bboxes:
            skipped += 1
            continue
        try:
            with Image.open(img_path) as im:
                iw, ih = im.size
        except Exception:
            skipped += 1
            continue
        lines = []
        for b in bboxes:
            try:
                cls_id = int(b.get("cls", 0))
                x = int(b["x"])
                y = int(b["y"])
                w = int(b["w"])
                h = int(b["h"])
                # 범위 체크 (음수 또는 0 크기)
                if w <= 0 or h <= 0:
                    continue
                # 이미지 경계를 벗어나면 클램프
                if x < 0: x = 0
                if y < 0: y = 0
                if x + w > iw: w = iw - x
                if y + h > ih: h = ih - y
                lines.append(_bbox_to_yolo_line(cls_id, x, y, w, h, iw, ih))
            except Exception:  # pragma: no cover
                continue
        if not lines:
            skipped += 1
            continue
        _write_yolo_bbox_label(img_path, lines)
        converted += 1
    # (미구현) 2) 예측 결과 기반 불확실성 샘플 선택은 이후 확장
    logger.info("수동 BBox 변환 완료: labels=%d skipped=%d", converted, skipped)
    return {"manual_bbox_converted": converted, "skipped": skipped, "selected": 0}
