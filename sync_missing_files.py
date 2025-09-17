#!/usr/bin/env python3
"""
누락된 JSON 파일들을 MongoDB에 동기화하는 스크립트
"""

import os
import json
from anylabeling.services.annotation_manager import AnnotationManager

def sync_missing_files():
    """unclear_file 디렉토리의 JSON 파일들을 MongoDB와 동기화"""
    
    # AnnotationManager 초기화
    manager = AnnotationManager()
    
    # unclear_file 디렉토리 경로
    unclear_dir = r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file"
    
    # JSON 파일 목록
    json_files = [
        "231012_060258_0_side1.json",
        "231012_060258_0_side2.json", 
        "231012_060304_0_side2.json",
        "231012_060920_0_side2.json"
    ]
    
    print("🔄 JSON 파일 동기화 시작...")
    print(f"📁 디렉토리: {unclear_dir}")
    
    for filename in json_files:
        file_path = os.path.join(unclear_dir, filename)
        
        if not os.path.exists(file_path):
            print(f"❌ 파일이 존재하지 않음: {filename}")
            continue
            
        try:
            print(f"\n📄 처리 중: {filename}")
            
            # MongoDB에서 해당 파일 검색 (json_file_path로)
            existing = manager.collection.find_one({'json_file_path': file_path})
            
            if existing:
                print(f"   ✅ 이미 존재함 - ID: {existing.get('_id')}")
            else:
                # MongoDB에 저장 (insert_annotation 사용)
                result = manager.insert_annotation(json_file_path=file_path)
                if result:
                    print(f"   ➕ 새로 추가됨 - ID: {result}")
                else:
                    print(f"   ❌ 추가 실패")
                    
        except Exception as e:
            print(f"   ❌ 오류 발생: {e}")
    
    # 최종 상태 확인
    print(f"\n" + "="*50)
    print("📊 동기화 완료 후 상태:")
    
    total_count = manager.collection.count_documents({})
    print(f"MongoDB 총 문서 수: {total_count}")
    
    # unclear_file 디렉토리 파일들만 조회
    unclear_files = list(manager.collection.find({
        'json_file_path': {'$regex': r'Unclear_file'}
    }, {'json_file_path': 1, '_id': 0}))
    
    print(f"unclear_file 관련 문서 수: {len(unclear_files)}")
    
    for i, doc in enumerate(unclear_files, 1):
        file_path = doc.get('json_file_path', 'Unknown')
        filename = os.path.basename(file_path) if file_path != 'Unknown' else 'Unknown'
        print(f"  {i}. {filename}")

if __name__ == "__main__":
    sync_missing_files()