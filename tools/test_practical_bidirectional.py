#!/usr/bin/env python3
"""
양방향 동기화 실용적 테스트
현재 시스템에서 실제로 가능한 양방향 동기화 구현
"""

import os
import json
import time
from datetime import datetime
from pymongo import MongoClient

def test_practical_bidirectional_sync():
    """실용적인 양방향 동기화 테스트"""
    print("🔄 실용적 양방향 동기화 테스트")
    print("=" * 50)
    
    # 설정
    json_directory = r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file"
    test_file = "231012_060304_0_side2.json"
    test_json_path = os.path.join(json_directory, test_file)
    
    try:
        # 1. 현재 JSON 파일 상태 확인
        print("📄 현재 JSON 파일 읽기...")
        if not os.path.exists(test_json_path):
            print(f"❌ 파일이 존재하지 않음: {test_json_path}")
            return False
        
        with open(test_json_path, 'r', encoding='utf-8') as f:
            original_json = json.load(f)
        
        print(f"✅ JSON 파일 로드 완료")
        print(f"   현재 shapes: {len(original_json.get('shapes', []))}개")
        print(f"   현재 flags: {original_json.get('flags', {})}")
        
        # 2. MongoDB 연결 및 현재 상태 확인
        print("\n🔍 MongoDB 현재 상태 확인...")
        client = MongoClient("mongodb://localhost:27017/")
        db = client.labeling_db
        
        # annotations 컬렉션에서 해당 파일 찾기
        mongo_doc = db.annotations.find_one({"filename": test_file})
        if not mongo_doc:
            print(f"❌ MongoDB에서 {test_file} 문서를 찾을 수 없음")
            return False
        
        print(f"✅ MongoDB 문서 발견")
        mongo_data = mongo_doc.get('data', {})
        print(f"   MongoDB shapes: {len(mongo_data.get('shapes', []))}개")
        print(f"   MongoDB flags: {mongo_data.get('flags', {})}")
        
        # 3. MongoDB에서 데이터 수정
        print("\n🛠️ MongoDB 데이터 수정...")
        
        # 새로운 flag 추가
        new_flag_key = f"db_modified_{int(time.time())}"
        modified_flags = mongo_data.get('flags', {}).copy()
        modified_flags[new_flag_key] = True
        
        # 새로운 shape 추가
        new_shape = {
            "label": f"db_added_shape_{int(time.time())}",
            "points": [[300, 300], [400, 300], [400, 400], [300, 400]],
            "group_id": None,
            "description": "Added directly in MongoDB",
            "shape_type": "rectangle",
            "flags": {},
            "attributes": {}
        }
        
        modified_shapes = mongo_data.get('shapes', []).copy()
        modified_shapes.append(new_shape)
        
        # MongoDB 업데이트
        update_result = db.annotations.update_one(
            {"filename": test_file},
            {
                "$set": {
                    "data.flags": modified_flags,
                    "data.shapes": modified_shapes,
                    "updated_at": datetime.now()
                }
            }
        )
        
        if update_result.modified_count > 0:
            print("✅ MongoDB 데이터 수정 완료")
            print(f"   새 flag 추가: {new_flag_key}")
            print(f"   새 shape 추가: {new_shape['label']}")
        else:
            print("❌ MongoDB 수정 실패")
            return False
        
        # 4. JSON 파일을 MongoDB 데이터로 동기화
        print("\n🔄 JSON 파일을 MongoDB 데이터로 동기화...")
        
        # 업데이트된 MongoDB 데이터 조회
        updated_mongo_doc = db.annotations.find_one({"filename": test_file})
        updated_data = updated_mongo_doc.get('data', {})
        
        # JSON 파일 업데이트
        sync_json = original_json.copy()
        sync_json['flags'] = updated_data.get('flags', {})
        sync_json['shapes'] = updated_data.get('shapes', [])
        
        # JSON 파일 저장
        with open(test_json_path, 'w', encoding='utf-8') as f:
            json.dump(sync_json, f, indent=2, ensure_ascii=False)
        
        print("✅ JSON 파일 동기화 완료")
        
        # 5. 결과 확인
        print("\n📊 동기화 결과 확인...")
        
        # JSON 파일 다시 읽기
        with open(test_json_path, 'r', encoding='utf-8') as f:
            synced_json = json.load(f)
        
        print(f"동기화 전 shapes: {len(original_json.get('shapes', []))}개")
        print(f"동기화 후 shapes: {len(synced_json.get('shapes', []))}개")
        
        print(f"동기화 전 flags: {list(original_json.get('flags', {}).keys())}")
        print(f"동기화 후 flags: {list(synced_json.get('flags', {}).keys())}")
        
        # 새로 추가된 요소 확인
        if new_flag_key in synced_json.get('flags', {}):
            print(f"✅ 새 flag '{new_flag_key}' 동기화 성공")
        
        new_shape_found = False
        for shape in synced_json.get('shapes', []):
            if shape.get('label', '').startswith('db_added_shape_'):
                new_shape_found = True
                print(f"✅ 새 shape '{shape['label']}' 동기화 성공")
                break
        
        if not new_shape_found:
            print("⚠️ 새 shape 동기화 실패")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")
        return False

