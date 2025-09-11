#!/usr/bin/env python3
"""로컬 환경에서 MongoDB 연동 테스트"""

import os
import sys
import time
from datetime import datetime

# X-AnyLabeling 모듈 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'anylabeling'))

def test_network_storage():
    """네트워크 스토리지 설정 테스트"""
    print("🔍 네트워크 스토리지 설정 테스트")
    print("-" * 50)
    
    try:
        from services.network_storage import network_config, image_manager
        
        # 설정 정보 출력
        print("✅ 네트워크 설정 로드 성공")
        print(f"   로컬 테스트 경로: {network_config.config['nas_paths'].get('local_test', 'Not configured')}")
        print(f"   이미지 기본 경로: {network_config.config['nas_paths'].get('images_base', 'Not configured')}")
        print(f"   라벨 기본 경로: {network_config.config['nas_paths'].get('labels_base', 'Not configured')}")
        
        # 네트워크 경로 접근성 테스트
        for name, path in network_config.config['nas_paths'].items():
            if name.startswith('_comment_'):
                continue  # 주석 항목 건너뛰기
            if path and os.path.exists(path):
                print(f"✅ {name} 접근 가능: {path}")
            else:
                print(f"❌ {name} 접근 불가: {path}")
                
        return True
        
    except Exception as e:
        print(f"❌ 네트워크 설정 오류: {e}")
        return False

def test_mongodb_connection():
    """MongoDB 연결 테스트"""
    print("\n🔍 MongoDB 연결 테스트")
    print("-" * 50)
    
    try:
        from services.storage.mongodb_client import MongoStorage
        
        # MongoDB 연결
        mongo_storage = MongoStorage()
        
        # 연결 상태 확인
        if mongo_storage.client:
            print("✅ MongoDB 연결 성공")
            
            # 서버 정보
            server_info = mongo_storage.client.server_info()
            print(f"   서버 버전: {server_info.get('version', 'Unknown')}")
            
            # 데이터베이스 목록
            db_names = mongo_storage.client.list_database_names()
            print(f"   사용 가능한 DB: {db_names}")
            
            # 컬렉션 목록
            collections = mongo_storage.db.list_collection_names()
            print(f"   컬렉션: {collections}")
            
            return True
        else:
            print("❌ MongoDB 연결 실패")
            return False
            
    except Exception as e:
        print(f"❌ MongoDB 연결 오류: {e}")
        return False

def test_nas_directory_scan():
    """디렉토리 스캔 테스트 (로컬 경로 사용)"""
    print("\n🔍 로컬 디렉토리 스캔 테스트")
    print("-" * 50)
    
    try:
        from services.storage.mongodb_client import MongoStorage
        from services.network_storage import image_manager
        
        mongo_storage = MongoStorage()
        
        # 테스트할 로컬 경로들 (NAS 경로 주석처리됨)
        # test_paths = [
        #     r"\\busnas\HOV-work",
        #     r"\\schoolnas-work"
        # ]
        test_paths = [
            r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file"
        ]
        
        for nas_path in test_paths:
            print(f"\n📁 스캔 중: {nas_path}")
            
            if not os.path.exists(nas_path):
                print(f"   ❌ 경로에 접근할 수 없습니다: {nas_path}")
                continue
                
            try:
                # 이미지 스캔
                images = image_manager.scan_directory(nas_path, max_files=5)  # 최대 5개만 테스트
                
                if images:
                    print(f"   ✅ {len(images)}개 이미지 발견")
                    for img in images[:3]:  # 처음 3개만 출력
                        print(f"      - {os.path.basename(img)}")
                        
                    # MongoDB에 등록 테스트
                    result = mongo_storage.scan_and_register_directory(nas_path, project_id=None)
                    if result['success']:
                        print(f"   ✅ MongoDB 등록: {result['registered_count']}개")
                    else:
                        print(f"   ❌ MongoDB 등록 실패: {result.get('error', 'Unknown error')}")
                else:
                    print(f"   ❌ 이미지를 찾을 수 없습니다")
                    
            except Exception as e:
                print(f"   ❌ 스캔 오류: {e}")
                
        return True
        
    except Exception as e:
        print(f"❌ NAS 스캔 테스트 오류: {e}")
        return False

