"""
X-AnyLabeling 빠른 시작 캐시 시스템 (최적화된 버전)
필수 모듈과 리소스만 캐싱하여 시작 속도 향상
"""

import os
import sys
import time
import pickle
import threading
from pathlib import Path
from datetime import datetime, timedelta

import logging
logger = logging.getLogger(__name__)

class StartupCache:
    """시작 속도 향상을 위한 경량 캐시 시스템"""
    
    def __init__(self):
        cache_dir = Path.home() / ".xanylabeling_cache"
        cache_dir.mkdir(exist_ok=True)
        
        self.module_cache_file = cache_dir / "modules.pkl"
        self.cache_expiry_hours = 12  # 캐시 만료 시간 단축
        self._memory_cache = {}
    
    def is_cache_valid(self, cache_file):
        """캐시 유효성 빠른 체크"""
        try:
            if not cache_file.exists():
                return False
            
            mtime = cache_file.stat().st_mtime
            age_hours = (time.time() - mtime) / 3600
            return age_hours < self.cache_expiry_hours
        except:
            return False
    
    def load_module_cache(self):
        """모듈 캐시 빠른 로드"""
        if not self.is_cache_valid(self.module_cache_file):
            return None
        
        try:
            with open(self.module_cache_file, 'rb') as f:
                data = pickle.load(f)
                return data.get('modules', {})
        except:
            return None
    
    def save_module_cache(self, modules_info):
        """모듈 캐시 빠른 저장"""
        try:
            with open(self.module_cache_file, 'wb') as f:
                pickle.dump({'modules': modules_info, 'timestamp': time.time()}, f)
        except Exception as e:
            logger.debug(f"캐시 저장 실패: {e}")
    
    def preload_essential_modules(self, minimal=False):
        """필수 모듈만 빠르게 프리로드"""
        if minimal:
            modules = ['json', 'os']  # 절대 최소
        else:
            modules = ['json', 'os', 'sys', 'time', 'pathlib']  # 기본 필수
        
        loaded = {}
        start_time = time.time()
        
        for module in modules:
            try:
                if module not in sys.modules:
                    __import__(module)
                loaded[module] = True
            except:
                loaded[module] = False
        
        elapsed = time.time() - start_time
        logger.debug(f"모듈 프리로드: {elapsed:.3f}초, {len(modules)}개")
        
        self.save_module_cache(loaded)
        return loaded
    
    def optimize_startup(self, minimal=False):
        """빠른 시작 최적화"""
        start_time = time.time()
        optimizations = []
        
        # 1. 캐시된 모듈 확인
        cached = self.load_module_cache()
        if cached:
            optimizations.append("cache_hit")
        else:
            # 백그라운드 프리로드
            threading.Thread(
                target=lambda: self.preload_essential_modules(minimal),
                daemon=True
            ).start()
            optimizations.append("cache_miss")
        
        # 2. 메모리 설정
        if not minimal:
            self._memory_cache['startup_mode'] = 'full'
        else:
            self._memory_cache['startup_mode'] = 'minimal'
        
        elapsed = time.time() - start_time
        return {
            'elapsed_time': elapsed,
            'optimizations': optimizations,
            'minimal_mode': minimal
        }

# 전역 캐시 (싱글톤)
_cache = None

def get_startup_cache():
    global _cache
    if _cache is None:
        _cache = StartupCache()
    return _cache

def apply_startup_cache_optimizations(minimal=False):
    """시작 캐시 최적화 적용 (단순화)"""
    return get_startup_cache().optimize_startup(minimal)

if __name__ == "__main__":
    # 테스트
    cache = StartupCache()
    results = cache.optimize_startup_sequence()
    print(f"최적화 결과: {results}")
    
    # 캐시 상태 확인
    modules = cache.load_module_cache()
    if modules:
        print(f"캐시된 모듈: {len(modules)}개")
        for name, info in modules.items():
            if info.get('loaded'):
                print(f"  ✅ {name}")
            else:
                print(f"  ❌ {name}: {info.get('error', 'Unknown error')}")