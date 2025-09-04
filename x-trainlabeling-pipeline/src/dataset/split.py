"""Dataset split for YOLO segmentation.

시나리오 3가지 지원:
1. 자동 분할(folders)  : 기존 로직 - images/labels/{train,val} 생성 후 symlink/copy
2. 자동 분할(manifest) : train.txt / val.txt (각 줄 = 이미지 절대경로)
3. 수동 구성(manual)   : 사용자가 이미 (a) train.txt/val.txt(/test.txt) 를 만들었거나
                                                     (b) images/{train,val(,test)} 디렉터리 구조를 만들어 둔 경우
     -> 추가 작업 없이 검증/카운트만 수행 후 종료.

추가 전략:
4. 파일명 prefix(prefix) : 한 디렉터리에 train-xxx.jpg / val-yyy.png / test-zzz.jpg 형식으로
                   모아두고 이를 파싱하여 분할. labels 는 동일 접두어 + 확장자 .txt 로 가정.
5. 외부 베이스(external_base): 파이프라인 외부(or data/interim 외부)에 이미 다음 구조 존재할 때 사용
    <BASE>/train/*.jpg(.png...) + 대응 *.txt
    <BASE>/val/*
    <BASE>/test/* (선택)
    -> 이 경우 분할을 수행하지 않고 카운트 후, 필요 시 data/yolo/images/<split>, labels/<split> 으로
        symlink(또는 copy fallback) 만 구성.
   - 예) train-cat123.jpg / train-cat123.txt
       val-dog99.jpg / val-dog99.txt
       test-bird1.jpg / test-bird1.txt
   - prefix 전략은 기본적으로 images/labels/{split} 구조를 생성하며, prefix 제거(rename) 가능.

사용자가 "직접 넣고" 싶다면 data/yolo 아래 중 하나를 준비:
 A) Manifest 방식: train.txt, val.txt, (선택)test.txt
 B) 폴더 방식: images/train, images/val, (선택)images/test 와 대응 labels/* 동일 구조

dataset.yolov8-seg.yaml 예 (manifest):
    train: data/yolo/train.txt
    val: data/yolo/val.txt
    test: data/yolo/test.txt  # 선택

자동 분할을 비활성화하려면 DAG/task 호출 시 strategy="manual" 또는 파일/폴더 사전 존재하게 두면 자동 감지.
"""
from __future__ import annotations
from pathlib import Path
import yaml
import random
from ..common.io_utils import ensure_dir, list_images, symlink_or_copy
from ..common.logging_utils import get_logger

logger = get_logger(__name__)
INTERIM = Path("data/interim")
LABELS = Path("data/labels")
YOLO = Path("data/yolo")

def _count_manifest(path: Path) -> int:
    if not path.exists():
        return 0
    lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return len(lines)


def _count_dir(img_dir: Path) -> int:
    if not img_dir.exists():
        return 0
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
    return sum(1 for p in img_dir.iterdir() if p.suffix.lower() in exts)

def _detect_manual() -> dict | None:
    # Manifest 우선 검사
    train_manifest = YOLO / "train.txt"
    val_manifest = YOLO / "val.txt"
    test_manifest = YOLO / "test.txt"
    if train_manifest.exists() and val_manifest.exists():
        info = {
            "mode": "manifest",
            "train": _count_manifest(train_manifest),
            "val": _count_manifest(val_manifest),
            "test": _count_manifest(test_manifest) if test_manifest.exists() else 0,
        }
        return info
    # 폴더 구조 검사
    train_dir = YOLO / "images" / "train"
    val_dir = YOLO / "images" / "val"
    test_dir = YOLO / "images" / "test"
    if train_dir.exists() and val_dir.exists():
        info = {
            "mode": "folders",
            "train": _count_dir(train_dir),
            "val": _count_dir(val_dir),
            "test": _count_dir(test_dir) if test_dir.exists() else 0,
        }
        return info
    return None

def _collect_prefix_split() -> dict | None:
    """한 곳(interim)에 train-/val-/test- 접두어가 섞여 있는 경우 감지.
    규칙: 파일명 소문자 기준 시작이 train-|val-|test- 중 하나.
    반환 예: {"train": [Path, ...], "val": [...], "test": [...]} (존재 split만)
    """
    imgs = list_images(INTERIM)
    if not imgs:
        return None
    buckets: dict[str, list[Path]] = {"train": [], "val": [], "test": []}
    any_match = False
    for p in imgs:
        name = p.name.lower()
        for split in ("train", "val", "test"):
            pref = f"{split}-"
            if name.startswith(pref):
                buckets[split].append(p)
                any_match = True
                break
    if not any_match:
        return None
    return {k: v for k, v in buckets.items() if v}


