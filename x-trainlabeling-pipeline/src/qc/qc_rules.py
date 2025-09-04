"""QC rules for generated YOLO-style segmentation labels.

현재 구현:
1. 통계 수집: 총 라벨 파일 수, 총 어노테이션 라인 수
2. 클래스 불일치 필터링: 허용되지 않은 클래스 ID 라인 제거 (원본 백업 .bak 저장)
3. 제거/보존 라인 수 리포트 및 JSON 저장

향후 추가 가능: IOU 중복 제거, polygon 면적/비율 outlier 검출 등
"""
from __future__ import annotations
from pathlib import Path
import json
from ..common.logging_utils import get_logger
from ..common.io_utils import read_json  # 재사용 가능(현재 read_json 필요 시 확장)

logger = get_logger(__name__)
LABELS = Path("data/labels")
QC_DIR = Path("data/qc")
CLASSES_CONFIG = Path("configs/classes.yaml")


def _load_allowed_classes() -> set[int]:
    # 간단 파서 (yaml.safe_load 사용하려면 pyyaml, 이미 requirements 포함)
    import yaml

    if not CLASSES_CONFIG.exists():
        logger.warning("classes.yaml not found; allow all")
        return set()
    data = yaml.safe_load(CLASSES_CONFIG.read_text(encoding="utf-8")) or {}
    classes = data.get("classes", {})
    # key 가 int string 혼합 가능 -> int 변환
    result = {int(k) for k in classes.keys()}
    return result


def _parse_label_line(line: str):
    # YOLO seg 포맷(간단): class cx cy ... (polygon coords 등) -> class id 첫 토큰
    parts = line.strip().split()
    if not parts:
        return None, parts
    try:
        cls_id = int(float(parts[0]))
    except ValueError:
        return None, parts
    return cls_id, parts


def run(config_path: str | None = None):
    QC_DIR.mkdir(parents=True, exist_ok=True)
    label_files = list(LABELS.glob("*.txt"))
    allowed = _load_allowed_classes()
    enforce = len(allowed) > 0
    total_lines = 0
    removed_lines = 0
    modified_files = 0

    for lf in label_files:
        lines = lf.read_text(encoding="utf-8").splitlines()
        total_lines += len(lines)
        if not lines:
            continue
        keep = []
        removed_local = 0
        for ln in lines:
            cls_id, parts = _parse_label_line(ln)
            if cls_id is None:  # format issue -> 제거
                removed_local += 1
                continue
            if enforce and cls_id not in allowed:
                removed_local += 1
                continue
            keep.append(ln)
        if removed_local > 0:
            # backup
            bak = lf.with_suffix(lf.suffix + ".bak")
            if not bak.exists():
                bak.write_text("\n".join(lines) + "\n", encoding="utf-8")
            lf.write_text("\n".join(keep) + ("\n" if keep else ""), encoding="utf-8")
            removed_lines += removed_local
            modified_files += 1

    report = {
        "label_files": len(label_files),
        "total_lines": total_lines,
        "removed_lines": removed_lines,
        "modified_files": modified_files,
        "allowed_class_count": len(allowed),
    }
    with (QC_DIR / "qc_report.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info(
        "QC report: files=%d modified=%d removed_lines=%d",
        report["label_files"],
        report["modified_files"],
        report["removed_lines"],
    )
    return report
