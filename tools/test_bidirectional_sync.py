#!/usr/bin/env python3
"""
양방향 동기화 테스트 스크립트
MongoDB 데이터 변경 시 JSON 파일이 자동으로 업데이트되는지 확인
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from bson import ObjectId

# 프로젝트 루트를 Python path에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from anylabeling.services.annotation_manager import AnnotationManager
except ImportError as e:
    print(f"AnnotationManager import 실패: {e}")
    print("직접 MongoDB 연결을 사용하여 테스트를 진행합니다")
    AnnotationManager = None


def test_bidirectional_sync():
    """양방향 동기화 테스트"""
    print("🔄 양방향 동기화 테스트 시작")
    print("=" * 50)
    
    # 테스트 설정
    json_directory = r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file"
    test_image = "test_bidirectional_sync.jpg"
    test_json_path = os.path.join(json_directory, "test_bidirectional_sync.json")
    
    # 초기 JSON 파일 생성
    initial_json_data = {
        "version": "1.0.0",
        "flags": {},
        "shapes": [
            {
                "label": "original_label",
                "points": [[100, 100], [200, 100], [200, 200], [100, 200]],
                "group_id": None,
                "description": "Original annotation",
                "shape_type": "rectangle",
                "flags": {},
                "attributes": {}
            }
        ],
        "imagePath": test_image,
        "imageData": None,
        "imageHeight": 300,
        "imageWidth": 400
    }
    
    # JSON 파일 생성
    print(f"📝 초기 JSON 파일 생성: {test_json_path}")
    os.makedirs(json_directory, exist_ok=True)
    with open(test_json_path, 'w', encoding='utf-8') as f:
        json.dump(initial_json_data, f, indent=2, ensure_ascii=False)
    
    # AnnotationManager를 통해 MongoDB에 저장
    print("💾 JSON 데이터를 MongoDB에 저장...")
    try:
        if AnnotationManager:
            ann_manager = AnnotationManager()
            ann_manager.insert_annotation(test_json_path)
            print("✅ MongoDB 저장 완료 (AnnotationManager 사용)")
        else:
            # 직접 MongoDB에 저장
            from pymongo import MongoClient
            client = MongoClient("mongodb://localhost:27017/")
            db = client.labeling_db
            
            # JSON 데이터를 MongoDB 형식으로 변환
            annotation_doc = {
                'image_id': test_image,
                'label': 'original_label',
                'points': [[100, 100], [200, 100], [200, 200], [100, 200]],
                'shape_type': 'rectangle',
                'description': 'Original annotation',
                'flags': {},
                'attributes': {},
                'created_at': datetime.now()
            }
            
            db.annotations.insert_one(annotation_doc)
            print("✅ MongoDB 저장 완료 (직접 연결 사용)")
            
    except Exception as e:
        print(f"❌ MongoDB 저장 실패: {e}")
        return False
    
    # 잠시 대기
    time.sleep(2)
    
    # MongoDB에서 직접 데이터 수정
    print("\n🛠️ MongoDB에서 직접 어노테이션 수정...")
    try:
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017/")
        db = client.labeling_db
        annotations = db.annotations
        
        # 방금 생성한 어노테이션 찾기
        annotation = annotations.find_one({"image_id": test_image})
        if not annotation:
            print("❌ 테스트 어노테이션을 찾을 수 없음")
            return False
        
        annotation_id = annotation["_id"]
        print(f"📍 어노테이션 ID: {annotation_id}")
        
        # 라벨 변경
        result = annotations.update_one(
            {"_id": annotation_id},
            {
                "$set": {
                    "label": "modified_by_mongodb",
                    "description": "Modified directly in MongoDB",
                    "updated_at": datetime.now()
                }
            }
        )
        
        if result.modified_count > 0:
            print("✅ MongoDB에서 어노테이션 수정 완료")
            print(f"   라벨: 'original_label' → 'modified_by_mongodb'")
            print(f"   설명: 'Original annotation' → 'Modified directly in MongoDB'")
        else:
            print("❌ MongoDB 수정 실패")
            return False
            
    except Exception as e:
        print(f"❌ MongoDB 수정 오류: {e}")
        return False
    
    # Change Stream Watcher가 실행 중인지 확인하고 알림
    print("\n⏰ MongoDB Change Stream이 감지하여 JSON 파일을 업데이트할 때까지 대기...")
    print("   (mongodb_change_watcher.py가 실행 중이어야 합니다)")
    
    # 10초간 JSON 파일 변경 확인
    for i in range(10):
        time.sleep(1)
        
        try:
            with open(test_json_path, 'r', encoding='utf-8') as f:
                updated_json = json.load(f)
            
            # JSON 파일이 업데이트되었는지 확인
            if updated_json.get('shapes') and len(updated_json['shapes']) > 0:
                first_shape = updated_json['shapes'][0]
                if first_shape.get('label') == 'modified_by_mongodb':
                    print(f"✅ JSON 파일이 자동 업데이트되었습니다! (대기 시간: {i+1}초)")
                    print(f"   업데이트된 라벨: {first_shape.get('label')}")
                    print(f"   업데이트된 설명: {first_shape.get('description')}")
                    return True
        except Exception as e:
            print(f"⚠️ JSON 파일 읽기 오류: {e}")
        
        print(f"   대기 중... ({i+1}/10초)")
    
    print("❌ JSON 파일이 자동으로 업데이트되지 않았습니다")
    print("   mongodb_change_watcher.py가 실행 중인지 확인하세요")
    return False


def check_change_stream_support():
    """MongoDB Change Streams 지원 여부 확인"""
    print("🔍 MongoDB Change Streams 지원 여부 확인...")
    
    try:
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017/")
        
        # MongoDB 버전 확인
        server_info = client.server_info()
        version = server_info.get('version', 'Unknown')
        print(f"📊 MongoDB 버전: {version}")
        
        # Change Streams 테스트
        db = client.labeling_db
        try:
            # 간단한 change stream 생성 시도
            change_stream = db.annotations.watch([])
            change_stream.close()
            print("✅ Change Streams 지원됨")
            return True
        except Exception as e:
            print(f"❌ Change Streams 지원되지 않음: {e}")
            print("   MongoDB 3.6+ 및 Replica Set이 필요합니다")
            return False
            
    except Exception as e:
        print(f"❌ MongoDB 연결 실패: {e}")
        return False


def cleanup_test_data():
    """테스트 데이터 정리"""
    print("\n🧹 테스트 데이터 정리...")
    
    # JSON 파일 삭제
    json_path = os.path.join(r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file", "test_bidirectional_sync.json")
    if os.path.exists(json_path):
        os.remove(json_path)
        print(f"✅ 테스트 JSON 파일 삭제: {json_path}")
    
    # MongoDB 데이터 삭제
    try:
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017/")
        db = client.labeling_db
        
        result = db.annotations.delete_many({"image_id": "test_bidirectional_sync.jpg"})
        print(f"✅ 테스트 MongoDB 데이터 삭제: {result.deleted_count}개")
        
    except Exception as e:
        print(f"⚠️ MongoDB 데이터 삭제 오류: {e}")


def main():
    """메인 실행 함수"""
    print("🔄 MongoDB ↔ JSON 양방향 동기화 테스트")
    print("=" * 60)
    
    try:
        # 1. Change Streams 지원 확인
        if not check_change_stream_support():
            print("\n❌ 테스트를 진행할 수 없습니다")
            return 1
        
        # 2. 양방향 동기화 테스트
        print("\n" + "=" * 60)
        success = test_bidirectional_sync()
        
        # 3. 테스트 결과
        print("\n" + "=" * 60)
        if success:
            print("🎉 양방향 동기화 테스트 성공!")
            print("   MongoDB 변경 → JSON 파일 자동 업데이트 확인됨")
        else:
            print("❌ 양방향 동기화 테스트 실패")
            print("   다음을 확인하세요:")
            print("   1. mongodb_change_watcher.py가 실행 중인가?")
            print("   2. MongoDB가 Replica Set으로 구성되었는가?")
            print("   3. Change Streams가 지원되는가?")
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n👋 사용자가 테스트를 중단했습니다")
        return 1
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        return 1
    finally:
        cleanup_test_data()


if __name__ == "__main__":
    exit(main())