"""
2. 자동 어노테이션 (Auto-Annotation)

YOLO 기반 자동 라벨링, 어노테이션 제안, 배치 처리를 담당하는 모듈
"""

import os
import time
import torch
from PIL import Image
from pathlib import Path
from typing import Dict, List, Any, Tuple

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False
    print("⚠️ ultralytics가 설치되지 않았습니다. pip install ultralytics로 설치하세요.")


class AutoAnnotationManager:
    """YOLO 기반 자동 어노테이션 관리 클래스"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        초기화
        
        Args:
            config: 설정 딕셔너리
        """
        self.config = config or {}
        self.confidence_threshold = self.config.get('confidence_threshold', 0.5)
        self.model_path = self.config.get('model_path', '')
        self.batch_size = self.config.get('batch_size', 16)
        self.device = self._get_device()
        self.model = None
        self.class_names = {}
        
        if ULTRALYTICS_AVAILABLE and self.model_path:
            self._load_yolo_model()
    
    def _get_device(self) -> str:
        """최적 디바이스 자동 선택"""
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            device_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"🚀 Using GPU: {device_name} ({device_mem:.1f} GB)")
            return "cuda:0"
        else:
            print("💻 Using CPU")
            return "cpu"
    
    def _load_yolo_model(self):
        """YOLO 모델 로드"""
        try:
            if os.path.exists(self.model_path):
                self.model = YOLO(self.model_path)
                self.class_names = self.model.model.names
                print(f"✅ YOLO 모델 로드 완료: {self.model_path}")
                print(f"📋 클래스 수: {len(self.class_names)}")
            else:
                print(f"❌ 모델 파일을 찾을 수 없음: {self.model_path}")
        except Exception as e:
            print(f"❌ YOLO 모델 로드 실패: {e}")
            self.model = None
    
    def auto_detect_objects(self, dataset_path: str) -> Dict[str, Any]:
        """
        YOLO 모델로 배치 객체 자동 탐지
        
        Args:
            dataset_path: 데이터셋 경로
            
        Returns:
            탐지 결과 딕셔너리
        """
        try:
            if not ULTRALYTICS_AVAILABLE:
                return {"success": False, "error": "ultralytics가 설치되지 않았습니다"}
            
            if self.model is None:
                return {"success": False, "error": "YOLO 모델이 로드되지 않았습니다"}
            
            dataset_path = Path(dataset_path)
            images_path = dataset_path / "images"
            
            if not images_path.exists():
                return {"success": False, "error": "이미지 폴더를 찾을 수 없습니다"}
            
            # 지원되는 이미지 형식
            image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')
            image_files = []
            
            for ext in image_extensions:
                image_files.extend(list(images_path.rglob(f"*{ext}")))
                image_files.extend(list(images_path.rglob(f"*{ext.upper()}")))
            
            if not image_files:
                return {"success": False, "error": "처리할 이미지를 찾을 수 없습니다"}
            print(f"🔍 {len(image_files)}개 이미지 탐지 시작...")
            
            # 배치 추론 시간 측정
            start_time = time.time()
            
            # YOLO 배치 추론 실행
            results_gen = self.model.predict(
                source=[str(img) for img in image_files],
                conf=self.confidence_threshold,
                batch=self.batch_size,
                device=self.device,
                save=False,
                save_txt=False,
                save_conf=False,
                verbose=False,
                stream=True
            )
            
            # 결과 수집
            results = list(results_gen)
            inference_time = time.time() - start_time
            
            # 결과 파싱
            detections = []
            total_detections = 0
            
            for img_file, result in zip(image_files, results):
                if result.boxes is not None and len(result.boxes) > 0:
                    image_detections = []
                    confidence_scores = []
                    
                    for box in result.boxes:
                        # YOLO 결과에서 정보 추출
                        xyxy = box.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
                        conf = float(box.conf[0].cpu().numpy())
                        cls_id = int(box.cls[0].cpu().numpy())
                        
                        # xyxy를 xywh로 변환
                        x1, y1, x2, y2 = xyxy
                        x, y, w, h = x1, y1, x2-x1, y2-y1
                        
                        # 중심점 계산
                        center_x = x + w/2
                        center_y = y + h/2
                        
                        class_name = self.class_names.get(cls_id, f"class_{cls_id}")
                        
                        image_detections.append({
                            "class_id": cls_id,
                            "class_name": class_name,
                            "bbox": [int(x), int(y), int(w), int(h)],
                            "center": [int(center_x), int(center_y)],
                            "confidence": conf
                        })
                        confidence_scores.append(conf)
                    
                    if image_detections:
                        detections.append({
                            "image_path": str(img_file),
                            "detections": image_detections,
                            "confidence_scores": confidence_scores
                        })
                        total_detections += len(image_detections)
            
            print(f"✅ 탐지 완료: {total_detections}개 객체, {inference_time:.2f}초 소요")
            print(f"⚡ 처리 속도: {len(image_files)/inference_time:.2f} 이미지/초")
            
            return {
                "success": True,
                "detections": detections,
                "processed_count": len(image_files),
                "total_detections": total_detections,
                "inference_time": inference_time,
                "images_per_second": len(image_files)/inference_time,
                "batch_size": self.batch_size,
                "device": self.device
            }
            
        except Exception as e:
            return {"success": False, "error": f"자동 탐지 중 오류: {str(e)}"}
    
    def suggest_annotations(self, detections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        어노테이션 제안 생성
        
        Args:
            detections: 탐지 결과 리스트
            
        Returns:
            제안 결과 딕셔너리
        """
        try:
            suggestions = []
            
            for detection_data in detections:
                image_path = detection_data["image_path"]
                detected_objects = detection_data["detections"]
                confidence_scores = detection_data["confidence_scores"]
                
                # 각 탐지된 객체에 대한 제안 생성
                image_suggestions = []
                for i, obj in enumerate(detected_objects):
                    confidence = confidence_scores[i] if i < len(confidence_scores) else 0.0
                    
                    suggestion = {
                        "suggested_label": obj["class_name"],
                        "bbox": obj["bbox"],
                        "confidence": confidence,
                        "suggestion_type": "yolo_detection",
                        "requires_review": confidence < 0.8  # 낮은 신뢰도는 검토 필요
                    }
                    image_suggestions.append(suggestion)
                
                suggestions.append({
                    "image_path": image_path,
                    "suggestions": image_suggestions,
                    "total_suggestions": len(image_suggestions)
                })
            
            return {
                "success": True,
                "suggestions": suggestions,
                "total_images": len(suggestions),
                "total_suggestions": sum(s["total_suggestions"] for s in suggestions),
                "high_confidence_count": sum(
                    len([s for s in img["suggestions"] if not s["requires_review"]]) 
                    for img in suggestions
                )
            }
            
        except Exception as e:
            return {"success": False, "error": f"제안 생성 중 오류: {str(e)}"}
    
    def batch_annotation(self, dataset_path: str, suggestions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        일괄 어노테이션 처리 (YOLO 형식 txt 파일 생성)
        
        Args:
            dataset_path: 데이터셋 경로
            suggestions: 제안 리스트
            
        Returns:
            일괄 처리 결과 딕셔너리
        """
        try:
            dataset_path = Path(dataset_path)
            labels_path = dataset_path / "labels"
            labels_path.mkdir(exist_ok=True)  # labels 폴더 생성
            
            processed_annotations = []
            
            for suggestion_data in suggestions:
                image_path = suggestion_data["image_path"]
                image_name = Path(image_path).stem
                
                # 이미지 크기 정보 가져오기
                try:
                    with Image.open(image_path) as img:
                        img_width, img_height = img.size
                except Exception as e:
                    print(f"⚠️ 이미지 로드 실패 {image_path}: {e}")
                    continue
                
                # YOLO 형식 txt 파일 경로
                txt_file = labels_path / f"{image_name}.txt"
                
                yolo_lines = []
                
                # 제안된 어노테이션을 YOLO 형식으로 변환
                for suggestion in suggestion_data["suggestions"]:
                    if not suggestion.get("requires_review", False):  # 검토가 필요하지 않은 것만
                        bbox = suggestion["bbox"]
                        x, y, w, h = bbox
                        class_name = suggestion["suggested_label"]
                        
                        # 클래스 ID 찾기
                        class_id = 0
                        if hasattr(self, 'class_names') and class_name in self.class_names.values():
                            # class_names가 딕셔너리인 경우 value로 key 찾기
                            for k, v in self.class_names.items():
                                if v == class_name:
                                    class_id = k
                                    break
                        
                        # YOLO 형식으로 좌표 정규화
                        x_center = (x + w/2) / img_width
                        y_center = (y + h/2) / img_height
                        norm_width = w / img_width
                        norm_height = h / img_height
                        
                        # YOLO 형식 라인 생성: class_id x_center y_center width height
                        yolo_line = f"{class_id} {x_center:.6f} {y_center:.6f} {norm_width:.6f} {norm_height:.6f}"
                        yolo_lines.append(yolo_line)
                
                # txt 파일 저장 로직
                if yolo_lines:  # 자동 탐지된 라벨이 있는 경우에만 처리
                    if txt_file.exists():
                        # 기존 파일이 있으면 append 모드로 추가
                        with open(txt_file, 'a', encoding='utf-8') as f:
                            f.write('\n'.join(yolo_lines) + '\n')
                        print(f"📝 기존 라벨에 추가: {txt_file}")
                    else:
                        # 기존 파일이 없으면 새로 생성
                        with open(txt_file, 'w', encoding='utf-8') as f:
                            f.write('\n'.join(yolo_lines) + '\n')
                        print(f"🆕 새 라벨 생성: {txt_file}")
                
                processed_annotations.append(str(txt_file))
            
            return {
                "success": True,
                "processed_annotations": processed_annotations,
                "total_processed": len(processed_annotations),
                "output_format": "YOLO (.txt)",
                "sample_output": self._get_sample_yolo_output(processed_annotations[0] if processed_annotations else None)
            }
            
        except Exception as e:
            return {"success": False, "error": f"일괄 처리 중 오류: {str(e)}"}
    
    def _get_sample_yolo_output(self, txt_file_path: str) -> str:
        """샘플 YOLO 출력 형식 반환"""
        if txt_file_path and os.path.exists(txt_file_path):
            try:
                with open(txt_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:3]  # 첫 3줄만
                    return '\n'.join(line.strip() for line in lines)
            except:
                pass
        return "0 0.565829 0.271714 0.074665 0.131164"
    
    def measure_inference_speed(self, dataset_path: str, batch_sizes: List[int] = None) -> Dict[str, Any]:
        """
        다양한 배치 사이즈로 추론 속도 측정
        
        Args:
            dataset_path: 데이터셋 경로
            batch_sizes: 테스트할 배치 사이즈 리스트
            
        Returns:
            성능 측정 결과
        """
        try:
            if not ULTRALYTICS_AVAILABLE or self.model is None:
                return {"success": False, "error": "YOLO 모델이 준비되지 않았습니다"}
            
            if batch_sizes is None:
                batch_sizes = [1, 4, 8, 16, 32]
            
            dataset_path = Path(dataset_path)
            images_path = dataset_path / "images"
            
            # 이미지 파일 수집
            image_extensions = ('.jpg', '.jpeg', '.png')
            image_files = []
            for ext in image_extensions:
                image_files.extend(list(images_path.rglob(f"*{ext}")))
            
            if not image_files:
                return {"success": False, "error": "측정할 이미지를 찾을 수 없습니다"}
            
            # 테스트용으로 최대 100개 이미지만 사용
            test_images = image_files[:min(100, len(image_files))]
            
            results = {}
            
            for batch_size in batch_sizes:
                print(f"🔄 배치 사이즈 {batch_size} 테스트 중...")
                
                start_time = time.time()
                
                # 배치 추론 실행
                results_gen = self.model.predict(
                    source=[str(img) for img in test_images],
                    conf=self.confidence_threshold,
                    batch=batch_size,
                    device=self.device,
                    save=False,
                    verbose=False,
                    stream=True
                )
                
                # 결과 수집 (완전 소모)
                batch_results = list(results_gen)
                inference_time = time.time() - start_time
                
                # 탐지된 객체 수 계산
                total_detections = 0
                for result in batch_results:
                    if result.boxes is not None:
                        total_detections += len(result.boxes)
                
                results[batch_size] = {
                    "inference_time": inference_time,
                    "images_per_second": len(test_images) / inference_time,
                    "avg_time_per_image": inference_time / len(test_images),
                    "total_detections": total_detections,
                    "detections_per_second": total_detections / inference_time
                }
                
                print(f"   ✅ {inference_time:.2f}초, {len(test_images)/inference_time:.1f} 이미지/초")
            
            return {
                "success": True,
                "device": self.device,
                "total_test_images": len(test_images),
                "model_path": self.model_path,
                "confidence_threshold": self.confidence_threshold,
                "batch_results": results
            }
            
        except Exception as e:
            return {"success": False, "error": f"성능 측정 중 오류: {str(e)}"}
    