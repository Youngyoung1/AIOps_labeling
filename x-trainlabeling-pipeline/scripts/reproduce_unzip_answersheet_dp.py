"""answersheet_dp DAG 의 unzip_files 태스크 + JPG fallback 재현 스크립트.

시나리오 지원:
    A) ZIP 존재: folder_path/<YYMMDD>.zip → folder_path/<YYMMDD>/ 로 압축 해제
    B) ZIP 없음 + folder_path/<YYMMDD>/ 이미 존재: 그대로 사용
    C) ZIP 없음 + 날짜 디렉터리 없음 + folder_path 에 jpg 들만 있는 경우:
         jpg 파일을 folder_path/<YYMMDD>/ 로 복사(또는 심볼릭 링크)하여 동일 구조 생성

기본 동작:
 1) 어제 날짜(Asia/Seoul 기준)를 answersheet_dp DAG 와 동일 포맷(YYMMDD)으로 산출(미지정 시)
 2) 위 우선순위(A→B→C)로 처리
 3) 처리 후 최종 경로 출력

사용 예시:
    python reproduce_unzip_answersheet_dp.py --folder /mnt/s/04.seatbelt --date 230831
    python reproduce_unzip_answersheet_dp.py --folder /data/images --prefer-copy

옵션:
    --prefer-copy : fallback(C) 모드에서 symlink 대신 파일 복사 사용
    --force       : 기존 생성 디렉터리가 있어도 재구성 (C 모드)
"""
from __future__ import annotations
import argparse
from pathlib import Path
import zipfile
import datetime
import sys
import os
import shutil

TRY_TZ = None
try:
    import pendulum  # type: ignore
    TRY_TZ = pendulum.timezone("Asia/Seoul")
except Exception:  # pragma: no cover
    TRY_TZ = None


def calc_default_date() -> str:
    if TRY_TZ:
        now = pendulum.now("Asia/Seoul")
    else:
        now = datetime.datetime.now()
    yday = now - datetime.timedelta(days=1)
    # YYMMDD
    return f"{str(yday.year)[2:4]}{yday.month:02d}{yday.day:02d}"


def _log_path_existence(zip_file_path: Path):
    # 원래 DAG 출력 형태 재현
    print(f"{zip_file_path.exists()}: zip_path")
    print(f"{Path('/mnt/s/04.seatbelt').exists()}: s_seatbelt_path")
    print(f"{Path('/mnt/s/04.seatbelt/01.수집데이터').exists()}: s_collected_path")


def ensure_dataset(folder_path: Path, date: str, prefer_copy: bool = False, force: bool = False) -> Path:
    """ZIP 또는 JPG fallback 으로 날짜 디렉터리 확보.

    반환: 최종 이미지 디렉터리 Path
    """
    zip_file_path = folder_path / f"{date}.zip"
    extract_path = folder_path / date
    _log_path_existence(zip_file_path)

    # A) ZIP 존재 → 압축 해제
    if zip_file_path.exists():
        extract_path.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_file_path, "r") as zf:
            zf.extractall(extract_path)
        print(f"[MODE=A:ZIP] Extracted to: {extract_path}")
        return extract_path

    # B) ZIP 없음 + 날짜 디렉터리 이미 존재
    if extract_path.exists():
        print(f"[MODE=B:EXISTING] Using existing directory: {extract_path}")
        return extract_path

    # C) fallback - folder_path 내 jpg 수집 후 생성
    exts = {".jpg", ".jpeg", ".png"}
    imgs = [p for p in folder_path.iterdir() if p.suffix.lower() in exts]
    if not imgs:
        raise FileNotFoundError(
            f"ZIP도 없고 JPG도 찾을 수 없습니다. (searched in: {folder_path})"
        )
    extract_path.mkdir(parents=True, exist_ok=True)
    if force and any(extract_path.iterdir()):
        for item in extract_path.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        print(f"[FORCE] Cleared existing contents of {extract_path}")
    copied = 0
    for img in imgs:
        target = extract_path / img.name
        if target.exists():
            continue
        if prefer_copy:
            shutil.copy2(img, target)
        else:
            try:
                target.symlink_to(img)
            except OSError:
                shutil.copy2(img, target)
        copied += 1
    mode = "copy" if prefer_copy else "link/copy"
    print(f"[MODE=C:JPG-FALLBACK] Prepared {extract_path} files={copied} mode={mode}")
    return extract_path


def main():
    parser = argparse.ArgumentParser(description="answersheet_dp unzip_files 재현")
    parser.add_argument("--folder", "--folder_path", dest="folder_path", default="/mnt/s/04.seatbelt", help="ZIP 또는 JPG 가 있는 폴더")
    parser.add_argument("--date", dest="date", default=None, help="YYMMDD (미지정 시 어제 날짜 자동)")
    parser.add_argument("--prefer-copy", action="store_true", help="fallback(C) 모드에서 symlink 대신 복사 사용")
    parser.add_argument("--force", action="store_true", help="fallback(C) 모드 생성 디렉터리 초기화 후 재구성")
    parser.add_argument("--recursive", action="store_true", help="fallback(C) 모드에서 하위 디렉터리까지 이미지 탐색")
    args = parser.parse_args()

    date = args.date or calc_default_date()
    folder_path = Path(args.folder_path).resolve()
    try:
        # ensure_dataset 내부를 변경하지 않고 recursive 처리를 사전 준비
        if args.recursive:
            # fallback(C) 상황 대비: 상위 폴더에 직접 이미지가 없고 하위에만 있는 경우 상위로 올림용 임시 링크 디렉터리 구성
            exts = {".jpg", ".jpeg", ".png"}
            direct_imgs = [p for p in folder_path.iterdir() if p.suffix.lower() in exts] if folder_path.exists() else []
            if not direct_imgs:
                collected = [p for p in folder_path.rglob("*") if p.is_file() and p.suffix.lower() in exts]
                if collected:
                    staging = folder_path / "_recursive_flat_temp"
                    staging.mkdir(exist_ok=True)
                    created = 0
                    for img in collected:
                        target = staging / img.name
                        if target.exists():
                            continue
                        try:
                            target.symlink_to(img)
                        except OSError:
                            import shutil as _sh
                            _sh.copy2(img, target)
                        created += 1
                    print(f"[RECURSIVE] Collected {created} images into {staging}")
        extracted = ensure_dataset(folder_path, date, prefer_copy=args.prefer_copy, force=args.force)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1
    print(f"DONE: {extracted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
