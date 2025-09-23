"""
6. 데이터셋 분할 (Dataset Splitting)
Train/Validation/Test 분할, 계층적 샘플링, 시간적 분할을 담당하는 모듈
"""

import os
import shutil
import random
import json
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from collections import defaultdict, Counter
import datetime


class DatasetSplittingManager:
    """데이터셋 분할 관리 클래스"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        초기화
        
        Args:
            config: 설정 딕셔너리
        """
        self.config = config or {}
        self.split_ratios = self.config.get('split_ratios', {'train': 0.7, 'val': 0.2, 'test': 0.1})
        self.stratify = self.config.get('stratify', True)
        self.random_seed = self.config.get('random_seed', 42)
        self.shuffle = self.config.get('shuffle', True)
        
        # 시드 설정
        random.seed(self.random_seed)
        np.random.seed(self.random_seed)
    
    def smart_train_val_test_split(self, data_path: str, annotation_path: str = None) -> Dict[str, Any]:
        """
        스마트 Train/Validation/Test 분할
        
        Args:
            data_path: 이미지 데이터 경로
            annotation_path: 어노테이션 경로 (선택사항)
            
        Returns:
            데이터셋 분할 결과 딕셔너리
        """
        try:
            data_path = Path(data_path)
            annotation_path = Path(annotation_path) if annotation_path else None
            
            # 출력 디렉토리 생성
            output_base = data_path.parent / "split_dataset"
            output_base.mkdir(exist_ok=True)
            
            for split in ['train', 'val', 'test']:
                (output_base / split / 'images').mkdir(parents=True, exist_ok=True)
                if annotation_path:
                    (output_base / split / 'labels').mkdir(parents=True, exist_ok=True)
            
            # 이미지 파일 목록 가져오기
            image_files = []
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp']:
                image_files.extend(data_path.glob(ext))
            
            # 계층적 분할을 위한 클래스 정보 수집
            if annotation_path and self.stratify:
                class_distribution = self._analyze_class_distribution(image_files, annotation_path)
                splits = self._stratified_split(image_files, class_distribution)
            else:
                # 단순 랜덤 분할
                splits = self._random_split(image_files)
            
            # 파일 복사
            copy_results = {}
            for split_name, files in splits.items():
                result = self._copy_split_files(files, output_base / split_name, annotation_path)
                copy_results[split_name] = result
            
            # 분할 통계 생성
            statistics = self._generate_split_statistics(splits, annotation_path)
            
            # 분할 정보 저장
            split_info = {
                'split_ratios': self.split_ratios,
                'total_files': len(image_files),
                'splits': {split: len(files) for split, files in splits.items()},
                'stratified': self.stratify,
                'random_seed': self.random_seed,
                'timestamp': datetime.datetime.now().isoformat(),
                'statistics': statistics
            }
            
            with open(output_base / 'split_info.json', 'w', encoding='utf-8') as f:
                json.dump(split_info, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "output_path": str(output_base),
                "splits": {split: len(files) for split, files in splits.items()},
                "copy_results": copy_results,
                "statistics": statistics,
                "split_info_file": str(output_base / 'split_info.json')
            }
            
        except Exception as e:
            return {"success": False, "error": f"데이터셋 분할 중 오류: {str(e)}"}
    
    def _analyze_class_distribution(self, image_files: List[Path], annotation_path: Path) -> Dict[str, List[str]]:
        """클래스 분포 분석"""
        class_to_files = defaultdict(list)
        
        for image_file in image_files:
            annotation_file = annotation_path / f"{image_file.stem}.txt"
            
            if annotation_file.exists():
                try:
                    with open(annotation_file, 'r') as f:
                        lines = f.readlines()
                    
                    # 이 이미지에 포함된 클래스들
                    image_classes = set()
                    for line in lines:
                        line = line.strip()
                        if line:
                            parts = line.split()
                            if len(parts) >= 5:
                                class_id = int(parts[0])
                                image_classes.add(class_id)
                    
                    # 각 클래스에 이 이미지 추가
                    if image_classes:
                        # 주요 클래스 결정 (가장 많이 등장하는 클래스)
                        class_counts = Counter()
                        for line in lines:
                            line = line.strip()
                            if line:
                                parts = line.split()
                                if len(parts) >= 5:
                                    class_id = int(parts[0])
                                    class_counts[class_id] += 1
                        
                        main_class = class_counts.most_common(1)[0][0] if class_counts else 0
                        class_to_files[str(main_class)].append(str(image_file))
                    else:
                        # 어노테이션이 없는 경우
                        class_to_files['no_annotation'].append(str(image_file))
                        
                except Exception as e:
                    print(f"어노테이션 분석 실패 {annotation_file}: {e}")
                    class_to_files['error'].append(str(image_file))
            else:
                class_to_files['no_annotation'].append(str(image_file))
        
        return class_to_files
    
    def _stratified_split(self, image_files: List[Path], class_distribution: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """계층적 분할"""
        splits = {'train': [], 'val': [], 'test': []}
        
        for class_name, files in class_distribution.items():
            if self.shuffle:
                random.shuffle(files)
            
            # 클래스별 분할 비율 적용
            total_files = len(files)
            train_count = int(total_files * self.split_ratios['train'])
            val_count = int(total_files * self.split_ratios['val'])
            test_count = total_files - train_count - val_count
            
            # 분할 수행
            splits['train'].extend(files[:train_count])
            splits['val'].extend(files[train_count:train_count + val_count])
            splits['test'].extend(files[train_count + val_count:])
        
        return splits
    
    def _random_split(self, image_files: List[Path]) -> Dict[str, List[str]]:
        """랜덤 분할"""
        file_list = [str(f) for f in image_files]
        
        if self.shuffle:
            random.shuffle(file_list)
        
        total_files = len(file_list)
        train_count = int(total_files * self.split_ratios['train'])
        val_count = int(total_files * self.split_ratios['val'])
        
        splits = {
            'train': file_list[:train_count],
            'val': file_list[train_count:train_count + val_count],
            'test': file_list[train_count + val_count:]
        }
        
        return splits
    
    def _copy_split_files(self, file_list: List[str], output_dir: Path, annotation_path: Optional[Path]) -> Dict[str, Any]:
        """분할된 파일들 복사"""
        try:
            copied_images = 0
            copied_annotations = 0
            failed_copies = []
            
            for file_path in file_list:
                try:
                    file_path = Path(file_path)
                    
                    # 이미지 파일 복사
                    dst_image = output_dir / 'images' / file_path.name
                    shutil.copy2(file_path, dst_image)
                    copied_images += 1
                    
                    # 어노테이션 파일 복사 (있는 경우)
                    if annotation_path:
                        annotation_file = annotation_path / f"{file_path.stem}.txt"
                        if annotation_file.exists():
                            dst_annotation = output_dir / 'labels' / f"{file_path.stem}.txt"
                            shutil.copy2(annotation_file, dst_annotation)
                            copied_annotations += 1
                    
                except Exception as e:
                    failed_copies.append({
                        'file': str(file_path),
                        'error': str(e)
                    })
            
            return {
                'copied_images': copied_images,
                'copied_annotations': copied_annotations,
                'failed_copies': failed_copies,
                'success_rate': (copied_images - len(failed_copies)) / len(file_list) if file_list else 0
            }
            
        except Exception as e:
            return {
                'copied_images': 0,
                'copied_annotations': 0,
                'failed_copies': [{'error': f'복사 과정 오류: {str(e)}'}],
                'success_rate': 0
            }
    
    def stratified_sampling(self, data_path: str, annotation_path: str, sample_size: int) -> Dict[str, Any]:
        """
        계층적 샘플링
        
        Args:
            data_path: 이미지 데이터 경로
            annotation_path: 어노테이션 경로
            sample_size: 샘플 크기
            
        Returns:
            계층적 샘플링 결과 딕셔너리
        """
        try:
            data_path = Path(data_path)
            annotation_path = Path(annotation_path)
            
            # 이미지 파일 목록
            image_files = []
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp']:
                image_files.extend(data_path.glob(ext))
            
            # 클래스 분포 분석
            class_distribution = self._analyze_class_distribution(image_files, annotation_path)
            
            # 각 클래스에서 비례적으로 샘플링
            total_files = len(image_files)
            sampled_files = []
            
            for class_name, files in class_distribution.items():
                class_ratio = len(files) / total_files
                class_sample_size = int(sample_size * class_ratio)
                
                if class_sample_size > 0:
                    if self.shuffle:
                        random.shuffle(files)
                    sampled_files.extend(files[:class_sample_size])
            
            # 부족한 경우 추가 샘플링
            if len(sampled_files) < sample_size:
                remaining_files = [f for f in image_files if str(f) not in sampled_files]
                if self.shuffle:
                    random.shuffle(remaining_files)
                additional_needed = sample_size - len(sampled_files)
                sampled_files.extend([str(f) for f in remaining_files[:additional_needed]])
            
            # 출력 디렉토리 생성 및 파일 복사
            output_dir = data_path.parent / "stratified_sample"
            output_dir.mkdir(exist_ok=True)
            (output_dir / 'images').mkdir(exist_ok=True)
            (output_dir / 'labels').mkdir(exist_ok=True)
            
            copy_result = self._copy_split_files(sampled_files, output_dir, annotation_path)
            
            # 샘플링 정보 저장
            sampling_info = {
                'original_size': total_files,
                'sample_size': len(sampled_files),
                'target_size': sample_size,
                'class_distribution': {k: len(v) for k, v in class_distribution.items()},
                'sampling_ratios': {k: len([f for f in sampled_files if f in v]) / len(v) 
                                  for k, v in class_distribution.items() if v},
                'random_seed': self.random_seed,
                'timestamp': datetime.datetime.now().isoformat()
            }
            
            with open(output_dir / 'sampling_info.json', 'w', encoding='utf-8') as f:
                json.dump(sampling_info, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "output_path": str(output_dir),
                "sampled_files": sampled_files,
                "sampling_info": sampling_info,
                "copy_result": copy_result
            }
            
        except Exception as e:
            return {"success": False, "error": f"계층적 샘플링 중 오류: {str(e)}"}
    
    def temporal_split(self, data_path: str, time_column: str = 'created_time') -> Dict[str, Any]:
        """
        시간적 분할 (파일 생성 시간 기준)
        
        Args:
            data_path: 데이터 경로
            time_column: 시간 기준 컬럼명
            
        Returns:
            시간적 분할 결과 딕셔너리
        """
        try:
            data_path = Path(data_path)
            
            # 이미지 파일들과 생성 시간 수집
            file_times = []
            for image_file in data_path.glob("*"):
                if image_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
                    creation_time = os.path.getctime(str(image_file))
                    file_times.append((str(image_file), creation_time))
            
            # 시간순 정렬
            file_times.sort(key=lambda x: x[1])
            
            # 시간적 분할 수행
            total_files = len(file_times)
            train_count = int(total_files * self.split_ratios['train'])
            val_count = int(total_files * self.split_ratios['val'])
            
            splits = {
                'train': [f[0] for f in file_times[:train_count]],
                'val': [f[0] for f in file_times[train_count:train_count + val_count]],
                'test': [f[0] for f in file_times[train_count + val_count:]]
            }
            
            # 출력 디렉토리 생성
            output_base = data_path.parent / "temporal_split"
            output_base.mkdir(exist_ok=True)
            
            for split in ['train', 'val', 'test']:
                (output_base / split / 'images').mkdir(parents=True, exist_ok=True)
            
            # 파일 복사
            copy_results = {}
            for split_name, files in splits.items():
                result = self._copy_split_files(files, output_base / split_name, None)
                copy_results[split_name] = result
            
            # 시간 범위 정보
            time_ranges = {}
            for split_name, files in splits.items():
                if files:
                    times = [t for f, t in file_times if f in files]
                    time_ranges[split_name] = {
                        'start': datetime.datetime.fromtimestamp(min(times)).isoformat(),
                        'end': datetime.datetime.fromtimestamp(max(times)).isoformat(),
                        'count': len(files)
                    }
            
            # 분할 정보 저장
            temporal_info = {
                'split_method': 'temporal',
                'total_files': total_files,
                'splits': {split: len(files) for split, files in splits.items()},
                'time_ranges': time_ranges,
                'timestamp': datetime.datetime.now().isoformat()
            }
            
            with open(output_base / 'temporal_split_info.json', 'w', encoding='utf-8') as f:
                json.dump(temporal_info, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "output_path": str(output_base),
                "splits": {split: len(files) for split, files in splits.items()},
                "copy_results": copy_results,
                "time_ranges": time_ranges,
                "temporal_info_file": str(output_base / 'temporal_split_info.json')
            }
            
        except Exception as e:
            return {"success": False, "error": f"시간적 분할 중 오류: {str(e)}"}
    
    def _generate_split_statistics(self, splits: Dict[str, List[str]], annotation_path: Optional[Path]) -> Dict[str, Any]:
        """분할 통계 생성"""
        statistics = {}
        
        for split_name, files in splits.items():
            stats = {
                'file_count': len(files),
                'percentage': len(files) / sum(len(f) for f in splits.values()) * 100 if splits else 0
            }
            
            if annotation_path:
                # 클래스 분포 통계
                class_counts = Counter()
                total_objects = 0
                
                for file_path in files:
                    file_path = Path(file_path)
                    annotation_file = annotation_path / f"{file_path.stem}.txt"
                    
                    if annotation_file.exists():
                        try:
                            with open(annotation_file, 'r') as f:
                                lines = f.readlines()
                            
                            for line in lines:
                                line = line.strip()
                                if line:
                                    parts = line.split()
                                    if len(parts) >= 5:
                                        class_id = int(parts[0])
                                        class_counts[class_id] += 1
                                        total_objects += 1
                        except Exception:
                            pass
                
                stats['class_distribution'] = dict(class_counts)
                stats['total_objects'] = total_objects
                stats['avg_objects_per_image'] = total_objects / len(files) if files else 0
            
            statistics[split_name] = stats
        
        return statistics
    
    def validate_split_balance(self, split_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        분할 균형성 검증
        
        Args:
            split_results: 분할 결과
            
        Returns:
            균형성 검증 결과 딕셔너리
        """
        try:
            statistics = split_results.get('statistics', {})
            
            # 크기 균형성 검사
            size_balance = {}
            total_files = sum(stats['file_count'] for stats in statistics.values())
            
            for split_name, stats in statistics.items():
                actual_ratio = stats['file_count'] / total_files if total_files > 0 else 0
                expected_ratio = self.split_ratios.get(split_name, 0)
                difference = abs(actual_ratio - expected_ratio)
                
                size_balance[split_name] = {
                    'actual_ratio': actual_ratio,
                    'expected_ratio': expected_ratio,
                    'difference': difference,
                    'balanced': difference < 0.05  # 5% 이내 허용
                }
            
            # 클래스 균형성 검사 (어노테이션이 있는 경우)
            class_balance = {}
            if all('class_distribution' in stats for stats in statistics.values()):
                # 전체 클래스 목록
                all_classes = set()
                for stats in statistics.values():
                    all_classes.update(stats['class_distribution'].keys())
                
                for class_id in all_classes:
                    class_balance[class_id] = {}
                    total_class_objects = sum(
                        stats['class_distribution'].get(class_id, 0) 
                        for stats in statistics.values()
                    )
                    
                    for split_name, stats in statistics.items():
                        class_count = stats['class_distribution'].get(class_id, 0)
                        class_ratio = class_count / total_class_objects if total_class_objects > 0 else 0
                        expected_ratio = self.split_ratios.get(split_name, 0)
                        
                        class_balance[class_id][split_name] = {
                            'count': class_count,
                            'ratio': class_ratio,
                            'expected_ratio': expected_ratio,
                            'difference': abs(class_ratio - expected_ratio)
                        }
            
            # 전체 균형성 점수 계산
            size_score = np.mean([
                1 - min(1, balance['difference'] * 20)  # 5% 차이 = 0점
                for balance in size_balance.values()
            ])
            
            class_score = 1.0  # 기본값
            if class_balance:
                class_differences = []
                for class_data in class_balance.values():
                    for split_data in class_data.values():
                        class_differences.append(split_data['difference'])
                
                if class_differences:
                    class_score = np.mean([
                        1 - min(1, diff * 10)  # 10% 차이 = 0점
                        for diff in class_differences
                    ])
            
            overall_score = (size_score + class_score) / 2
            
            return {
                "success": True,
                "size_balance": size_balance,
                "class_balance": class_balance,
                "scores": {
                    "size_balance_score": size_score,
                    "class_balance_score": class_score,
                    "overall_balance_score": overall_score
                },
                "recommendations": self._generate_balance_recommendations(size_balance, class_balance)
            }
            
        except Exception as e:
            return {"success": False, "error": f"균형성 검증 중 오류: {str(e)}"}
    
    def _generate_balance_recommendations(self, size_balance: Dict[str, Any], class_balance: Dict[str, Any]) -> List[str]:
        """균형성 개선 권장사항 생성"""
        recommendations = []
        
        # 크기 균형성 권장사항
        for split_name, balance in size_balance.items():
            if not balance['balanced']:
                if balance['actual_ratio'] > balance['expected_ratio']:
                    recommendations.append(f"{split_name} 세트의 크기를 줄이는 것을 고려하세요")
                else:
                    recommendations.append(f"{split_name} 세트의 크기를 늘리는 것을 고려하세요")
        
        # 클래스 균형성 권장사항
        if class_balance:
            for class_id, class_data in class_balance.items():
                for split_name, split_data in class_data.items():
                    if split_data['difference'] > 0.1:  # 10% 이상 차이
                        recommendations.append(
                            f"클래스 {class_id}의 {split_name} 세트 분포를 조정하세요 "
                            f"(현재: {split_data['ratio']:.1%}, 목표: {split_data['expected_ratio']:.1%})"
                        )
        
        if not recommendations:
            recommendations.append("데이터셋 분할이 잘 균형을 이루고 있습니다")
        
        return recommendations