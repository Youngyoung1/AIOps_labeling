"""YOLOv8 학습 스텁 (Detection / Segmentation 겸용).

현재 최소 설정(epochs=1 기본) 데모용. project.yaml 의 train.task 가 detect 인 경우
YOLOv8 detection 가중치(예: yolov8s.pt), segment 인 경우 세그 가중치(yolov8s-seg.pt) 선택.

확장 TODO:
1. project.yaml 에서 epochs / batch / 이미지 크기 / 모델명 가변 적용
2. resume / checkpoint 관리
3. 멀티 GPU 지원
4. 메트릭 JSON/CSV 로그 출력
"""
from __future__ import annotations
from pathlib import Path
from ..common.logging_utils import get_logger
import yaml

logger = get_logger(__name__)
YOLO = Path("data/yolo")
REGISTRY = Path("data/registry")

try:
    from ultralytics import YOLO as YoloModel  # type: ignore
except Exception:  # pragma: no cover - ultralytics optional in bare env
    YoloModel = None  # type: ignore

DEFAULT_SEG_MODEL = "yolov8s-seg.pt"
DEFAULT_DET_MODEL = "yolov8s.pt"

def run(config_path: str | None = None):  # TODO: config 파싱하여 동적 하이퍼파라미터 적용
    if YoloModel is None:
        logger.warning("ultralytics 미설치: 학습을 스킵합니다")
        return {"trained": False}
    # config 로드
    task = "segment"
    epochs = 1
    imgsz = 640
    batch = 4
    try:
        if config_path and Path(config_path).exists():
            cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
            train_cfg = cfg.get("train", {})
            task = train_cfg.get("task", task)
            epochs = int(train_cfg.get("epochs", epochs))
            imgsz = int(train_cfg.get("image_size", imgsz))
            batch = int(train_cfg.get("batch", batch))
    except Exception as e:  # pragma: no cover
        logger.warning("config 파싱 실패: %s", e)

    if task == "detect":
        model_name = DEFAULT_DET_MODEL
        data_cfg = "configs/dataset.yolov8-seg.yaml"  # detection 도 동일 구조 사용 가능
    else:  # segment
        model_name = DEFAULT_SEG_MODEL
        data_cfg = "configs/dataset.yolov8-seg.yaml"

    logger.info("학습 시작 task=%s model=%s epochs=%d batch=%d imgsz=%d", task, model_name, epochs, batch, imgsz)
    model = YoloModel(model_name)
    results = model.train(data=data_cfg, epochs=epochs, imgsz=imgsz, batch=batch)
    REGISTRY.mkdir(parents=True, exist_ok=True)
    (REGISTRY / "latest_model.txt").write_text("yolov8s-seg.pt", encoding="utf-8")
    logger.info("YOLOv8 세그멘테이션 학습 완료")
    return {"trained": True, "results": str(results)}
