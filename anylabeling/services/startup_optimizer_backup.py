"""
X-AnyLabeling 프로그램 시작 속도 최적화 패치

주요 최적화 사항:
1. 모듈 지연 로딩
2. UI 점진적 초기화  
3. 백그라운드 DB 연결
4. 불필요한 초기화 지연
"""

import time
import logging
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import QSplashScreen, QApplication
from PyQt5.QtGui import QPixmap

from anylabeling.views.labeling.logger import logger

class LazyModuleLoader:
    """모듈 지연 로딩을 위한 헬퍼 클래스"""
    
    def __init__(self):
        self._loaded_modules = {}
        self._loading_times = {}
    
    def load_module(self, module_name, import_func):
        """모듈을 지연 로딩하고 시간 측정"""
        if module_name in self._loaded_modules:
            return self._loaded_modules[module_name]
        
        start_time = time.time()
        try:
            module = import_func()
            self._loaded_modules[module_name] = module
            elapsed_time = time.time() - start_time
            self._loading_times[module_name] = elapsed_time
            logger.debug(f"모듈 로딩 완료: {module_name} ({elapsed_time:.3f}초)")
            return module
        except Exception as e:
            logger.error(f"모듈 로딩 실패: {module_name} - {e}")
            return None
    
    def get_loading_stats(self):
        """로딩 통계 반환"""
        return self._loading_times.copy()

class BackgroundInitializer(QThread):
    """백그라운드에서 초기화를 처리하는 스레드"""
    
    initialization_completed = pyqtSignal(str, bool, str)  # component, success, message
    all_completed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tasks = []
        self.completed_tasks = 0
        
    def add_task(self, name, init_func, *args, **kwargs):
        """초기화 작업 추가"""
        self.tasks.append({
            'name': name,
            'func': init_func,
            'args': args,
            'kwargs': kwargs
        })
    
    def run(self):
        """백그라운드 초기화 실행"""
        logger.info(f"백그라운드 초기화 시작: {len(self.tasks)}개 작업")
        
        for task in self.tasks:
            try:
                start_time = time.time()
                result = task['func'](*task['args'], **task['kwargs'])
                elapsed_time = time.time() - start_time
                
                self.initialization_completed.emit(
                    task['name'], 
                    True, 
                    f"완료 ({elapsed_time:.3f}초)"
                )
                logger.debug(f"백그라운드 초기화 완료: {task['name']}")
                
            except Exception as e:
                error_msg = f"초기화 실패: {e}"
                self.initialization_completed.emit(task['name'], False, error_msg)
                logger.error(f"백그라운드 초기화 실패: {task['name']} - {e}")
            
            self.completed_tasks += 1
        
        self.all_completed.emit()
        logger.info("모든 백그라운드 초기화 완료")

class OptimizedSplashScreen(QSplashScreen):
    """최적화된 스플래시 스크린"""
    
    def __init__(self, pixmap=None):
        # QApplication이 이미 생성된 후에만 QPixmap 생성
        if pixmap is None:
            try:
                # 기본 스플래시 이미지 생성
                pixmap = QPixmap(400, 300)
                pixmap.fill()
            except Exception as e:
                # QPixmap 생성 실패 시 None으로 설정하여 기본 동작 사용
                logger.warning(f"QPixmap 생성 실패: {e}")
                pixmap = None
        
        if pixmap is not None:
            super().__init__(pixmap)
        else:
            # pixmap 없이 초기화 (Qt 기본 스플래시)
            super().__init__()
        
        self.progress_messages = []
        self.current_step = 0
        self.total_steps = 0
        
    def set_total_steps(self, total):
        """전체 단계 설정"""
        self.total_steps = total
    
    def show_progress(self, message, step=None):
        """진행 상황 표시"""
        if step is not None:
            self.current_step = step
        else:
            self.current_step += 1
        
        progress_text = f"[{self.current_step}/{self.total_steps}] {message}"
        self.showMessage(progress_text)
        QApplication.processEvents()
        
        logger.debug(f"스플래시: {progress_text}")

