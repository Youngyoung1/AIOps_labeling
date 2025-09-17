#!/usr/bin/env python3
"""
X-AnyLabeling 성능 분석 도구

프로그램 시작 시간을 분석하고 병목 지점을 식별하는 도구입니다.
"""

import time
import sys
import importlib
import os
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime

# 프로파일링 결과 저장
profile_results = {}

@contextmanager
def time_block(name):
    """코드 블록 실행 시간 측정"""
    start_time = time.time()
    print(f"⏱️  [{name}] 시작...")
    try:
        yield
    finally:
        elapsed_time = time.time() - start_time
        profile_results[name] = elapsed_time
        print(f"✅ [{name}] 완료: {elapsed_time:.3f}초")

def analyze_startup_performance():
    """X-AnyLabeling 시작 시 성능 분석"""
    print("🚀 X-AnyLabeling 성능 분석 시작")
    print("=" * 60)
    
    total_start = time.time()
    
    # 1. 환경 변수 설정 시간
    with time_block("환경 변수 설정"):
        os.environ["MKL_NUM_THREADS"] = "1"
        os.environ["NUMEXPR_NUM_THREADS"] = "1"
        os.environ["OMP_NUM_THREADS"] = "1"
        os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.gui.icc=false"
    
    # 2. 기본 모듈 임포트
    with time_block("기본 모듈 임포트"):
        import argparse
        import codecs
        import logging
        import yaml
        from pathlib import Path
    
    # 3. PyQt5 임포트 
    with time_block("PyQt5 임포트"):
        from PyQt5 import QtCore, QtWidgets
    
    # 4. 어플리케이션 관련 모듈 임포트
    with time_block("어플리케이션 모듈 임포트"):
        sys.path.append(str(Path(__file__).resolve().parent))
        
        # anylabeling 모듈 임포트 시간 측정
        from anylabeling.app_info import __appname__, __version__, __url__
        from anylabeling.config import get_config
        from anylabeling import config as anylabeling_config
    
    # 5. 리소스 로딩
    with time_block("리소스 로딩"):
        from anylabeling.resources import resources
    
    # 6. UI 모듈 임포트
    with time_block("UI 모듈 임포트"):
        from anylabeling.views.mainwindow import MainWindow
        from anylabeling.views.labeling.logger import logger
        from anylabeling.views.labeling.utils import new_icon, gradient_text
    
    # 7. 설정 로딩
    with time_block("설정 파일 로딩"):
        config = get_config()
    
    # 8. Qt Application 생성
    with time_block("Qt Application 생성"):
        app = QtWidgets.QApplication(sys.argv)
        app.processEvents()
        
        app.setApplicationName(__appname__)
        app.setApplicationVersion(__version__)
        app.setWindowIcon(new_icon("icon"))
    
    # 9. MainWindow 생성
    with time_block("MainWindow 생성"):
        win = MainWindow(
            app,
            config=config,
            filename=None,
            output_file=None,
            output_dir=None,
        )
    
    # 10. MongoDB 연결 테스트
    with time_block("MongoDB 연결 테스트"):
        try:
            # MongoDB 연결 상태 확인
            if hasattr(win, 'mongo_storage') and win.mongo_storage:
                db_ok = win.mongo_storage.test_connection()
            else:
                db_ok = False
        except Exception as e:
            print(f"   ⚠️  MongoDB 연결 실패: {e}")
            db_ok = False
    
    total_time = time.time() - total_start
    profile_results["전체 시작 시간"] = total_time
    
    print("\n" + "=" * 60)
    print("📊 성능 분석 결과")
    print("=" * 60)
    
    # 결과 정렬 (시간 순)
    sorted_results = sorted(profile_results.items(), key=lambda x: x[1], reverse=True)
    
    for name, elapsed_time in sorted_results:
        percentage = (elapsed_time / total_time) * 100
        print(f"{name:25}: {elapsed_time:6.3f}초 ({percentage:5.1f}%)")
    
    print(f"\n🔍 병목 지점 분석:")
    bottlenecks = [item for item in sorted_results if item[1] > 1.0]  # 1초 이상 걸리는 작업
    
    if bottlenecks:
        print("   다음 항목들이 가장 많은 시간을 소모합니다:")
        for name, time_taken in bottlenecks:
            print(f"   • {name}: {time_taken:.3f}초")
    else:
        print("   🎉 1초 이상 걸리는 병목 지점이 없습니다!")
    
    print(f"\n💡 최적화 제안:")
    
    # PyQt5 임포트가 오래 걸리는 경우
    if profile_results.get("PyQt5 임포트", 0) > 2.0:
        print("   • PyQt5 임포트 최적화: 필요한 모듈만 선택적으로 임포트")
    
    # UI 모듈 임포트가 오래 걸리는 경우  
    if profile_results.get("UI 모듈 임포트", 0) > 2.0:
        print("   • UI 모듈 지연 로딩: 사용 시점에 임포트하도록 변경")
    
    # MainWindow 생성이 오래 걸리는 경우
    if profile_results.get("MainWindow 생성", 0) > 3.0:
        print("   • MainWindow 최적화: 필수 위젯만 먼저 로딩 후 백그라운드에서 나머지 로딩")
    
    # MongoDB 연결이 오래 걸리는 경우
    if profile_results.get("MongoDB 연결 테스트", 0) > 1.0:
        print("   • MongoDB 연결 최적화: 백그라운드 스레드에서 연결 처리")
    
    print(f"\n🎯 DB 상태: {'✅ 연결됨' if db_ok else '❌ 연결 실패'}")
    
    return profile_results, win, app

