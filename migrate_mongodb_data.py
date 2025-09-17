#!/usr/bin/env python3
"""
기존 MongoDB 데이터를 새로운 annotation_manager 구조로 마이그레이션
"""

import json
import os
import logging
from datetime import datetime
from pymongo import MongoClient
from typing import Dict, Any

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataMigrator:
    def __init__(self, connection_string: str = "mongodb://localhost:27017", db_name: str = "labeling_db"):
        try:
            self.client = MongoClient(connection_string)
            self.db = self.client[db_name]
            self.collection = self.db['annotations']
            logger.info(f"MongoDB 연결 성공: {db_name}")
        except Exception as e:
            logger.error(f"MongoDB 연결 실패: {e}")
            raise
    
    def _extract_annotation_features(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """JSON 데이터에서 검색 최적화용 필드들 추출 (annotation_manager와 동일)"""
        shapes = json_data.get('shapes', [])
        
        # labels 배열 생성 (중복 제거)
        labels = list(set([shape.get('label', '') for shape in shapes if shape.get('label')]))
        
        # shape_types 추출
        shape_types = list(set([shape.get('shape_type', '') for shape in shapes if shape.get('shape_type')]))
        
        # descriptions 추출 (비어있지 않은 것만)
        descriptions = [shape.get('description', '') for shape in shapes 
                      if shape.get('description') and shape.get('description').strip()]
        has_descriptions = len(descriptions) > 0
        
        # difficult 플래그 체크
        has_difficult = any(shape.get('difficult', False) for shape in shapes)
        
        # tag 정보 추출
        all_tags = []
        for shape in shapes:
            tags = shape.get('tag', [])
            if tags and isinstance(tags, list):
                all_tags.extend(tags)
        unique_tags = list(set(all_tags))
        has_tags = len(unique_tags) > 0
        
        # attributes 정보 추출
        has_attributes = any(shape.get('attributes', {}) for shape in shapes 
                           if isinstance(shape.get('attributes'), dict) and shape.get('attributes'))
        
        # flags 정보 추출 (전역 + shape별)
        global_flags = json_data.get("flags", {})
        has_global_flags = bool(global_flags)
        
        shape_flags = []
        for shape in shapes:
            if shape.get('flags') and shape.get('flags') is not None:
                if isinstance(shape.get('flags'), dict) and shape.get('flags'):
                    shape_flags.append(shape.get('flags'))
        has_shape_flags = len(shape_flags) > 0
        
        return {
            "labels": labels,
            "shape_types": shape_types,
            "tags": unique_tags,
            
            # 개수 정보
            "shape_count": len(shapes),
            "label_count": len(labels),
            "tag_count": len(unique_tags),
            "description_count": len(descriptions),
            
            # 플래그 정보
            "has_descriptions": has_descriptions,
            "has_difficult": has_difficult,
            "has_tags": has_tags,
            "has_attributes": has_attributes,
            "has_global_flags": has_global_flags,
            "has_shape_flags": has_shape_flags
        }
    
    def migrate_single_document(self, doc_id):
        """단일 문서 마이그레이션"""
        try:
            # 기존 문서 조회
            doc = self.collection.find_one({"_id": doc_id})
            if not doc:
                logger.error(f"문서를 찾을 수 없음: {doc_id}")
                return False
            
            # imagePath에서 JSON 파일 경로 유추
            image_path = doc.get("imagePath")
            if not image_path:
                logger.error(f"imagePath가 없는 문서: {doc_id}")
                return False
            
            # JSON 파일 경로 생성 (이미지 확장자를 .json으로 변경)
            json_file_path = os.path.splitext(image_path)[0] + ".json"
            
            # 파일 경로 정보 생성
            path_info = {
                "json_file_path": json_file_path,  # JSON 파일의 전체 경로
                "json_file_name": os.path.basename(json_file_path),  # JSON 파일명
                "json_directory": os.path.dirname(json_file_path),  # JSON 파일이 있는 디렉토리
                "json_relative_path": os.path.relpath(json_file_path),  # 상대 경로
                
                # 이미지 파일 경로 정보
                "image_file_path": image_path,  # 이미지 파일의 전체 경로
                "image_file_name": os.path.basename(image_path),  # 이미지 파일명
                "image_directory": os.path.dirname(image_path),  # 이미지 파일이 있는 디렉토리
                "image_relative_path": os.path.relpath(image_path),  # 이미지 상대 경로
                "image_exists": os.path.exists(image_path),  # 이미지 파일 존재 여부
                "same_directory": True,  # JSON과 이미지가 같은 디렉토리인지 (일반적으로 True)
                "image_extension": os.path.splitext(image_path)[1].lower(),  # 이미지 확장자
            }
            
            # 전체 문서를 annotation 형태로 구성
            annotation_data = {
                "version": doc.get("version"),
                "flags": doc.get("flags", {}),
                "shapes": doc.get("shapes", []),
                "imagePath": doc.get("imagePath"),
                "imageData": doc.get("imageData"),
                "imageHeight": doc.get("imageHeight"),
                "imageWidth": doc.get("imageWidth"),
                "description": doc.get("description", ""),
            }
            
            # 검색 최적화용 필드들 추출
            features = self._extract_annotation_features(annotation_data)
            
            # 업데이트할 필드들
            update_fields = {
                # 파일 경로 정보 추가
                **path_info,
                
                # 원본 JSON 전체 보존
                "annotation": annotation_data,
                
                # 검색 최적화용 필드들
                **features,
                
                # 시간 정보 (기존 것이 있으면 유지, 없으면 현재 시간)
                "created_at": doc.get("created_at", datetime.now()),
                "updated_at": datetime.now()
            }
            
            # 문서 업데이트
            result = self.collection.update_one(
                {"_id": doc_id},
                {"$set": update_fields}
            )
            
            if result.modified_count > 0:
                logger.info(f"문서 마이그레이션 완료: {doc_id}")
                logger.info(f"  - JSON 파일명: {path_info['json_file_name']}")
                logger.info(f"  - 라벨 수: {features['label_count']}")
                logger.info(f"  - Shape 수: {features['shape_count']}")
                return True
            else:
                logger.warning(f"문서 업데이트되지 않음: {doc_id}")
                return False
                
        except Exception as e:
            logger.error(f"문서 마이그레이션 실패 {doc_id}: {e}")
            return False
    
    def migrate_all_documents(self):
        """모든 문서 마이그레이션"""
        try:
            # json_file_name 필드가 없는 문서들 조회
            docs_to_migrate = list(self.collection.find({"json_file_name": {"$exists": False}}))
            total_count = len(docs_to_migrate)
            
            logger.info(f"마이그레이션 대상 문서: {total_count}개")
            
            success_count = 0
            for i, doc in enumerate(docs_to_migrate, 1):
                logger.info(f"진행률: {i}/{total_count}")
                if self.migrate_single_document(doc["_id"]):
                    success_count += 1
            
            logger.info(f"마이그레이션 완료: {success_count}/{total_count}")
            return success_count
            
        except Exception as e:
            logger.error(f"전체 마이그레이션 실패: {e}")
            return 0
    
    def verify_migration(self):
        """마이그레이션 결과 검증"""
        try:
            # 전체 문서 수
            total_count = self.collection.count_documents({})
            
            # json_file_name 필드가 있는 문서 수
            migrated_count = self.collection.count_documents({"json_file_name": {"$exists": True}})
            
            logger.info(f"검증 결과:")
            logger.info(f"  - 전체 문서: {total_count}")
            logger.info(f"  - 마이그레이션된 문서: {migrated_count}")
            
            # 샘플 문서 조회
            sample = self.collection.find_one({"json_file_name": {"$exists": True}})
            if sample:
                logger.info(f"  - 샘플 json_file_name: {sample.get('json_file_name')}")
                logger.info(f"  - 샘플 json_file_path: {sample.get('json_file_path')}")
                logger.info(f"  - 샘플 labels: {sample.get('labels')}")
            
            return migrated_count == total_count
            
        except Exception as e:
            logger.error(f"검증 실패: {e}")
            return False
    
    def close(self):
        """연결 종료"""
        try:
            self.client.close()
            logger.info("MongoDB 연결 종료")
        except Exception as e:
            logger.error(f"연결 종료 중 에러: {e}")

def main():
    """메인 마이그레이션 함수"""
    try:
        migrator = DataMigrator()
        
        print("\n=== 마이그레이션 전 상태 ===")
        migrator.verify_migration()
        
        print("\n=== 마이그레이션 실행 ===")
        success_count = migrator.migrate_all_documents()
        
        print("\n=== 마이그레이션 후 상태 ===")
        migrator.verify_migration()
        
        # 특정 파일 검색 테스트
        print("\n=== 검색 테스트 ===")
        target_file = "231012_060258_0_side1.json"
        result = migrator.collection.find_one({"json_file_name": target_file})
        if result:
            print(f"✅ 파일 검색 성공: {target_file}")
            print(f"   경로: {result.get('json_file_path')}")
            print(f"   라벨: {result.get('labels')}")
        else:
            print(f"❌ 파일 검색 실패: {target_file}")
        
        migrator.close()
        
    except Exception as e:
        logger.error(f"마이그레이션 실행 중 에러: {e}")

if __name__ == "__main__":
    main()