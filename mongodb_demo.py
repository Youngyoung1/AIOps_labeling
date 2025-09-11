"""MongoDB 라벨링 툴 CRUD 데모"""

from datetime import datetime
import sys
import os

# MongoDB 클라이언트 import (절대 경로 사용)
try:
    from anylabeling.services.storage.mongodb_client import MongoStorage
except ImportError:
    # 상대 경로로 시도
    sys.path.append(os.path.dirname(__file__))
    from anylabeling.services.storage.mongodb_client import MongoStorage

def simple_crud_demo():
    """간단한 CRUD 데모"""
    print("="*60)
    print("MongoDB 라벨링 툴 CRUD 기능 데모")
    print("="*60)
    
    # MongoDB 연결
    try:
        storage = MongoStorage()
        print("✅ MongoDB 연결 성공")
    except Exception as e:
        print(f"❌ MongoDB 연결 실패: {e}")
        print("MongoDB 서버가 실행 중인지 확인해주세요.")
        return
    
    # 1. CREATE - 데이터 생성
    print("\n📝 1. CREATE - 데이터 생성")
    
    # 테스트 이미지 저장
    test_image = {
        'image_id': 'demo_car_001.jpg',
        'filename': 'demo_car_001.jpg', 
        'file_path': '/demo/images/demo_car_001.jpg',
        'status': 'completed',
        'uploaded_at': datetime.now()
    }
    
    storage.upsert_image(test_image)
    print("  ✓ 테스트 이미지 저장됨")
    
    # 번호판 어노테이션 저장
    plate_annotation = {
        'image_id': 'demo_car_001.jpg',
        'label': 'license_plate',
        'category': 'vehicle',
        'confidence': 0.92,
        'bbox': [120, 200, 150, 40],  # x, y, width, height
        'properties': {
            'plate_number': '12가3456',
            'plate_category': 'plate_0to6',
            'vehicle_type': 'car'
        },
        'created_by': 'demo_user'
    }
    
    ann_id = storage.insert_annotation(plate_annotation)
    print(f"  ✓ 번호판 어노테이션 생성됨 (ID: {ann_id})")
    
    # 2. READ - 데이터 조회
    print("\n📖 2. READ - 데이터 조회")
    
    # 모든 어노테이션 조회
    all_annotations = storage.find_annotations()
    print(f"  📊 총 어노테이션 수: {len(all_annotations)}개")
    
    # 최근 3개 어노테이션 표시
    recent_annotations = all_annotations[-3:] if len(all_annotations) >= 3 else all_annotations
    for i, ann in enumerate(recent_annotations, 1):
        plate_num = ann.get('properties', {}).get('plate_number', 'N/A')
        confidence = ann.get('confidence', 0)
        print(f"    {i}. 번호판: {plate_num}, 신뢰도: {confidence:.2f}")
    
    # 특정 라벨 검색
    plate_annotations = storage.find_annotations({'label': 'license_plate'})
    print(f"  🔍 번호판 어노테이션: {len(plate_annotations)}개")
    
    # 3. UPDATE - 데이터 수정
    print("\n✏️ 3. UPDATE - 데이터 수정")
    
    # 신뢰도 업데이트
    if all_annotations:
        from bson import ObjectId
        first_ann = all_annotations[0]
        ann_object_id = first_ann['_id']
        
        updated_count = storage.update_annotation(
            {'_id': ann_object_id},
            {
                'confidence': 0.98,
                'verified': True,
                'updated_at': datetime.now()
            }
        )
        print(f"  ✓ 어노테이션 업데이트: {updated_count}개")
    
    # 4. SEARCH - 검색 기능
    print("\n🔍 4. SEARCH - 고급 검색")
    
    # 다중 필드 검색
    search_results = storage.multi_field_search('12가')
    print(f"  📝 '12가' 검색 결과: {len(search_results)}개")
    
    # 신뢰도 기반 검색
    high_confidence = storage.search_by_confidence(0.9)
    print(f"  📈 고신뢰도 어노테이션 (0.9+): {len(high_confidence)}개")
    
    # 카테고리별 검색
    vehicle_annotations = storage.search_by_category('vehicle')
    print(f"  🚗 차량 카테고리: {len(vehicle_annotations)}개")
    
    # 5. STATISTICS - 통계 정보
    print("\n📊 5. STATISTICS - 통계 정보")
    
    stats = storage.get_database_stats()
    print(f"  📁 총 이미지: {stats.get('total_images', 0)}개")
    print(f"  ✅ 라벨링 완료: {stats.get('labeled_images', 0)}개")
    print(f"  📋 총 어노테이션: {stats.get('total_annotations', 0)}개")
    print(f"  📈 진행률: {stats.get('progress', 0):.1f}%")
    
    # 카테고리별 통계
    categories = stats.get('categories', [])
    if categories:
        print("  🏷️ 카테고리별 분포:")
        for cat in categories:
            cat_name = cat.get('_id', 'Unknown')
            count = cat.get('count', 0)
            avg_conf = cat.get('avg_confidence', 0)
            print(f"    - {cat_name}: {count}개 (평균 신뢰도: {avg_conf:.2f})")
    
    # 6. EXPORT - 데이터 내보내기
    print("\n💾 6. EXPORT - 데이터 내보내기")
    
    # JSON 내보내기 (일부만)
    export_filter = {'label': 'license_plate'}
    json_data = storage.export_annotations(filters=export_filter, format='json')
    print(f"  📄 JSON 내보내기: {len(json_data.splitlines())}줄")
    
    # CSV 내보내기
    csv_data = storage.export_annotations(filters=export_filter, format='csv')
    csv_lines = len([line for line in csv_data.split('\n') if line.strip()])
    print(f"  📊 CSV 내보내기: {csv_lines}줄")
    
    # 7. 번호판 특화 기능
    print("\n🚗 7. 번호판 특화 기능")
    
    # 번호판 인식 결과 저장 시뮬레이션
    demo_plates = [
        {'filename': 'car1.jpg', 'plate': '78나1234', 'conf': 0.94},
        {'filename': 'car2.jpg', 'plate': '89다5678', 'conf': 0.88},
        {'filename': 'car3.jpg', 'plate': '12가9999', 'conf': 0.96}
    ]
    
    for plate_data in demo_plates:
        # 번호판 카테고리 분류
        first_char = plate_data['plate'][0]
        if first_char == '7':
            category = 'plate_7'
        elif first_char in ['8', '9']:
            category = 'plate_8to9'
        else:
            category = 'plate_0to6'
        
        storage.save_plate_recognition_result(
            filename=plate_data['filename'],
            file_path=f"/demo/{plate_data['filename']}",
            plate_number=plate_data['plate'],
            confidence=plate_data['conf'],
            category=category
        )
    
    print("  ✓ 번호판 인식 결과 3개 저장됨")
    
    # 번호판 통계
    plate_stats = storage.get_plate_statistics()
    plate_categories = plate_stats.get('plate_categories', [])
    if plate_categories:
        print("  📋 번호판 카테고리별 분포:")
        for cat in plate_categories:
            print(f"    - {cat.get('_id', 'Unknown')}: {cat.get('count', 0)}개")
    
    # 8. 정리
    print("\n🧹 8. 정리")
    
    # 최종 통계 표시
    final_stats = storage.get_database_stats()
    print(f"  📊 최종 통계:")
    print(f"    - 총 이미지: {final_stats.get('total_images', 0)}개")
    print(f"    - 총 어노테이션: {final_stats.get('total_annotations', 0)}개")
    
    storage.close()
    print("\n✅ 데이터베이스 연결 종료")
    
    print("\n" + "="*60)
    print("🎉 MongoDB CRUD 데모 완료!")
    print("="*60)
    print("\n💡 주요 기능:")
    print("  • 이미지 및 어노테이션 저장/조회/수정/삭제")
    print("  • 다중 필드 검색 및 필터링")
    print("  • 실시간 통계 및 진행률 추적")
    print("  • 번호판 인식 결과 자동 분류 및 저장")
    print("  • JSON/CSV 형식 데이터 내보내기")
    print("  • 배치 작업 지원")

