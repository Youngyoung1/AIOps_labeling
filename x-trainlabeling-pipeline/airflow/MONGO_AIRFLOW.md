# Airflow ↔ MongoDB 연동 가이드

이 저장소에는 `airflow/airflow/dags/mongo_integration_demo.py` 예제 DAG가 포함되어 있으며,
Airflow 환경에서 MongoDB 연결을 검증하고 단순 작업(카운트/로그 기록)을 수행합니다.

## 의존성

- Airflow Provider: `apache-airflow-providers-mongo`
- Mongo 드라이버: `pymongo`

Airflow가 Docker/WSL에서 동작한다면 해당 컨테이너/가상환경에 위 패키지를 설치하세요.

## 커넥션 설정(권장)

Airflow UI(Connections) 또는 환경변수로 Mongo 커넥션을 등록합니다.

- Conn Id: `mongo_default` (예제 DAG 기본값)
- Conn URI 예시: `mongodb://user:password@host:27017/dbname`
- 환경변수로 지정하는 방법(대소문자 주의):
  - `AIRFLOW_CONN_MONGO_DEFAULT=mongodb://user:password@host:27017/dbname`

만약 Airflow Connection을 만들지 않았다면, 저장소 루트의 `mongo_config.json`을 읽어
`connection_string`과 `db_name`으로 폴백합니다.

## DAG

- `mongo_integration_demo` DAG를 수동 트리거하면 다음 순서로 실행됩니다.
  1) `ping_mongo`: ping
  2) `count_labels`: `labels` 컬렉션 문서 수 카운트
  3) `insert_run_log`: 실행 메타데이터를 `pipeline_runs` 컬렉션에 기록

컬렉션 이름은 DAG 파라미터(`op_kwargs`)로 변경할 수 있습니다.

## 트러블슈팅

- `No module named airflow.providers.mongo`: provider 패키지가 미설치
- 인증 오류: Conn URI의 사용자/비밀번호/DB명 확인
- 네트워크: 컨테이너 ↔ MongoDB 포트/호스트 접근 가능 여부 점검