def run(
    config_path: str | None = None,
    train_ratio: float = 0.8,
    strategy: str | None = None,  # None -> auto, 'folders'|'manifest'|'manual'|'prefix'
    seed: int = 42,
    keep_prefix: bool = False,    # prefix 전략에서 대상 파일명을 그대로 둘지 여부
    external_base: str | None = None,  # 외부 베이스 경로 제공 시 우선 적용 (strategy 무시 가능)
    link_external: bool = True,       # 외부 베이스 사용 시 data/yolo 하위로 링크 구성 여부
):
    # 0) config 내 shared_flat_dir 감지 -> 단일 폴더(shared flat) 전략 (train 전용)
    shared_flat_dir: Path | None = None
    if config_path and Path(config_path).exists():
        try:
            cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
            ds_cfg = cfg.get("dataset", {})
            sfd = ds_cfg.get("shared_flat_dir")
            if sfd:
                p = Path(sfd)
                if p.exists() and p.is_dir():
                    shared_flat_dir = p
        except Exception as e:  # pragma: no cover
            logger.warning("config 파싱 중 오류(shared_flat_dir 무시): %s", e)

    if shared_flat_dir and strategy in (None, "shared_flat"):
        imgs = [p for p in shared_flat_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}]
        if not imgs:
            logger.warning("shared_flat_dir 에 이미지가 없음: %s", shared_flat_dir)
        else:
            img_dir = ensure_dir(YOLO / "images" / "train")
            lbl_dir = ensure_dir(YOLO / "labels" / "train")
            linked = 0
            for img in imgs:
                label_src = img.with_suffix(".txt")
                if not label_src.exists():
                    continue  # 라벨 없는 이미지 스킵
                symlink_or_copy(img, img_dir / img.name)
                symlink_or_copy(label_src, lbl_dir / label_src.name)
                linked += 1
            (YOLO / "_SHARED_FLAT_LINKED").write_text("ok", encoding="utf-8")
            logger.info("Shared flat 링크 완료 images(linked with labels)=%d", linked)
            return {"train": linked, "val": 0, "test": 0, "strategy": "shared_flat"}

    # 외부 베이스 우선 처리
    if external_base:
        base = Path(external_base)
        if not base.exists():
            logger.warning("external_base 경로가 존재하지 않습니다: %s", base)
            return {"train": 0, "val": 0, "test": 0, "strategy": "external_base:not_found"}
        splits = {}
        img_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
        for split in ("train", "val", "test"):
            d = base / split
            if not d.exists():
                continue
            images = [p for p in d.iterdir() if p.suffix.lower() in img_exts]
            splits[split] = images
        if not splits:
            logger.warning("external_base 에서 train/val/test 디렉터리를 찾지 못함: %s", base)
            return {"train": 0, "val": 0, "test": 0, "strategy": "external_base:empty"}
        if link_external:
            for split, imgs in splits.items():
                img_dir = ensure_dir(YOLO / "images" / split)
                lbl_dir = ensure_dir(YOLO / "labels" / split)
                for img in imgs:
                    symlink_or_copy(img, img_dir / img.name)
                    lbl_candidate = img.with_suffix(".txt")
                    if lbl_candidate.exists():
                        symlink_or_copy(lbl_candidate, lbl_dir / lbl_candidate.name)
            (YOLO / "_EXTERNAL_LINKED").write_text("ok", encoding="utf-8")
        stats = {k: len(v) for k, v in splits.items()}
        logger.info(
            "External base dataset detected %s", ", ".join(f"{k}={len(v)}" for k, v in splits.items())
        )
        return {**{s: stats.get(s, 0) for s in ("train", "val", "test")}, "strategy": "external_base", "linked": link_external}
    # manual 감지 (사용자 제공) 우선
    manual_info = _detect_manual()
    if strategy == "manual" or (manual_info and strategy is None):
        if not manual_info:
            logger.warning("manual 모드이지만 존재하는 manifest/dir 구조를 찾지 못함")
            return {"train": 0, "val": 0, "test": 0, "strategy": "manual"}
        logger.info(
            "Manual dataset detected mode=%s train=%d val=%d test=%d (no split)",
            manual_info["mode"],
            manual_info["train"],
            manual_info["val"],
            manual_info["test"],
        )
        return {
            "train": manual_info["train"],
            "val": manual_info["val"],
            "test": manual_info["test"],
            "strategy": f"manual::{manual_info['mode']}",
        }

    # 자동 전략 결정
    if strategy is None:
        # prefix 패턴 자동 감지 우선
        if _collect_prefix_split() is not None:
            strategy = "prefix"
        else:
            strategy = "folders"  # 기본

    if strategy == "manifest":
        # raw/interim에서 분할 -> manifest 작성 (test 분할 생략)
        random.seed(seed)
        all_imgs = list_images(INTERIM)
        if not all_imgs:
            logger.warning("No images to split in %s", INTERIM)
            return {"train": 0, "val": 0, "strategy": strategy}
        random.shuffle(all_imgs)
        split_idx = int(len(all_imgs) * train_ratio)
        train_imgs = all_imgs[:split_idx]
        val_imgs = all_imgs[split_idx:]
        ensure_dir(YOLO)
        (YOLO / "train.txt").write_text(
            "\n".join(str(p.resolve()) for p in train_imgs) + "\n", encoding="utf-8"
        )
        (YOLO / "val.txt").write_text(
            "\n".join(str(p.resolve()) for p in val_imgs) + "\n", encoding="utf-8"
        )
        (YOLO / "_MANIFEST_SPLIT_DONE").write_text("ok", encoding="utf-8")
        logger.info(
            "Manifest split complete train=%d val=%d", len(train_imgs), len(val_imgs)
        )
        return {"train": len(train_imgs), "val": len(val_imgs), "strategy": strategy}

    if strategy == "folders":
        random.seed(seed)
        all_imgs = list_images(INTERIM)
        if not all_imgs:
            logger.warning("No images to split in %s", INTERIM)
            return {"train": 0, "val": 0, "strategy": strategy}
        random.shuffle(all_imgs)
        split_idx = int(len(all_imgs) * train_ratio)
        train_imgs = all_imgs[:split_idx]
        val_imgs = all_imgs[split_idx:]
        for subset, imgs in {"train": train_imgs, "val": val_imgs}.items():
            img_dir = ensure_dir(YOLO / "images" / subset)
            lbl_dir = ensure_dir(YOLO / "labels" / subset)
            for img in imgs:
                symlink_or_copy(img, img_dir / img.name)
                lbl_src = LABELS / (img.stem + ".txt")
                if lbl_src.exists():
                    symlink_or_copy(lbl_src, lbl_dir / lbl_src.name)
        (YOLO / "_SPLIT_DONE").write_text("ok", encoding="utf-8")
        logger.info(
            "Folder split complete train=%d val=%d", len(train_imgs), len(val_imgs)
        )
        return {"train": len(train_imgs), "val": len(val_imgs), "strategy": strategy}

    if strategy == "prefix":
        bucket = _collect_prefix_split()
        if not bucket:
            logger.warning("prefix 전략 선택했지만 접두어(train-/val-/test-) 파일을 찾지 못함")
            return {"train": 0, "val": 0, "test": 0, "strategy": strategy}
        # 각 split 별 대상 복사/링크
        stats = {}
        for split, items in bucket.items():
            img_dir = ensure_dir(YOLO / "images" / split)
            lbl_dir = ensure_dir(YOLO / "labels" / split)
            for img in items:
                # prefix 제거 파일명 (train-cat.jpg -> cat.jpg)
                if keep_prefix:
                    new_name = img.name
                else:
                    lower = img.name
                    # 첫 '-' 이전 부분 제거
                    if '-' in lower:
                        new_name = img.name.split('-', 1)[1]
                    else:
                        new_name = img.name
                target_img = img_dir / new_name
                symlink_or_copy(img, target_img)
                # 라벨 찾기: 동일 원본 stem + .txt (원본 파일명 기준)
                label_src = LABELS / (img.stem + ".txt")
                if label_src.exists():
                    if keep_prefix:
                        label_name = label_src.name
                    else:
                        if '-' in label_src.name:
                            label_name = label_src.name.split('-', 1)[1]
                        else:
                            label_name = label_src.name
                    symlink_or_copy(label_src, lbl_dir / label_name)
            stats[split] = len(items)
        (YOLO / "_PREFIX_SPLIT_DONE").write_text("ok", encoding="utf-8")
        logger.info(
            "Prefix split complete %s", ", ".join(f"{k}={v}" for k, v in stats.items())
        )
        return {**stats, "strategy": strategy, "keep_prefix": keep_prefix}

    raise ValueError(f"Unknown strategy: {strategy}")