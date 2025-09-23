"""
로컬 파일 시스템 데이터셋 관리자

이 모듈은 로컬 이미지와 TXT 어노테이션 파일들을 YOLO 형식 데이터셋으로 변환합니다.
"""

import os
import json
import shutil
from typing import List, Dict, Any, Optional
from pathlib import Path

from .roboflow_client import LocalDatasetManager, LocalDatasetConfig


class DatasetManager:
    """로컬 데이터셋 관리 클래스"""
    
    def __init__(self, client: LocalDatasetManager):
        self.client = client
    
    def prepare_dataset_from_local_files(self, local_folder_path: str, image_pattern: str = "*.jpg") -> Dict[str, Any]:
        """로컬 파일 시스템에서 이미지와 txt 어노테이션 파일들을 읽어 데이터셋 준비"""
        try:
            from pathlib import Path
            
            local_path = Path(local_folder_path)
            if not local_path.exists():
                print(f"로컬 폴더가 존재하지 않습니다: {local_folder_path}")
                return {}
            
            # 이미지 파일들 찾기
            image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
            image_files = []
            for ext in image_extensions:
                image_files.extend(list(local_path.glob(ext)))
                image_files.extend(list(local_path.glob(ext.upper())))
            
            dataset_info = {
                "total_images": len(image_files),
                "annotations": 0,
                "classes": set(),
                "files": []
            }
            
            for image_file in image_files:
                try:
                    # 대응하는 txt 파일 찾기
                    txt_file = image_file.with_suffix('.txt')
                    
                    shapes = []
                    if txt_file.exists():
                        # txt 파일에서 어노테이션 읽기 (YOLO 형식 가정)
                        with open(txt_file, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if line:
                                    parts = line.split()
                                    if len(parts) >= 5:
                                        class_id = int(parts[0])
                                        center_x = float(parts[1])
                                        center_y = float(parts[2])
                                        width = float(parts[3])
                                        height = float(parts[4])
                                        
                                        # YOLO 형식을 shape 형식으로 변환
                                        shape = {
                                            "label": f"class_{class_id}",
                                            "shape_type": "rectangle",
                                            "points": [
                                                [center_x - width/2, center_y - height/2],
                                                [center_x + width/2, center_y + height/2]
                                            ]
                                        }
                                        shapes.append(shape)
                                        dataset_info["classes"].add(f"class_{class_id}")
                    
                    dataset_info["annotations"] += len(shapes)
                    
                    # 이미지 메타데이터 가져오기
                    from PIL import Image
                    try:
                        with Image.open(image_file) as img:
                            img_width, img_height = img.size
                    except:
                        img_width, img_height = None, None
                    
                    # 이미지 경로 해결
                    image_path = self._resolve_image_path_from_image(image_file, local_path)
                    
                    dataset_info["files"].append({
                        "image_path": image_path,
                        "shapes": shapes,
                        "metadata": {
                            "txt_file": str(txt_file) if txt_file.exists() else None,
                            "width": img_width,
                            "height": img_height
                        }
                    })
                    
                except Exception as e:
                    print(f"파일 처리 중 오류 ({image_file}): {e}")
                    continue
            
            dataset_info["classes"] = list(dataset_info["classes"])
            return dataset_info
            
        except Exception as e:
            print(f"로컬 데이터셋 준비 중 오류: {e}")
            return {}
    
    def _resolve_image_path_from_image(self, image_file: Path, base_path: Path) -> Optional[str]:
        """이미지 파일 경로가 존재하는지 확인"""
        try:
            if image_file.exists():
                return str(image_file)
            return None
            
        except Exception as e:
            print(f"이미지 경로 해결 중 오류: {e}")
            return None
    
    def create_local_yolo_dataset(self, dataset_info: Dict[str, Any], 
                                 train_ratio: float = 0.7, 
                                 val_ratio: float = 0.2,
                                 test_ratio: float = 0.1) -> bool:
        """로컬 파일 시스템에서 YOLO 데이터셋 생성"""
        try:
            # 데이터셋 폴더 구조 생성
            result = self.client.create_dataset_structure()
            if not result.get("success", False):
                print(f"폴더 구조 생성 실패: {result.get('error', 'Unknown error')}")
            return False
            
            output_path = Path(self.client.get_output_path())
            
            # 클래스 목록 가져오기
            classes = dataset_info.get("classes", [])
            
            # data.yaml 파일 생성 (YOLO 학습용)
            self._create_data_yaml(output_path, classes, train_ratio, val_ratio, test_ratio)
            
            # 파일들 처리 (분할 없이 모든 파일을 train으로)
            files = dataset_info.get("files", [])
            if not files:
                print("변환할 파일이 없습니다.")
            return False
            
            # train 폴더에 모든 파일 생성
            images_dir = output_path / "images" / "train"
            labels_dir = output_path / "labels" / "train"
            
            for file_info in files:
                success = self._process_single_file(
                    file_info, images_dir, labels_dir, classes
                )
            if not success:
                print(f"파일 처리 실패: {file_info.get('image_path', 'unknown')}")
            
            # 데이터셋 정보 저장
            self.client.save_dataset_info(dataset_info)
            
            print(f"✅ 로컬 YOLO 데이터셋 생성 완료: {output_path}")
            return True
            
        except Exception as e:
            print(f"YOLO 데이터셋 생성 중 오류: {e}")
            return False
    
    def _create_data_yaml(self, output_path: Path, classes: List[str], 
                         train_ratio: float, val_ratio: float, test_ratio: float):
        """YOLO data.yaml 파일 생성"""
        try:
            data_yaml_content = f"""# X-AnyLabeling에서 생성된 데이터셋
path: {output_path.absolute()}
train: images/train
val: images/val
test: images/test

# 클래스 정보
nc: {len(classes)}
names: {classes}

# 데이터 분할 비율
# train: {train_ratio:.1%}, val: {val_ratio:.1%}, test: {test_ratio:.1%}
"""
            
            with open(output_path / "data.yaml", "w", encoding="utf-8") as f:
                f.write(data_yaml_content)
                
        except Exception as e:
            print(f"data.yaml 생성 중 오류: {e}")
    
    def _process_single_file(self, file_info: Dict[str, Any], 
                           images_dir: Path, labels_dir: Path, 
                           classes: List[str]) -> bool:
        """단일 파일 처리 (이미지 복사 + 어노테이션 변환)"""
        try:
            image_path = file_info["image_path"]
            shapes = file_info["shapes"]
            metadata = file_info["metadata"]
            
            if not os.path.exists(image_path):
                return False
            
            # 이미지 파일명
            image_name = Path(image_path).name
            base_name = Path(image_path).stem
            
            # 이미지 복사 (옵션에 따라)
            if self.client.config.copy_images:
                dest_image_path = images_dir / image_name
                shutil.copy2(image_path, dest_image_path)
            
            # YOLO 어노테이션 파일 생성
            annotation_file = labels_dir / f"{base_name}.txt"
            
            with open(annotation_file, "w", encoding="utf-8") as f:
                for shape in shapes:
                    yolo_line = self._convert_shape_to_yolo(shape, metadata, classes)
                    if yolo_line:
                        f.write(f"{yolo_line}\n")
            
            return True
            
        except Exception as e:
            print(f"파일 처리 중 오류: {e}")
            return False
    
    def _convert_shape_to_yolo(self, shape: Dict[str, Any], metadata: Dict[str, Any], classes: List[str]) -> Optional[str]:
        """단일 shape을 YOLO 형식으로 변환"""
        try:
            label = shape.get('label')
            if not label or label not in classes:
                return None
            
            class_id = classes.index(label)
            
            # 바운딩박스 좌표 추출 (shape_type에 따라 다름)
            shape_type = shape.get('shape_type', 'rectangle')
            points = shape.get('points', [])
            
            if shape_type == 'rectangle' and len(points) >= 2:
                x1, y1 = points[0]
                x2, y2 = points[1]
                
                # 정규화 (0-1 범위)
                img_width = metadata.get('width', 1)
                img_height = metadata.get('height', 1)
                
                center_x = (x1 + x2) / 2 / img_width
                center_y = (y1 + y2) / 2 / img_height
                width = abs(x2 - x1) / img_width
                height = abs(y2 - y1) / img_height
                
                return f"{class_id} {center_x:.6f} {center_y:.6f} {width:.6f} {height:.6f}"
            
            return None
            
        except Exception as e:
            print(f"Shape 변환 중 오류: {e}")
            return None