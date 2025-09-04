"""x-trainlabeling 파이프라인 Airflow DAG

변경 사항:
1) 사용자가 이미 정규화된 파일명(예: 000850_02_EO_B_20250403181441982.jpg)으로 데이터를 준비한다고 하였으므로
    별도의 데이터 수집(ingest) 단계는 제거하였다.
2) 파이프라인 시작은 전처리(preprocess) → 자동 라벨(autolabel) → QC → 분할(split+옵션증강) → 학습(train) → 액티브러닝(AL) 순서.
3) 추후 필요 시 ingest 단계 복구하려면 ingest_pull_data() 태스크와 의존성만 다시 추가하면 된다.
"""
from __future__ import annotations
import os
from datetime import datetime, timedelta
from airflow.decorators import dag, task
from airflow.models import Variable

# Simplified: tasks call python modules in src/
ROOT = os.getenv("AIRFLOW_HOME", "/opt/airflow")
SRC_DIR = os.path.join(ROOT, "src")
CONFIG_PATH = os.path.join(ROOT, "configs", "project.yaml")

def _import(module: str, attr: str = None):  # lazy import helper
    mod = __import__(module, fromlist=[attr] if attr else [])
    return getattr(mod, attr) if attr else mod

@dag(
    dag_id="x_trainlabeling_pipeline",
    schedule_interval="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    default_args={
        "owner": "airflow",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["labeling", "training", "yolov8", "segmentation"],
)
def x_trainlabeling_pipeline():

    @task()
    def preprocess_dataset():
        mod = _import("src.preprocess.preprocess")
        return mod.main(CONFIG_PATH)

    @task()
    def autolabel_generate():
        mod = _import("src.autolabel.yolo_infer")
        return mod.run(CONFIG_PATH)

    @task()
    def qc_validate_labels():
        mod = _import("src.qc.qc_rules")
        return mod.run(CONFIG_PATH)

    @task()
    def dataset_split_and_augment():
        import yaml
        # split 항상 수행
        split_mod = _import("src.dataset.split")
        split_result = split_mod.run(CONFIG_PATH)
        # config 로드하여 augmentation.enabled 확인
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            enabled = cfg.get("augmentation", {}).get("enabled", False)
        except Exception as e:  # pragma: no cover
            enabled = False
        if enabled:
            aug_mod = _import("src.dataset.augment")
            aug_mod.run(CONFIG_PATH)
        return split_result

    @task()
    def train_yolov8_seg():
        mod = _import("src.train.train_yolov8_seg")
        return mod.run(CONFIG_PATH)

    @task()
    def inference_and_active_learning():
        mod = _import("src.feedback.active_learning")
        return mod.run(CONFIG_PATH)

    # 실행 순서 구성 (ingest 제거)
    prep = preprocess_dataset()
    autolabeled = autolabel_generate()
    qc = qc_validate_labels()
    split = dataset_split_and_augment()
    trained = train_yolov8_seg()
    al = inference_and_active_learning()
    # preprocess 완료 후 autolabel 진행
    prep >> autolabeled >> qc >> split >> trained >> al


globals()["x_trainlabeling_pipeline"] = x_trainlabeling_pipeline()
