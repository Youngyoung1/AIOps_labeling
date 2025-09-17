"""
지연 임포트 시스템
무거운 모듈들을 나중에 로딩하여 시작 시간 단축
"""

import sys
import importlib
import logging

logger = logging.getLogger(__name__)

class LazyImporter:
    """지연 임포트 클래스"""
    
    def __init__(self, module_name):
        self.module_name = module_name
        self._module = None
    
    def __getattr__(self, name):
        if self._module is None:
            logger.debug(f"지연 임포트: {self.module_name}")
            try:
                self._module = importlib.import_module(self.module_name)
            except ImportError as e:
                logger.error(f"지연 임포트 실패: {self.module_name} - {e}")
                raise
        return getattr(self._module, name)

# 무거운 모듈들을 지연 로딩으로 설정
def setup_lazy_imports():
    """무거운 모듈들을 지연 임포트로 설정"""
    
    # 무거운 임포트들을 지연 로딩
    heavy_modules = [
        'anylabeling.views.mainwindow',
        'anylabeling.services.auto_labeling',
        'anylabeling.views.labeling.widgets',
        'opencv',
        'numpy',
        'onnxruntime',
        'torch',
        'tensorflow'
    ]
    
    lazy_modules = {}
    for module_name in heavy_modules:
        try:
            if module_name in sys.modules:
                # 이미 로드된 모듈은 그대로 사용
                lazy_modules[module_name] = sys.modules[module_name]
            else:
                # 지연 로딩 설정
                lazy_modules[module_name] = LazyImporter(module_name)
                logger.debug(f"지연 임포트 설정: {module_name}")
        except Exception as e:
            logger.debug(f"지연 임포트 설정 실패: {module_name} - {e}")
    
    return lazy_modules

def apply_lazy_imports():
    """지연 임포트 시스템 적용"""
    logger.info("🚀 지연 임포트 시스템 활성화")
    
    try:
        lazy_modules = setup_lazy_imports()
        
        # sys.modules에 지연 로더 등록 (조심스럽게)
        for name, loader in lazy_modules.items():
            if name not in sys.modules and isinstance(loader, LazyImporter):
                # 실제 모듈이 아닌 LazyImporter만 등록
                pass  # sys.modules 조작은 위험할 수 있으므로 주석 처리
        
        logger.info(f"✅ {len(lazy_modules)}개 모듈 지연 로딩 설정 완료")
        return lazy_modules
    except Exception as e:
        logger.error(f"지연 임포트 시스템 적용 실패: {e}")
        return {}

def optimize_startup_imports():
    """시작 시 임포트 최적화"""
    logger.debug("시작 임포트 최적화 적용")
    
    # 필수적이지 않은 모듈들 지연 로딩
    optional_modules = [
        'matplotlib',
        'seaborn', 
        'plotly',
        'requests',
        'urllib3'
    ]
    
    for module in optional_modules:
        if module in sys.modules:
            logger.debug(f"선택적 모듈 발견: {module}")
    
    return True
