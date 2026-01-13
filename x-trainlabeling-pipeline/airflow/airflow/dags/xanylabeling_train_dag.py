"""X-AnyLabeling 파이프라인 DAG

전처리 -> 데이터 분할 -> YOLOv8 학습 순으로 실행합니다.

주의(Windows): Airflow는 Windows 네이티브 환경에서 제약이 있으므로
가능하면 WSL2 또는 Docker 기반으로 실행하세요. 이 DAG는 저장소 내
`x-trainlabeling-pipeline/src` 모듈들을 import 하므로, DAG 파일 기준
상대 경로로 sys.path 를 보정합니다.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
import pendulum
from airflow import DAG
from airflow.operators.python import PythonOperator

# ---- import path 보정: <repo>/x-trainlabeling-pipeline/src 를 sys.path 에 추가
THIS_FILE = Path(__file__).resolve()
# 우선 환경변수로 파이프라인 루트를 지정할 수 있게 함(도커/WSL에서 안정적)
PIPELINE_ROOT_ENV = os.environ.get("X_TRAINLABELING_ROOT")
if PIPELINE_ROOT_ENV:
    PIPELINE_ROOT = Path(PIPELINE_ROOT_ENV).resolve()
else:
    # 폴백: 파일 위치 기준으로 추정
    # __file__ = <repo>/x-trainlabeling-pipeline/airflow/airflow/dags/<this>.py
    # parents[3] => <repo>/x-trainlabeling-pipeline
    PIPELINE_ROOT = THIS_FILE.parents[3]
SRC_DIR = PIPELINE_ROOT / "src"
CONFIG_DIR = PIPELINE_ROOT / "configs"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# 이제 src 하위 모듈 import (상대 패키지 아님에 주의)
from preprocess.preprocess import main as preprocess_main  # noqa: E402
from dataset.split import run as split_run  # noqa: E402
from train.train_yolov8_seg import run as train_run  # noqa: E402


PROJECT_YAML = str(CONFIG_DIR / "project.yaml")


def _task_preprocess(**_):
    # 작업 디렉터리를 파이프라인 루트로 설정
    os.chdir(str(PIPELINE_ROOT))
    # 필요한 경우 PROJECT_YAML 로 파라미터 확장 가능
    return preprocess_main(config_path=PROJECT_YAML)


def _task_split(**_):
    os.chdir(str(PIPELINE_ROOT))
    # 기본은 자동 전략(auto). 필요 시 strategy="manifest" 등으로 고정 가능
    return split_run(config_path=PROJECT_YAML, strategy=None)


def _task_train(**_):
    os.chdir(str(PIPELINE_ROOT))
    # project.yaml 의 train 설정을 읽어 YOLOv8 학습 실행
    return train_run(config_path=PROJECT_YAML)


with DAG(
    dag_id="xanylabeling_train",
    description="X-AnyLabeling: preprocess -> split -> train",
    start_date=pendulum.datetime(2025, 1, 1, tz="Asia/Seoul"),
    schedule_interval=None,  # 수동 트리거
    catchup=False,
    tags=["xanylabeling", "yolov8", "training"],
) as dag:

    preprocess = PythonOperator(
        task_id="preprocess",
        python_callable=_task_preprocess,
    )

    split = PythonOperator(
        task_id="split_dataset",
        python_callable=_task_split,
    )

    train = PythonOperator(
        task_id="train_yolov8",
        python_callable=_task_train,
    )

    preprocess >> split >> train
