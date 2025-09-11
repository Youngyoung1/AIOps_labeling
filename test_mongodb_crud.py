"""MongoDB CRUD 테스트 스크립트"""

import sys
import os
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from anylabeling.services.storage.mongodb_client import MongoStorage

def test_mongodb_crud():
    """MongoDB CRUD 기능 테스트"""
    print("MongoDB CRUD 테스트 시작...")
    
    # MongoDB 연결
    storage = MongoStorage()
    
    # 연결 테스트
    if not storage.test_connection():
        print("❌ MongoDB 연결 실패")
        return
    print("✅ MongoDB 연결 성공")
    
    # 1. 프로젝트 생성 테스트
    print("\n1. 프로젝트 생성 테스트")
    project_id = storage.create_project(
        name="테스트 프로젝트",
        description="CRUD 테스트용 프로젝트"
    )
    print(f"프로젝트 생성됨: {project_id}")
    
    # 2. 이미지 저장 테스트
    print("\n2. 이미지 저장 테스트")
    test_images = [
        {
            'image_id': 'test_img_001.jpg',
            'filename': 'test_img_001.jpg',
            'file_path': '/test/path/test_img_001.jpg',
            'status': 'pending',
            'project_id': project_id
        },
        {
            'image_id': 'test_img_002.jpg', 
            'filename': 'test_img_002.jpg',
            'file_path': '/test/path/test_img_002.jpg',
            'status': 'completed',
            'project_id': project_id
        }
    ]
    
    for img in test_images:
        image_id = storage.upsert_image(img)
        print(f"이미지 저장됨: {image_id}")
    
    # 3. 어노테이션 생성 테스트
    print("\n3. 어노테이션 생성 테스트")
    test_annotations = [
        {
            'image_id': 'test_img_001.jpg',
            'label': 'license_plate',
            'category': 'vehicle',
            'confidence': 0.95,
            'bbox': [100, 100, 200, 50],
            'properties': {
                'plate_number': '12가3456',
                'plate_category': 'plate_0to6'
            },
            'project_id': project_id
        },
        {
            'image_id': 'test_img_002.jpg',
            'label': 'license_plate', 
            'category': 'vehicle',
            'confidence': 0.87,
            'bbox': [150, 120, 180, 45],
            'properties': {
                'plate_number': '78나9012',
                'plate_category': 'plate_7'
            },
            'project_id': project_id
        }
    ]
    
    annotation_ids = []
    for ann in test_annotations:
        ann_id = storage.insert_annotation(ann)
        annotation_ids.append(ann_id)
        print(f"어노테이션 생성됨: {ann_id}")
    
    # 4. 조회 테스트
    print("\n4. 데이터 조회 테스트")
    
    # 프로젝트 목록 조회
    projects = storage.get_projects()
    print(f"프로젝트 수: {len(projects)}")
    for project in projects[-2:]:  # 최근 2개만 표시
        print(f"  - {project.get('name', 'Unknown')} ({project.get('status', 'Unknown')})")
    
    # 어노테이션 조회
    annotations = storage.find_annotations({'project_id': project_id})
    print(f"어노테이션 수: {len(annotations)}")
    for ann in annotations:
        plate_num = ann.get('properties', {}).get('plate_number', 'N/A')
        print(f"  - {ann.get('label', 'Unknown')}: {plate_num} (신뢰도: {ann.get('confidence', 0):.2f})")
    
    # 5. 검색 테스트
    print("\n5. 검색 테스트")
    
    # 카테고리별 검색
    vehicle_annotations = storage.search_by_category('vehicle')
    print(f"차량 카테고리 어노테이션: {len(vehicle_annotations)}개")
    
    # 신뢰도 범위 검색
    high_confidence = storage.search_by_confidence(0.9)
    print(f"고신뢰도 어노테이션 (0.9+): {len(high_confidence)}개")
    
    # 다중 필드 검색
    search_results = storage.multi_field_search('12가')
    print(f"'12가' 검색 결과: {len(search_results)}개")
    
    # 6. 업데이트 테스트
    print("\n6. 데이터 업데이트 테스트")
    if annotation_ids:
        # 첫 번째 어노테이션 신뢰도 업데이트
        from bson import ObjectId
        ann_id = ObjectId(annotation_ids[0])
        updated = storage.update_annotation(
            {'_id': ann_id},
            {'confidence': 0.99, 'verified': True}
        )
        print(f"어노테이션 업데이트됨: {updated}개")
    
    # 프로젝트 통계 업데이트
    storage.update_project_stats(project_id)
    print("프로젝트 통계 업데이트 완료")
    
    # 7. 통계 조회 테스트
    print("\n7. 통계 조회 테스트")
    stats = storage.get_database_stats()
    print(f"전체 이미지: {stats.get('total_images', 0)}개")
    print(f"라벨링 완료: {stats.get('labeled_images', 0)}개")
    print(f"진행률: {stats.get('progress', 0):.1f}%")
    print(f"총 어노테이션: {stats.get('total_annotations', 0)}개")
    
    # 카테고리별 통계
    categories = stats.get('categories', [])
    if categories:
        print("카테고리별 통계:")
        for cat in categories:
            print(f"  - {cat.get('_id', 'Unknown')}: {cat.get('count', 0)}개")
    
    # 8. 내보내기 테스트  
    print("\n8. 데이터 내보내기 테스트")
    
    # JSON 형식 내보내기
    json_data = storage.export_annotations(format='json')
    print(f"JSON 내보내기: {len(json_data)}자")
    
    # CSV 형식 내보내기
    csv_data = storage.export_annotations(format='csv')
    print(f"CSV 내보내기: {len(csv_data)}자")
    
    # 9. 배치 작업 테스트
    print("\n9. 배치 작업 테스트")
    
    # 이미지 상태 배치 업데이트
    updated_count = storage.batch_update_status(
        ['test_img_001.jpg', 'test_img_002.jpg'], 
        'verified'
    )
    print(f"배치 상태 업데이트: {updated_count}개")
    
    # 어노테이션 카테고리 배치 업데이트
    if annotation_ids:
        category_updated = storage.batch_update_category(
            annotation_ids[:1],  # 첫 번째만
            'verified_vehicle'
        )
        print(f"배치 카테고리 업데이트: {category_updated}개")
    
    # 10. 정리 (선택사항)
    print("\n10. 테스트 데이터 정리")
    
    cleanup = input("테스트 데이터를 삭제하시겠습니까? (y/N): ").strip().lower()
    if cleanup == 'y':
        # 어노테이션 삭제
        if annotation_ids:
            deleted_ann = storage.batch_delete_annotations(annotation_ids)
            print(f"어노테이션 삭제됨: {deleted_ann}개")
        
        # 이미지 삭제
        storage.images.delete_many({'project_id': project_id})
        print("테스트 이미지 삭제됨")
        
        # 프로젝트 삭제
        from bson import ObjectId
        storage.db.projects.delete_one({'_id': ObjectId(project_id)})
        print("테스트 프로젝트 삭제됨")
    
    print("\n✅ MongoDB CRUD 테스트 완료!")
    storage.close()