def show_menu():
    """메뉴 표시 및 선택"""
    while True:
        print("\n" + "="*40)
        print("MongoDB 라벨링 툴 데모")
        print("="*40)
        print("1. CRUD 기능 데모 실행")
        print("2. 연결 테스트만 실행")
        print("3. 통계 정보만 보기")
        print("0. 종료")
        print("-"*40)
        
        choice = input("선택하세요 (0-3): ").strip()
        
        if choice == '1':
            simple_crud_demo()
        elif choice == '2':
            test_connection_only()
        elif choice == '3':
            show_stats_only()
        elif choice == '0':
            print("프로그램을 종료합니다.")
            break
        else:
            print("올바른 번호를 선택해주세요.")

def test_connection_only():
    """연결 테스트만 수행"""
    print("\n🔌 MongoDB 연결 테스트...")
    try:
        storage = MongoStorage()
        if storage.test_connection():
            print("✅ MongoDB 연결 성공!")
            print(f"  📁 데이터베이스: {storage.db.name}")
            print(f"  🔗 URI: {storage.uri}")
        else:
            print("❌ MongoDB 연결 실패")
        storage.close()
    except Exception as e:
        print(f"❌ 연결 오류: {e}")

def show_stats_only():
    """통계 정보만 표시"""
    print("\n📊 데이터베이스 통계 조회...")
    try:
        storage = MongoStorage()
        stats = storage.get_database_stats()
        
        print(f"📁 총 이미지: {stats.get('total_images', 0)}개")
        print(f"✅ 라벨링 완료: {stats.get('labeled_images', 0)}개")
        print(f"📋 총 어노테이션: {stats.get('total_annotations', 0)}개")
        print(f"📈 진행률: {stats.get('progress', 0):.1f}%")
        
        categories = stats.get('categories', [])
        if categories:
            print("\n🏷️ 카테고리별 분포:")
            for cat in categories:
                print(f"  - {cat.get('_id', 'Unknown')}: {cat.get('count', 0)}개")
        
        storage.close()
    except Exception as e:
        print(f"❌ 통계 조회 오류: {e}")

if __name__ == "__main__":
    try:
        show_menu()
    except KeyboardInterrupt:
        print("\n\n👋 프로그램이 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 예기치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