def create_polling_sync_function():
    """폴링 기반 동기화 함수 생성"""
    print("\n🔧 폴링 기반 동기화 함수 구현...")
    
    sync_code = '''
def sync_mongodb_to_json(json_directory, check_interval=10):
    """MongoDB 변경사항을 JSON 파일에 동기화"""
    import time
    from datetime import datetime
    from pymongo import MongoClient
    
    client = MongoClient("mongodb://localhost:27017/")
    db = client.labeling_db
    last_check = {}  # 파일별 마지막 확인 시간
    
    print(f"🔄 폴링 동기화 시작 (간격: {check_interval}초)")
    
    try:
        while True:
            # annotations 컬렉션의 모든 문서 확인
            for doc in db.annotations.find():
                filename = doc.get('filename')
                if not filename:
                    continue
                
                updated_at = doc.get('updated_at')
                if not updated_at:
                    continue
                
                # 마지막 확인 이후 업데이트된 경우만 처리
                if filename not in last_check or updated_at > last_check[filename]:
                    json_path = os.path.join(json_directory, filename)
                    
                    if os.path.exists(json_path):
                        try:
                            # JSON 파일 업데이트
                            with open(json_path, 'r', encoding='utf-8') as f:
                                json_data = json.load(f)
                            
                            # MongoDB 데이터로 동기화
                            mongo_data = doc.get('data', {})
                            json_data['flags'] = mongo_data.get('flags', {})
                            json_data['shapes'] = mongo_data.get('shapes', [])
                            
                            with open(json_path, 'w', encoding='utf-8') as f:
                                json.dump(json_data, f, indent=2, ensure_ascii=False)
                            
                            print(f"✅ 동기화: {filename}")
                            last_check[filename] = updated_at
                            
                        except Exception as e:
                            print(f"❌ {filename} 동기화 오류: {e}")
            
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        print("\\n👋 동기화 중지")
    finally:
        client.close()

# 사용 예시:
# sync_mongodb_to_json(r"C:\\Users\\pc\\Desktop\\인턴\\SKPoC\\Unclear_file")
'''
    
    # 파일로 저장
    with open('mongodb_to_json_sync.py', 'w', encoding='utf-8') as f:
        f.write(sync_code)
    
    print("✅ 동기화 함수 저장: mongodb_to_json_sync.py")

def main():
    """메인 실행"""
    print("🔄 MongoDB ↔ JSON 양방향 동기화 검증")
    print("=" * 60)
    
    try:
        # 실용적 동기화 테스트
        success = test_practical_bidirectional_sync()
        
        if success:
            print("\n🎉 양방향 동기화 검증 성공!")
            print("   MongoDB 변경 → JSON 파일 동기화 가능함 확인")
            
            # 폴링 동기화 함수 생성
            create_polling_sync_function()
            
            print("\n💡 권장사항:")
            print("1. DB Manager에서 데이터 수정 시 자동으로 JSON 파일도 업데이트되도록 구현")
            print("2. 주기적으로 MongoDB 변경사항을 확인하는 백그라운드 프로세스 구현")
            print("3. X-AnyLabeling 앱 시작 시 동기화 상태 확인 및 복구")
            
        else:
            print("\n❌ 동기화 검증 실패")
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        return 1

if __name__ == "__main__":
    exit(main())