"""
빠른 파일 열기 디버깅 및 최적화
파일이 열리지 않는 문제 해결
"""

import os
import logging
from PyQt5 import QtCore, QtGui

logger = logging.getLogger(__name__)

class FastFileLoader:
    """빠른 파일 로더"""
    
    def __init__(self):
        self.supported_formats = [
            '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'
        ]
        logger.debug("FastFileLoader 초기화 완료")
    
    def can_load_file(self, filename):
        """파일이 로드 가능한지 빠른 확인"""
        if not filename or not os.path.exists(filename):
            logger.error(f"파일이 존재하지 않음: {filename}")
            return False
        
        ext = os.path.splitext(filename)[1].lower()
        if ext not in self.supported_formats:
            logger.error(f"지원하지 않는 파일 형식: {ext}")
            return False
        
        return True
    
    def quick_load_image(self, filename):
        """빠른 이미지 로딩"""
        try:
            # 1. 파일 존재 확인
            if not self.can_load_file(filename):
                return None
            
            # 2. 파일 크기 확인 (너무 크면 스킵)
            file_size = os.path.getsize(filename)
            if file_size > 100 * 1024 * 1024:  # 100MB 제한
                logger.warning(f"파일이 너무 큼: {file_size / 1024 / 1024:.1f}MB")
                return None
            
            # 3. 빠른 이미지 로딩
            logger.debug(f"이미지 로딩 시작: {filename}")
            
            # 직접 QImage로 로딩 (더 빠름)
            image = QtGui.QImage(filename)
            
            if image.isNull():
                logger.error(f"QImage 로딩 실패: {filename}")
                return None
            
            logger.debug(f"이미지 로딩 성공: {image.width()}x{image.height()}")
            return image
            
        except Exception as e:
            logger.error(f"이미지 로딩 중 오류: {e}")
            return None
    
    def patch_main_window_load_file(self, main_window):
        """MainWindow의 load_file 함수를 빠른 버전으로 패치 (개선된 버전)"""
        
        # 중복 패치 방지 - 이미 패치되었는지 확인
        if hasattr(main_window, '_fast_file_loader_patched'):
            logger.debug("이미 패치된 MainWindow - 건너뜀")
            return
        
        # 실제 load_file 함수를 찾기
        actual_load_file = None
        
        # 1. MainWindow 자체에 load_file이 있는지 확인
        if hasattr(main_window, 'load_file'):
            actual_load_file = main_window.load_file
            logger.info("MainWindow에서 load_file 발견")
        
        # 2. labeling_widget에서 찾기
        elif hasattr(main_window, 'labeling_widget'):
            if hasattr(main_window.labeling_widget, 'load_file'):
                actual_load_file = main_window.labeling_widget.load_file
                logger.info("labeling_widget에서 load_file 발견")
            elif hasattr(main_window.labeling_widget, 'widget') and hasattr(main_window.labeling_widget.widget, 'load_file'):
                actual_load_file = main_window.labeling_widget.widget.load_file
                logger.info("labeling_widget.widget에서 load_file 발견")
        
        if not actual_load_file:
            logger.warning("load_file 함수를 찾을 수 없음, 패치 건너뜀")
            return
        
        def fast_load_file(filename=None):
            """빠른 파일 로딩 버전"""
            if not filename:
                logger.warning("파일명이 없음")
                return False
            
            logger.info(f"🚀 빠른 파일 로딩: {filename}")
            
            # 1. 빠른 이미지 로딩
            image = self.quick_load_image(filename)
            if image is None:
                # 실패 시 원본 함수 호출
                logger.info("빠른 로딩 실패, 원본 함수 사용")
                return actual_load_file(filename)
            
            # 2. 실제 위젯 찾기
            target_widget = main_window
            if hasattr(main_window, 'labeling_widget'):
                if hasattr(main_window.labeling_widget, 'widget'):
                    target_widget = main_window.labeling_widget.widget
                else:
                    target_widget = main_window.labeling_widget
            
            # 3. 필수 속성 설정
            if hasattr(target_widget, 'image'):
                target_widget.image = image
            if hasattr(target_widget, 'filename'):
                target_widget.filename = filename
            
            # 4. 캔버스에 표시
            try:
                pixmap = QtGui.QPixmap.fromImage(image)
                canvas = getattr(target_widget, 'canvas', None)
                
                if canvas:
                    canvas.load_pixmap(pixmap)
                    canvas.setEnabled(True)
                    logger.info("✅ 캔버스 로딩 완료")
                else:
                    logger.warning("캔버스를 찾을 수 없음")
            except Exception as e:
                logger.error(f"캔버스 로딩 실패: {e}")
            
            # 5. 상태 업데이트
            try:
                if hasattr(target_widget, 'status'):
                    target_widget.status(f"Loaded {os.path.basename(filename)}")
                if hasattr(target_widget, 'toggle_actions'):
                    target_widget.toggle_actions(True)
                
                logger.info("✅ 상태 업데이트 완료")
            except Exception as e:
                logger.error(f"상태 업데이트 실패: {e}")
            
            logger.info(f"✅ 빠른 파일 로딩 완료: {filename}")
            return True
        
        # MainWindow의 load_file 함수 패치
        main_window.load_file = fast_load_file
        logger.info("MainWindow.load_file 함수 패치 완료")
        
        # 패치 완료 플래그 설정
        main_window._fast_file_loader_patched = True

# 전역 로더
_fast_loader = None

def get_fast_file_loader():
    """빠른 파일 로더 가져오기"""
    global _fast_loader
    if _fast_loader is None:
        _fast_loader = FastFileLoader()
    return _fast_loader

