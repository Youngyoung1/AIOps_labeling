#!/usr/bin/env python3
"""
특정 MongoDB 문서 (ObjectId: 68c3c1c4552d9f64690f36ea)를 annotation_manager 구조로 업데이트
"""

import json
import os
import logging
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
from typing import Dict, Any

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentUpdater:
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
        """JSON 데이터에서 검색 최적화용 필드들 추출"""
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
    
    def update_specific_document(self, object_id_str: str):
        """특정 ObjectId 문서 업데이트"""
        try:
            # ObjectId 변환
            doc_id = ObjectId(object_id_str)
            
            # 기존 문서 조회
            doc = self.collection.find_one({"_id": doc_id})
            if not doc:
                logger.error(f"문서를 찾을 수 없음: {object_id_str}")
                return False
            
            print(f"📄 현재 문서 구조:")
            print(f"  - _id: {doc['_id']}")
            print(f"  - version: {doc.get('version')}")
            print(f"  - imagePath: {doc.get('imagePath')}")
            print(f"  - shapes 개수: {len(doc.get('shapes', []))}")
            print(f"  - 기존 필드: {list(doc.keys())}")
            
            # imagePath에서 JSON 파일 경로 유추
            image_path = doc.get("imagePath")
            if not image_path:
                logger.error(f"imagePath가 없는 문서: {object_id_str}")
                return False
            
            print(f"\n🔄 경로 정보 생성:")
            print(f"  - 이미지 경로: {image_path}")
            
            # JSON 파일 경로 생성 (이미지 확장자를 .json으로 변경)
            json_file_path = os.path.splitext(image_path)[0] + ".json"
            print(f"  - JSON 경로: {json_file_path}")
            
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
                "same_directory": True,  # JSON과 이미지가 같은 디렉토리인지
                "image_extension": os.path.splitext(image_path)[1].lower(),  # 이미지 확장자
            }
            
            print(f"  - JSON 파일명: {path_info['json_file_name']}")
            print(f"  - 이미지 존재 여부: {path_info['image_exists']}")
            
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
            
            print(f"\n🏷️ 추출된 특성:")
            print(f"  - 라벨: {features['labels']}")
            print(f"  - Shape 타입: {features['shape_types']}")
            print(f"  - Shape 개수: {features['shape_count']}")
            print(f"  - 설명 있음: {features['has_descriptions']}")
            print(f"  - Difficult 있음: {features['has_difficult']}")
            
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
            
            print(f"\n⚙️ 업데이트할 필드 수: {len(update_fields)}")
            
            # 문서 업데이트
            result = self.collection.update_one(
                {"_id": doc_id},
                {"$set": update_fields}
            )
            
            if result.modified_count > 0:
                print(f"\n✅ 문서 업데이트 완료!")
                print(f"  - ObjectId: {object_id_str}")
                print(f"  - JSON 파일명: {path_info['json_file_name']}")
                print(f"  - 라벨 수: {features['label_count']}")
                print(f"  - Shape 수: {features['shape_count']}")
                
                # 업데이트된 문서 확인
                updated_doc = self.collection.find_one({"_id": doc_id})
                print(f"  - 업데이트 후 필드 수: {len(updated_doc.keys())}")
                
                return True
            else:
                logger.warning(f"문서가 업데이트되지 않음: {object_id_str}")
                return False
                
        except Exception as e:
            logger.error(f"문서 업데이트 실패 {object_id_str}: {e}")
            return False
    
    def recreate_indexes(self):
        """인덱스 재생성"""
        try:
            print(f"\n🔍 기존 인덱스 삭제...")
            
            # 기본 _id 인덱스를 제외한 모든 인덱스 삭제
            indexes = self.collection.list_indexes()
            for index in indexes:
                index_name = index.get('name')
                if index_name and index_name != '_id_':
                    try:
                        self.collection.drop_index(index_name)
                        print(f"  - 삭제: {index_name}")
                    except Exception as e:
                        print(f"  - 삭제 실패: {index_name} ({e})")
            
            print(f"\n🚀 새 인덱스 생성...")
            
            # 🚀 이미지 경로 관련 고성능 인덱스들
            self.collection.create_index("imagePath")
            print(f"  - imagePath 인덱스 생성")
            
            self.collection.create_index("json_file_path")
            print(f"  - json_file_path 인덱스 생성")
            
            self.collection.create_index("image_file_path")
            print(f"  - image_file_path 인덱스 생성")
            
            self.collection.create_index("json_file_name")
            print(f"  - json_file_name 인덱스 생성")
            
            self.collection.create_index("image_file_name")
            print(f"  - image_file_name 인덱스 생성")
            
            # 🔍 검색 최적화 인덱스들
            self.collection.create_index("labels")
            print(f"  - labels 인덱스 생성")
            
            self.collection.create_index("shapes.label")
            print(f"  - shapes.label 인덱스 생성")
            
            self.collection.create_index([("imagePath", 1), ("labels", 1)])
            print(f"  - imagePath+labels 복합 인덱스 생성")
            
            # 📊 어노테이션 최적화 인덱스들
            self.collection.create_index("shape_types")
            self.collection.create_index("tags")
            self.collection.create_index("shape_count")
            self.collection.create_index("label_count")
            print(f"  - 어노테이션 관련 인덱스들 생성")
            
            # 🏷️ 플래그 검색 인덱스들
            self.collection.create_index("has_descriptions")
            self.collection.create_index("has_difficult")
            self.collection.create_index("has_tags")
            self.collection.create_index("has_attributes")
            self.collection.create_index("has_shape_flags")
            print(f"  - 플래그 관련 인덱스들 생성")
            
            # ⏰ 시간 기반 인덱스들
            self.collection.create_index("created_at")
            self.collection.create_index("updated_at")
            print(f"  - 시간 관련 인덱스들 생성")
            
            # 🔗 복합 인덱스들
            self.collection.create_index([("labels", 1), ("shape_count", -1)])
            self.collection.create_index([("json_directory", 1), ("json_file_name", 1)])
            print(f"  - 복합 인덱스들 생성")
            
            print(f"\n✅ 인덱스 재생성 완료!")
            
        except Exception as e:
            logger.error(f"인덱스 재생성 실패: {e}")
    
    def verify_update(self, object_id_str: str):
        """업데이트 검증"""
        try:
            doc_id = ObjectId(object_id_str)
            doc = self.collection.find_one({"_id": doc_id})
            
            if not doc:
                print(f"❌ 문서를 찾을 수 없음")
                return False
            
            print(f"\n🔍 업데이트 검증:")
            print(f"  - json_file_name: {doc.get('json_file_name')}")
            print(f"  - json_file_path: {doc.get('json_file_path')}")
            print(f"  - labels: {doc.get('labels')}")
            print(f"  - shape_count: {doc.get('shape_count')}")
            print(f"  - has_descriptions: {doc.get('has_descriptions')}")
            
            # 검색 테스트
            print(f"\n🔎 검색 테스트:")
            
            # 파일명으로 검색
            result1 = self.collection.find_one({"json_file_name": doc.get('json_file_name')})
            print(f"  - 파일명 검색: {'✅ 성공' if result1 else '❌ 실패'}")
            
            # 라벨로 검색
            if doc.get('labels'):
                result2 = self.collection.find_one({"labels": doc.get('labels')[0]})
                print(f"  - 라벨 검색 ({doc.get('labels')[0]}): {'✅ 성공' if result2 else '❌ 실패'}")
            
            return True
            
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
    """메인 업데이트 함수"""
    try:
        # 특정 ObjectId
        target_object_id = "68c3c1c4552d9f64690f36ea"
        
        updater = DocumentUpdater()
        
        print(f"🎯 타겟 문서: {target_object_id}")
        print(f"=" * 60)
        
        # 1. 문서 업데이트
        success = updater.update_specific_document(target_object_id)
        
        if success:
            # 2. 인덱스 재생성
            updater.recreate_indexes()
            
            # 3. 업데이트 검증
            updater.verify_update(target_object_id)
        
        updater.close()
        
        print(f"\n🎉 작업 완료!")
        
    except Exception as e:
        logger.error(f"작업 실행 중 에러: {e}")

if __name__ == "__main__":
    main()