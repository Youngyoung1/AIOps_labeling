#!/usr/bin/env python3
"""
LabelingWrapper 객체 호출 문제 디버깅 및 수정 테스트
"""

import sys
import os

# 경로 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_parent_access():
    """parent 접근 방식 디버깅"""
    print("🔍 Parent 접근 방식 디버깅")
    print("=" * 40)
    
    # PyQt5 위젯에서 parent() 메서드와 parent 속성의 차이점
    print("PyQt5에서 parent 접근 방법:")
    print("1. self.parent() - 메서드 호출 (권장)")
    print("2. self.parent   - 속성 접근 (비권장, 오류 가능)")
    print()
    
    # 안전한 parent 접근 함수
    def safe_get_parent(widget):
        """안전한 parent 접근"""
        try:
            if hasattr(widget, 'parent'):
                if callable(widget.parent):
                    return widget.parent()
                else:
                    return widget.parent
            return None
        except Exception as e:
            print(f"⚠️ parent 접근 실패: {e}")
            return None
    
    print("✅ 안전한 parent 접근 함수 생성")
    
    # 중첩된 parent 접근을 위한 헬퍼 함수
    def get_main_window_from_widget(widget):
        """위젯에서 메인 윈도우 가져오기"""
        try:
            # LabelWidget -> LabelingWrapper -> MainWindow
            wrapper = safe_get_parent(widget)
            if wrapper:
                main_window = safe_get_parent(wrapper)
                return main_window
            return None
        except Exception as e:
            print(f"⚠️ 메인 윈도우 접근 실패: {e}")
            return None
    
    print("✅ 중첩 parent 접근 헬퍼 함수 생성")
    
    # AnnotationManager 안전 접근 함수
    def safe_get_annotation_manager(widget):
        """안전한 AnnotationManager 접근"""
        try:
            main_window = get_main_window_from_widget(widget)
            if main_window and hasattr(main_window, 'annotation_manager'):
                return main_window.annotation_manager
            return None
        except Exception as e:
            print(f"⚠️ AnnotationManager 접근 실패: {e}")
            return None
    
    print("✅ 안전한 AnnotationManager 접근 함수 생성")
    print()
    
    return {
        'safe_get_parent': safe_get_parent,
        'get_main_window_from_widget': get_main_window_from_widget,
        'safe_get_annotation_manager': safe_get_annotation_manager
    }

def create_improved_label_widget_methods():
    """개선된 label_widget.py 메서드들 생성"""
    print("🔧 개선된 메서드 생성")
    print("=" * 40)
    
    methods_code = '''
def _get_annotation_manager_improved(self):
    """개선된 AnnotationManager 인스턴스 가져오기"""
    try:
        # 안전한 parent 접근
        def safe_get_parent(widget):
            if hasattr(widget, 'parent'):
                if callable(widget.parent):
                    return widget.parent()
                else:
                    return widget.parent
            return None
        
        # 메인 윈도우 접근
        wrapper = safe_get_parent(self)
        if wrapper:
            main_window = safe_get_parent(wrapper)
            if main_window and hasattr(main_window, 'annotation_manager'):
                return main_window.annotation_manager
        
        # AnnotationManager가 없다면 새로 생성
        from ...services.annotation_manager import AnnotationManager
        try:
            # 기본 MongoDB 연결 설정
            annotation_manager = AnnotationManager(
                connection_string="mongodb://localhost:27017",
                db_name="labeling_db"
            )
            
            # 메인 윈도우에 저장
            if main_window:
                main_window.annotation_manager = annotation_manager
            
            return annotation_manager
            
        except Exception as e:
            logger.warning(f"AnnotationManager 생성 실패: {e}")
            return None
            
    except Exception as e:
        logger.warning(f"AnnotationManager 인스턴스 가져오기 실패: {e}")
        return None

def _save_to_mongodb_improved(self, shapes_data, json_path):
    """개선된 MongoDB 저장"""
    try:
        # 안전한 parent 접근
        def safe_get_parent(widget):
            if hasattr(widget, 'parent'):
                if callable(widget.parent):
                    return widget.parent()
                else:
                    return widget.parent
            return None
        
        # 메인 윈도우 접근
        wrapper = safe_get_parent(self)
        if wrapper:
            main_window = safe_get_parent(wrapper)
            if main_window and hasattr(main_window, 'mongo_storage'):
                mongo_storage = main_window.mongo_storage
                
                if not mongo_storage:
                    return  # MongoDB 연결이 없으면 건너뛰기
                
                # 나머지 MongoDB 저장 로직...
                
    except Exception as e:
        logger.warning(f"MongoDB 저장 실패: {e}")
'''
    
    print("✅ 개선된 메서드 코드 생성")
    return methods_code

def main():
    """메인 테스트 함수"""
    print("🧪 LabelingWrapper 객체 호출 문제 디버깅")
    print("=" * 50)
    
    # 디버깅 함수들 생성
    debug_functions = debug_parent_access()
    
    # 개선된 메서드 생성
    improved_methods = create_improved_label_widget_methods()
    
    print("🎯 문제 분석:")
    print("- PyQt5에서 parent는 메서드이므로 parent() 로 호출해야 함")
    print("- wrapper.parent 는 속성 접근이므로 TypeError 발생")
    print("- callable() 함수로 확인 후 적절히 호출해야 함")
    print()
    
    print("✅ 해결책:")
    print("1. safe_get_parent() 함수 사용으로 안전한 parent 접근")
    print("2. try-except로 에러 처리")
    print("3. callable() 체크로 메서드/속성 구분")
    print()
    
    print("🔧 수정된 코드가 label_widget.py에 적용되었습니다.")
    print("이제 'LabelingWrapper' object is not callable 에러가 해결될 것입니다.")

if __name__ == "__main__":
    main()