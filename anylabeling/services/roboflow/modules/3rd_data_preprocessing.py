"""
3. 데이터 전처리 (Data Preprocessing)

현대적인 이미지 처리: 고성능 리사이징, 정규화, 필터링, 배치 처리를 담당하는 모듈
"""

import os
import time
import concurrent.futures
from multiprocessing import cpu_count
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
from PIL.ExifTags import ORIENTATION

# 선택적 의존성
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("💡 tqdm을 설치하면 진행률 표시가 가능합니다: pip install tqdm")

class DataPreprocessingManager:
    """현대적인 데이터 전처리 관리 클래스"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        초기화
        
        Args:
            config: 설정 딕셔너리
        """
        self.config = config or {}
        self.target_size = self.config.get('target_size', (640, 640))
        self.quality = self.config.get('output_quality', 95)
        self.keep_aspect_ratio = self.config.get('keep_aspect_ratio', True)
        self.padding_color = self.config.get('padding_color', (114, 114, 114))  # YOLO 기본값
        self.num_workers = self.config.get('num_workers', min(8, cpu_count()))
        
        # 지원하는 이미지 형식
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        
        print(f"🔧 데이터 전처리 설정:")
        print(f"   - 목표 크기: {self.target_size}")
        print(f"   - 종횡비 유지: {self.keep_aspect_ratio}")
        print(f"   - 병렬 처리: {self.num_workers}개 프로세스")
        print(f"   - 이미지 품질: {self.quality}")
    
    def _get_image_files(self, data_path: Path) -> List[Path]:
        """지원되는 이미지 파일 수집"""
        image_files = []
        for file_path in data_path.rglob("*"):
            if file_path.suffix.lower() in self.supported_formats:
                image_files.append(file_path)
        return sorted(image_files)
    
    def _fix_image_orientation(self, img: Image.Image) -> Image.Image:
        """EXIF 정보 기반 이미지 회전 보정"""
        try:
            if hasattr(img, '_getexif'):
                exif = img._getexif()
                if exif is not None:
                    for tag, value in exif.items():
                        if tag in ORIENTATION:
                            if value == 3:
                                img = img.rotate(180, expand=True)
                            elif value == 6:
                                img = img.rotate(270, expand=True)
                            elif value == 8:
                                img = img.rotate(90, expand=True)
            return img
        except:
            return img
        
    def resize_images(self, data_path: str) -> Dict[str, Any]:
        """
        고성능 배치 이미지 리사이징
        
        Args:
            data_path: 데이터 경로
            
        Returns:
            크기 조정 결과 딕셔너리
        """
        try:
            data_path = Path(data_path)
            output_path = data_path / "processed" / "resized"
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 이미지 파일 수집
            image_files = self._get_image_files(data_path)
            if not image_files:
                return {"success": False, "error": "처리할 이미지를 찾을 수 없습니다"}
            
            print(f"🔄 {len(image_files)}개 이미지 리사이징 시작...")
            start_time = time.time()
            
            # 병렬 처리
            processed_files = []
            failed_files = []
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                # 작업 제출
                future_to_file = {
                    executor.submit(self._resize_single_image, str(img_file), output_path): img_file
                    for img_file in image_files
                }
                
                # 진행률 표시
                if TQDM_AVAILABLE:
                    futures = tqdm(concurrent.futures.as_completed(future_to_file), 
                                 total=len(image_files), desc="리사이징")
                else:
                    futures = concurrent.futures.as_completed(future_to_file)
                
                # 결과 수집
                for future in futures:
                    img_file = future_to_file[future]
                    try:
                        result = future.result()
                        if result["success"]:
                            processed_files.append(result["output_path"])
                        else:
                            failed_files.append({"file": str(img_file), "error": result["error"]})
                    except Exception as e:
                        failed_files.append({"file": str(img_file), "error": str(e)})
            
            processing_time = time.time() - start_time
            
            print(f"✅ 리사이징 완료: {len(processed_files)}개 성공, {len(failed_files)}개 실패")
            print(f"⚡ 처리 시간: {processing_time:.2f}초 ({len(processed_files)/processing_time:.1f} 이미지/초)")
            
            return {
                "success": True,
                "processed_path": str(output_path),
                "processed_files": processed_files,
                "failed_files": failed_files,
                "total_processed": len(processed_files),
                "processing_time": processing_time,
                "images_per_second": len(processed_files) / processing_time if processing_time > 0 else 0,
                "target_size": self.target_size
            }
            
        except Exception as e:
            return {"success": False, "error": f"크기 조정 중 오류: {str(e)}"}
    
    def _resize_single_image(self, image_path: str, output_path: Path) -> Dict[str, Any]:
        """단일 이미지 고품질 리사이징"""
        try:
            with Image.open(image_path) as img:
                # EXIF 방향 정보 보정
                img = self._fix_image_orientation(img)
                
                # RGBA를 RGB로 변환
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                original_size = img.size
                target_width, target_height = self.target_size
                
                if self.keep_aspect_ratio:
                    # 종횡비 유지하면서 리사이즈 + 패딩
                    img = ImageOps.fit(img, self.target_size, Image.Resampling.LANCZOS)
                    
                    # 패딩 추가 (중앙 정렬)
                    result_img = Image.new('RGB', self.target_size, self.padding_color)
                    paste_x = (target_width - img.size[0]) // 2
                    paste_y = (target_height - img.size[1]) // 2
                    result_img.paste(img, (paste_x, paste_y))
                    final_img = result_img
                else:
                    # 강제 리사이즈 (종횡비 무시)
                    final_img = img.resize(self.target_size, Image.Resampling.LANCZOS)
                
                # 출력 파일명 생성
                input_name = Path(image_path).stem
                output_file = output_path / f"{input_name}.jpg"  # 통일된 형식
                
                # 고품질 저장
                final_img.save(output_file, 'JPEG', quality=self.quality, optimize=True)
                
                return {
                    "success": True,
                    "output_path": str(output_file),
                    "original_size": original_size,
                    "new_size": final_img.size
                }
                
        except Exception as e:
            return {"success": False, "error": f"이미지 처리 실패: {str(e)}"}
    
    def normalize_images(self, data_path: str, method: str = 'imagenet') -> Dict[str, Any]:
        """
        현대적인 이미지 정규화
        
        Args:
            data_path: 데이터 경로
            method: 정규화 방법 ('imagenet', 'zero_one', 'custom')
            
        Returns:
            정규화 결과 딕셔너리
        """
        try:
            data_path = Path(data_path)
            output_path = data_path.parent / "normalized"
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 정규화 파라미터 설정
            if method == 'imagenet':
                mean = [0.485, 0.456, 0.406]
                std = [0.229, 0.224, 0.225]
            elif method == 'zero_one':
                mean = [0.0, 0.0, 0.0]
                std = [1.0, 1.0, 1.0]
            else:
                mean = self.config.get('normalization_mean', [0.5, 0.5, 0.5])
                std = self.config.get('normalization_std', [0.5, 0.5, 0.5])
            
            image_files = self._get_image_files(data_path)
            if not image_files:
                return {"success": False, "error": "처리할 이미지를 찾을 수 없습니다"}
            
            print(f"🔄 {len(image_files)}개 이미지 정규화 시작 (방법: {method})...")
            start_time = time.time()
            
            processed_files = []
            
            # 병렬 처리
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                future_to_file = {
                    executor.submit(self._normalize_single_image, str(img_file), output_path, mean, std): img_file
                    for img_file in image_files
                }
                
                if TQDM_AVAILABLE:
                    futures = tqdm(concurrent.futures.as_completed(future_to_file), 
                                 total=len(image_files), desc="정규화")
                else:
                    futures = concurrent.futures.as_completed(future_to_file)
                
                for future in futures:
                    try:
                        result = future.result()
                        if result["success"]:
                            processed_files.append(result["output_path"])
                    except Exception as e:
                        print(f"정규화 실패: {e}")
            
            processing_time = time.time() - start_time
            
            print(f"✅ 정규화 완료: {len(processed_files)}개 처리")
            print(f"⚡ 처리 시간: {processing_time:.2f}초")
            
            return {
                "success": True,
                "processed_path": str(output_path),
                "processed_files": processed_files,
                "processing_time": processing_time,
                "normalization_params": {
                    "method": method,
                    "mean": mean,
                    "std": std
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"정규화 중 오류: {str(e)}"}
    
    def _normalize_single_image(self, image_path: str, output_path: Path, mean: List[float], std: List[float]) -> Dict[str, Any]:
        """단일 이미지 정규화 (PIL 기반)"""
        try:
            with Image.open(image_path) as img:
                # RGB로 변환
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # NumPy 배열로 변환
                img_array = np.array(img, dtype=np.float32) / 255.0
                
                # 정규화 적용
                for i in range(3):  # RGB 채널
                    img_array[:, :, i] = (img_array[:, :, i] - mean[i]) / std[i]
                
                # 시각화를 위해 0-255 범위로 복원 (실제 모델에서는 정규화된 값 사용)
                # 클리핑하여 범위 보정
                img_array = np.clip(img_array, -2, 2)  # 대략적인 정규화 범위
                img_array = ((img_array + 2) / 4 * 255).astype(np.uint8)
                
                # PIL 이미지로 변환
                normalized_img = Image.fromarray(img_array)
                
                # 출력 파일명 생성
                input_name = Path(image_path).stem
                output_file = output_path / f"{input_name}.jpg"
                
                # 저장
                normalized_img.save(output_file, 'JPEG', quality=self.quality)
                
                return {
                    "success": True,
                    "output_path": str(output_file)
                }
                
        except Exception as e:
            return {"success": False, "error": f"정규화 실패: {str(e)}"}
    
    def apply_filters(self, data_path: str, filter_preset: str = 'default') -> Dict[str, Any]:
        """
        현대적인 이미지 필터링
        
        Args:
            data_path: 데이터 경로
            filter_preset: 필터 프리셋 ('default', 'enhance', 'denoise', 'sharpen')
            
        Returns:
            필터 적용 결과 딕셔너리
        """
        try:
            data_path = Path(data_path)
            output_path = data_path.parent / f"filtered_{filter_preset}"
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 필터 프리셋 설정
            filter_configs = {
                'default': ['denoise', 'enhance_contrast'],
                'enhance': ['enhance_brightness', 'enhance_contrast', 'enhance_color'],
                'denoise': ['gaussian_blur', 'median_filter'],
                'sharpen': ['sharpen', 'enhance_contrast'],
                'custom': self.config.get('filters', ['denoise'])
            }
            
            filters = filter_configs.get(filter_preset, filter_configs['default'])
            
            image_files = self._get_image_files(data_path)
            if not image_files:
                return {"success": False, "error": "처리할 이미지를 찾을 수 없습니다"}
            
            print(f"🔄 {len(image_files)}개 이미지 필터링 시작 (프리셋: {filter_preset})...")
            start_time = time.time()
            
            processed_files = []
            
            # 병렬 처리
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                future_to_file = {
                    executor.submit(self._apply_filters_single_image, str(img_file), output_path, filters): img_file
                    for img_file in image_files
                }
                
                if TQDM_AVAILABLE:
                    futures = tqdm(concurrent.futures.as_completed(future_to_file), 
                                 total=len(image_files), desc="필터링")
                else:
                    futures = concurrent.futures.as_completed(future_to_file)
                
                for future in futures:
                    try:
                        result = future.result()
                        if result["success"]:
                            processed_files.append(result["output_path"])
                    except Exception as e:
                        print(f"필터링 실패: {e}")
            
            processing_time = time.time() - start_time
            
            print(f"✅ 필터링 완료: {len(processed_files)}개 처리")
            print(f"⚡ 처리 시간: {processing_time:.2f}초")
            
            return {
                "success": True,
                "processed_path": str(output_path),
                "processed_files": processed_files,
                "processing_time": processing_time,
                "applied_filters": filters,
                "filter_preset": filter_preset
            }
            
        except Exception as e:
            return {"success": False, "error": f"필터 적용 중 오류: {str(e)}"}
    
    def _apply_filters_single_image(self, image_path: str, output_path: Path, filter_types: List[str]) -> Dict[str, Any]:
        """단일 이미지에 고급 필터 적용"""
        try:
            with Image.open(image_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                filtered_img = img.copy()
                
                for filter_type in filter_types:
                    if filter_type == 'denoise' or filter_type == 'gaussian_blur':
                        # 가우시안 블러로 노이즈 제거
                        filtered_img = filtered_img.filter(ImageFilter.GaussianBlur(radius=0.8))
                    
                    elif filter_type == 'median_filter':
                        # 중간값 필터 (salt-and-pepper 노이즈 제거)
                        filtered_img = filtered_img.filter(ImageFilter.MedianFilter(size=3))
                    
                    elif filter_type == 'sharpen':
                        # 샤프닝 필터
                        filtered_img = filtered_img.filter(ImageFilter.SHARPEN)
                    
                    elif filter_type == 'enhance_contrast':
                        # 대비 향상
                        enhancer = ImageEnhance.Contrast(filtered_img)
                        filtered_img = enhancer.enhance(1.2)
                    
                    elif filter_type == 'enhance_brightness':
                        # 밝기 향상
                        enhancer = ImageEnhance.Brightness(filtered_img)
                        filtered_img = enhancer.enhance(1.1)
                    
                    elif filter_type == 'enhance_color':
                        # 색상 채도 향상
                        enhancer = ImageEnhance.Color(filtered_img)
                        filtered_img = enhancer.enhance(1.1)
                    
                    elif filter_type == 'enhance_sharpness':
                        # 선명도 향상
                        enhancer = ImageEnhance.Sharpness(filtered_img)
                        filtered_img = enhancer.enhance(1.2)
                    
                    elif filter_type == 'edge_enhance':
                        # 엣지 강화
                        filtered_img = filtered_img.filter(ImageFilter.EDGE_ENHANCE)
                
                # 출력 파일명 생성
                input_name = Path(image_path).stem
                output_file = output_path / f"{input_name}.jpg"
                
                # 고품질 저장
                filtered_img.save(output_file, 'jpg', quality=self.quality, optimize=True)
                
                return {
                    "success": True,
                    "output_path": str(output_file)
                }
                
        except Exception as e:
            return {"success": False, "error": f"필터 적용 실패: {str(e)}"}
    
    def crop_and_pad(self, data_path: str, strategy: str = 'letterbox') -> Dict[str, Any]:
        """
        고급 크롭 및 패딩 처리
        
        Args:
            data_path: 데이터 경로
            strategy: 처리 전략 ('letterbox', 'center_crop', 'smart_crop')
            
        Returns:
            크롭/패딩 결과 딕셔너리
        """
        try:
            data_path = Path(data_path)
            output_path = data_path.parent / f"processed_{strategy}"
            output_path.mkdir(parents=True, exist_ok=True)
            
            image_files = self._get_image_files(data_path)
            if not image_files:
                return {"success": False, "error": "처리할 이미지를 찾을 수 없습니다"}
            
            print(f"🔄 {len(image_files)}개 이미지 크롭/패딩 시작 (전략: {strategy})...")
            start_time = time.time()
            
            processed_files = []
            target_width, target_height = self.target_size
            
            # 병렬 처리
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                future_to_file = {
                    executor.submit(self._process_single_image_advanced, str(img_file), output_path, 
                                  target_width, target_height, strategy): img_file
                    for img_file in image_files
                }
                
                if TQDM_AVAILABLE:
                    futures = tqdm(concurrent.futures.as_completed(future_to_file), 
                                 total=len(image_files), desc="크롭/패딩")
                else:
                    futures = concurrent.futures.as_completed(future_to_file)
                
                for future in futures:
                    try:
                        result = future.result()
                        if result["success"]:
                            processed_files.append(result["output_path"])
                    except Exception as e:
                        print(f"크롭/패딩 실패: {e}")
            
            processing_time = time.time() - start_time
            
            print(f"✅ 크롭/패딩 완료: {len(processed_files)}개 처리")
            print(f"⚡ 처리 시간: {processing_time:.2f}초")
            
            return {
                "success": True,
                "processed_path": str(output_path),
                "processed_files": processed_files,
                "processing_time": processing_time,
                "target_size": self.target_size,
                "strategy": strategy
            }
            
        except Exception as e:
            return {"success": False, "error": f"크롭/패딩 중 오류: {str(e)}"}
    
    def _process_single_image_advanced(self, image_path: str, output_path: Path, 
                                     target_width: int, target_height: int, strategy: str) -> Dict[str, Any]:
        """고급 단일 이미지 처리"""
        try:
            with Image.open(image_path) as img:
                # EXIF 방향 보정
                img = self._fix_image_orientation(img)
                
                # RGB로 변환
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                original_width, original_height = img.size
                
                if strategy == 'letterbox':
                    # YOLO 스타일 letterbox (종횡비 유지 + 패딩)
                    scale = min(target_width / original_width, target_height / original_height)
                    new_width = int(original_width * scale)
                    new_height = int(original_height * scale)
                    
                    # 리사이즈
                    resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # 패딩으로 채우기
                    result_img = Image.new('RGB', (target_width, target_height), self.padding_color)
                    paste_x = (target_width - new_width) // 2
                    paste_y = (target_height - new_height) // 2
                    result_img.paste(resized_img, (paste_x, paste_y))
                    
                elif strategy == 'center_crop':
                    # 중앙 크롭 (종횡비 무시하고 중앙 부분만 추출)
                    scale = max(target_width / original_width, target_height / original_height)
                    new_width = int(original_width * scale)
                    new_height = int(original_height * scale)
                    
                    # 리사이즈
                    resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # 중앙 크롭
                    crop_x = (new_width - target_width) // 2
                    crop_y = (new_height - target_height) // 2
                    result_img = resized_img.crop((crop_x, crop_y, crop_x + target_width, crop_y + target_height))
                    
                elif strategy == 'smart_crop':
                    # 스마트 크롭 (내용 기반 중요 영역 감지)
                    # 간단한 구현: 밝기 기반 중요 영역 감지
                    gray_img = img.convert('L')
                    img_array = np.array(gray_img)
                    
                    # 그래디언트 계산으로 중요 영역 찾기
                    grad_x = np.abs(np.diff(img_array, axis=1))
                    grad_y = np.abs(np.diff(img_array, axis=0))
                    
                    # 패딩하여 크기 맞추기
                    grad_x = np.pad(grad_x, ((0, 0), (0, 1)), mode='edge')
                    grad_y = np.pad(grad_y, ((0, 1), (0, 0)), mode='edge')
                    
                    importance = grad_x + grad_y
                    
                    # 중요도가 높은 영역의 중심 찾기
                    y_indices, x_indices = np.where(importance > np.percentile(importance, 75))
                    if len(x_indices) > 0:
                        center_x = int(np.mean(x_indices))
                        center_y = int(np.mean(y_indices))
                    else:
                        center_x = original_width // 2
                        center_y = original_height // 2
                    
                    # 스마트 크롭 실행
                    scale = max(target_width / original_width, target_height / original_height)
                    new_width = int(original_width * scale)
                    new_height = int(original_height * scale)
                    
                    resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # 중요 영역 중심으로 크롭
                    scaled_center_x = int(center_x * scale)
                    scaled_center_y = int(center_y * scale)
                    
                    crop_x = max(0, min(scaled_center_x - target_width // 2, new_width - target_width))
                    crop_y = max(0, min(scaled_center_y - target_height // 2, new_height - target_height))
                    
                    result_img = resized_img.crop((crop_x, crop_y, crop_x + target_width, crop_y + target_height))
                    
                else:
                    # 기본: 강제 리사이즈
                    result_img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                
                # 출력 파일명 생성
                input_name = Path(image_path).stem
                output_file = output_path / f"{input_name}.jpg"
                
                # 고품질 저장
                result_img.save(output_file, 'JPEG', quality=self.quality, optimize=True)
                
                return {
                    "success": True,
                    "output_path": str(output_file),
                    "original_size": (original_width, original_height),
                    "final_size": (target_width, target_height),
                    "strategy": strategy
                }
                
        except Exception as e:
            return {"success": False, "error": f"이미지 처리 실패: {str(e)}"}
    
    def batch_process_all(self, data_path: str, operations: List[str] = None) -> Dict[str, Any]:
        """
        모든 전처리 작업을 순차적으로 실행
        
        Args:
            data_path: 데이터 경로
            operations: 실행할 작업 리스트 ['resize', 'normalize', 'filter', 'crop_pad']
            
        Returns:
            전체 처리 결과
        """
        try:
            if operations is None:
                operations = ['resize', 'filter']
            
            data_path = Path(data_path)
            results = {}
            current_path = str(data_path)
            
            print(f"🚀 배치 전처리 시작: {operations}")
            total_start = time.time()
            
            for operation in operations:
                print(f"\n📋 작업: {operation}")
                
                if operation == 'resize':
                    result = self.resize_images(current_path)
                    if result["success"]:
                        current_path = result["processed_path"]
                        results[operation] = result
                    else:
                        return {"success": False, "error": f"리사이징 실패: {result['error']}"}
                
                elif operation == 'normalize':
                    result = self.normalize_images(current_path)
                    if result["success"]:
                        current_path = result["processed_path"]
                        results[operation] = result
                    else:
                        return {"success": False, "error": f"정규화 실패: {result['error']}"}
                
                elif operation == 'filter':
                    result = self.apply_filters(current_path, 'default')
                    if result["success"]:
                        current_path = result["processed_path"]
                        results[operation] = result
                    else:
                        return {"success": False, "error": f"필터링 실패: {result['error']}"}
                
                elif operation == 'crop_pad':
                    result = self.crop_and_pad(current_path, 'letterbox')
                    if result["success"]:
                        current_path = result["processed_path"]
                        results[operation] = result
                    else:
                        return {"success": False, "error": f"크롭/패딩 실패: {result['error']}"}
            
            total_time = time.time() - total_start
            
            print(f"\n🎉 배치 전처리 완료!")
            print(f"⚡ 총 처리 시간: {total_time:.2f}초")
            print(f"📁 최종 출력: {current_path}")
            
            return {
                "success": True,
                "operations": operations,
                "results": results,
                "final_output_path": current_path,
                "total_processing_time": total_time
            }
            
        except Exception as e:
            return {"success": False, "error": f"배치 처리 중 오류: {str(e)}"}
    
    def clean_orphan_annotations(self, dataset_path: str) -> Dict[str, Any]:
        """
        고아 어노테이션 파일 정리 (txt 파일은 있지만 해당 이미지가 없는 경우)
        
        Args:
            dataset_path: 데이터셋 경로
            
        Returns:
            정리 결과 딕셔너리
        """
        try:
            print(f"🧹 고아 어노테이션 파일 정리 시작...")
            
            # txt 파일들 수집
            txt_files = list(Path(dataset_path).glob("**/*.txt"))
            
            orphan_files = []
            valid_pairs = []
            
            # 각 txt 파일에 대해 해당하는 이미지 파일이 있는지 확인
            for txt_file in txt_files:
                has_image = False
                
                # 지원하는 이미지 형식들 확인
                for ext in self.supported_formats:
                    img_file = txt_file.with_suffix(ext)
                    if img_file.exists():
                        has_image = True
                        valid_pairs.append((str(img_file), str(txt_file)))
                        break
                
                if not has_image:
                    orphan_files.append(str(txt_file))
            
            # 고아 파일들 삭제
            deleted_count = 0
            for orphan_file in orphan_files:
                try:
                    os.remove(orphan_file)
                    deleted_count += 1
                    print(f"🗑️  삭제: {os.path.basename(orphan_file)}")
                except Exception as e:
                    print(f"❌ 삭제 실패 {orphan_file}: {str(e)}")
            
            print(f"\n✅ 고아 어노테이션 파일 정리 완료!")
            print(f"📊 총 txt 파일: {len(txt_files)}개")
            print(f"📊 유효한 쌍: {len(valid_pairs)}개")
            print(f"🗑️  삭제된 고아 파일: {deleted_count}개")
            
            return {
                "success": True,
                "total_txt_files": len(txt_files),
                "valid_pairs": len(valid_pairs),
                "orphan_files_found": len(orphan_files),
                "orphan_files_deleted": deleted_count,
                "orphan_file_list": orphan_files
            }
            
        except Exception as e:
            return {"success": False, "error": f"고아 파일 정리 중 오류: {str(e)}"}
    
    def clean_orphan_images(self, dataset_path: str) -> Dict[str, Any]:
        """
        고아 이미지 파일 정리 (이미지는 있지만 해당 txt 파일이 없는 경우)
        
        Args:
            dataset_path: 데이터셋 경로
            
        Returns:
            정리 결과 딕셔너리
        """
        try:
            print(f"🧹 고아 이미지 파일 정리 시작...")
            
            # 이미지 파일들 수집
            image_files = []
            for ext in self.supported_formats:
                image_files.extend(Path(dataset_path).glob(f"**/*{ext}"))
            
            orphan_files = []
            valid_pairs = []
            
            # 각 이미지 파일에 대해 해당하는 txt 파일이 있는지 확인
            for img_file in image_files:
                txt_file = img_file.with_suffix('.txt')
                
                if txt_file.exists():
                    valid_pairs.append((str(img_file), str(txt_file)))
                else:
                    orphan_files.append(str(img_file))
            
            # 고아 파일들 삭제
            deleted_count = 0
            for orphan_file in orphan_files:
                try:
                    os.remove(orphan_file)
                    deleted_count += 1
                    print(f"🗑️  삭제: {os.path.basename(orphan_file)}")
                except Exception as e:
                    print(f"❌ 삭제 실패 {orphan_file}: {str(e)}")
            
            print(f"\n✅ 고아 이미지 파일 정리 완료!")
            print(f"📊 총 이미지 파일: {len(image_files)}개")
            print(f"📊 유효한 쌍: {len(valid_pairs)}개")
            print(f"🗑️  삭제된 고아 파일: {deleted_count}개")
            
            return {
                "success": True,
                "total_image_files": len(image_files),
                "valid_pairs": len(valid_pairs),
                "orphan_files_found": len(orphan_files),
                "orphan_files_deleted": deleted_count,
                "orphan_file_list": orphan_files
            }
            
        except Exception as e:
            return {"success": False, "error": f"고아 파일 정리 중 오류: {str(e)}"}
    
    def validate_dataset_pairs(self, dataset_path: str, auto_clean: bool = False) -> Dict[str, Any]:
        """
        데이터셋 쌍 검증 및 선택적 정리
        
        Args:
            dataset_path: 데이터셋 경로
            auto_clean: True면 고아 파일들을 자동으로 삭제
            
        Returns:
            검증 결과 딕셔너리
        """
        try:
            print(f"🔍 데이터셋 쌍 검증 시작...")
            
            # 이미지와 txt 파일 수집
            image_files = []
            for ext in self.supported_formats:
                image_files.extend(Path(dataset_path).glob(f"**/*{ext}"))
            
            txt_files = list(Path(dataset_path).glob("**/*.txt"))
            
            # 파일명 기준으로 매칭
            image_stems = {f.stem: str(f) for f in image_files}
            txt_stems = {f.stem: str(f) for f in txt_files}
            
            # 매칭된 쌍과 고아 파일들 분류
            valid_pairs = []
            orphan_images = []
            orphan_txt = []
            
            # 이미지 기준으로 체크
            for stem, img_path in image_stems.items():
                if stem in txt_stems:
                    valid_pairs.append((img_path, txt_stems[stem]))
                else:
                    orphan_images.append(img_path)
            
            # txt 기준으로 고아 체크
            for stem, txt_path in txt_stems.items():
                if stem not in image_stems:
                    orphan_txt.append(txt_path)
            
            print(f"\n📊 검증 결과:")
            print(f"   총 이미지 파일: {len(image_files)}개")
            print(f"   총 txt 파일: {len(txt_files)}개")
            print(f"   ✅ 유효한 쌍: {len(valid_pairs)}개")
            print(f"   🖼️  고아 이미지: {len(orphan_images)}개")
            print(f"   📝 고아 txt: {len(orphan_txt)}개")
            
            # 자동 정리 옵션
            cleanup_results = {}
            if auto_clean:
                print(f"\n🧹 자동 정리 시작...")
                
                # 고아 이미지 삭제
                deleted_images = 0
                for img_path in orphan_images:
                    try:
                        os.remove(img_path)
                        deleted_images += 1
                        print(f"🗑️  이미지 삭제: {os.path.basename(img_path)}")
                    except Exception as e:
                        print(f"❌ 이미지 삭제 실패 {img_path}: {str(e)}")
                
                # 고아 txt 삭제
                deleted_txt = 0
                for txt_path in orphan_txt:
                    try:
                        os.remove(txt_path)
                        deleted_txt += 1
                        print(f"🗑️  txt 삭제: {os.path.basename(txt_path)}")
                    except Exception as e:
                        print(f"❌ txt 삭제 실패 {txt_path}: {str(e)}")
                
                cleanup_results = {
                    "deleted_images": deleted_images,
                    "deleted_txt": deleted_txt
                }
                
                print(f"\n✅ 자동 정리 완료! 이미지 {deleted_images}개, txt {deleted_txt}개 삭제")
            
            return {
                "success": True,
                "total_images": len(image_files),
                "total_txt": len(txt_files),
                "valid_pairs": len(valid_pairs),
                "orphan_images": len(orphan_images),
                "orphan_txt": len(orphan_txt),
                "orphan_image_list": orphan_images,
                "orphan_txt_list": orphan_txt,
                "valid_pair_list": valid_pairs,
                "auto_clean": auto_clean,
                "cleanup_results": cleanup_results
            }
            
        except Exception as e:
            return {"success": False, "error": f"데이터셋 검증 중 오류: {str(e)}"}

# 편의 함수들
def clean_orphan_annotations(dataset_path: str) -> Dict[str, Any]:
    """고아 어노테이션 파일 정리 편의 함수"""
    processor = DataPreprocessingManager()
    return processor.clean_orphan_annotations(dataset_path)

def clean_orphan_images(dataset_path: str) -> Dict[str, Any]:
    """고아 이미지 파일 정리 편의 함수"""
    processor = DataPreprocessingManager()
    return processor.clean_orphan_images(dataset_path)

def validate_dataset_pairs(dataset_path: str, auto_clean: bool = False) -> Dict[str, Any]:
    """데이터셋 쌍 검증 편의 함수"""
    processor = DataPreprocessingManager()
    return processor.validate_dataset_pairs(dataset_path, auto_clean)

if __name__ == "__main__":
    # 사용 예시
    print("🧹 데이터셋 정리 도구")
    print("사용 가능한 함수:")
    print("1. clean_orphan_annotations(path) - txt 파일은 있지만 이미지가 없는 경우 txt 삭제")
    print("2. clean_orphan_images(path) - 이미지는 있지만 txt가 없는 경우 이미지 삭제")
    print("3. validate_dataset_pairs(path, auto_clean=True) - 전체 검증 및 자동 정리")
    