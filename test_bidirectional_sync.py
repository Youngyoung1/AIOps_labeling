#!/usr/bin/env python3
"""
양방향 동기화 테스트 스크립트
MongoDB에서 데이터를 직접 수정하고 JSON 파일이 자동으로 업데이트되는지 확인
"""

from anylabeling.services.annotation_manager import AnnotationManager
from datetime import datetime
import json
import os
import time

def test_mongodb_to_json_sync():
    """MongoDB → JSON 동기화 테스트"""
    
    print("🧪 양방향 동기화 테스트 시작")
    print("="*60)
    
    # AnnotationManager 초기화
    manager = AnnotationManager()
    
    # 테스트할 unclear_file JSON 문서 하나 선택
    unclear_doc = manager.collection.find_one({
        'json_file_path': {'$regex': r'231012_060304_0_side2\.json'}
    })
    
    if not unclear_doc:
        print("❌ 테스트용 문서를 찾을 수 없음")
        return
    
    json_file_path = unclear_doc['json_file_path']
    doc_id = unclear_doc['_id']
    
    print(f"📄 테스트 파일: {os.path.basename(json_file_path)}")
    print(f"📄 MongoDB ID: {doc_id}")
    
    # 현재 JSON 파일 내용 확인
    with open(json_file_path, 'r', encoding='utf-8') as f:
        original_json = json.load(f)
    
    original_flags = original_json.get('flags', {})
    print(f"📄 원본 JSON flags: {original_flags}")
    
    # MongoDB에서 flags 업데이트
    test_timestamp = int(time.time())
    new_flags = {
        **original_flags,
        'bidirectional_test': True,
        'test_timestamp': test_timestamp,
        'mongodb_direct_update': '양방향 동기화 테스트 - MongoDB에서 직접 수정'
    }
    
    print(f"\n🔄 MongoDB에서 flags 업데이트...")
    print(f"새로운 flags: {new_flags}")
    
    # MongoDB 업데이트 (last_modified도 함께 업데이트)
    result = manager.collection.update_one(
        {'_id': doc_id},
        {
            '$set': {
                'flags': new_flags,
                'last_modified': datetime.now()
            }
        }
    )
    
    if result.modified_count > 0:
        print("✅ MongoDB 업데이트 성공")
        
        # 양방향 동기화 서비스가 변경사항을 감지하도록 잠시 대기
        print("\n⏰ 양방향 동기화 서비스가 변경사항을 감지할 때까지 대기 (10초)...")
        time.sleep(10)
        
        # JSON 파일이 업데이트되었는지 확인
        with open(json_file_path, 'r', encoding='utf-8') as f:
            updated_json = json.load(f)
        
        updated_flags = updated_json.get('flags', {})
        print(f"\n📄 업데이트 후 JSON flags: {updated_flags}")
        
        # 동기화 결과 확인
        if updated_flags.get('bidirectional_test') == True:
            print("✅ 양방향 동기화 성공!")
            print("✅ MongoDB 변경사항이 JSON 파일에 정상적으로 반영됨")
        else:
            print("❌ 양방향 동기화 실패")
            print("❌ MongoDB 변경사항이 JSON 파일에 반영되지 않음")
            
        # 세부 비교
        for key, value in new_flags.items():
            if key in updated_flags and updated_flags[key] == value:
                print(f"  ✅ {key}: {value}")
            else:
                print(f"  ❌ {key}: 예상={value}, 실제={updated_flags.get(key, 'MISSING')}")
                
    else:
        print("❌ MongoDB 업데이트 실패")
    
    print(f"\n" + "="*60)
    print("🧪 양방향 동기화 테스트 완료")

if __name__ == "__main__":
    test_mongodb_to_json_sync()