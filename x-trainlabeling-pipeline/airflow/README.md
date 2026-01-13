# X-AnyLabeling Airflow 파이프라인

이 폴더의 DAG(`airflow/dags/xanylabeling_train_dag.py`)는 다음 단계를 오케스트레이션합니다.

- preprocess: `data/raw` 이미지를 `data/interim`으로 전처리(현재는 복사)
- split: `data/labels`의 YOLO 포맷 라벨과 함께 `data/yolo`(images/labels/{train,val}) 구성
- train: Ultralytics YOLOv8로 학습 수행

## 데이터 준비

옵션 A) shared_flat_dir 사용(권장)
- `x-trainlabeling-pipeline/configs/project.yaml`의 `dataset.shared_flat_dir` 경로에
  이미지(.jpg/.png)와 동일 stem의 라벨(.txt, YOLO bbox)을 같은 폴더에 넣습니다.
- DAG의 split 단계에서 자동으로 `data/yolo/images/labels/train`으로 링크됩니다.

옵션 B) 수동
- `data/raw`에 이미지 복사, `data/labels`에 동일 stem의 .txt 라벨을 둡니다.
- 또는 `data/yolo/images/{train,val}` / `data/yolo/labels/{train,val}`를 미리 구성해 두면
  split 단계는 검증만 하고 넘어갑니다.

## Airflow에서 실행하기

Windows 네이티브 환경은 제약이 있으므로 WSL2 또는 Docker 기반 Airflow를 권장합니다.

- DAG 폴더로 `x-trainlabeling-pipeline/airflow/airflow/dags`를 마운트/지정하세요.
- 컨테이너 또는 스케줄러 프로세스의 작업 디렉터리가 저장소 루트여야 상대 경로(`data/*`)가 정상 동작합니다.
- Ultralytics 등 의존성은 Airflow 워커/컨테이너 환경에 설치되어 있어야 합니다.

학습 설정은 `x-trainlabeling-pipeline/configs/project.yaml`에서 수정 가능합니다.