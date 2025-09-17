#!/usr/bin/env python3
"""MongoDB 통계 확인"""

import sys
import os
sys.path.append(os.getcwd())

try:
    import pymongo
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client.labeling_db
    collection = db.annotations
    
    # 전체 통계
    total_count = collection.count_documents({})
    print(f'📊 총 어노테이션 문서: {total_count}개')
    
    # 라벨별 통계
    pipeline = [
        {'$unwind': '$labels'},
        {'$group': {'_id': '$labels', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}}
    ]
    label_stats = list(collection.aggregate(pipeline))
    print(f'🏷️ 라벨별 통계:')
    for stat in label_stats:
        print(f'  - {stat["_id"]}: {stat["count"]}개')
    
    # Shape 타입별 통계
    pipeline = [
        {'$unwind': '$shape_types'},
        {'$group': {'_id': '$shape_types', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}}
    ]
    shape_stats = list(collection.aggregate(pipeline))
    print(f'🔸 Shape 타입별 통계:')
    for stat in shape_stats:
        print(f'  - {stat["_id"]}: {stat["count"]}개')
    
    # 설명이 있는 항목
    desc_count = collection.count_documents({'has_descriptions': True})
    print(f'📝 설명이 있는 어노테이션: {desc_count}개')
    
    client.close()
    
except Exception as e:
    print(f'❌ 오류: {e}')