def test_plate_recognition_nas():
    """로컬 환경에서 번호판 인식 테스트"""
    print("\n🔍 로컬 번호판 인식 테스트")
    print("-" * 50)
    
    try:
        from services.plate_recognition import PlateRecognitionService
        
        # 번호판 인식 서비스 초기화
        plate_service = PlateRecognitionService()
        
        if not plate_service.mongo_storage:
            print("❌ MongoDB 연결이 필요합니다")
            return False
            
        if not plate_service.network_config:
            print("❌ 네트워크 설정이 필요합니다")
            return False
            
        # 테스트할 로컬 경로들 (NAS 경로는 주석 처리되어 있음)
        test_paths = [
            r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file"
        ]
        
        for local_path in test_paths:
            if os.path.exists(local_path):
                print(f"\n📁 번호판 인식 테스트: {local_path}")
                
                # 로컬 배치 처리 (최대 3개 파일만)
                results = plate_service.recognize_plate_local_batch(local_path, project_id="local_test")
                
                # 결과 출력
                total = sum(len(results[key]) for key in results)
                print(f"   ✅ 처리 완료: {total}개")
                
                for category, items in results.items():
                    if items:
                        print(f"   - {category}: {len(items)}개")
                        
                break  # 첫 번째 접근 가능한 경로만 테스트
        else:
            print("❌ 접근 가능한 NAS 경로가 없습니다")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ 번호판 인식 테스트 오류: {e}")
        return False

def test_database_query():
    """데이터베이스 쿼리 테스트"""
    print("\n🔍 데이터베이스 쿼리 테스트")
    print("-" * 50)
    
    try:
        from services.storage.mongodb_client import MongoStorage
        
        mongo_storage = MongoStorage()
        
        # 통계 정보
        stats = mongo_storage.get_statistics()
        print("📊 데이터베이스 통계:")
        print(f"   - 총 이미지: {stats.get('total_images', 0)}개")
        print(f"   - 총 어노테이션: {stats.get('total_annotations', 0)}개")
        print(f"   - 총 프로젝트: {stats.get('total_projects', 0)}개")
        
        # NAS 이미지 검색
        nas_images = mongo_storage.search_images({'nas_path': {'$exists': True}})
        print(f"\n🔍 NAS 이미지: {len(nas_images)}개 발견")
        
        # 번호판 어노테이션 검색
        plate_annotations = mongo_storage.search_annotations({'label': 'license_plate'})
        print(f"🔍 번호판 어노테이션: {len(plate_annotations)}개 발견")
        
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 쿼리 오류: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("🚀 NAS 네트워크 환경 MongoDB 연동 테스트 시작")
    print("=" * 60)
    
    test_results = []
    
    # 1. 네트워크 스토리지 설정 테스트
    test_results.append(("네트워크 설정", test_network_storage()))
    
    # 2. MongoDB 연결 테스트
    test_results.append(("MongoDB 연결", test_mongodb_connection()))
    
    # 3. NAS 디렉토리 스캔 테스트
    test_results.append(("NAS 디렉토리 스캔", test_nas_directory_scan()))
    
    # 4. 번호판 인식 테스트
    test_results.append(("번호판 인식", test_plate_recognition_nas()))
    
    # 5. 데이터베이스 쿼리 테스트
    test_results.append(("데이터베이스 쿼리", test_database_query()))
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("🏁 테스트 결과 요약")
    print("=" * 60)
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ 성공" if result else "❌ 실패"
        print(f"{test_name:<20}: {status}")
        if result:
            passed += 1
    
    print(f"\n총 {len(test_results)}개 테스트 중 {passed}개 성공")
    
    if passed == len(test_results):
        print("🎉 모든 테스트가 성공했습니다!")
    else:
        print("⚠️  일부 테스트가 실패했습니다. 설정을 확인해주세요.")

if __name__ == "__main__":
    main()
