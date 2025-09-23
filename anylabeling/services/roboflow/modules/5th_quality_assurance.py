"""
5. 품질 보증 (Quality Assurance)

중복 이미지 검출, 어노테이션 품질 검사, 바운딩박스 검증, 품질 플래그 표시를 담당하는 모듈
"""

import os
import cv2
import numpy as np
import hashlib
import json
from typing import Dict, List, Any, Optional, Tuple, Set
from pathlib import Path
from PIL import Image
from collections import defaultdict

class QualityAssuranceManager:
    """품질 보증 관리 클래스"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        초기화
        
        Args:
            config: 설정 딕셔너리
        """
        self.config = config or {}
        self.similarity_threshold = self.config.get('similarity_threshold', 0.95)
        self.min_bbox_area = self.config.get('min_bbox_area', 100)
        self.max_bbox_area_ratio = self.config.get('max_bbox_area_ratio', 0.9)
        self.min_image_size = self.config.get('min_image_size', (64, 64))
        self.max_aspect_ratio = self.config.get('max_aspect_ratio', 10.0)
        
    def detect_duplicates(self, data_path: str) -> Dict[str, Any]:
        """
        중복 이미지 검출
        
        Args:
            data_path: 데이터 경로
            
        Returns:
            중복 검출 결과 딕셔너리
        """
        try:
            data_path = Path(data_path)
            
            # 이미지 해시 계산
            image_hashes = {}
            duplicate_groups = []
            hash_to_files = defaultdict(list)
            
            # 모든 이미지 파일에 대해 해시 계산
            for image_file in data_path.rglob("*"):
                if image_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
                    try:
                        # 파일 해시와 구조적 해시 모두 계산
                        file_hash = self._calculate_file_hash(str(image_file))
                        structural_hash = self._calculate_structural_hash(str(image_file))
                        
                        # 결합 해시 생성
                        combined_hash = f"{file_hash}_{structural_hash}"
                        
                        image_hashes[str(image_file)] = {
                            'file_hash': file_hash,
                            'structural_hash': structural_hash,
                            'combined_hash': combined_hash
                        }
                        
                        hash_to_files[combined_hash].append(str(image_file))
                        
                    except Exception as e:
                        print(f"해시 계산 실패 {image_file}: {e}")
            
            # 중복 그룹 찾기
            for hash_value, files in hash_to_files.items():
                if len(files) > 1:
                    duplicate_groups.append({
                        'hash': hash_value,
                        'files': files,
                        'count': len(files)
                    })
            
            # 유사 이미지 검출 (구조적 유사성 기반)
            similar_pairs = self._find_similar_images(list(image_hashes.keys()))
            
            # 결과 요약
            total_images = len(image_hashes)
            total_duplicates = sum(len(group['files']) - 1 for group in duplicate_groups)
            
            return {
                "success": True,
                "total_images": total_images,
                "duplicate_groups": duplicate_groups,
                "similar_pairs": similar_pairs,
                "total_duplicates": total_duplicates,
                "image_hashes": image_hashes,
                "recommendations": self._generate_duplicate_recommendations(duplicate_groups)
            }
            
        except Exception as e:
            return {"success": False, "error": f"중복 검출 중 오류: {str(e)}"}
    
    def _calculate_file_hash(self, image_path: str) -> str:
        """파일 해시 계산 (MD5)"""
        hash_md5 = hashlib.md5()
        with open(image_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _calculate_structural_hash(self, image_path: str) -> str:
        """구조적 해시 계산 (이미지 내용 기반)"""
        try:
            # 이미지 로드 및 전처리
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            resized = cv2.resize(image, (8, 8), interpolation=cv2.INTER_AREA)
            
            # 평균 계산
            avg = resized.mean()
            
            # 이진 해시 생성
            binary_string = ""
            for row in resized:
                for pixel in row:
                    binary_string += "1" if pixel > avg else "0"
            
            # 16진수 해시로 변환
            hash_value = hex(int(binary_string, 2))[2:]
            return hash_value
            
        except Exception as e:
            return f"error_{str(e)[:8]}"
    
    def _find_similar_images(self, image_paths: List[str]) -> List[Dict[str, Any]]:
        """구조적 유사성 기반 유사 이미지 찾기"""
        similar_pairs = []
        
        for i in range(len(image_paths)):
            for j in range(i + 1, len(image_paths)):
                try:
                    similarity = self._calculate_similarity(image_paths[i], image_paths[j])
                    if similarity > self.similarity_threshold:
                        similar_pairs.append({
                            'image1': image_paths[i],
                            'image2': image_paths[j],
                            'similarity': similarity
                        })
                except Exception as e:
                    print(f"유사성 계산 실패: {e}")
        return similar_pairs
    
    def _calculate_similarity(self, image_path1: str, image_path2: str) -> float:
        """두 이미지 간 구조적 유사성 계산"""
        try:
            # 이미지 로드
            img1 = cv2.imread(image_path1, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(image_path2, cv2.IMREAD_GRAYSCALE)
            
            # 동일한 크기로 리사이즈
            size = (256, 256)
            img1 = cv2.resize(img1, size)
            img2 = cv2.resize(img2, size)
            
            # SSIM (Structural Similarity Index) 계산
            # OpenCV 4.x에서는 cv2.matchTemplate 사용
            result = cv2.matchTemplate(img1, img2, cv2.TM_CCOEFF_NORMED)
            similarity = np.max(result)
            return float(similarity)
            
        except Exception as e:
            return 0.0
    
    def _generate_duplicate_recommendations(self, duplicate_groups: List[Dict[str, Any]]) -> List[str]:
        """중복 제거 권장사항 생성"""
        recommendations = []
        
        for group in duplicate_groups:
            files = group['files']
            if len(files) > 1:
                # 파일 크기 기준으로 정렬 (큰 것을 유지)
                file_sizes = [(f, os.path.getsize(f)) for f in files]
                file_sizes.sort(key=lambda x: x[1], reverse=True)
                
                keep_file = file_sizes[0][0]
                remove_files = [f[0] for f in file_sizes[1:]]
                
                recommendations.append(f"유지: {keep_file}")
                for remove_file in remove_files:
                    recommendations.append(f"삭제: {remove_file}")
        return recommendations
    
    def check_annotation_quality(self, data_path: str, annotation_path: str) -> Dict[str, Any]:
        """
        어노테이션 품질 검사
        
        Args:
            data_path: 이미지 데이터 경로
            annotation_path: 어노테이션 경로
            
        Returns:
            어노테이션 품질 검사 결과 딕셔너리
        """
        try:
            data_path = Path(data_path)
            annotation_path = Path(annotation_path)
            
            quality_issues = []
            annotation_stats = {
                'total_files': 0,
                'annotated_files': 0,
                'empty_annotations': 0,
                'invalid_formats': 0,
                'bbox_issues': 0
            }
            
            for image_file in data_path.glob("*"):
                if image_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
                    annotation_stats['total_files'] += 1
                    
                    # 대응하는 어노테이션 파일 찾기
                    annotation_file = annotation_path / f"{image_file.stem}.txt"
                    
                    if annotation_file.exists():
                        annotation_stats['annotated_files'] += 1
                        
                        # 어노테이션 파일 검사
                        issues = self._check_single_annotation(str(image_file), str(annotation_file))
                        if issues:
                            quality_issues.extend(issues)
                            if any('형식' in issue['type'] for issue in issues):
                                annotation_stats['invalid_formats'] += 1
                            if any('바운딩박스' in issue['type'] for issue in issues):
                                annotation_stats['bbox_issues'] += 1
                    else:
                        quality_issues.append({
                            'file': str(image_file),
                            'type': '어노테이션 누락',
                            'description': '어노테이션 파일이 없습니다',
                            'severity': 'high'
                        })
            
            # 빈 어노테이션 파일 검사
            for annotation_file in annotation_path.glob("*.txt"):
                if annotation_file.stat().st_size == 0:
                    annotation_stats['empty_annotations'] += 1
                    quality_issues.append({
                        'file': str(annotation_file),
                        'type': '빈 어노테이션',
                        'description': '어노테이션이 비어있습니다',
                        'severity': 'medium'
                    })
            
            # 품질 점수 계산
            if annotation_stats['total_files'] > 0:
                annotation_rate = annotation_stats['annotated_files'] / annotation_stats['total_files']
                error_rate = len(quality_issues) / annotation_stats['total_files']
                quality_score = max(0, (annotation_rate - error_rate) * 100)
            else:
                quality_score = 0
            
            return {
                "success": True,
                "quality_issues": quality_issues,
                "annotation_stats": annotation_stats,
                "quality_score": quality_score,
                "recommendations": self._generate_quality_recommendations(quality_issues)
            }
            
        except Exception as e:
            return {"success": False, "error": f"어노테이션 품질 검사 중 오류: {str(e)}"}
    
    def _check_single_annotation(self, image_path: str, annotation_path: str) -> List[Dict[str, Any]]:
        """단일 어노테이션 파일 검사"""
        issues = []
        
        try:
            # 이미지 크기 정보 가져오기
            with Image.open(image_path) as img:
                img_width, img_height = img.size
            
            # 어노테이션 파일 읽기
            with open(annotation_path, 'r') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split()
                
                # 형식 검사
                if len(parts) < 5:
                    issues.append({
                        'file': annotation_path,
                        'line': line_num,
                        'type': '형식 오류',
                        'description': f'잘못된 형식: {line}',
                        'severity': 'high'
                    })
                    continue
                
                try:
                    class_id = int(parts[0])
                    x_center, y_center, width, height = map(float, parts[1:5])
                    
                    # 좌표 유효성 검사
                    if not (0 <= x_center <= 1 and 0 <= y_center <= 1 and 
                           0 <= width <= 1 and 0 <= height <= 1):
                        issues.append({
                            'file': annotation_path,
                            'line': line_num,
                            'type': '좌표 범위 오류',
                            'description': '좌표가 0-1 범위를 벗어났습니다',
                            'severity': 'high'
                        })
                    
                    # 바운딩박스 크기 검사
                    bbox_area = width * height * img_width * img_height
                    if bbox_area < self.min_bbox_area:
                        issues.append({
                            'file': annotation_path,
                            'line': line_num,
                            'type': '바운딩박스 너무 작음',
                            'description': f'바운딩박스 면적이 너무 작습니다: {bbox_area:.1f}',
                            'severity': 'medium'
                        })
                    
                    # 바운딩박스가 이미지의 대부분을 차지하는지 검사
                    area_ratio = width * height
                    if area_ratio > self.max_bbox_area_ratio:
                        issues.append({
                            'file': annotation_path,
                            'line': line_num,
                            'type': '바운딩박스 너무 큼',
                            'description': f'바운딩박스가 이미지의 {area_ratio:.1%}를 차지합니다',
                            'severity': 'medium'
                        })
                    
                    # 종횡비 검사
                    aspect_ratio = width / height if height > 0 else float('inf')
                    if aspect_ratio > self.max_aspect_ratio or aspect_ratio < 1/self.max_aspect_ratio:
                        issues.append({
                            'file': annotation_path,
                            'line': line_num,
                            'type': '비정상적인 종횡비',
                            'description': f'종횡비가 비정상적입니다: {aspect_ratio:.2f}',
                            'severity': 'low'
                        })
                    
                except ValueError:
                    issues.append({
                        'file': annotation_path,
                        'line': line_num,
                        'type': '형식 오류',
                        'description': '숫자 형식이 잘못되었습니다',
                        'severity': 'high'
                    })
            
        except Exception as e:
            issues.append({
                'file': annotation_path,
                'type': '파일 읽기 오류',
                'description': f'파일을 읽을 수 없습니다: {str(e)}',
                'severity': 'high'
            })
        
        return issues
    
    def validate_bboxes(self, data_path: str, annotation_path: str) -> Dict[str, Any]:
        """
        바운딩박스 검증
        
        Args:
            data_path: 이미지 데이터 경로
            annotation_path: 어노테이션 경로
            
        Returns:
            바운딩박스 검증 결과 딕셔너리
        """
        try:
            data_path = Path(data_path)
            annotation_path = Path(annotation_path)
            
            validation_results = []
            total_bboxes = 0
            valid_bboxes = 0
            
            for image_file in data_path.glob("*"):
                if image_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
                    annotation_file = annotation_path / f"{image_file.stem}.txt"
                    
                    if annotation_file.exists():
                        result = self._validate_single_bbox_file(str(image_file), str(annotation_file))
                        validation_results.append(result)
                        total_bboxes += result['total_bboxes']
                        valid_bboxes += result['valid_bboxes']
            
            # 검증 통계
            validation_rate = (valid_bboxes / total_bboxes * 100) if total_bboxes > 0 else 0
            
            return {
                "success": True,
                "validation_results": validation_results,
                "total_bboxes": total_bboxes,
                "valid_bboxes": valid_bboxes,
                "validation_rate": validation_rate,
                "summary": {
                    "total_files": len(validation_results),
                    "files_with_issues": len([r for r in validation_results if r['issues']]),
                    "validation_rate": validation_rate
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"바운딩박스 검증 중 오류: {str(e)}"}
    
    def _validate_single_bbox_file(self, image_path: str, annotation_path: str) -> Dict[str, Any]:
        """단일 바운딩박스 파일 검증"""
        try:
            # 이미지 정보
            with Image.open(image_path) as img:
                img_width, img_height = img.size
            
            issues = []
            total_bboxes = 0
            valid_bboxes = 0
            
            with open(annotation_path, 'r') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                total_bboxes += 1
                parts = line.split()
                
                if len(parts) >= 5:
                    try:
                        class_id = int(parts[0])
                        x_center, y_center, width, height = map(float, parts[1:5])
                        
                        # 바운딩박스 픽셀 좌표 계산
                        x1 = (x_center - width/2) * img_width
                        y1 = (y_center - height/2) * img_height
                        x2 = (x_center + width/2) * img_width
                        y2 = (y_center + height/2) * img_height
                        
                        # 검증 수행
                        bbox_valid = True
                        
                        # 이미지 경계 내부에 있는지 확인
                        if x1 < 0 or y1 < 0 or x2 > img_width or y2 > img_height:
                            issues.append(f"라인 {line_num}: 바운딩박스가 이미지 경계를 벗어남")
                            bbox_valid = False
                        
                        # 최소 크기 확인
                        bbox_area = (x2 - x1) * (y2 - y1)
                        if bbox_area < self.min_bbox_area:
                            issues.append(f"라인 {line_num}: 바운딩박스가 너무 작음 (면적: {bbox_area:.1f})")
                            bbox_valid = False
                        
                        # 유효한 바운딩박스인지 확인
                        if width <= 0 or height <= 0:
                            issues.append(f"라인 {line_num}: 바운딩박스 크기가 0 이하")
                            bbox_valid = False
                        
                        if bbox_valid:
                            valid_bboxes += 1
                            
                    except ValueError:
                        issues.append(f"라인 {line_num}: 숫자 형식 오류")
                else:
                    issues.append(f"라인 {line_num}: 형식 오류 (5개 값 필요)")
            
            return {
                'image_file': image_path,
                'annotation_file': annotation_path,
                'total_bboxes': total_bboxes,
                'valid_bboxes': valid_bboxes,
                'issues': issues
            }
            
        except Exception as e:
            return {
                'image_file': image_path,
                'annotation_file': annotation_path,
                'total_bboxes': 0,
                'valid_bboxes': 0,
                'issues': [f"파일 처리 오류: {str(e)}"]
            }
    
    def flag_quality_issues(self, data_path: str) -> Dict[str, Any]:
        """
        품질 이슈 플래그 표시
        
        Args:
            data_path: 데이터 경로
            
        Returns:
            품질 이슈 플래그 결과 딕셔너리
        """
        try:
            data_path = Path(data_path)
            flagged_files = []
            quality_flags = {
                'low_resolution': [],
                'corrupted': [],
                'suspicious_aspect_ratio': [],
                'too_small': [],
                'format_issues': []
            }
            
            for image_file in data_path.rglob("*"):
                if image_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
                    try:
                        flags = self._check_image_quality(str(image_file))
                        if flags:
                            flagged_files.append({
                                'file': str(image_file),
                                'flags': flags
                            })
                            
                            # 카테고리별 분류
                            for flag in flags:
                                if flag['type'] in quality_flags:
                                    quality_flags[flag['type']].append(str(image_file))
                                    
                    except Exception as e:
                        quality_flags['corrupted'].append(str(image_file))
                        flagged_files.append({
                            'file': str(image_file),
                            'flags': [{'type': 'corrupted', 'description': f'파일 처리 오류: {str(e)}'}]
                        })
            
            # 품질 보고서 생성
            total_files = len(list(data_path.rglob("*")))
            flagged_count = len(flagged_files)
            quality_percentage = ((total_files - flagged_count) / total_files * 100) if total_files > 0 else 0
            
            return {
                "success": True,
                "flagged_files": flagged_files,
                "quality_flags": quality_flags,
                "statistics": {
                    "total_files": total_files,
                    "flagged_files": flagged_count,
                    "quality_percentage": quality_percentage
                },
                "recommendations": self._generate_quality_fix_recommendations(quality_flags)
            }
            
        except Exception as e:
            return {"success": False, "error": f"품질 플래그 표시 중 오류: {str(e)}"}
    
    def _check_image_quality(self, image_path: str) -> List[Dict[str, Any]]:
        """단일 이미지 품질 검사"""
        flags = []
        
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                
                # 해상도 검사
                if width < self.min_image_size[0] or height < self.min_image_size[1]:
                    flags.append({
                        'type': 'low_resolution',
                        'description': f'해상도가 낮습니다: {width}x{height}'
                    })
                
                # 크기 검사
                if width < 64 or height < 64:
                    flags.append({
                        'type': 'too_small',
                        'description': f'이미지가 너무 작습니다: {width}x{height}'
                    })
                
                # 종횡비 검사
                aspect_ratio = width / height
                if aspect_ratio > self.max_aspect_ratio or aspect_ratio < 1/self.max_aspect_ratio:
                    flags.append({
                        'type': 'suspicious_aspect_ratio',
                        'description': f'비정상적인 종횡비: {aspect_ratio:.2f}'
                    })
                
                # 이미지 형식 검사
                if img.mode not in ['RGB', 'RGBA', 'L']:
                    flags.append({
                        'type': 'format_issues',
                        'description': f'지원되지 않는 색상 모드: {img.mode}'
                    })
                
        except Exception as e:
            flags.append({
                'type': 'corrupted',
                'description': f'이미지 파일이 손상되었습니다: {str(e)}'
            })
        
        return flags
    
    def _generate_quality_recommendations(self, quality_issues: List[Dict[str, Any]]) -> List[str]:
        """품질 개선 권장사항 생성"""
        recommendations = []
        
        # 이슈 유형별 카운트
        issue_counts = defaultdict(int)
        for issue in quality_issues:
            issue_counts[issue['type']] += 1
        
        # 권장사항 생성
        if issue_counts['어노테이션 누락'] > 0:
            recommendations.append(f"{issue_counts['어노테이션 누락']}개 파일의 어노테이션을 추가하세요")
        
        if issue_counts['형식 오류'] > 0:
            recommendations.append(f"{issue_counts['형식 오류']}개 어노테이션의 형식을 수정하세요")
        
        if issue_counts['바운딩박스 너무 작음'] > 0:
            recommendations.append("작은 바운딩박스들을 검토하고 필요시 제거하세요")
        
        if issue_counts['바운딩박스 너무 큼'] > 0:
            recommendations.append("큰 바운딩박스들을 검토하고 적절히 분할하세요")
        
        return recommendations
    
    def _generate_quality_fix_recommendations(self, quality_flags: Dict[str, List[str]]) -> List[str]:
        """품질 수정 권장사항 생성"""
        recommendations = []
        
        if quality_flags['low_resolution']:
            recommendations.append(f"{len(quality_flags['low_resolution'])}개의 저해상도 이미지를 고해상도로 교체하세요")
        
        if quality_flags['corrupted']:
            recommendations.append(f"{len(quality_flags['corrupted'])}개의 손상된 파일을 제거하거나 복구하세요")
        
        if quality_flags['too_small']:
            recommendations.append(f"{len(quality_flags['too_small'])}개의 작은 이미지를 제거하거나 업스케일하세요")
        
        if quality_flags['suspicious_aspect_ratio']:
            recommendations.append(f"{len(quality_flags['suspicious_aspect_ratio'])}개의 비정상적인 종횡비 이미지를 검토하세요")
        
        if quality_flags['format_issues']:
            recommendations.append(f"{len(quality_flags['format_issues'])}개의 형식 이슈를 수정하세요")
        
        return recommendations