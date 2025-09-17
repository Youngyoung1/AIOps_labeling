#!/usr/bin/env python3
"""
실제 JSON 파일들을 MongoDB에 추가하는 간단한 스크립트
"""

import os
import json
from datetime import datetime
import pymongo
from pymongo import MongoClient


def add_real_json_files():
    """실제 JSON 파일들을 MongoDB에 추가"""
    
    # MongoDB 연결
    client = MongoClient('mongodb://localhost:27017/')
    db = client['x_anylabeling']
    collection = db['annotations']
    
    # 실제 JSON 파일들 경로
    json_files = [
        r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file\231012_060258_0_side1.json",
        r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file\231012_060258_0_side2.json",
        r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file\231012_060304_0_side2.json",
        r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file\231012_060355_0_side2.json",
        r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file\231012_060920_0_side2.json",
        r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file\231012_061126_0_side2.json"
    ]
    
    print(f"📁 {len(json_files)}개 JSON 파일 처리 시작")
    
    added_count = 0
    updated_count = 0
    
    for json_path in json_files:
        if not os.path.exists(json_path):
            print(f"❌ 파일 없음: {os.path.basename(json_path)}")
            continue
            
        try:
            # JSON 파일 읽기
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                
            # MongoDB 경로 (Windows → Unix 스타일)
            mongodb_path = json_path.replace('\\', '/')
            
            # 기존 문서 확인
            existing = collection.find_one({'json_file_path': mongodb_path})
            
            # MongoDB 문서 데이터
            mongodb_doc = {
                'json_file_path': mongodb_path,
                'flags': json_data.get('flags', {}),
                'shapes': json_data.get('shapes', []),
                'description': json_data.get('description', ''),
                'imagePath': json_data.get('imagePath', ''),
                'imageHeight': json_data.get('imageHeight', 0),
                'imageWidth': json_data.get('imageWidth', 0),
                'last_modified': datetime.now()
            }
            
            if existing:
                # 기존 문서 업데이트
                result = collection.update_one(
                    {'_id': existing['_id']},
                    {'$set': mongodb_doc}
                )
                
                if result.modified_count > 0:
                    updated_count += 1
                    print(f"🔄 업데이트됨: {os.path.basename(json_path)}")
                else:
                    print(f"📊 변경없음: {os.path.basename(json_path)}")
            else:
                # 새 문서 생성
                mongodb_doc['created_at'] = datetime.now()
                result = collection.insert_one(mongodb_doc)
                
                if result.inserted_id:
                    added_count += 1
                    print(f"✅ 추가됨: {os.path.basename(json_path)}")
                else:
                    print(f"❌ 추가 실패: {os.path.basename(json_path)}")
                    
        except Exception as e:
            print(f"❌ 처리 실패 {os.path.basename(json_path)}: {e}")
            
    print(f"\n🎯 결과:")
    print(f"   새로 추가: {added_count}개")
    print(f"   업데이트: {updated_count}개")
    
    # 전체 문서 개수 확인
    total_docs = collection.count_documents({})
    print(f"   전체 문서: {total_docs}개")
    
    return added_count + updated_count


if __name__ == '__main__':
    print("📊 실제 JSON 파일들을 MongoDB에 추가")
    print("=" * 50)
    
    try:
        count = add_real_json_files()
        
        if count > 0:
            print(f"\n✅ {count}개 파일 처리 완료!")
            print("\n다음 단계:")
            print("  python standalone_flag_sync.py status")
            print("  python standalone_flag_sync.py update-test")
            print("  python standalone_flag_sync.py sync")
        else:
            print("\n❌ 처리된 파일이 없습니다")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        
    print("=" * 50)