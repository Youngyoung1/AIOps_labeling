#!/usr/bin/env python3
"""
JSON 파일을 MongoDB에 추가하고 플래그 동기화 테스트
"""

import os
import sys
import json
from datetime import datetime
import pymongo
from pymongo import MongoClient


def add_json_files_to_mongodb():
    """JSON 파일들을 MongoDB에 추가"""
    
    # MongoDB 연결
    client = MongoClient('mongodb://localhost:27017/')
    db = client['x_anylabeling']
    collection = db['annotations']
    
    # 테스트 디렉토리
    test_directory = r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file"
    
    if not os.path.exists(test_directory):
        print(f"❌ 디렉토리가 존재하지 않음: {test_directory}")
        return 0
        
    json_files = [f for f in os.listdir(test_directory) if f.endswith('.json')]
    
    if not json_files:
        print(f"❌ JSON 파일이 없음: {test_directory}")
        return 0
        
    print(f"📁 {len(json_files)}개 JSON 파일 발견")
    
    added_count = 0
    
    for json_file in json_files[:5]:  # 처음 5개만 테스트
        json_path = os.path.join(test_directory, json_file)
        
        try:
            # JSON 파일 읽기
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                
            # MongoDB에 존재하는지 확인
            mongodb_path = json_path.replace('\\', '/')
            existing = collection.find_one({'json_file_path': mongodb_path})
            
            if existing:
                print(f"⏭️ 이미 존재함: {json_file}")
                continue
                
            # MongoDB 문서 생성
            mongodb_doc = {
                'json_file_path': mongodb_path,
                'flags': json_data.get('flags', {}),
                'shapes': json_data.get('shapes', []),
                'description': json_data.get('description', ''),
                'imagePath': json_data.get('imagePath', ''),
                'imageHeight': json_data.get('imageHeight', 0),
                'imageWidth': json_data.get('imageWidth', 0),
                'created_at': datetime.now(),
                'last_modified': datetime.now()
            }
            
            # MongoDB에 삽입
            result = collection.insert_one(mongodb_doc)
            
            if result.inserted_id:
                added_count += 1
                print(f"✅ 추가됨: {json_file}")
            else:
                print(f"❌ 추가 실패: {json_file}")
                
        except Exception as e:
            print(f"❌ 처리 실패 {json_file}: {e}")
            
    print(f"🎯 결과: {added_count}개 파일이 MongoDB에 추가됨")
    return added_count


def main():
    """메인 함수"""
    print("📊 JSON → MongoDB 초기 데이터 추가")
    print("=" * 50)
    
    try:
        count = add_json_files_to_mongodb()
        
        if count > 0:
            print(f"\n✅ 성공적으로 {count}개 파일 추가됨")
            print("이제 플래그 동기화 테스트를 할 수 있습니다:")
            print("  python standalone_flag_sync.py status")
            print("  python standalone_flag_sync.py update-test")
            print("  python standalone_flag_sync.py sync")
        else:
            print("\n❌ 추가된 파일이 없습니다")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        
    print("=" * 50)


if __name__ == '__main__':
    main()