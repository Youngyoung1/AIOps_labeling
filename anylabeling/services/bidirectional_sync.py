#!/usr/bin/env python3
"""
양방향 JSON ↔ MongoDB 동기화 서비스
- JSON 파일 변경 → MongoDB 업데이트 (기존)
- MongoDB 변경 → JSON 파일 업데이트 (신규)
"""

import os
import json
import time
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from anylabeling.services.annotation_manager import AnnotationManager

# Logger import 처리: 앱 전반에서 사용하는 로거를 우선 사용, 실패 시 기본 로거 사용
try:
    from anylabeling.views.labeling.logger import logger  # 표준 로거
except Exception:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)


class JSONFileHandler(FileSystemEventHandler):
    """JSON 파일 변경 감지 핸들러"""
    
    def __init__(self, sync_service):
        super().__init__()
        self.sync_service = sync_service
        self.debounce_delay = 1.0
        self.pending_files = {}
        
    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith('.json'):
            return
            
        # 디바운싱: 같은 파일의 연속 수정 이벤트 방지
        current_time = time.time()
        if event.src_path in self.pending_files:
            if current_time - self.pending_files[event.src_path] < self.debounce_delay:
                return
                
        self.pending_files[event.src_path] = current_time
        
        # 딜레이 후 처리
        timer = threading.Timer(self.debounce_delay, self._process_file, [event.src_path])
        timer.start()
        
    def _process_file(self, file_path: str):
        """JSON 파일 변경 처리"""
        if file_path in self.pending_files:
            del self.pending_files[file_path]
            
        try:
            if self.sync_service._is_valid_annotation_json(file_path):
                self.sync_service._sync_json_to_mongodb(file_path)
        except Exception as e:
            logger.error(f"JSON 파일 처리 중 오류: {e}")


