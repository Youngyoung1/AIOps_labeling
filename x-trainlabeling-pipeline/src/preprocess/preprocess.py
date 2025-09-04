"""원천 이미지 전처리 (현재는 단순 복사 스텁)."""
from __future__ import annotations
from pathlib import Path
import shutil
from ..common.io_utils import ensure_dir, list_images
from ..common.logging_utils import get_logger

logger = get_logger(__name__)
RAW = Path("data/raw")
INTERIM = Path("data/interim")


def main(config_path: str | None = None):  # TODO: config 활용한 리사이즈/정규화 파이프라인 확장
    ensure_dir(INTERIM)
    imgs = list_images(RAW)
    for p in imgs:
        out = INTERIM / p.name
        if not out.exists():
            shutil.copy2(p, out)
    logger.info("Preprocess copied %d images", len(imgs))
    return {"count": len(imgs)}

if __name__ == "__main__":  # 수동 실행
    main()