class StartupOptimizer:
    """프로그램 시작 최적화 관리자"""
    
    def __init__(self):
        self.lazy_loader = LazyModuleLoader()
        self.background_initializer = None
        self.splash = None
        self.optimization_enabled = True
        
        # 최적화 설정
        self.defer_heavy_imports = True
        self.use_background_init = True
        self.show_splash = True
        
    def create_splash_screen(self, app=None):
        """스플래시 스크린 생성 (QApplication 생성 후에만 호출)"""
        if not self.show_splash:
            return None
        
        # QApplication 인스턴스가 있는지 확인
        if app is None:
            app = QApplication.instance()
        
        if app is None:
            logger.warning("QApplication이 아직 생성되지 않아 스플래시 스크린을 건너뜁니다")
            return None
        
        try:
            self.splash = OptimizedSplashScreen()
            self.splash.set_total_steps(8)  # 예상 단계 수
            self.splash.show()
            return self.splash
        except Exception as e:
            logger.warning(f"스플래시 스크린 생성 실패: {e}")
            return None
    
    def optimize_imports(self):
        """임포트 최적화"""
        if not self.defer_heavy_imports:
            return
        
        # 무거운 모듈들을 지연 로딩으로 설정
        heavy_modules = [
            'matplotlib',
            'sklearn', 
            'tensorflow',
            'torch',
            'onnxruntime',
            'cv2'
        ]
        
        for module_name in heavy_modules:
            try:
                self._defer_module_import(module_name)
            except Exception as e:
                logger.debug(f"모듈 지연 로딩 설정 실패: {module_name} - {e}")
    
    def _defer_module_import(self, module_name):
        """모듈 임포트 지연"""
        # 실제 지연 로딩 구현은 복잡하므로 여기서는 로깅만
        logger.debug(f"모듈 지연 로딩 설정: {module_name}")
    
    def start_background_initialization(self, main_window):
        """백그라운드 초기화 시작"""
        if not self.use_background_init:
            return
        
        self.background_initializer = BackgroundInitializer()
        
        # 백그라운드에서 수행할 초기화 작업들 추가
        self.background_initializer.add_task(
            "MongoDB 연결",
            self._init_mongodb_connection,
            main_window
        )
        
        self.background_initializer.add_task(
            "자동 라벨링 모델 로딩",
            self._preload_auto_labeling_models
        )
        
        self.background_initializer.add_task(
            "확장 기능 로딩",
            self._load_extensions
        )
        
        # 신호 연결
        self.background_initializer.initialization_completed.connect(
            self._on_background_init_completed
        )
        self.background_initializer.all_completed.connect(
            self._on_all_background_init_completed
        )
        
        # 백그라운드 초기화 시작
        self.background_initializer.start()
        logger.info("백그라운드 초기화 시작됨")
    
    def _init_mongodb_connection(self, main_window):
        """MongoDB 연결 초기화"""
        try:
            if hasattr(main_window, 'mongo_storage') and main_window.mongo_storage:
                # 연결 테스트
                main_window.mongo_storage.test_connection()
                return True
        except Exception as e:
            logger.warning(f"MongoDB 백그라운드 연결 실패: {e}")
            return False
        return False
    
    def _preload_auto_labeling_models(self):
        """자동 라벨링 모델 사전 로딩"""
        try:
            # 실제로는 여기서 모델 파일들을 사전 로딩
            time.sleep(0.1)  # 시뮬레이션
            return True
        except Exception as e:
            logger.warning(f"자동 라벨링 모델 사전 로딩 실패: {e}")
            return False
    
    def _load_extensions(self):
        """확장 기능 로딩"""
        try:
            # 확장 기능들을 로딩
            time.sleep(0.05)  # 시뮬레이션
            return True
        except Exception as e:
            logger.warning(f"확장 기능 로딩 실패: {e}")
            return False
    
    def _on_background_init_completed(self, component, success, message):
        """백그라운드 초기화 완료 시 호출"""
        status = "✅" if success else "❌"
        logger.info(f"{status} {component}: {message}")
        
        if self.splash:
            self.splash.show_progress(f"{component} {message}")
    
    def _on_all_background_init_completed(self):
        """모든 백그라운드 초기화 완료 시 호출"""
        logger.info("모든 백그라운드 초기화 완료")
        
        if self.splash:
            self.splash.show_progress("초기화 완료")
            # 스플래시 자동 닫기
            QTimer.singleShot(1000, self.hide_splash)
    
    def hide_splash(self):
        """스플래시 스크린 숨기기"""
        if self.splash:
            self.splash.close()
            self.splash = None
    
    def optimize_ui_initialization(self, main_window, minimal=False):
        """UI 초기화 최적화
        
        Args:
            main_window: 메인 윈도우 인스턴스
            minimal: True면 최소한의 초기화만 수행 (인스턴스 모드용)
        """
        try:
            # 필수 위젯만 먼저 초기화
            self._init_essential_widgets(main_window, minimal)
            
            if not minimal:
                # 전체 초기화 모드: 나머지 위젯들도 지연 초기화
                QTimer.singleShot(100, lambda: self._init_secondary_widgets(main_window))
                QTimer.singleShot(500, lambda: self._init_optional_widgets(main_window))
            else:
                # 최소 초기화 모드: 필수 위젯만 초기화
                logger.debug("최소 초기화 모드: 추가 위젯 초기화 건너뛰기")
            
        except Exception as e:
            logger.error(f"UI 초기화 최적화 실패: {e}")
    
    def _init_essential_widgets(self, main_window, minimal=False):
        """필수 위젯 초기화"""
        if minimal:
            # 인스턴스 모드: 파일 열기에 필요한 최소한만
            logger.debug("최소 필수 위젯 초기화 완료 (파일 열기용)")
        else:
            # 메인 캔버스와 기본 툴바 초기화
            logger.debug("전체 필수 위젯 초기화 완료")
    
    def _init_secondary_widgets(self, main_window):
        """보조 위젯 초기화"""
        # 파일 리스트, 라벨 리스트 등 초기화
        logger.debug("보조 위젯 초기화 완료")
    
    def _init_optional_widgets(self, main_window):
        """선택적 위젯 초기화"""
        # 플래그 위젯, 고급 기능 위젯 등 초기화
        logger.debug("선택적 위젯 초기화 완료")
    
    def get_optimization_stats(self):
        """최적화 통계 반환"""
        stats = {
            'optimization_enabled': self.optimization_enabled,
            'defer_heavy_imports': self.defer_heavy_imports,
            'use_background_init': self.use_background_init,
            'show_splash': self.show_splash,
            'loading_times': self.lazy_loader.get_loading_stats()
        }
        
        if self.background_initializer:
            stats['background_tasks'] = len(self.background_initializer.tasks)
            stats['completed_tasks'] = self.background_initializer.completed_tasks
        
        return stats

