"""MongoDB ↔ Airflow 연동 데모 DAG

기능:
 - Airflow Connection(mongo) 또는 repo의 mongo_config.json을 사용해 MongoDB 연결
 - 핑 체크, 특정 컬렉션 문서 수 카운트, 파이프라인 실행 로그 기록

사전 준비:
 - Airflow 환경에 다음 패키지 설치 권장:
   apache-airflow-providers-mongo, pymongo
 - Airflow UI 또는 환경변수로 Mongo Connection 생성(권장): Conn Id 예) mongo_default
   환경변수: AIRFLOW_CONN_MONGO_DEFAULT=mongodb://user:pass@host:27017/db
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, Tuple
import pendulum

from airflow import DAG
from airflow.operators.python import PythonOperator


def _find_repo_root(start: Path) -> Path:
    """상위 디렉터리를 탐색해 repo 루트를 추정 (mongo_config.json 또는 pyproject.toml 기준)."""
    cur = start
    for _ in range(6):
        if (cur / "mongo_config.json").exists() or (cur / "pyproject.toml").exists():
            return cur
        cur = cur.parent
    return start


THIS_FILE = Path(__file__).resolve()
REPO_ROOT = _find_repo_root(THIS_FILE)


def _get_mongo_client(conn_id_env: str = "MONGO_CONN_ID",
                       default_conn_id: str = "mongo_default") -> Tuple[object, str]:
    """MongoDB Client, db_name 반환.

    우선순위:
      1) Airflow providers.mongo MongoHook + (Conn Id: 환경변수 MONGO_CONN_ID 또는 mongo_default)
      2) repo 루트의 mongo_config.json(connection_string, db_name)
    """
    import os
    conn_id = os.environ.get(conn_id_env, default_conn_id)

    # 1) MongoHook 시도
    try:
        from airflow.providers.mongo.hooks.mongo import MongoHook  # type: ignore
        hook = MongoHook(conn_id)
        client = hook.get_conn()  # pymongo.MongoClient
        # db_name은 Connection의 schema 또는 extras에서 읽을 수 있음. 없으면 기본 사용.
        db_name = hook.conn.schema or os.environ.get("MONGO_DB_NAME", "labeling_db")
        return client, db_name
    except Exception:
        pass

    # 2) mongo_config.json 폴백
    cfg_path = REPO_ROOT / "mongo_config.json"
    if not cfg_path.exists():
        raise RuntimeError("mongo_config.json을 찾을 수 없고 Airflow MongoHook 연결도 실패했습니다.")
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    conn_str = data.get("connection_string", "mongodb://localhost:27017")
    db_name = data.get("db_name", "labeling_db")

    try:
        from pymongo import MongoClient  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("pymongo가 필요합니다. Airflow 환경에 설치해 주세요.") from e

    client = MongoClient(conn_str)
    return client, db_name


def _task_ping(**_):
    client, db_name = _get_mongo_client()
    try:
        client.admin.command("ping")
    finally:
        client.close()
    return {"ok": True, "db": db_name}


def _task_count(collection: str = "labels", **_):
    client, db_name = _get_mongo_client()
    try:
        db = client[db_name]
        cnt = db[collection].count_documents({}) if collection in db.list_collection_names() else 0
        return {"collection": collection, "count": cnt}
    finally:
        client.close()


def _task_insert_run_log(collection: str = "pipeline_runs", **context):
    client, db_name = _get_mongo_client()
    try:
        db = client[db_name]
        dag_run = context.get("dag_run")
        ti = context.get("ti")
        payload = {
            "dag_id": dag_run.dag_id if dag_run else None,
            "run_id": dag_run.run_id if dag_run else None,
            "execution_date": str(dag_run.execution_date) if dag_run else None,
            "ts": pendulum.now("Asia/Seoul").to_iso8601_string(),
            "upstream_counts": context.get("ti").xcom_pull(task_ids="count_labels", default=None),
        }
        res = db[collection].insert_one(payload)
        return {"inserted_id": str(res.inserted_id)}
    finally:
        client.close()


with DAG(
    dag_id="mongo_integration_demo",
    description="MongoDB 연결 테스트 및 간단한 카운트/로그 기록",
    start_date=pendulum.datetime(2025, 1, 1, tz="Asia/Seoul"),
    schedule_interval=None,
    catchup=False,
    tags=["mongo", "integration", "demo"],
) as dag:

    ping = PythonOperator(
        task_id="ping_mongo",
        python_callable=_task_ping,
    )

    count = PythonOperator(
        task_id="count_labels",
        python_callable=_task_count,
        op_kwargs={"collection": "labels"},  # 필요 시 컬렉션명 변경
    )

    log = PythonOperator(
        task_id="insert_run_log",
        python_callable=_task_insert_run_log,
        op_kwargs={"collection": "pipeline_runs"},
    )

    ping >> count >> log
