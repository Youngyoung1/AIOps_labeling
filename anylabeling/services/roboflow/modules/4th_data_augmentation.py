"""
4. 데이터 증강 (Data Augmentation)

이미지 회전, 밝기/대비 조정, 노이즈 추가, 기하학적 변환을 담당하는 모듈
"""

import os
import cv2
import numpy as np
import random
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import albumentations as A


class DataAugmentationManager:
    """데이터 증강 관리 클래스"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        초기화
        
        Args:
            config: 설정 딕셔너리
        """
        self.config = config or {}
        self.augmentation_factor = self.config.get('augmentation_factor', 3)
        self.rotation_range = self.config.get('rotation_range', 15)
        self.brightness_range = self.config.get('brightness_range', (0.8, 1.2))
        self.contrast_range = self.config.get('contrast_range', (0.8, 1.2))
        self.noise_probability = self.config.get('noise_probability', 0.3)
        
        # Albumentations 변환 파이프라인 정의
        self.transform = A.Compose([
            A.RandomRotate90(p=0.3),
            A.Rotate(limit=self.rotation_range, p=0.5),
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.2),
            A.RandomBrightnessContrast(
                brightness_limit=0.2, 
                contrast_limit=0.2, 
                p=0.5
            ),
            A.GaussNoise(var_limit=(10.0, 50.0), p=self.noise_probability),
            A.OneOf([
                A.MotionBlur(p=0.2),
                A.MedianBlur(blur_limit=3, p=0.1),
                A.Blur(blur_limit=3, p=0.1),
            ], p=0.2),
            A.ShiftScaleRotate(
                shift_limit=0.0625, 
                scale_limit=0.1, 
                rotate_limit=0, 
                p=0.3
            ),
            A.OneOf([
                A.OpticalDistortion(p=0.3),
                A.GridDistortion(p=0.1),
                A.PiecewiseAffine(p=0.3),
            ], p=0.2),
            A.OneOf([
                A.CLAHE(clip_limit=2),
                A.Sharpen(),
                A.Emboss(),
                A.RandomBrightnessContrast(),
            ], p=0.3),
            A.HueSaturationValue(p=0.3),
        ], bbox_params=A.BboxParams(format='yolo', label_fields=['labels']))
    
    def apply_rotations(self, data_path: str) -> Dict[str, Any]:
        """
        이미지 회전 변환 적용
        
        Args:
            data_path: 데이터 경로
            
        Returns:
            회전 변환 결과 딕셔너리
        """
        try:
            data_path = Path(data_path)
            output_path = data_path.parent / "augmented" / "rotated"
            output_path.mkdir(parents=True, exist_ok=True)
            
            processed_files = []
            rotation_angles = [-15, -10, -5, 5, 10, 15]  # 회전 각도들
            
            for image_file in data_path.glob("*.jpg"):
                try:
                    for angle in rotation_angles:
                        result = self._rotate_single_image(str(image_file), output_path, angle)
                        if result["success"]:
                            processed_files.append(result["output_path"])
                except Exception as e:
                    print(f"회전 변환 실패 {image_file}: {e}")
            
            return {
                "success": True,
                "processed_path": str(output_path),
                "processed_files": processed_files,
                "rotation_angles": rotation_angles,
                "total_generated": len(processed_files)
            }
            
        except Exception as e:
            return {"success": False, "error": f"회전 변환 중 오류: {str(e)}"}
    
    def _rotate_single_image(self, image_path: str, output_path: Path, angle: float) -> Dict[str, Any]:
        """단일 이미지 회전"""
        try:
            # OpenCV로 이미지 로드
            image = cv2.imread(image_path)
            h, w = image.shape[:2]
            
            # 회전 중심점 계산
            center = (w // 2, h // 2)
            
            # 회전 매트릭스 생성
            rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            
            # 회전된 이미지의 새로운 경계 계산
            cos = np.abs(rotation_matrix[0, 0])
            sin = np.abs(rotation_matrix[0, 1])
            new_w = int((h * sin) + (w * cos))
            new_h = int((h * cos) + (w * sin))
            
            # 회전 매트릭스 조정 (이미지 중앙 유지)
            rotation_matrix[0, 2] += (new_w / 2) - center[0]
            rotation_matrix[1, 2] += (new_h / 2) - center[1]
            
            # 이미지 회전 적용
            rotated = cv2.warpAffine(image, rotation_matrix, (new_w, new_h), 
                                   flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
            
            # 출력 파일명 생성
            input_name = Path(image_path).stem
            output_file = output_path / f"{input_name}_rot_{int(angle)}.jpg"
            
            # 이미지 저장
            cv2.imwrite(str(output_file), rotated)
            
            return {
                "success": True,
                "output_path": str(output_file),
                "rotation_angle": angle
            }
            
        except Exception as e:
            return {"success": False, "error": f"회전 실패: {str(e)}"}
    
    def adjust_brightness_contrast(self, data_path: str) -> Dict[str, Any]:
        """
        밝기 및 대비 조정
        
        Args:
            data_path: 데이터 경로
            
        Returns:
            밝기/대비 조정 결과 딕셔너리
        """
        try:
            data_path = Path(data_path)
            output_path = data_path.parent / "augmented" / "brightness_contrast"
            output_path.mkdir(parents=True, exist_ok=True)
            
            processed_files = []
            brightness_factors = [0.7, 0.85, 1.15, 1.3]
            contrast_factors = [0.7, 0.85, 1.15, 1.3]
            
            for image_file in data_path.glob("*.jpg"):
                try:
                    for brightness in brightness_factors:
                        for contrast in contrast_factors:
                            result = self._adjust_brightness_contrast_single(
                                str(image_file), output_path, brightness, contrast
                            )
                            if result["success"]:
                                processed_files.append(result["output_path"])
                except Exception as e:
                    print(f"밝기/대비 조정 실패 {image_file}: {e}")
            
            return {
                "success": True,
                "processed_path": str(output_path),
                "processed_files": processed_files,
                "brightness_factors": brightness_factors,
                "contrast_factors": contrast_factors,
                "total_generated": len(processed_files)
            }
            
        except Exception as e:
            return {"success": False, "error": f"밝기/대비 조정 중 오류: {str(e)}"}
    
    def _adjust_brightness_contrast_single(self, image_path: str, output_path: Path, 
                                         brightness: float, contrast: float) -> Dict[str, Any]:
        """단일 이미지 밝기/대비 조정"""
        try:
            with Image.open(image_path) as img:
                # 밝기 조정
                brightness_enhancer = ImageEnhance.Brightness(img)
                bright_img = brightness_enhancer.enhance(brightness)
                
                # 대비 조정
                contrast_enhancer = ImageEnhance.Contrast(bright_img)
                enhanced_img = contrast_enhancer.enhance(contrast)
                
                # 출력 파일명 생성
                input_name = Path(image_path).stem
                output_file = output_path / f"{input_name}_br{int(brightness*100)}_co{int(contrast*100)}.jpg"
                
                # 이미지 저장
                enhanced_img.save(output_file, quality=95)
                
                return {
                    "success": True,
                    "output_path": str(output_file),
                    "brightness_factor": brightness,
                    "contrast_factor": contrast
                }
                
        except Exception as e:
            return {"success": False, "error": f"밝기/대비 조정 실패: {str(e)}"}
    
    def add_noise(self, data_path: str) -> Dict[str, Any]:
        """
        노이즈 추가
        
        Args:
            data_path: 데이터 경로
            
        Returns:
            노이즈 추가 결과 딕셔너리
        """
        try:
            data_path = Path(data_path)
            output_path = data_path.parent / "augmented" / "noisy"
            output_path.mkdir(parents=True, exist_ok=True)
            
            processed_files = []
            noise_types = ['gaussian', 'salt_pepper', 'poisson']
            
            for image_file in data_path.glob("*.jpg"):
                try:
                    for noise_type in noise_types:
                        result = self._add_noise_single(str(image_file), output_path, noise_type)
                        if result["success"]:
                            processed_files.append(result["output_path"])
                except Exception as e:
                    print(f"노이즈 추가 실패 {image_file}: {e}")
            
            return {
                "success": True,
                "processed_path": str(output_path),
                "processed_files": processed_files,
                "noise_types": noise_types,
                "total_generated": len(processed_files)
            }
            
        except Exception as e:
            return {"success": False, "error": f"노이즈 추가 중 오류: {str(e)}"}
    
    def _add_noise_single(self, image_path: str, output_path: Path, noise_type: str) -> Dict[str, Any]:
        """단일 이미지에 노이즈 추가"""
        try:
            # OpenCV로 이미지 로드
            image = cv2.imread(image_path)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            if noise_type == 'gaussian':
                # 가우시안 노이즈
                mean = 0
                std = 25
                noise = np.random.normal(mean, std, image.shape).astype(np.uint8)
                noisy_image = cv2.add(image, noise)
                
            elif noise_type == 'salt_pepper':
                # 소금-후추 노이즈
                noisy_image = image.copy()
                # 소금 노이즈
                salt = np.random.random(image.shape[:2]) < 0.01
                noisy_image[salt] = [255, 255, 255]
                # 후추 노이즈
                pepper = np.random.random(image.shape[:2]) < 0.01
                noisy_image[pepper] = [0, 0, 0]
                
            elif noise_type == 'poisson':
                # 포아송 노이즈
                vals = len(np.unique(image))
                vals = 2 ** np.ceil(np.log2(vals))
                noisy_image = np.random.poisson(image * vals) / float(vals)
                noisy_image = np.clip(noisy_image, 0, 255).astype(np.uint8)
            
            # 출력 파일명 생성
            input_name = Path(image_path).stem
            output_file = output_path / f"{input_name}_noise_{noise_type}.jpg"
            
            # RGB에서 BGR로 변환 후 저장
            noisy_bgr = cv2.cvtColor(noisy_image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(output_file), noisy_bgr)
            
            return {
                "success": True,
                "output_path": str(output_file),
                "noise_type": noise_type
            }
            
        except Exception as e:
            return {"success": False, "error": f"노이즈 추가 실패: {str(e)}"}
    
    def geometric_transforms(self, data_path: str) -> Dict[str, Any]:
        """
        기하학적 변환 (플립, 스케일, 전단 등)
        
        Args:
            data_path: 데이터 경로
            
        Returns:
            기하학적 변환 결과 딕셔너리
        """
        try:
            data_path = Path(data_path)
            output_path = data_path.parent / "augmented" / "geometric"
            output_path.mkdir(parents=True, exist_ok=True)
            
            processed_files = []
            transforms = ['horizontal_flip', 'vertical_flip', 'scale_up', 'scale_down', 'shear']
            
            for image_file in data_path.glob("*.jpg"):
                try:
                    for transform_type in transforms:
                        result = self._apply_geometric_transform(str(image_file), output_path, transform_type)
                        if result["success"]:
                            processed_files.append(result["output_path"])
                except Exception as e:
                    print(f"기하학적 변환 실패 {image_file}: {e}")
            
            return {
                "success": True,
                "processed_path": str(output_path),
                "processed_files": processed_files,
                "transforms": transforms,
                "total_generated": len(processed_files)
            }
            
        except Exception as e:
            return {"success": False, "error": f"기하학적 변환 중 오류: {str(e)}"}
    
    def _apply_geometric_transform(self, image_path: str, output_path: Path, transform_type: str) -> Dict[str, Any]:
        """단일 이미지에 기하학적 변환 적용"""
        try:
            # OpenCV로 이미지 로드
            image = cv2.imread(image_path)
            h, w = image.shape[:2]
            
            if transform_type == 'horizontal_flip':
                # 수평 플립
                transformed = cv2.flip(image, 1)
            
            elif transform_type == 'vertical_flip':
                # 수직 플립
                transformed = cv2.flip(image, 0)
            
            elif transform_type == 'scale_up':
                # 스케일 업 (1.2배)
                scale_factor = 1.2
                new_w, new_h = int(w * scale_factor), int(h * scale_factor)
                transformed = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                # 원래 크기로 중앙 크롭
                start_x = (new_w - w) // 2
                start_y = (new_h - h) // 2
                transformed = transformed[start_y:start_y+h, start_x:start_x+w]
            
            elif transform_type == 'scale_down':
                # 스케일 다운 (0.8배)
                scale_factor = 0.8
                new_w, new_h = int(w * scale_factor), int(h * scale_factor)
                scaled = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                # 패딩으로 원래 크기 복원
                transformed = np.zeros_like(image)
                start_x = (w - new_w) // 2
                start_y = (h - new_h) // 2
                transformed[start_y:start_y+new_h, start_x:start_x+new_w] = scaled
            
            elif transform_type == 'shear':
                # 전단 변환
                shear_factor = 0.2
                M = np.float32([[1, shear_factor, 0], [0, 1, 0]])
                transformed = cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_REFLECT_101)
            
            # 출력 파일명 생성
            input_name = Path(image_path).stem
            output_file = output_path / f"{input_name}_{transform_type}.jpg"
            
            # 이미지 저장
            cv2.imwrite(str(output_file), transformed)
            
            return {
                "success": True,
                "output_path": str(output_file),
                "transform_type": transform_type
            }
            
        except Exception as e:
            return {"success": False, "error": f"기하학적 변환 실패: {str(e)}"}
    
    def advanced_augmentation(self, data_path: str, annotation_path: str = None) -> Dict[str, Any]:
        """
        Albumentations를 사용한 고급 데이터 증강 (어노테이션 보존)
        
        Args:
            data_path: 이미지 데이터 경로
            annotation_path: 어노테이션 파일 경로 (YOLO 형식)
            
        Returns:
            고급 증강 결과 딕셔너리
        """
        try:
            data_path = Path(data_path)
            output_path = data_path.parent / "augmented" / "advanced"
            output_path.mkdir(parents=True, exist_ok=True)
            
            processed_files = []
            
            for image_file in data_path.glob("*.jpg"):
                try:
                    # 어노테이션 파일 찾기
                    annotation_file = None
                    if annotation_path:
                        ann_path = Path(annotation_path)
                        annotation_file = ann_path / f"{image_file.stem}.txt"
                    
                    # 여러 증강 버전 생성
                    for i in range(self.augmentation_factor):
                        result = self._advanced_augment_single(
                            str(image_file), 
                            str(annotation_file) if annotation_file and annotation_file.exists() else None,
                            output_path, 
                            i
                        )
                        if result["success"]:
                            processed_files.extend(result["output_files"])
                            
                except Exception as e:
                    print(f"고급 증강 실패 {image_file}: {e}")
            
            return {
                "success": True,
                "processed_path": str(output_path),
                "processed_files": processed_files,
                "augmentation_factor": self.augmentation_factor,
                "total_generated": len(processed_files)
            }
            
        except Exception as e:
            return {"success": False, "error": f"고급 증강 중 오류: {str(e)}"}
    
    def _advanced_augment_single(self, image_path: str, annotation_path: Optional[str], 
                               output_path: Path, index: int) -> Dict[str, Any]:
        """단일 이미지 고급 증강"""
        try:
            # 이미지 로드
            image = cv2.imread(image_path)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # 어노테이션 로드 (있는 경우)
            bboxes = []
            labels = []
            if annotation_path and os.path.exists(annotation_path):
                with open(annotation_path, 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            label = int(parts[0])
                            x_center, y_center, width, height = map(float, parts[1:5])
                            bboxes.append([x_center, y_center, width, height])
                            labels.append(label)
            
            # 증강 적용
            if bboxes:
                transformed = self.transform(image=image_rgb, bboxes=bboxes, labels=labels)
                augmented_image = transformed['image']
                augmented_bboxes = transformed['bboxes']
                augmented_labels = transformed['labels']
            else:
                # 어노테이션이 없는 경우 이미지만 증강
                transform_no_bbox = A.Compose([
                    A.RandomRotate90(p=0.3),
                    A.Rotate(limit=self.rotation_range, p=0.5),
                    A.HorizontalFlip(p=0.5),
                    A.RandomBrightnessContrast(p=0.5),
                    A.GaussNoise(p=self.noise_probability),
                ])
                augmented_image = transform_no_bbox(image=image_rgb)['image']
                augmented_bboxes = []
                augmented_labels = []
            
            # 출력 파일명 생성
            input_name = Path(image_path).stem
            output_image_file = output_path / f"{input_name}_aug_{index}.jpg"
            output_annotation_file = output_path / f"{input_name}_aug_{index}.txt"
            
            # 증강된 이미지 저장
            augmented_bgr = cv2.cvtColor(augmented_image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(output_image_file), augmented_bgr)
            
            output_files = [str(output_image_file)]
            
            # 증강된 어노테이션 저장
            if augmented_bboxes:
                with open(output_annotation_file, 'w') as f:
                    for bbox, label in zip(augmented_bboxes, augmented_labels):
                        f.write(f"{label} {bbox[0]:.6f} {bbox[1]:.6f} {bbox[2]:.6f} {bbox[3]:.6f}\n")
                output_files.append(str(output_annotation_file))
            
            return {
                "success": True,
                "output_files": output_files
            }
            
        except Exception as e:
            return {"success": False, "error": f"고급 증강 실패: {str(e)}"}