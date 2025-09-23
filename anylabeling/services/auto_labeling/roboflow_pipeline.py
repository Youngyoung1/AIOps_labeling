"""
Roboflow 자동화 파이프라인

기존 auto_labeling 시스템과 통합된 Roboflow 파이프라인
"""

import os
from typing import Dict, Any, Optional

# 기존 auto_labeling 모듈과의 통합
from ..auto_labeling.model import Model
from ..roboflow.roboflow_client import RoboflowClient, RoboflowConfig
from ..roboflow.pipeline_automation import PipelineAutomation, PipelineConfig


class RoboflowPipeline(Model):
    """Roboflow 자동화 파이프라인 모델"""
    
    class Meta:
        required_config_names = ['roboflow_api_key', 'roboflow_workspace', 'roboflow_project']
        widgets = ['button']
        output_modes = ['pipeline']
        default_output_mode = 'pipeline'
    
    def __init__(self, config_path: str, on_message):
        super().__init__(config_path, on_message)
        self.roboflow_client: Optional[RoboflowClient] = None
        self.pipeline_automation: Optional[PipelineAutomation] = None
        self._initialize_roboflow()
    
    def _initialize_roboflow(self):
        """Roboflow 클라이언트 초기화"""
        try:
            api_key = self.config.get('roboflow_api_key', '')
            workspace = self.config.get('roboflow_workspace', '')
            project = self.config.get('roboflow_project', '')
            
            if not all([api_key, workspace, project]):
                self.on_message("Roboflow 설정이 불완전합니다. API 키, 워크스페이스, 프로젝트를 설정하세요.")
                return
            
            roboflow_config = RoboflowConfig(
                api_key=api_key,
                workspace=workspace,
                project=project
            )
            
            self.roboflow_client = RoboflowClient(roboflow_config)
            self.pipeline_automation = PipelineAutomation(self.roboflow_client)
            
            # 상태 콜백 설정
            self.pipeline_automation.set_status_callback(self._on_pipeline_status_change)
            
            self.on_message("Roboflow 클라이언트가 초기화되었습니다.")
            
        except Exception as e:
            self.on_message(f"Roboflow 초기화 중 오류: {str(e)}")
    
    def _on_pipeline_status_change(self, status, progress, message):
        """파이프라인 상태 변경 콜백"""
        self.on_message(f"[{status.value.upper()}] {progress}% - {message}")
    
    def predict_shapes(self, image, image_path=None):
        """
        기존 auto_labeling 인터페이스 호환성을 위한 메서드
        실제로는 파이프라인 실행 버튼 역할
        """
        return []  # 직접적인 예측은 하지 않음
    
    def run_pipeline(self, mongo_storage, dataset_name: str, query: Dict[str, Any] = None) -> bool:
        """파이프라인 실행"""
        if not self.pipeline_automation:
            self.on_message("Roboflow가 초기화되지 않았습니다.")
            return False
        
        try:
            config = PipelineConfig(
                dataset_name=dataset_name,
                description=f"X-AnyLabeling에서 생성된 데이터셋: {dataset_name}",
                train_ratio=0.7,
                val_ratio=0.2,
                test_ratio=0.1,
                auto_annotate=self.config.get('auto_training', False)
            )
            
            return self.pipeline_automation.run_full_pipeline(mongo_storage, config, query)
            
        except Exception as e:
            self.on_message(f"파이프라인 실행 중 오류: {str(e)}")
            return False
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """파이프라인 상태 조회"""
        if not self.pipeline_automation:
            return {"status": "not_initialized", "progress": 0, "is_running": False}
        
        return self.pipeline_automation.get_pipeline_status()
    
    def test_connection(self) -> bool:
        """Roboflow 연결 테스트"""
        if not self.roboflow_client:
            return False
        
        return self.roboflow_client.test_connection()
    
    def unload(self):
        """모델 언로드"""
        self.roboflow_client = None
        self.pipeline_automation = None
        super().unload()