def test_plate_recognition_integration():
    """번호판 인식 통합 테스트"""
    print("\n번호판 인식 통합 테스트...")
    
    storage = MongoStorage()
    
    # 테스트 번호판 데이터 저장
    test_plates = [
        {'filename': 'plate1.jpg', 'plate_number': '12가3456', 'confidence': 0.95},
        {'filename': 'plate2.jpg', 'plate_number': '78나9012', 'confidence': 0.87},
        {'filename': 'plate3.jpg', 'plate_number': '89다1234', 'confidence': 0.92},
    ]
    
    for plate_data in test_plates:
        # 번호판 카테고리 분류
        first_char = plate_data['plate_number'][0]
        if first_char == '7':
            category = 'plate_7'
        elif first_char in ['8', '9']:
            category = 'plate_8to9'
        else:
            category = 'plate_0to6'
        
        # 저장
        storage.save_plate_recognition_result(
            filename=plate_data['filename'],
            file_path=f"/test/{plate_data['filename']}",
            plate_number=plate_data['plate_number'],
            confidence=plate_data['confidence'],
            category=category
        )
        print(f"번호판 데이터 저장: {plate_data['plate_number']} ({category})")
    
    # 번호판 통계 조회
    plate_stats = storage.get_plate_statistics()
    print("\n번호판 통계:")
    for cat_stat in plate_stats.get('plate_categories', []):
        print(f"  - {cat_stat.get('_id', 'Unknown')}: {cat_stat.get('count', 0)}개")
    
    storage.close()
    print("✅ 번호판 인식 통합 테스트 완료!")

if __name__ == "__main__":
    try:
        # 기본 CRUD 테스트
        test_mongodb_crud()
        
        # 번호판 인식 통합 테스트
        test_plate_recognition_integration()
        
        print("\n🎉 모든 테스트가 성공적으로 완료되었습니다!")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
