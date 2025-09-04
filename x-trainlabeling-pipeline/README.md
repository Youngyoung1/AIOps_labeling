# x-trainlabeling E2E Pipeline (Airflow + YOLOv8-seg)

수집 → 전처리 → 자동라벨 → 검수(QC) → 데이터셋 스플릿/증강 → 학습 → 피드백(active learning) → 재순환 을 단일 파이프라인으로 관리.

## 핵심 특징
- Apache Airflow 기반 DAG: 일 배치(or 주기) 실행.
- YOLOv8 Segmentation 자동 학습 파이프라인.
- SAM / YOLO inference 조합 자동 라벨링 (확장 지점 제공).
- QC 룰 기반 필터 및 리포트.
- Registry: 간이 모델/메타 버전 관리(JSON + symlink).
- Active Learning: 낮은 confidence 샘플 재라벨 루프.

## 디렉터리 구조
(요약)
```
x-trainlabeling-pipeline/
  configs/            # 프로젝트, 데이터셋, 클래스 정의
  airflow/            # Airflow DAG & (선택) docker-compose
  src/                # 파이프라인 모듈 구현
  data/               # 데이터 레이어 (raw→interim→labels→yolo 등)
```

## 빠른 시작 (로컬 Airflow)
1. 가상환경 생성 & 설치
```
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
2. 환경변수 작성
```
cp .env.example .env
```
3. (선택) docker-compose 로 Airflow
```
cd airflow
# docker compose up -d  (필요 시)
```
4. Airflow 변수/연결 설정 (CLI 예시 추후 추가)

## DAG
메인 DAG: `airflow/dags/x_trainlabeling_dag.py`

주요 태스크들:
- ingest_pull_data
- preprocess_dataset
- autolabel_generate
- qc_validate_labels
- dataset_split_and_augment
- train_yolov8_seg
- inference_and_active_learning

## 확장 포인트
- `src/autolabel/` : 추가 모델 wrapper
- `src/qc/qc_rules.py` : 사용자 정의 QC 룰
- `src/feedback/active_learning.py` : 샘플 선정 전략 교체

## 라이선스
(추후 적용)