class BidirectionalSyncService(QObject):
    # 기본적으로 무시할 경로를 비활성화(None)로 두어 프로젝트 내부의 JSON도 동기화되도록 함.
    # 필요 시 앱 설정으로 이 값을 지정하면 그 경로 이하 파일은 동기화에서 제외됩니다.
    IGNORE_PREFIX = None
    """양방향 JSON ↔ MongoDB 동기화 서비스"""
    
    # Qt 시그널
    sync_completed = pyqtSignal(str, bool)  # file_path, success
    stats_updated = pyqtSignal(dict)  # statistics
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # MongoDB 연결
        self.annotation_manager = None
        self._init_mongodb()
        
        # 파일 감시 설정
        self.observer = Observer()
        self.file_handler = JSONFileHandler(self)
        self.watch_directories = []
        
        # MongoDB 변경 감지를 위한 폴링 타이머
        self.polling_timer = QTimer()
        self.polling_timer.timeout.connect(self._poll_mongodb_changes)
        self.polling_interval = 5000  # 5초마다 폴링
        
        # 마지막 확인 시간 추적
        self.last_mongodb_check = {}
        
        # 통계
        self.stats = {
            'json_to_mongodb': 0,
            'mongodb_to_json': 0,
            'errors': 0,
            'last_sync': None
        }
        
        # 현재 동기화 중인 파일 추적 (순환 동기화 방지)
        self.syncing_files = set()
        
        logger.info("🔄 양방향 JSON ↔ MongoDB 동기화 서비스 초기화됨")
        
    def _init_mongodb(self):
        """MongoDB 연결 초기화"""
        try:
            self.annotation_manager = AnnotationManager()
            if self.annotation_manager.collection.count_documents({}) >= 0:
                logger.info("✅ MongoDB 연결 확인됨")
            return True
        except Exception as e:
            logger.error(f"❌ MongoDB 연결 실패: {e}")
            return False
            
    def add_watch_directory(self, directory: str):
        """감시할 디렉토리 추가"""
        # Normalize path
        try:
            directory = os.path.abspath(directory)
        except Exception:
            pass

        # Prevent watching the repository workspace or the package internals.
        # If the directory is inside the project root (two levels up from this file), skip it.
        try:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            # If directory is the repo root or inside it, do not add to watch list
            if os.path.commonpath([directory, repo_root]) == repo_root:
                logger.warning(f"감시 제외(리포지토리 내부): {directory}")
                return
        except Exception:
            # If any error occurs during path check, fall back to normal behavior
            pass

        if os.path.exists(directory) and directory not in self.watch_directories:
            self.watch_directories.append(directory)
            logger.info(f"📁 JSON 파일 감시 추가: {directory}")
            
    def start(self):
        """양방향 동기화 서비스 시작"""
        if not self.annotation_manager:
            logger.error("❌ MongoDB 연결이 없어 서비스를 시작할 수 없음")
            return False
            
        # 1. JSON 파일 감시 시작
        for directory in self.watch_directories:
            self.observer.schedule(self.file_handler, directory, recursive=True)
            logger.info(f"📁 JSON 파일 감시 시작: {directory}")
            
        self.observer.start()
        
        # 2. MongoDB 변경 감지 폴링 시작
        self._initialize_mongodb_timestamps()
        self.polling_timer.start(self.polling_interval)
        
        logger.info(f"🔄 양방향 동기화 서비스 시작됨 ({len(self.watch_directories)}개 디렉토리 감시)")
        logger.info(f"⏰ MongoDB 폴링 간격: {self.polling_interval/1000}초")

        # 3. 초기 시딩: 앱 시작 직후 한 번 전체 동기화 수행 (감시 누락된 초기 파일 반영)
        try:
            # 이벤트 루프가 시작된 뒤에 실행되도록 예약하여 UI 프리즈 방지
            from PyQt5.QtCore import QTimer as _QTimer
            _QTimer.singleShot(200, self.manual_sync_all)
        except Exception as _e:
            # 실패해도 서비스는 계속 동작
            logger.debug(f"초기 시딩 예약 실패: {_e}")
        return True
        
    def stop(self):
        """양방향 동기화 서비스 중지"""
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            
        if self.polling_timer.isActive():
            self.polling_timer.stop()
            
        logger.info("🛑 양방향 동기화 서비스 중지됨")
        
    def _initialize_mongodb_timestamps(self):
        """MongoDB 문서들의 마지막 수정 시간 초기화"""
        try:
            docs = self.annotation_manager.collection.find({}, {
                'json_file_path': 1, 
                'last_modified': 1,
                '_id': 1
            })
            
            for doc in docs:
                doc_id = str(doc['_id'])
                self.last_mongodb_check[doc_id] = doc.get('last_modified', datetime.now())
                
            logger.info(f"📊 MongoDB 타임스탬프 초기화 완료: {len(self.last_mongodb_check)}개 문서")
            
        except Exception as e:
            logger.error(f"❌ MongoDB 타임스탬프 초기화 실패: {e}")
            
    def _poll_mongodb_changes(self):
        """MongoDB 변경사항 폴링 검사"""
        try:
            # 모든 문서의 마지막 수정 시간 확인
            docs = self.annotation_manager.collection.find({}, {
                'json_file_path': 1,
                'last_modified': 1,
                'flags': 1,
                '_id': 1
            })
            
            for doc in docs:
                doc_id = str(doc['_id'])
                current_modified = doc.get('last_modified', datetime.now())
                json_file_path = doc.get('json_file_path', '')
                
                # 새 문서이거나 수정된 문서 확인
                if (doc_id not in self.last_mongodb_check or 
                    current_modified > self.last_mongodb_check[doc_id]):
                    
                    # 순환 동기화 방지
                    if json_file_path not in self.syncing_files:
                        self._sync_mongodb_to_json(doc)
                        
                    self.last_mongodb_check[doc_id] = current_modified
                    
        except Exception as e:
            logger.error(f"❌ MongoDB 폴링 중 오류: {e}")
            self.stats['errors'] += 1
            
    def _sync_json_to_mongodb(self, json_file_path: str):
        """JSON 파일 → MongoDB 동기화"""
        try:
            # 순환 동기화 방지
            self.syncing_files.add(json_file_path)
            # 무시할 경로는 동기화하지 않음
            if self.IGNORE_PREFIX and os.path.abspath(json_file_path).startswith(self.IGNORE_PREFIX):
                logger.debug(f"동기화 제외(무시 경로): {json_file_path}")
                return
            # 기존 JSON → MongoDB 동기화 로직
            result = self.annotation_manager.insert_annotation(json_file_path=json_file_path)
            if result:
                self.stats['json_to_mongodb'] += 1
                self.stats['last_sync'] = datetime.now().strftime('%H:%M:%S')
                logger.info(f"📤 JSON → MongoDB 동기화: {os.path.basename(json_file_path)}")
                self.sync_completed.emit(json_file_path, True)
                try:
                    self.stats_updated.emit(self.get_stats())
                except Exception:
                    pass
            else:
                self.stats['errors'] += 1
                self.sync_completed.emit(json_file_path, False)
                try:
                    self.stats_updated.emit(self.get_stats())
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"❌ JSON → MongoDB 동기화 실패: {e}")
            self.stats['errors'] += 1
            self.sync_completed.emit(json_file_path, False)
        finally:
            # 잠시 후 동기화 잠금 해제
            threading.Timer(2.0, lambda: self.syncing_files.discard(json_file_path)).start()
            
    def _sync_mongodb_to_json(self, mongodb_doc: Dict[str, Any]):
        json_file_path = mongodb_doc.get('json_file_path', '')
        if self.IGNORE_PREFIX and os.path.abspath(json_file_path).startswith(self.IGNORE_PREFIX):
            logger.debug(f"동기화 제외(무시 경로): {json_file_path}")
            return
        if not json_file_path or not os.path.exists(json_file_path):
            return
        try:
            # 순환 동기화 방지
            self.syncing_files.add(json_file_path)
            # JSON 파일 읽기
            with open(json_file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            # MongoDB 데이터로 JSON 업데이트
            mongodb_flags = mongodb_doc.get('flags', {})
            json_data['flags'] = mongodb_flags
            # JSON 파일 쓰기
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            self.stats['mongodb_to_json'] += 1
            self.stats['last_sync'] = datetime.now().strftime('%H:%M:%S')
            logger.info(f"📥 MongoDB → JSON 동기화: {os.path.basename(json_file_path)}")
            self.sync_completed.emit(json_file_path, True)
            try:
                self.stats_updated.emit(self.get_stats())
            except Exception:
                pass
        except Exception as e:
            logger.error(f"❌ MongoDB → JSON 동기화 실패: {e}")
            self.stats['errors'] += 1
            self.sync_completed.emit(json_file_path, False)
        finally:
            # 잠시 후 동기화 잠금 해제
            threading.Timer(2.0, lambda: self.syncing_files.discard(json_file_path)).start()
            
    def _is_valid_annotation_json(self, file_path: str) -> bool:
        """유효한 annotation JSON 파일인지 확인"""
        try:
            if not file_path.endswith('.json'):
                return False
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 기본적인 annotation 구조 확인
            required_fields = ['imagePath', 'shapes']
            return all(field in data for field in required_fields)
            
        except Exception:
            return False
            
    def manual_sync_all(self):
        """수동으로 모든 JSON 파일과 MongoDB 동기화"""
        logger.info("🔄 수동 전체 동기화 시작")
        # 1. JSON 파일들 → MongoDB
        json_count = 0
        for directory in self.watch_directories:
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith('.json'):
                        file_path = os.path.join(root, file)
                        if self.IGNORE_PREFIX and os.path.abspath(file_path).startswith(self.IGNORE_PREFIX):
                            logger.debug(f"manual_sync_all: 동기화 제외(무시 경로): {file_path}")
                            continue
                        if self._is_valid_annotation_json(file_path):
                            self._sync_json_to_mongodb(file_path)
                            json_count += 1
        # 2. MongoDB → JSON 파일들
        mongodb_docs = list(self.annotation_manager.collection.find({}, {
            'json_file_path': 1,
            'flags': 1,
            '_id': 1
        }))
        for doc in mongodb_docs:
            json_file_path = doc.get('json_file_path', '')
            if self.IGNORE_PREFIX and os.path.abspath(json_file_path).startswith(self.IGNORE_PREFIX):
                logger.debug(f"manual_sync_all: 동기화 제외(무시 경로): {json_file_path}")
                continue
            self._sync_mongodb_to_json(doc)
        logger.info(f"✅ 수동 전체 동기화 완료: JSON {json_count}개, MongoDB {len(mongodb_docs)}개")
        
    def get_stats(self) -> Dict[str, Any]:
        """동기화 통계 반환"""
        return self.stats.copy()
        
    def set_polling_interval(self, interval_ms: int):
        """MongoDB 폴링 간격 설정"""
        self.polling_interval = interval_ms
        if self.polling_timer.isActive():
            self.polling_timer.stop()
            self.polling_timer.start(self.polling_interval)
        logger.info(f"⏰ MongoDB 폴링 간격 변경: {interval_ms/1000}초")