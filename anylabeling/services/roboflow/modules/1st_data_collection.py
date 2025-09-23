"""
1. 데이터 수집 및 관리 (Data Collection & Management)

이미지 업로드, 포맷 검증, 데이터셋 구조 검증을 담당하는 모듈
"""

import os
import shutil
import subprocess
import platform
from typing import Dict, List, Any, Optional
from pathlib import Path

class DataCollectionManager:
    """데이터 수집 및 관리 클래스"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.supported_formats = self.config.get('supported_formats', ['.jpg', '.jpeg', '.png', '.bmp', '.tiff'])
        self.max_file_size = self.config.get('max_file_size', 5 * 1024 * 1024 * 1024)  # MAX 파일 크기 5GB
        
    def upload_images(self, input_path: str) -> Dict[str, Any]:
        """
        이미지 일괄 업로드
        
        Args:
            input_path: 입력 이미지 폴더 경로
            
        Returns:
            업로드 결과 딕셔너리
        """
        try:
            input_path = Path(input_path)
            if not input_path.exists():
                return {"success": False, "error": f"입력 경로가 존재하지 않습니다: {input_path}"}
            
            uploaded_files = []
            failed_files = []
            
            # 지원되는 이미지 파일 찾기
            for ext in self.supported_formats:
                pattern = f"*{ext}"
                files = list(input_path.glob(pattern)) + list(input_path.glob(pattern.upper()))
                
                for file_path in files:
                    try:
                        if file_path.stat().st_size > self.max_file_size:
                            failed_files.append({
                                "file": str(file_path),
                                "reason": f"파일 크기 초과 (최대 {self.max_file_size} bytes)"
                            })
                            continue
                        
                        uploaded_files.append({
                            "path": str(file_path),
                            "size": file_path.stat().st_size,
                            "name": file_path.name
                        })
                        
                    except Exception as e:
                        failed_files.append({
                            "file": str(file_path),
                            "reason": f"업로드 실패: {str(e)}"
                        })
            
            return {
                "success": True,
                "uploaded_files": uploaded_files,
                "failed_files": failed_files,
                "total_uploaded": len(uploaded_files),
                "total_failed": len(failed_files)
            }
            
        except Exception as e:
            return {"success": False, "error": f"업로드 중 오류: {str(e)}"}
    
    def validate_image_format(self, uploaded_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        이미지 포맷 검증
        
        Args:
            uploaded_files: 업로드된 파일 리스트
            
        Returns:
            검증 결과 딕셔너리
        """
        try:
            from PIL import Image
            
            valid_files = []
            invalid_files = []
            
            for file_info in uploaded_files:
                file_path = Path(file_info['path'])
                
                try:
                    with Image.open(file_path) as img:
                        if img.width > 0 and img.height > 0:
                            valid_files.append({
                                **file_info,
                                "width": img.width,
                                "height": img.height,
                                "mode": img.mode,
                                "format": img.format
                            })
                        else:
                            invalid_files.append({
                                "file": file_info['path'],
                                "reason": "유효하지 않은 이미지 크기"
                            })
                            
                except Exception as e:
                    invalid_files.append({
                        "file": file_info['path'],
                        "reason": f"이미지 포맷 오류: {str(e)}"
                    })
            
            return {
                "success": True,
                "valid_files": valid_files,
                "invalid_files": invalid_files,
                "validation_summary": {
                    "total_checked": len(uploaded_files),
                    "valid_count": len(valid_files),
                    "invalid_count": len(invalid_files)
                }
            }
        except Exception as e:
            return {"success": False, "error": f"포맷 검증 중 오류: {str(e)}"}
    
    def organize_dataset(self, dataset_path: str) -> Dict[str, Any]:
        """
        사용자가 직접 만든 데이터셋 폴더 구조 검증
        train/val/test 폴더가 존재하는지 확인하고 각 폴더의 파일 현황을 반환
        이미지 파일이 없으면 파일 탐색기를 열어 사용자가 직접 찾도록 안내
        
        Args:
            dataset_path: 데이터셋 경로 (train, val, test 폴더가 있어야 함)
            
        Returns:
            폴더 구조 검증 결과 딕셔너리
        """
        try:
            dataset_path = Path(dataset_path)
            
            if not dataset_path.exists():
                return {"success": False, "error": f"데이터셋 경로가 존재하지 않습니다: {dataset_path}"}
            
            # 필수 폴더 확인
            required_folders = ["train", "val", "test"]
            existing_folders = []
            missing_folders = []
            folder_status = {}
            folders_needing_files = []
            
            for folder in required_folders:
                folder_path = dataset_path / folder
                if folder_path.exists() and folder_path.is_dir():
                    existing_folders.append(folder)
                    
                    image_files = []
                    txt_files = []
                    
                    for ext in self.supported_formats:
                        pattern = f"*{ext}"
                        image_files.extend(list(folder_path.glob(pattern)))
                        image_files.extend(list(folder_path.glob(pattern.upper())))
                    
                    # 이미지 파일이 없으면 파일 탐색기 열기 제안
                    if not image_files:
                        folders_needing_files.append({
                            'folder': folder,
                            'path': str(folder_path)
                        })
                    
                    txt_files = list(folder_path.glob("*.txt"))
                    
                    # 매칭된 쌍 확인 (val 폴더는 txt 파일이 선택사항)
                    matched_pairs = 0
                    unmatched_images = []
                    unmatched_txt = []
                    
                    if folder == "val":
                        matched_pairs = len(image_files)  # 모든 이미지를 매칭된 것으로 간주
                        
                        # val 폴더에 txt 파일이 있다면 매칭 여부 확인 (선택사항)
                        for txt_file in txt_files:
                            img_exists = False
                            for ext in self.supported_formats:
                                if (txt_file.with_suffix(ext).exists() or 
                                    txt_file.with_suffix(ext.upper()).exists()):
                                    img_exists = True
                                    break
                    
                    else:
                        # train, test 폴더는 이미지-txt 쌍이 필수
                        for img_file in image_files:
                            txt_file = img_file.with_suffix('.txt')
                            if txt_file in txt_files:
                                matched_pairs += 1
                            else:
                                unmatched_images.append(img_file.name)
                        
                        for txt_file in txt_files:
                            img_exists = False
                            for ext in self.supported_formats:
                                if (txt_file.with_suffix(ext).exists() or 
                                    txt_file.with_suffix(ext.upper()).exists()):
                                    img_exists = True
                                    break
                            if not img_exists:
                                unmatched_txt.append(txt_file.name)
                    
                    folder_status[folder] = {
                        "path": str(folder_path),
                        "image_count": len(image_files),
                        "txt_count": len(txt_files),
                        "matched_pairs": matched_pairs,
                        "unmatched_images": unmatched_images,
                        "unmatched_txt": unmatched_txt
                    }
                else:
                    missing_folders.append(folder)
            
            # 이미지 파일이 없는 폴더들에 대해 파일 탐색기 열기
            if folders_needing_files:
                self._open_file_explorer_for_empty_folders(folders_needing_files)
            
            # 전체 현황 요약
            total_images = sum([folder_status[f]["image_count"] for f in existing_folders])
            total_txt = sum([folder_status[f]["txt_count"] for f in existing_folders])
            total_matched = sum([folder_status[f]["matched_pairs"] for f in existing_folders])
            
            # 성공 조건: 모든 필수 폴더 존재 + 이미지 있음 + train/test의 매칭률 확인
            val_images = folder_status.get("val", {}).get("image_count", 0)
            train_images = folder_status.get("train", {}).get("image_count", 0)
            test_images = folder_status.get("test", {}).get("image_count", 0)
            train_matched = folder_status.get("train", {}).get("matched_pairs", 0)
            test_matched = folder_status.get("test", {}).get("matched_pairs", 0)
            
            # train/test는 100% 매칭 필요, val은 이미지만 있으면 됨
            train_complete = (train_images == 0) or (train_images > 0 and train_matched == train_images)
            test_complete = (test_images == 0) or (test_images > 0 and test_matched == test_images)
            val_complete = val_images > 0  # val은 이미지만 있으면 됨
            
            dataset_complete = len(missing_folders) == 0 and total_images > 0 and train_complete and test_complete
            
            return {
                "success": dataset_complete,
                "dataset_path": str(dataset_path),
                "existing_folders": existing_folders,
                "missing_folders": missing_folders,
                "folders_needing_files": folders_needing_files,
                "folder_details": folder_status,
                "summary": {
                    "total_images": total_images,
                    "total_txt_files": total_txt,
                    "total_matched_pairs": total_matched,
                    "completion_rate": (total_matched / total_images * 100) if total_images > 0 else 0,
                    "train_complete": train_complete,
                    "val_complete": val_complete,
                    "test_complete": test_complete
                },
                "recommendations": self._get_organization_recommendations(folder_status, missing_folders, folders_needing_files)
            }
            
        except Exception as e:
            return {"success": False, "error": f"폴더 구조 검증 중 오류: {str(e)}"}
    
    def _open_file_explorer_for_empty_folders(self, folders_needing_files: List[Dict[str, str]]) -> None:
        """
        이미지 파일이 없는 폴더들에 대해 파일 탐색기를 열어서 사용자가 직접 파일을 추가하도록 안내
        
        Args:
            folders_needing_files: 이미지 파일이 없는 폴더들의 정보 리스트
        """
        try:
            current_os = platform.system()
            
            for folder_info in folders_needing_files:
                folder_name = folder_info['folder']
                folder_path = folder_info['path']
                
                print(f"\n⚠️  '{folder_name}' 폴더에 이미지 파일이 없습니다!")
                print(f"📁 폴더 경로: {folder_path}")
                print(f"🔍 파일 탐색기를 열어서 이미지 파일을 추가해주세요...")
                
                # 운영체제별로 파일 탐색기 열기
                if current_os == "Windows":
                    # Windows 탐색기 열기
                    subprocess.run(['explorer', folder_path], check=False)
                elif current_os == "Linux":
                    try:
                        subprocess.run(['xdg-open', folder_path], check=False)
                    except:
                        try:
                            subprocess.run(['nautilus', folder_path], check=False)
                        except:
                            print(f"수동으로 파일 매니저를 열어서 {folder_path}로 이동해주세요.")
                
                print(f"✅ 이미지 파일을 추가한 후 다시 organize_dataset()을 실행해주세요.\n")
        except Exception as e:
            print(f"❌ 파일 탐색기 열기 실패: {str(e)}")
            print("수동으로 파일 탐색기를 열어서 이미지 파일을 추가해주세요.")
    
    def _get_organization_recommendations(self, folder_status: Dict, missing_folders: List[str], folders_needing_files: List[Dict[str, str]]) -> List[str]:
        """데이터셋 구조 개선 권장사항 생성"""
        recommendations = []
        
        if missing_folders:
            recommendations.append(f"누락된 폴더를 생성하세요: {', '.join(missing_folders)}")
        
        if folders_needing_files:
            folder_names = [f['folder'] for f in folders_needing_files]
            recommendations.append(f"다음 폴더에 이미지 파일을 추가하세요: {', '.join(folder_names)}")
            recommendations.append("파일 탐색기가 자동으로 열렸습니다. 이미지 파일을 해당 폴더에 복사해주세요.")
        
        for folder, status in folder_status.items():
            if folder == "val":
                if status["image_count"] == 0:
                    recommendations.append(f"{folder} 폴더: 이미지 파일이 없습니다")
                if status["unmatched_txt"]:
                    recommendations.append(f"{folder} 폴더: {len(status['unmatched_txt'])}개 txt 파일에 대응하는 이미지가 없습니다 (선택사항)")
            else:
                # train, test 폴더는 이미지-txt 쌍 필수
                if status["unmatched_images"]:
                    recommendations.append(f"{folder} 폴더: {len(status['unmatched_images'])}개 이미지에 대응하는 txt 파일이 없습니다 (필수)")
                
                if status["unmatched_txt"]:
                    recommendations.append(f"{folder} 폴더: {len(status['unmatched_txt'])}개 txt 파일에 대응하는 이미지가 없습니다")
                
                if status["image_count"] == 0:
                    recommendations.append(f"{folder} 폴더: 이미지 파일이 없습니다")
        
        if not recommendations:
            recommendations.append("✅ 데이터셋 구조가 올바르게 구성되어 있습니다!")
        
        return recommendations