def create_optimization_recommendations():
    """최적화 권장사항 생성"""
    recommendations = []
    
    # 1. 모듈 지연 로딩
    recommendations.append({
        "category": "모듈 로딩",
        "title": "지연 로딩 구현",
        "description": "자주 사용되지 않는 모듈을 사용 시점에 로딩",
        "implementation": [
            "improved_review_widgets 모듈을 필요시에만 임포트",
            "자동 라벨링 모델들을 백그라운드에서 로딩",
            "데이터베이스 연결을 별도 스레드에서 처리"
        ]
    })
    
    # 2. UI 최적화
    recommendations.append({
        "category": "UI 최적화", 
        "title": "위젯 점진적 로딩",
        "description": "필수 UI만 먼저 표시하고 나머지는 백그라운드에서 로딩",
        "implementation": [
            "메인 캔버스와 기본 툴바만 먼저 표시",
            "도크 위젯들을 필요시에 초기화",
            "메뉴 항목을 지연 생성"
        ]
    })
    
    # 3. 데이터베이스 최적화
    recommendations.append({
        "category": "데이터베이스",
        "title": "비동기 연결 처리", 
        "description": "MongoDB 연결을 백그라운드에서 처리하여 UI 블로킹 방지",
        "implementation": [
            "QThread를 사용한 비동기 DB 연결",
            "연결 실패시 재시도 로직 구현",
            "연결 상태 UI 업데이트"
        ]
    })
    
    return recommendations

if __name__ == "__main__":
    try:
        results, win, app = analyze_startup_performance()
        
        print("\n" + "=" * 60)
        print("🔧 최적화 권장사항")
        print("=" * 60)
        
        recommendations = create_optimization_recommendations()
        for rec in recommendations:
            print(f"\n📂 {rec['category']}: {rec['title']}")
            print(f"   {rec['description']}")
            print("   구현 방안:")
            for impl in rec['implementation']:
                print(f"   • {impl}")
        
        # 결과를 파일로 저장
        report_file = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("X-AnyLabeling 성능 분석 보고서\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("성능 분석 결과:\n")
            for name, elapsed_time in results.items():
                f.write(f"{name:25}: {elapsed_time:6.3f}초\n")
            
            f.write(f"\n최적화 권장사항:\n")
            for rec in recommendations:
                f.write(f"\n{rec['category']}: {rec['title']}\n")
                f.write(f"{rec['description']}\n")
                for impl in rec['implementation']:
                    f.write(f"• {impl}\n")
        
        print(f"\n📄 상세 보고서가 '{report_file}'에 저장되었습니다.")
        
        # 윈도우 표시 (테스트용)
        print(f"\n🖥️  테스트용으로 윈도우를 5초간 표시합니다...")
        win.show()
        
        # 5초 후 종료
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(5000, app.quit)
        
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"❌ 성능 분석 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()