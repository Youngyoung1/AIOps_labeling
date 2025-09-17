#!/usr/bin/env python3
"""
MongoDB 컬렉션 직접 확인 및 폴링 동기화 테스트
"""

import os
import sys
from pymongo import MongoClient
from datetime import datetime

def check_annotations_collection():
    """annotations 컬렉션 내용 확인"""
    try:
        client = MongoClient("mongodb://localhost:27017/")
        db = client.labeling_db
        
        print("=== Annotations Collection 확인 ===")
        
        # 전체 어노테이션 수
        total_count = db.annotations.count_documents({})
        print(f"전체 어노테이션 수: {total_count}")
        
        if total_count > 0:
            # 최근 어노테이션 조회
            recent_annotations = list(db.annotations.find().sort("_id", -1).limit(5))
            
            print("\n최근 어노테이션 5개:")
            for i, ann in enumerate(recent_annotations, 1):
                print(f"{i}. ID: {ann.get('_id')}")
                print(f"   image_id: {ann.get('image_id', 'N/A')}")
                print(f"   label: {ann.get('label', 'N/A')}")
                print(f"   created_at: {ann.get('created_at', 'N/A')}")
                print(f"   updated_at: {ann.get('updated_at', 'N/A')}")
                print()
        
        # JSON 기반 데이터 확인
        print("=== JSON Documents Collection 확인 ===")
        json_count = db.documents.count_documents({})
        print(f"전체 JSON 문서 수: {json_count}")
        
        if json_count > 0:
            recent_docs = list(db.documents.find().sort("_id", -1).limit(3))
            print("\n최근 JSON 문서 3개:")
            for i, doc in enumerate(recent_docs, 1):
                print(f"{i}. {doc.get('filename', 'N/A')}")
                print(f"   imagePath: {doc.get('data', {}).get('imagePath', 'N/A')}")
                shapes = doc.get('data', {}).get('shapes', [])
                print(f"   shapes: {len(shapes)}개")
                print()
        
        client.close()
        return total_count, json_count
        
    except Exception as e:
        print(f"❌ MongoDB 확인 오류: {e}")
        return 0, 0

def test_direct_annotation_update():
    """어노테이션 컬렉션에 직접 데이터 추가/수정 테스트"""
    try:
        client = MongoClient("mongodb://localhost:27017/")
        db = client.labeling_db
        
        print("🧪 어노테이션 컬렉션에 테스트 데이터 추가...")
        
        # 테스트 어노테이션 추가
        test_annotation = {
            "image_id": "231012_060304_0_side2.jpg",
            "label": "test_polling_sync",
            "points": [[50, 50], [150, 50], [150, 150], [50, 150]],
            "shape_type": "rectangle",
            "description": "Polling sync test annotation",
            "flags": {},
            "attributes": {},
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = db.annotations.insert_one(test_annotation)
        print(f"✅ 테스트 어노테이션 추가: {result.inserted_id}")
        
        # 잠시 후 수정
        import time
        time.sleep(1)
        
        update_result = db.annotations.update_one(
            {"_id": result.inserted_id},
            {
                "$set": {
                    "label": "modified_by_polling_test",
                    "description": "Modified for polling sync test",
                    "updated_at": datetime.now()
                }
            }
        )
        
        if update_result.modified_count > 0:
            print("✅ 어노테이션 수정 완료")
            print("   라벨: 'test_polling_sync' → 'modified_by_polling_test'")
            
            # 수정된 어노테이션 조회
            modified_ann = db.annotations.find_one({"_id": result.inserted_id})
            print(f"   최종 라벨: {modified_ann.get('label')}")
            print(f"   최종 설명: {modified_ann.get('description')}")
            
            client.close()
            return str(result.inserted_id)
        else:
            print("❌ 어노테이션 수정 실패")
            client.close()
            return None
            
    except Exception as e:
        print(f"❌ 어노테이션 테스트 오류: {e}")
        return None

def cleanup_test_annotation(annotation_id):
    """테스트 어노테이션 정리"""
    try:
        client = MongoClient("mongodb://localhost:27017/")
        db = client.labeling_db
        
        from bson import ObjectId
        result = db.annotations.delete_one({"_id": ObjectId(annotation_id)})
        
        if result.deleted_count > 0:
            print(f"✅ 테스트 어노테이션 삭제: {annotation_id}")
        
        client.close()
        
    except Exception as e:
        print(f"⚠️ 테스트 어노테이션 삭제 오류: {e}")

def main():
    """메인 실행"""
    print("🔍 MongoDB Annotations Collection 테스트")
    print("=" * 50)
    
    # 1. 현재 컬렉션 상태 확인
    ann_count, doc_count = check_annotations_collection()
    
    # 2. 어노테이션 컬렉션에 데이터가 없으면 테스트 데이터 추가
    if ann_count == 0:
        print("\n📝 어노테이션 컬렉션이 비어있음 - 테스트 데이터 추가...")
        test_annotation_id = test_direct_annotation_update()
        
        if test_annotation_id:
            print(f"\n✅ 테스트 준비 완료!")
            print(f"이제 다음 명령으로 폴링 동기화를 테스트할 수 있습니다:")
            print(f"python polling_sync_manager.py --test-sync \"231012_060304_0_side2.jpg\"")
            
            # 사용자 입력 대기
            input("\n테스트가 끝나면 Enter를 눌러 정리하세요...")
            cleanup_test_annotation(test_annotation_id)
        
    else:
        print(f"\n✅ {ann_count}개의 어노테이션이 이미 존재합니다")
        print("폴링 동기화 테스트가 가능합니다")

if __name__ == "__main__":
    main()