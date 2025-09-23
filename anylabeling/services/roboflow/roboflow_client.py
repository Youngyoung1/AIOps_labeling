"""
로컬 데이터셋 관리자

이 모듈은 API 없이 로컬에서 데이터셋을 관리합니다.
"""

import os
import shutil
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LocalDatasetConfig:
    """로컬 데이터셋 설정 클래스"""
    output_directory: str
    dataset_name: str
    create_subfolders: bool = True
    copy_images: bool = True


class LocalDatasetManager:
    """로컬 데이터셋 관리자 (API 없음)"""
    
    def __init__(self, config: LocalDatasetConfig):
        self.config = config
        self.dataset_path = Path(config.output_directory) / config.dataset_name
    
    def test_connection(self) -> bool:
        """로컬 디렉토리 접근 테스트"""
        try:
            os.makedirs(self.config.output_directory, exist_ok=True)
            return True
        except Exception as e:
            print(f"로컬 디렉토리 접근 실패: {e}")
            return False
    
    def create_dataset_structure(self) -> Dict[str, Any]:
        """로컬 데이터셋 폴더 구조 생성"""
        try:
            # 기본 폴더 구조 생성
            folders = ['images', 'labels']
            if self.config.create_subfolders:
                subfolders = ['train', 'val', 'test']
                for folder in folders:
                    for subfolder in subfolders:
                        folder_path = self.dataset_path / folder / subfolder
                        folder_path.mkdir(parents=True, exist_ok=True)
            else:
                for folder in folders:
                    folder_path = self.dataset_path / folder
                    folder_path.mkdir(parents=True, exist_ok=True)
            
            return {
                "success": True,
                "dataset_path": str(self.dataset_path),
                "message": "데이터셋 폴더 구조가 생성되었습니다."
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"폴더 구조 생성 실패: {str(e)}"
            }
    
    def save_dataset_info(self, dataset_info: Dict[str, Any]) -> bool:
        """데이터셋 정보를 파일로 저장"""
        try:
            import json
            info_file = self.dataset_path / "dataset_info.json"
            
            summary = {
                "dataset_name": self.config.dataset_name,
                "total_images": dataset_info.get("total_images", 0),
                "total_annotations": dataset_info.get("annotations", 0),
                "classes": dataset_info.get("classes", []),
                "created_at": str(Path.ctime(Path.cwd())),
                "source": "X-AnyLabeling MongoDB"
            }
            
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"데이터셋 정보 저장 실패: {e}")
            return False
    
    def get_output_path(self) -> str:
        """출력 경로 반환"""
        return str(self.dataset_path)