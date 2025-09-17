#!/usr/bin/env python3
"""
MongoDB와 JSON 파일 상태 비교 스크립트
"""

from anylabeling.services.annotation_manager import AnnotationManager
import json
import os

def check_mongodb_json_sync():
    """MongoDB와 JSON 파일의 동기화 상태 확인"""
    
    # MongoDB 연결
    manager = AnnotationManager()
    
    print('🔍 MongoDB vs JSON 파일 상태 비교')
    print('='*60)
    
    # 전체 문서 수
    total_count = manager.collection.count_documents({})
    print(f'MongoDB 전체 문서 수: {total_count}')
    
    # unclear_file 관련 문서들
    unclear_count = manager.collection.count_documents({'json_file_path': {'$regex': r'Unclear_file'}})
    print(f'unclear_file 관련 문서 수: {unclear_count}')
    
    # unclear_file 문서들 조회
    mongodb_docs = list(manager.collection.find({
        'json_file_path': {'$regex': r'Unclear_file'}
    }, {'json_file_path': 1, 'json_file_name': 1, 'flags': 1, '_id': 1}))
    
    if not mongodb_docs:
        print('❌ unclear_file 관련 문서를 찾을 수 없음')
        return
    
    print(f'\n📊 발견된 MongoDB 문서: {len(mongodb_docs)}개')
    
    for i, doc in enumerate(mongodb_docs, 1):
        file_path = doc.get('json_file_path', '')
        file_name = doc.get('json_file_name', '')
        mongodb_flags = doc.get('flags', {})
        doc_id = str(doc.get('_id', ''))
        
        print(f'\n📄 #{i} 파일: {file_name}')
        print(f'   경로: {file_path}')
        print(f'   MongoDB ID: {doc_id}')
        print(f'   MongoDB flags: {mongodb_flags}')
        
        # 해당 JSON 파일 읽기
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                json_flags = json_data.get('flags', {})
                print(f'   JSON flags: {json_flags}')
                
                # 플래그 비교
                if mongodb_flags == json_flags:
                    print('   ✅ 동기화됨')
                else:
                    print('   ❌ 불일치 발견!')
                    mongodb_only = set(mongodb_flags.keys()) - set(json_flags.keys())
                    json_only = set(json_flags.keys()) - set(mongodb_flags.keys())
                    
                    if mongodb_only:
                        print(f'      MongoDB에만 있는 플래그: {list(mongodb_only)}')
                    if json_only:
                        print(f'      JSON에만 있는 플래그: {list(json_only)}')
                        
                    # 값이 다른 플래그들
                    common_keys = set(mongodb_flags.keys()) & set(json_flags.keys())
                    different_values = []
                    for key in common_keys:
                        if mongodb_flags[key] != json_flags[key]:
                            different_values.append(key)
                    
                    if different_values:
                        print(f'      값이 다른 플래그: {different_values}')
                        for key in different_values:
                            print(f'        {key}: MongoDB={mongodb_flags[key]}, JSON={json_flags[key]}')
                            
            except Exception as e:
                print(f'   ❌ JSON 파일 읽기 실패: {e}')
        else:
            print(f'   ❌ JSON 파일이 존재하지 않음')

if __name__ == "__main__":
    check_mongodb_json_sync()