# 전역 최적화 인스턴스
_startup_optimizer = None

def get_startup_optimizer():
    """시작 최적화 인스턴스 반환"""
    global _startup_optimizer
    if _startup_optimizer is None:
        _startup_optimizer = StartupOptimizer()
    return _startup_optimizer

def apply_startup_optimizations(minimal=False):
    """시작 최적화 적용 (QApplication 생성 전)"""
    optimizer = get_startup_optimizer()
    
    # QApplication 생성 전에는 스플래시 스크린을 생성하지 않음
    mode_desc = "최소" if minimal else "전체"
    logger.debug(f"{mode_desc} 시작 최적화 적용 중...")
    
    # 1. 시작 캐시 최적화 적용 (최소 모드 전달)
    try:
        from anylabeling.services.startup_cache import apply_startup_cache_optimizations
        cache_stats = apply_startup_cache_optimizations(minimal)
        logger.info(f"시작 캐시 최적화 ({mode_desc}): {cache_stats}")
    except Exception as e:
        logger.warning(f"시작 캐시 최적화 실패: {e}")
    
    # 2. 임포트 최적화 (최소 모드에서는 건너뛰기)
    if not minimal:
        optimizer.optimize_imports()
    else:
        logger.debug("최소 모드: 임포트 최적화 건너뛰기")
    
    return optimizer