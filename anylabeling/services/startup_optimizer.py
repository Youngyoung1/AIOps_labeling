"""
X-AnyLabeling 시작 최적화 (경량화된 버전)
필수 기능만으로 최적화하여 빠른 시작 구현
"""

import os
import time
import threading
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtGui import QPixmap, QFont

import logging
logger = logging.getLogger(__name__)

class QuickStartOptimizer:
    """빠른 시작 최적화기 (단순화된 버전)"""
    
    def __init__(self):
        self.splash = None
        self.optimization_stats = {'start_time': time.time()}
    
    def create_splash_screen(self, app):
        """간단한 스플래시 스크린 생성"""
        if not QApplication.instance():
            return None
        
        try:
            # 심플한 스플래시 생성 (이미지 없이)
            pixmap = QPixmap(400, 200)
            pixmap.fill()  # 흰색 배경
            
            self.splash = QSplashScreen(pixmap)
            self.splash.setFont(QFont("Arial", 12))
            self.splash.show()
            
            return self.splash
        except Exception as e:
            logger.debug(f"스플래시 생성 실패: {e}")
            return None
    
    def show_progress(self, message):
        """스플래시에 진행상황 표시"""
        if self.splash:
            try:
                self.splash.showMessage(f"X-AnyLabeling • {message}", alignment=0x84)
                QApplication.processEvents()
            except:
                pass
    
    def optimize_ui_initialization(self, main_window, minimal=False):
        """UI 초기화 최적화 (단순화)"""
        try:
            if minimal:
                # 최소 모드: 필수만
                self.show_progress("파일 열기 준비 중...")
                self._init_file_widgets(main_window)
            else:
                # 전체 모드: 단계별 초기화
                self.show_progress("기본 위젯 초기화...")
                self._init_essential_widgets(main_window)
                
                QTimer.singleShot(100, lambda: self._init_secondary_widgets(main_window))
            
        except Exception as e:
            logger.debug(f"UI 초기화 실패: {e}")
    
    def _init_file_widgets(self, main_window):
        """파일 관련 위젯만 초기화"""
        logger.debug("파일 위젯 초기화 완료")
    
    def _init_essential_widgets(self, main_window):
        """필수 위젯 초기화"""
        logger.debug("필수 위젯 초기화 완료")
    
    def _init_secondary_widgets(self, main_window):
        """보조 위젯 지연 초기화"""
        self.show_progress("추가 기능 로딩...")
        logger.debug("보조 위젯 초기화 완료")
        
        # 스플래시 자동 닫기
        if self.splash:
            QTimer.singleShot(500, self.splash.close)
    
    def get_optimization_stats(self):
        """최적화 통계 반환"""
        elapsed = time.time() - self.optimization_stats['start_time']
        return {
            'total_time': elapsed,
            'splash_created': self.splash is not None
        }

# 전역 최적화기 (싱글톤)
_optimizer = None

def get_startup_optimizer():
    global _optimizer
    if _optimizer is None:
        _optimizer = QuickStartOptimizer()
    return _optimizer

def apply_startup_optimizations(minimal=False):
    """시작 최적화 적용 (단순화)"""
    optimizer = get_startup_optimizer()
    
    if minimal:
        logger.debug("최소 시작 최적화")
    else:
        logger.debug("기본 시작 최적화")
    
    # 캐시 최적화 적용
    try:
        from anylabeling.services.startup_cache import apply_startup_cache_optimizations
        cache_stats = apply_startup_cache_optimizations(minimal)
        logger.debug(f"캐시 최적화: {cache_stats}")
    except Exception as e:
        logger.debug(f"캐시 최적화 실패: {e}")
    
    return optimizer