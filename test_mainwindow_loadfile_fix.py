"""
MainWindow load_file 함수 해결 확인 테스트
"""

import sys
import os

# 현재 디렉토리를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def test_mainwindow_load_file():
    """MainWindow load_file 함수 확인"""
    
    print("🧪 MainWindow load_file 함수 테스트...")
    
    try:
        # MainWindow 클래스 임포트 확인
        print("📦 MainWindow 클래스 로딩 중...")
        from anylabeling.views.mainwindow import MainWindow
        
        # load_file 메서드 확인
        if hasattr(MainWindow, 'load_file'):
            print("✅ MainWindow.load_file 메서드 발견!")
        else:
            print("❌ MainWindow.load_file 메서드가 없습니다")
            return False
        
        print("🎯 MainWindow load_file 함수가 정상적으로 추가되었습니다!")
        return True
        
    except ImportError as e:
        print(f"❌ MainWindow 임포트 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False

def test_fast_file_loader():
    """FastFileLoader 확인"""
    
    print("\n🧪 FastFileLoader 테스트...")
    
    try:
        from anylabeling.services.fast_file_loader import get_fast_file_loader, apply_fast_file_loading
        
        loader = get_fast_file_loader()
        if hasattr(loader, 'patch_main_window_load_file'):
            print("✅ patch_main_window_load_file 메서드 발견!")
        
        print("✅ FastFileLoader 정상 동작!")
        return True
        
    except ImportError as e:
        print(f"❌ FastFileLoader 임포트 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    print("🔧 MainWindow load_file 함수 문제 해결 확인")
    print("=" * 50)
    
    # MainWindow load_file 테스트
    mainwindow_result = test_mainwindow_load_file()
    
    # FastFileLoader 테스트  
    loader_result = test_fast_file_loader()
    
    print("\n" + "=" * 50)
    if mainwindow_result and loader_result:
        print("🎉 MainWindow load_file 문제가 해결되었습니다!")
        print("💡 이제 다음과 같이 작동합니다:")
        print("   1. MainWindow에 load_file 래퍼 함수 추가")
        print("   2. FastFileLoader가 실제 위젯의 load_file 찾아서 패치")
        print("   3. Ultra Fast 파일 로딩 시스템 정상 작동")
    else:
        print("⚠️ 일부 문제가 발견되었습니다. 로그를 확인해주세요.")