"""
로컬 데이터셋 생성 자동화

이 모듈은 MongoDB에서 로컬 YOLO 데이터셋 생성을 자동화합니다.
"""

import os
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from .roboflow_client import LocalDatasetManager
from .dataset_manager import DatasetManager


class PipelineStatus(Enum):
    """파이프라인 상태"""
    IDLE = "idle"
    PREPARING = "preparing"
    CONVERTING = "converting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class PipelineConfig:
    """파이프라인 설정"""
    dataset_name: str
    output_directory: str
    description: str = ""
    train_ratio: float = 0.7
    val_ratio: float = 0.2
    test_ratio: float = 0.1
    copy_images: bool = True
    create_subfolders: bool = True


class PipelineAutomation:
    """로컬 데이터셋 생성 자동화 클래스"""
    
    def __init__(self, client: LocalDatasetManager):
        self.client = client
        self.dataset_manager = DatasetManager(client)
        self.status = PipelineStatus.IDLE
        self.progress = 0
        self.status_callback: Optional[Callable] = None
    
    def set_status_callback(self, callback: Callable[[PipelineStatus, int, str], None]):
        """상태 변경 콜백 설정"""
        self.status_callback = callback
    
    def _update_status(self, status: PipelineStatus, progress: int = 0, message: str = ""):
        """상태 업데이트"""
        self.status = status
        self.progress = progress
        if self.status_callback:
            self.status_callback(status, progress, message)
    
    def run_full_pipeline(self, mongo_storage, config: PipelineConfig, query: Dict[str, Any] = None) -> bool:
        """전체 파이프라인 실행"""
        try:
            self._update_status(PipelineStatus.PREPARING, 10, "MongoDB에서 데이터 로딩 중...")
            
            # 1. 데이터셋 준비
            dataset_info = self.dataset_manager.prepare_dataset_from_mongodb(mongo_storage, query)
            if not dataset_info or dataset_info.get("total_images", 0) == 0:
                self._update_status(PipelineStatus.ERROR, 0, "데이터셋을 찾을 수 없습니다")
                return False
            
            total_images = dataset_info.get("total_images", 0)
            total_classes = len(dataset_info.get("classes", []))
            
            self._update_status(PipelineStatus.PREPARING, 30, 
                f"{total_images}개 이미지, {total_classes}개 클래스 발견")
            
            # 2. 클라이언트 설정 업데이트
            from .roboflow_client import LocalDatasetConfig
            local_config = LocalDatasetConfig(
                output_directory=config.output_directory,
                dataset_name=config.dataset_name,
                create_subfolders=config.create_subfolders,
                copy_images=config.copy_images
            )
            self.client.config = local_config
            self.client.dataset_path = self.client.dataset_path.parent / config.dataset_name
            
            self._update_status(PipelineStatus.CONVERTING, 50, "YOLO 형식으로 변환 중...")
            
            # 3. 로컬 YOLO 데이터셋 생성
            success = self.dataset_manager.create_local_yolo_dataset(
                dataset_info,
                config.train_ratio,
                config.val_ratio,
                config.test_ratio
            )
            
            if not success:
                self._update_status(PipelineStatus.ERROR, 0, "YOLO 데이터셋 생성 실패")
                return False
            
            output_path = self.client.get_output_path()
            self._update_status(PipelineStatus.COMPLETED, 100, 
                f"데이터셋 생성 완료!\n경로: {output_path}")
            
            return True
            
        except Exception as e:
            self._update_status(PipelineStatus.ERROR, 0, f"파이프라인 실행 중 오류: {str(e)}")
            return False
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """현재 파이프라인 상태 반환"""
        return {
            "status": self.status.value,
            "progress": self.progress,
            "is_running": self.status not in [PipelineStatus.IDLE, PipelineStatus.COMPLETED, PipelineStatus.ERROR]
        }
    
    def get_output_directory(self) -> str:
        """출력 디렉토리 반환"""
        return self.client.get_output_path() if self.client else ""