"""
Roboflow 설정

Roboflow API 연결을 위한 설정값들
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class RoboflowSettings:
    """Roboflow 설정 클래스"""
    api_key: str = ""
    workspace: str = ""
    project: str = ""
    base_url: str = "https://api.roboflow.com"
    
    # 기본 설정값
    default_train_ratio: float = 0.7
    default_val_ratio: float = 0.2
    default_test_ratio: float = 0.1
    
    # 업로드 설정
    batch_size: int = 50
    max_retries: int = 3
    timeout_seconds: int = 30
    
    @classmethod
    def from_env(cls) -> 'RoboflowSettings':
        """환경 변수에서 설정 로드"""
        return cls(
            api_key=os.getenv('ROBOFLOW_API_KEY', ''),
            workspace=os.getenv('ROBOFLOW_WORKSPACE', ''),
            project=os.getenv('ROBOFLOW_PROJECT', ''),
            base_url=os.getenv('ROBOFLOW_BASE_URL', cls.base_url)
        )
    
    def is_configured(self) -> bool:
        """설정이 완료되었는지 확인"""
        return bool(self.api_key and self.workspace and self.project)
    
    def get_project_url(self) -> str:
        """프로젝트 URL 생성"""
        if not self.is_configured():
            return ""
        return f"{self.base_url}/{self.workspace}/{self.project}"


# 기본 설정 인스턴스
default_settings = RoboflowSettings.from_env()


def get_roboflow_settings() -> RoboflowSettings:
    """Roboflow 설정 가져오기"""
    # TODO: 실제 앱 설정에서 로드하도록 구현
    return default_settings


def save_roboflow_settings(settings: RoboflowSettings):
    """Roboflow 설정 저장"""
    # TODO: 실제 앱 설정에 저장하도록 구현
    global default_settings
    default_settings = settings