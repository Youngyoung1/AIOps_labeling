#!/usr/bin/env python3
"""
MongoDB → JSON 수동 동기화 도구
MongoDB에서 직접 수정한 데이터를 JSON 파일에 반영하는 스크립트
"""

from anylabeling.services.annotation_manager import AnnotationManager
import json
import os

def manual_mongodb_to_json_sync():
    """MongoDB → JSON 수동 동기화"""
    
    print("🔄 MongoDB → JSON 수동 동기화 시작")
    print("="*60)
    
    # AnnotationManager 초기화
    manager = AnnotationManager()
    
    # unclear_file 관련 모든 MongoDB 문서 조회
    mongodb_docs = list(manager.collection.find({
        'json_file_path': {'$regex': r'Unclear_file'}
    }, {
        'json_file_path': 1,
        'json_file_name': 1, 
        'flags': 1,
        'shapes': 1,
        'description': 1,
        '_id': 1
    }))
    
    if not mongodb_docs:
        print("❌ unclear_file 관련 문서를 찾을 수 없음")
        return
    
    print(f"📊 MongoDB에서 {len(mongodb_docs)}개 문서 발견")
    
    sync_count = 0
    error_count = 0
    
    for doc in mongodb_docs:
        json_file_path = doc.get('json_file_path', '')
        json_file_name = doc.get('json_file_name', '')
        mongodb_flags = doc.get('flags', {})
        mongodb_shapes = doc.get('shapes', [])
        mongodb_description = doc.get('description', '')
        
        if not json_file_path or not os.path.exists(json_file_path):
            print(f"❌ JSON 파일이 존재하지 않음: {json_file_name}")
            error_count += 1
            continue
        
        try:
            # JSON 파일 읽기
            with open(json_file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # MongoDB 데이터로 업데이트
            original_flags = json_data.get('flags', {})
            json_data['flags'] = mongodb_flags
            json_data['shapes'] = mongodb_shapes
            json_data['description'] = mongodb_description
            
            # JSON 파일 쓰기
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 동기화 완료: {json_file_name}")
            
            # 변경사항 요약
            if mongodb_flags != original_flags:
                print(f"   📝 flags 업데이트: {len(mongodb_flags)}개 항목")
                for key, value in mongodb_flags.items():
                    if key not in original_flags or original_flags[key] != value:
                        print(f"      + {key}: {value}")
            
            sync_count += 1
            
        except Exception as e:
            print(f"❌ 동기화 실패 ({json_file_name}): {e}")
            error_count += 1
    
    print(f"\n" + "="*60)
    print(f"📊 동기화 결과:")
    print(f"   ✅ 성공: {sync_count}개")
    print(f"   ❌ 실패: {error_count}개")
    print(f"   📄 총 처리: {len(mongodb_docs)}개")
    
    if sync_count > 0:
        print(f"\n🎉 MongoDB의 변경사항이 JSON 파일에 반영되었습니다!")
    else:
        print(f"\n⚠️ 동기화된 파일이 없습니다.")

if __name__ == "__main__":
    manual_mongodb_to_json_sync()