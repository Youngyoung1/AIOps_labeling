#!/usr/bin/env python3
"""
특정 문서의 이미지 경로 관련 필드들을 상세히 확인하고 수정
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

class ImagePathFixer:
    def __init__(self, connection_string: str = "mongodb://localhost:27017", db_name: str = "labeling_db"):
        try:
            self.client = MongoClient(connection_string)
            self.db = self.client[db_name]
            self.collection = self.db['annotations']
            logger.info(f"MongoDB 연결 성공: {db_name}")
        except Exception as e:
            logger.error(f"MongoDB 연결 실패: {e}")
            raise
    
    def check_document_fields(self, object_id_str: str):
        """문서의 이미지 관련 필드들 상세 확인"""
        try:
            doc_id = ObjectId(object_id_str)
            doc = self.collection.find_one({"_id": doc_id})
            
            if not doc:
                print(f"❌ 문서를 찾을 수 없음: {object_id_str}")
                return False
            
            print(f"📋 문서 필드 상세 분석")
            print(f"=" * 60)
            
            # 기본 경로 정보
            print(f"🖼️ 기본 이미지 정보:")
            print(f"  - imagePath: {doc.get('imagePath')}")
            print(f"  - imageData: {'있음' if doc.get('imageData') else '없음'}")
            print(f"  - imageHeight: {doc.get('imageHeight')}")
            print(f"  - imageWidth: {doc.get('imageWidth')}")
            
            # 새로 추가된 경로 필드들
            print(f"\n📁 경로 관련 필드들:")
            print(f"  - image_file_path: {doc.get('image_file_path')}")
            print(f"  - image_file_name: {doc.get('image_file_name')}")
            print(f"  - image_directory: {doc.get('image_directory')}")
            print(f"  - image_exists: {doc.get('image_exists')}")
            
            print(f"\n📄 JSON 관련 필드들:")
            print(f"  - json_file_path: {doc.get('json_file_path')}")
            print(f"  - json_file_name: {doc.get('json_file_name')}")
            print(f"  - json_directory: {doc.get('json_directory')}")
            
            # 실제 파일 존재 여부 확인
            print(f"\n🔍 실제 파일 존재 여부:")
            image_path = doc.get('imagePath')
            if image_path:
                exists = os.path.exists(image_path)
                print(f"  - imagePath 존재: {'✅' if exists else '❌'} ({image_path})")
            
            image_file_path = doc.get('image_file_path')
            if image_file_path:
                exists = os.path.exists(image_file_path)
                print(f"  - image_file_path 존재: {'✅' if exists else '❌'} ({image_file_path})")
            
            json_file_path = doc.get('json_file_path')
            if json_file_path:
                exists = os.path.exists(json_file_path)
                print(f"  - json_file_path 존재: {'✅' if exists else '❌'} ({json_file_path})")
            
            return True
            
        except Exception as e:
            logger.error(f"문서 확인 실패: {e}")
            return False
    
    def fix_image_paths(self, object_id_str: str):
        """이미지 경로 관련 필드들 수정"""
        try:
            doc_id = ObjectId(object_id_str)
            doc = self.collection.find_one({"_id": doc_id})
            
            if not doc:
                print(f"❌ 문서를 찾을 수 없음: {object_id_str}")
                return False
            
            print(f"\n🔧 이미지 경로 필드 수정 중...")
            
            # 기본 imagePath 확인
            image_path = doc.get('imagePath')
            if not image_path:
                print(f"❌ imagePath가 없습니다.")
                return False
            
            print(f"📍 기준 imagePath: {image_path}")
            
            # JSON 파일 경로 생성
            json_file_path = os.path.splitext(image_path)[0] + ".json"
            
            # 파일 경로 정보 재생성
            path_info = {
                # JSON 파일 정보
                "json_file_path": json_file_path,
                "json_file_name": os.path.basename(json_file_path),
                "json_directory": os.path.dirname(json_file_path),
                "json_relative_path": os.path.relpath(json_file_path),
                
                # 이미지 파일 정보
                "image_file_path": image_path,
                "image_file_name": os.path.basename(image_path),
                "image_directory": os.path.dirname(image_path),
                "image_relative_path": os.path.relpath(image_path),
                "image_exists": os.path.exists(image_path),
                "same_directory": True,
                "image_extension": os.path.splitext(image_path)[1].lower(),
            }
            
            print(f"📁 새로 생성된 경로 정보:")
            for key, value in path_info.items():
                print(f"  - {key}: {value}")
            
            # 업데이트 수행
            result = self.collection.update_one(
                {"_id": doc_id},
                {"$set": {**path_info, "updated_at": datetime.now()}}
            )
            
            if result.modified_count > 0:
                print(f"\n✅ 경로 정보 업데이트 완료!")
                return True
            else:
                print(f"\n⚠️ 업데이트되지 않음 (이미 최신 상태일 수 있음)")
                return False
                
        except Exception as e:
            logger.error(f"경로 수정 실패: {e}")
            return False
    
    def test_get_image_path_fast(self, object_id_str: str):
        """get_image_path_fast 메서드 테스트"""
        try:
            doc_id = ObjectId(object_id_str)
            doc = self.collection.find_one({"_id": doc_id})
            
            if not doc:
                print(f"❌ 문서를 찾을 수 없음: {object_id_str}")
                return False
            
            print(f"\n🧪 get_image_path_fast 테스트")
            print(f"=" * 50)
            
            # 테스트할 식별자들
            identifiers = [
                (doc.get('imagePath'), "imagePath"),
                (doc.get('json_file_name'), "json_file_name"),
                (doc.get('image_file_name'), "image_file_name"),
            ]
            
            for identifier, identifier_type in identifiers:
                if identifier:
                    print(f"\n🔍 테스트: {identifier_type} = {identifier}")
                    
                    # 실제 쿼리 수행
                    projection = {
                        "imagePath": 1,
                        "image_file_path": 1,
                        "image_file_name": 1,
                        "json_file_path": 1,
                        "json_file_name": 1,
                        "json_directory": 1,
                        "image_directory": 1,
                        "image_exists": 1,
                        "same_directory": 1
                    }
                    
                    query = {identifier_type: identifier}
                    result = self.collection.find_one(query, projection)
                    
                    if result:
                        result.pop("_id", None)
                        print(f"  ✅ 검색 성공:")
                        for key, value in result.items():
                            print(f"    - {key}: {value}")
                    else:
                        print(f"  ❌ 검색 실패")
            
            return True
            
        except Exception as e:
            logger.error(f"테스트 실패: {e}")
            return False
    
    def close(self):
        """연결 종료"""
        try:
            self.client.close()
            logger.info("MongoDB 연결 종료")
        except Exception as e:
            logger.error(f"연결 종료 중 에러: {e}")

def main():
    """메인 함수"""
    try:
        target_object_id = "68c3c1c4552d9f64690f36ea"
        
        fixer = ImagePathFixer()
        
        print(f"🎯 대상 문서: {target_object_id}")
        
        # 1. 현재 상태 확인
        fixer.check_document_fields(target_object_id)
        
        # 2. 경로 정보 수정
        fixer.fix_image_paths(target_object_id)
        
        # 3. 수정 후 상태 확인
        print(f"\n" + "="*60)
        print(f"🔄 수정 후 상태:")
        fixer.check_document_fields(target_object_id)
        
        # 4. get_image_path_fast 테스트
        fixer.test_get_image_path_fast(target_object_id)
        
        fixer.close()
        
        print(f"\n🎉 작업 완료!")
        
    except Exception as e:
        logger.error(f"작업 실행 중 에러: {e}")

if __name__ == "__main__":
    main()