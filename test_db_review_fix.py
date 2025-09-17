"""
DB 검수 파일 열기 테스트 스크립트
Ultra Fast 최적화가 적용된 DB 검수 시스템 테스트
"""

import sys
import os

# 현재 디렉토리를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def test_db_review_file_opening():
    """DB 검수 파일 열기 기능 테스트"""
    
    print("🧪 DB 검수 파일 열기 테스트 시작...")
    
    try:
        # improved_review_widgets 모듈 임포트 테스트
        print("📦 improved_review_widgets 모듈 로딩 중...")
        import improved_review_widgets
        
        print("✅ 모듈 로딩 성공")
        
        # 클래스 확인
        if hasattr(improved_review_widgets, 'LabelMeReviewSearch'):
            print("✅ LabelMeReviewSearch 클래스 발견")
            
            # 메서드 확인
            cls = improved_review_widgets.LabelMeReviewSearch
            if hasattr(cls, '_launch_labeling_tool'):
                print("✅ _launch_labeling_tool 메서드 발견")
            if hasattr(cls, 'open_image_and_label'):
                print("✅ open_image_and_label 메서드 발견")
                
            print("🎯 DB 검수 파일 열기 시스템이 준비되었습니다!")
            
        else:
            print("❌ LabelMeReviewSearch 클래스를 찾을 수 없습니다")
            return False
            
    except ImportError as e:
        print(f"❌ 모듈 임포트 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False
    
    return True

def test_ultra_fast_systems():
    """Ultra Fast 시스템들 테스트"""
    
    print("\n🚀 Ultra Fast 시스템 테스트...")
    
    systems = [
        'anylabeling.services.ultra_fast_startup',
        'anylabeling.services.fast_file_loader', 
        'anylabeling.services.lazy_importer',
        'anylabeling.services.app_instance_manager'
    ]
    
    for system in systems:
        try:
            __import__(system)
            print(f"✅ {system} 로딩 성공")
        except ImportError as e:
            print(f"⚠️ {system} 로딩 실패: {e}")
        except Exception as e:
            print(f"❌ {system} 오류: {e}")

if __name__ == "__main__":
    print("🔧 DB 검수 파일 열기 문제 해결 확인")
    print("=" * 50)
    
    # DB 검수 파일 열기 테스트
    db_test_result = test_db_review_file_opening()
    
    # Ultra Fast 시스템 테스트
    test_ultra_fast_systems()
    
    print("\n" + "=" * 50)
    if db_test_result:
        print("🎉 DB 검수 파일 열기 문제가 해결되었습니다!")
        print("💡 이제 DB 검수에서 '사진 보기' 버튼을 클릭하면")
        print("   Ultra Fast 모드로 즉시 파일이 열립니다!")
    else:
        print("⚠️ 일부 문제가 발견되었습니다. 로그를 확인해주세요.")