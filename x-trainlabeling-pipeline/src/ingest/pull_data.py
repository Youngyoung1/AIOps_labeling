"""(사용 중단 / Deprecated)
사용자가 이미 정리된 파일명을 가진 데이터를 직접 배치한다고 하여
이 모듈은 더 이상 파이프라인에서 사용되지 않는다.
필요 시 외부 스토리지 → 로컬 동기화 로직을 여기에 구현하고
Airflow DAG 에 ingest 태스크를 다시 추가하면 된다.
현재는 호출되어도 아무 영향이 없는 마커 생성만 수행.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from ..common.io_utils import ensure_dir
from ..common.logging_utils import get_logger

logger = get_logger(__name__)

RAW = Path("data/raw")


def main():  # 유지보수 편의를 위한 no-op (마커만 생성)
    ensure_dir(RAW)
    marker = RAW / f"deprecated_ingest_{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.done"
    marker.write_text("deprecated", encoding="utf-8")
    files = list(RAW.iterdir())
    logger.info("Ingest(deprecated) 호출됨. total=%d (실제 pull 없음)", len(files))
    return {"files": len(files), "deprecated": True}

if __name__ == "__main__":  # 수동 실행 시
    main()
