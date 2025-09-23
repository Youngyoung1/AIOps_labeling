"""
통합 자동화 파이프라인 모듈

이 모듈은 전체 데이터 처리 워크플로우를 관리하는 메인 컨트롤러입니다.
"""

import os
from typing import Dict, List, Any, Optional
from pathlib import Path

from .modules.data_collection import DataCollectionManager
from .modules.auto_annotation import AutoAnnotationManager
from .modules.data_preprocessing import DataPreprocessingManager
from .modules import DataAugmentationManager
from .modules import QualityAssuranceManager
from .modules import DatasetSplittingManager


class AutomationPipeline:
    """통합 자동화 파이프라인 관리 클래스"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        파이프라인 초기화
        
        Args:
            config: 파이프라인 설정 딕셔너리
        """
        self.config = config or {}
        
        # 각 모듈 초기화
        self.data_collection = DataCollectionManager(self.config.get('data_collection', {}))
        self.auto_annotation = AutoAnnotationManager(self.config.get('auto_annotation', {}))
        self.data_preprocessing = DataPreprocessingManager(self.config.get('preprocessing', {}))
        self.data_augmentation = DataAugmentationManager(self.config.get('augmentation', {}))
        self.quality_assurance = QualityAssuranceManager(self.config.get('quality', {}))
        self.dataset_splitting = DatasetSplittingManager(self.config.get('splitting', {}))
        
        # 파이프라인 상태
        self.current_step = 0
        self.total_steps = 6
        self.results = {}
    
    def run_full_pipeline(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """
        전체 파이프라인 실행
        
        Args:
            input_path: 입력 데이터 경로
            output_path: 출력 데이터 경로
            
        Returns:
            처리 결과 딕셔너리
        """
        print("🚀 자동화 파이프라인 시작")
        
        try:
            # 1. 데이터 수집 및 관리
            print("📁 1단계: 데이터 수집 및 관리")
            self.current_step = 1
            collection_result = self._run_data_collection(input_path, output_path)
            self.results['data_collection'] = collection_result
            
            # 2. 자동 어노테이션
            print("🤖 2단계: 자동 어노테이션")
            self.current_step = 2
            annotation_result = self._run_auto_annotation(collection_result['dataset_path'])
            self.results['auto_annotation'] = annotation_result
            
            # 3. 데이터 전처리
            print("⚙️ 3단계: 데이터 전처리")
            self.current_step = 3
            preprocessing_result = self._run_preprocessing(annotation_result['processed_data'])
            self.results['preprocessing'] = preprocessing_result
            
            # 4. 데이터 증강
            print("📈 4단계: 데이터 증강")
            self.current_step = 4
            augmentation_result = self._run_augmentation(preprocessing_result['processed_data'])
            self.results['augmentation'] = augmentation_result
            
            # 5. 품질 관리
            print("✅ 5단계: 품질 관리")
            self.current_step = 5
            quality_result = self._run_quality_assurance(augmentation_result['augmented_data'])
            self.results['quality'] = quality_result
            
            # 6. 데이터셋 분할
            print("📊 6단계: 데이터셋 분할")
            self.current_step = 6
            splitting_result = self._run_dataset_splitting(quality_result['validated_data'])
            self.results['splitting'] = splitting_result
            
            print("🎉 파이프라인 완료!")
            
            return {
                "success": True,
                "results": self.results,
                "final_dataset_path": splitting_result['output_path']
            }
            
        except Exception as e:
            print(f"❌ 파이프라인 실행 중 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "failed_step": self.current_step,
                "partial_results": self.results
            }
    
    def _run_data_collection(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """데이터 수집 및 관리 단계 실행"""
        # 이미지 업로드 및 관리
        upload_result = self.data_collection.upload_images(input_path)
        
        # 이미지 포맷 검증
        validation_result = self.data_collection.validate_image_format(upload_result['uploaded_files'])
        
        # 데이터셋 폴더 구조 생성
        organization_result = self.data_collection.organize_dataset(output_path)
        
        # 데이터셋 버전 관리
        version_result = self.data_collection.track_dataset_version(output_path)
        
        return {
            "upload": upload_result,
            "validation": validation_result,
            "organization": organization_result,
            "version": version_result,
            "dataset_path": organization_result['dataset_path']
        }
    
    def _run_auto_annotation(self, dataset_path: str) -> Dict[str, Any]:
        """자동 어노테이션 단계 실행"""
        # AI 기반 자동 라벨링
        detection_result = self.auto_annotation.auto_detect_objects(dataset_path)
        
        # 어노테이션 제안
        suggestion_result = self.auto_annotation.suggest_annotations(detection_result['detections'])
        
        # 스마트 폴리곤 생성
        polygon_result = self.auto_annotation.smart_polygon_tool(detection_result['detections'])
        
        # 일괄 어노테이션 처리
        batch_result = self.auto_annotation.batch_annotation(dataset_path, suggestion_result['suggestions'])
        
        return {
            "detection": detection_result,
            "suggestions": suggestion_result,
            "polygons": polygon_result,
            "batch_processing": batch_result,
            "processed_data": batch_result['output_path']
        }
    
    def _run_preprocessing(self, data_path: str) -> Dict[str, Any]:
        """데이터 전처리 단계 실행"""
        # 이미지 크기 표준화
        resize_result = self.data_preprocessing.resize_images(data_path)
        
        # 픽셀 값 정규화
        normalize_result = self.data_preprocessing.normalize_images(resize_result['processed_path'])
        
        # 필터 적용
        filter_result = self.data_preprocessing.apply_filters(normalize_result['processed_path'])
        
        # 크롭 및 패딩 처리
        crop_result = self.data_preprocessing.crop_and_pad(filter_result['processed_path'])
        
        return {
            "resize": resize_result,
            "normalize": normalize_result,
            "filters": filter_result,
            "crop_pad": crop_result,
            "processed_data": crop_result['processed_path']
        }
    
    def _run_augmentation(self, data_path: str) -> Dict[str, Any]:
        """데이터 증강 단계 실행"""
        # 자동 증강 정책 적용
        auto_aug_result = self.data_augmentation.auto_augmentation(data_path)
        
        # 회전 변환
        rotation_result = self.data_augmentation.rotation_augment(data_path)
        
        # 밝기/대비 조절
        brightness_result = self.data_augmentation.brightness_contrast(data_path)
        
        # 노이즈 추가
        noise_result = self.data_augmentation.noise_injection(data_path)
        
        # 기하학적 변환
        geometric_result = self.data_augmentation.geometric_transform(data_path)
        
        return {
            "auto_augmentation": auto_aug_result,
            "rotation": rotation_result,
            "brightness": brightness_result,
            "noise": noise_result,
            "geometric": geometric_result,
            "augmented_data": auto_aug_result['output_path']
        }
    
    def _run_quality_assurance(self, data_path: str) -> Dict[str, Any]:
        """품질 관리 단계 실행"""
        # 중복 이미지 탐지
        duplicate_result = self.quality_assurance.detect_duplicates(data_path)
        
        # 어노테이션 품질 검사
        annotation_quality_result = self.quality_assurance.check_annotation_quality(data_path)
        
        # 바운딩 박스 좌표 검증
        bbox_validation_result = self.quality_assurance.validate_bbox_coordinates(data_path)
        
        # 저품질 데이터 플래그
        quality_flag_result = self.quality_assurance.flag_poor_quality(data_path)
        
        return {
            "duplicates": duplicate_result,
            "annotation_quality": annotation_quality_result,
            "bbox_validation": bbox_validation_result,
            "quality_flags": quality_flag_result,
            "validated_data": quality_flag_result['cleaned_data_path']
        }
    
    def _run_dataset_splitting(self, data_path: str) -> Dict[str, Any]:
        """데이터셋 분할 단계 실행"""
        # 스마트 데이터 분할
        smart_split_result = self.dataset_splitting.smart_train_val_test_split(data_path)
        
        # 계층적 샘플링
        stratified_result = self.dataset_splitting.stratified_split(data_path)
        
        # 시간 기반 분할 (시계열 데이터용)
        temporal_result = self.dataset_splitting.temporal_split(data_path)
        
        return {
            "smart_split": smart_split_result,
            "stratified": stratified_result,
            "temporal": temporal_result,
            "output_path": smart_split_result['output_path']
        }
    
    def get_progress(self) -> Dict[str, Any]:
        """현재 진행 상태 반환"""
        return {
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "progress_percent": (self.current_step / self.total_steps) * 100,
            "completed_steps": list(self.results.keys())
        }
    
    def run_single_step(self, step_name: str, **kwargs) -> Dict[str, Any]:
        """특정 단계만 실행"""
        step_map = {
            "data_collection": self._run_data_collection,
            "auto_annotation": self._run_auto_annotation,
            "preprocessing": self._run_preprocessing,
            "augmentation": self._run_augmentation,
            "quality_assurance": self._run_quality_assurance,
            "dataset_splitting": self._run_dataset_splitting
        }
        
        if step_name not in step_map:
            raise ValueError(f"Unknown step: {step_name}")
        
        return step_map[step_name](**kwargs)