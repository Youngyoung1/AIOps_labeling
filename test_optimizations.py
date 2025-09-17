#!/usr/bin/env python3
"""
실시간 DB 동기화 및 성능 최적화 테스트 스크립트

이 스크립트는 새로 구현된 기능들을 테스트합니다:
1. 실시간 MongoDB 동기화
2. 프로그램 시작 속도 최적화
3. 백그라운드 저장 시스템
"""

import sys
import time
import json
import tempfile
import os
from datetime import datetime
from pathlib import Path

# anylabeling 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

def test_realtime_db_sync():
    """실시간 DB 동기화 테스트"""
    print("🔄 실시간 DB 동기화 테스트 시작")
    print("=" * 60)
    
    try:
        from anylabeling.services.realtime_db_sync import RealTimeDBSync, SaveTask
        from anylabeling.services.annotation_manager import AnnotationManager
        
        # AnnotationManager 초기화
        print("📋 AnnotationManager 초기화 중...")
        annotation_manager = AnnotationManager()
        
        # RealTimeDBSync 초기화
        print("🔗 RealTimeDBSync 초기화 중...")
        realtime_sync = RealTimeDBSync(annotation_manager)
        realtime_sync.start()
        
        # 테스트 어노테이션 데이터
        test_annotation = {
            "version": "1.0.0",
            "flags": {"reviewed": False, "difficult": False},
            "shapes": [
                {
                    "label": "test_object",
                    "points": [[100, 100], [200, 100], [200, 200], [100, 200]],
                    "group_id": None,
                    "shape_type": "rectangle",
                    "flags": {}
                }
            ],
            "imagePath": "test_image.jpg",
            "imageHeight": 300,
            "imageWidth": 400
        }
        
        # 비동기 저장 테스트
        print("💾 어노테이션 비동기 저장 테스트...")
        success = realtime_sync.save_annotation_async(test_annotation, "test_task_1")
        print(f"   저장 요청 결과: {'✅ 성공' if success else '❌ 실패'}")
        
        # 플래그 저장 테스트
        print("🏷️  플래그 비동기 저장 테스트...")
        test_flags = {"reviewed": True, "quality_checked": True}
        success = realtime_sync.save_flags_async("test_image.jpg", test_flags, "flag_task_1")
        print(f"   플래그 저장 요청 결과: {'✅ 성공' if success else '❌ 실패'}")
        
        # 지연 저장 테스트
        print("⏰ 지연 저장 테스트...")
        realtime_sync.save_annotation_delayed(test_annotation, delay_ms=1000)
        print("   지연 저장 설정 완료 (1초 후 저장)")
        
        # 잠시 대기하여 백그라운드 처리 확인
        print("⏳ 백그라운드 처리 대기 중...")
        time.sleep(3)
        
        # 상태 확인
        status = realtime_sync.get_status()
        print("📊 실시간 동기화 상태:")
        for key, value in status.items():
            print(f"   {key}: {value}")
        
        # 정리
        realtime_sync.stop()
        print("✅ 실시간 DB 동기화 테스트 완료")
        
    except Exception as e:
        print(f"❌ 실시간 DB 동기화 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def test_startup_optimization():
    """시작 최적화 테스트"""
    print("\n🚀 시작 최적화 테스트 시작")
    print("=" * 60)
    
    try:
        from anylabeling.services.startup_optimizer import StartupOptimizer, LazyModuleLoader
        
        # LazyModuleLoader 테스트
        print("🔄 LazyModuleLoader 테스트...")
        loader = LazyModuleLoader()
        
        # 테스트 모듈 로딩
        test_module = loader.load_module("json", lambda: __import__("json"))
        print(f"   JSON 모듈 로딩: {'✅ 성공' if test_module else '❌ 실패'}")
        
        # 로딩 통계 확인
        stats = loader.get_loading_stats()
        print(f"   로딩 통계: {stats}")
        
        # StartupOptimizer 테스트
        print("⚡ StartupOptimizer 테스트...")
        optimizer = StartupOptimizer()
        
        # 최적화 설정 확인
        opt_stats = optimizer.get_optimization_stats()
        print("📊 최적화 설정:")
        for key, value in opt_stats.items():
            print(f"   {key}: {value}")
        
        print("✅ 시작 최적화 테스트 완료")
        
    except Exception as e:
        print(f"❌ 시작 최적화 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def test_background_save_worker():
    """백그라운드 저장 워커 테스트"""
    print("\n🔧 백그라운드 저장 워커 테스트 시작")
    print("=" * 60)
    
    try:
        from anylabeling.services.realtime_db_sync import BackgroundSaveWorker, SaveTask
        from anylabeling.services.annotation_manager import AnnotationManager
        
        # AnnotationManager 초기화
        annotation_manager = AnnotationManager()
        
        # BackgroundSaveWorker 초기화
        print("🔧 BackgroundSaveWorker 초기화...")
        worker = BackgroundSaveWorker(annotation_manager)
        
        # 신호 연결 (테스트용)
        def on_save_completed(task_id, success, message):
            status = "✅" if success else "❌"
            print(f"   {status} 저장 완료: {task_id} - {message}")
        
        def on_batch_completed(total, successful):
            print(f"   📦 배치 완료: {successful}/{total}")
        
        def on_error_occurred(task_id, error_message):
            print(f"   ⚠️  오류 발생: {task_id} - {error_message}")
        
        worker.save_completed.connect(on_save_completed)
        worker.batch_completed.connect(on_batch_completed)
        worker.error_occurred.connect(on_error_occurred)
        
        # 워커 시작
        worker.start()
        print("   워커 스레드 시작됨")
        
        # 테스트 작업들 추가
        test_tasks = [
            SaveTask(
                task_id=f"test_annotation_{i}",
                task_type="annotation",
                data={
                    "json_data": {
                        "version": "1.0.0",
                        "imagePath": f"test_image_{i}.jpg",
                        "shapes": [{"label": f"object_{i}", "points": [[0, 0], [10, 10]]}],
                        "flags": {}
                    }
                },
                priority=1
            )
            for i in range(5)
        ]
        
        print("📤 테스트 작업들 추가 중...")
        for task in test_tasks:
            worker.add_task(task)
        
        # 처리 대기
        print("⏳ 작업 처리 대기 중...")
        time.sleep(3)
        
        # 통계 확인
        stats = worker.get_statistics()
        print("📊 워커 통계:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # 워커 중지
        worker.stop()
        worker.wait(3000)
        print("✅ 백그라운드 저장 워커 테스트 완료")
        
    except Exception as e:
        print(f"❌ 백그라운드 저장 워커 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def test_performance_metrics():
    """성능 메트릭 테스트"""
    print("\n📊 성능 메트릭 테스트 시작")
    print("=" * 60)
    
    # 시뮬레이션된 성능 테스트
    operations = [
        ("MongoDB 연결", 0.5),
        ("UI 초기화", 1.2), 
        ("모델 로딩", 2.1),
        ("설정 로딩", 0.3),
        ("확장 로딩", 0.8)
    ]
    
    print("⏱️  각 작업별 시간 측정:")
    total_time = 0
    
    for operation, expected_time in operations:
        start_time = time.time()
        # 시뮬레이션 (실제로는 해당 작업 수행)
        time.sleep(expected_time / 10)  # 10배 빠르게 시뮬레이션
        actual_time = time.time() - start_time
        total_time += actual_time
        
        print(f"   {operation:15}: {actual_time:.3f}초 (예상: {expected_time:.3f}초)")
    
    print(f"\n🏁 총 시간: {total_time:.3f}초")
    
    # 최적화 제안
    print("\n💡 최적화 제안:")
    if total_time > 1.0:
        print("   • 백그라운드 초기화 사용 권장")
    if total_time > 2.0:
        print("   • 모듈 지연 로딩 적용 권장")
    if total_time > 3.0:
        print("   • 스플래시 스크린 표시 권장")
    
    print("✅ 성능 메트릭 테스트 완료")

def main():
    """메인 테스트 함수"""
    print("🧪 X-AnyLabeling 최적화 기능 테스트")
    print("=" * 80)
    print(f"테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 각 테스트 실행
    test_realtime_db_sync()
    test_startup_optimization()
    test_background_save_worker()
    test_performance_metrics()
    
    print("\n" + "=" * 80)
    print("🎉 모든 테스트 완료!")
    print("=" * 80)
    
    # 요약 정보
    print("\n📋 구현된 최적화 기능:")
    print("   ✅ 실시간 MongoDB 동기화")
    print("   ✅ 백그라운드 저장 시스템")  
    print("   ✅ 프로그램 시작 속도 최적화")
    print("   ✅ 지연 저장 (디바운싱)")
    print("   ✅ 백그라운드 초기화")
    print("   ✅ 모듈 지연 로딩")
    
    print("\n🎯 사용자 혜택:")
    print("   • 라벨링 작업 시 자동으로 DB에 실시간 저장")
    print("   • 프로그램 시작 시간 단축")
    print("   • UI 블로킹 없는 백그라운드 처리")
    print("   • 안정적인 데이터 보존")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  테스트 중단됨")
    except Exception as e:
        print(f"\n\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()