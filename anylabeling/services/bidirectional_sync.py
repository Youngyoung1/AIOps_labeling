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
    # X-AnyLabeling 하위 폴더는 동기화에서 제외
    # 필요 시 앱 설정으로 이 값을 지정하면 그 경로 이하 파일은 동기화에서 제외됩니다.
    IGNORE_PREFIX = None
    DEFAULT_IGNORE_MONGODB_TO_JSON_BASENAMES = {
        # 특정 파일의 MongoDB → JSON(덮어쓰기) 동기화를 기본적으로 차단
        "20251008093534367_right_img_1.json",
    }
    """양방향 JSON ↔ MongoDB 동기화 서비스"""
    
    # Qt 시그널
    sync_completed = pyqtSignal(str, bool)  # file_path, success
    stats_updated = pyqtSignal(dict)  # statistics
    
    def __init__(self, parent=None):
        super().__init__(parent)

        # IGNORE_PREFIX 기본값 설정
        self.IGNORE_PREFIX = None

        # 동기화 동작 옵션 (config/env로 제어)
        parent_config = getattr(parent, "config", None) if parent is not None else None
        sync_config = {}
        if isinstance(parent_config, dict):
            sync_config = parent_config.get("bidirectional_sync", {}) or {}
        self.enable_json_to_mongodb = bool(
            sync_config.get("enable_json_to_mongodb", True)
        )
        self.enable_mongodb_to_json = bool(
            sync_config.get("enable_mongodb_to_json", True)
        )
        if os.environ.get("XANYLABELING_DISABLE_MONGODB_TO_JSON", "").strip() in (
            "1",
            "true",
            "True",
            "yes",
            "YES",
            "on",
            "ON",
        ):
            self.enable_mongodb_to_json = False

        ignore_from_config = sync_config.get(
            "ignore_mongodb_to_json_basenames", []
        ) or []
        ignore_from_env = os.environ.get(
            "XANYLABELING_IGNORE_MONGODB_TO_JSON_BASENAMES", ""
        ).strip()
        ignore_from_env_list = (
            [part.strip() for part in ignore_from_env.split(",") if part.strip()]
            if ignore_from_env
            else []
        )
        self.ignore_mongodb_to_json_basenames = {
            str(name).strip().lower()
            for name in (
                list(self.DEFAULT_IGNORE_MONGODB_TO_JSON_BASENAMES)
                + list(ignore_from_config)
                + list(ignore_from_env_list)
            )
            if str(name).strip()
        }
        
        # X-AnyLabeling 하위 폴더 동기화 제외 설정
        try:
            # 현재 작업 디렉토리에서 X-AnyLabeling 폴더 찾기
            cwd = os.getcwd()
            # 기본 후보: 현재 작업 디렉토리 바로 아래의 X-AnyLabeling-main
            workspace_path = os.path.join(cwd, "X-AnyLabeling-main")

            # 현재 디렉토리에서 위로 올라가며 X-AnyLabeling-main 폴더 탐색
            probe = os.path.abspath(cwd)
            while True:
                # 현재 노드가 바로 X-AnyLabeling-main 인가?
                if os.path.basename(probe) == "X-AnyLabeling-main":
                    workspace_path = probe
                    break
                # 현재 노드 하위에 있는가?
                candidate = os.path.join(probe, "X-AnyLabeling-main")
                if os.path.isdir(candidate):
                    workspace_path = candidate
                    break
                parent = os.path.dirname(probe)
                if parent == probe:
                    break
                probe = parent

            # 파일 위치 기준으로도 한 번 더 탐색 (앱의 CWD와 파일 위치가 다를 수 있음)
            if not os.path.isdir(workspace_path):
                probe = os.path.dirname(os.path.abspath(__file__))
                while True:
                    if os.path.basename(probe) == "X-AnyLabeling-main":
                        workspace_path = probe
                        break
                    candidate = os.path.join(probe, "X-AnyLabeling-main")
                    if os.path.isdir(candidate):
                        workspace_path = candidate
                        break
                    parent = os.path.dirname(probe)
                    if parent == probe:
                        break
                    probe = parent
            if os.path.exists(workspace_path):
                self.IGNORE_PREFIX = os.path.abspath(workspace_path)
                logger.info(f"🚫 X-AnyLabeling 폴더 동기화 제외: {self.IGNORE_PREFIX}")
            else:
                logger.warning(f"X-AnyLabeling 폴더를 찾을 수 없습니다: {workspace_path}")
        except Exception as e:
            logger.warning(f"X-AnyLabeling 폴더 경로 설정 실패: {e}")
        
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

        # 한 번만 실행되어야 하는 동기화 여부 플래그
        self._startup_sync_done = False
        self._shutdown_sync_done = False
        
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
                'updated_at': 1,
                'flags': 1,
                '_id': 1
            })
            
            for doc in docs:
                doc_id = str(doc['_id'])
                # DB 문서의 기준 시각: updated_at 우선, 없으면 last_modified
                current_modified = doc.get('updated_at') or doc.get('last_modified') or datetime.now()
                json_file_path = doc.get('json_file_path')
                
                # 새 문서이거나 수정된 문서 확인
                if (doc_id not in self.last_mongodb_check or 
                    current_modified > self.last_mongodb_check[doc_id]):
                    
                    # JSON 우선 정책: 파일이 있고 파일이 더 최신이면 JSON→DB, 아니면 DB→JSON
                    try:
                        if json_file_path:
                            abs_path = os.path.abspath(os.fspath(json_file_path))
                        else:
                            abs_path = None
                    except Exception:
                        abs_path = None

                    json_is_newer = False
                    if abs_path and os.path.exists(abs_path):
                        try:
                            file_mtime = datetime.fromtimestamp(os.path.getmtime(abs_path))
                            # 1초 여유를 두고 비교
                            if file_mtime > (current_modified or datetime.min):
                                json_is_newer = True
                        except Exception:
                            pass

                    if json_is_newer:
                        # JSON이 최신이면 DB를 최신 상태로 반영
                        if abs_path and abs_path not in self.syncing_files:
                            self._sync_json_to_mongodb(abs_path)
                    else:
                        # 그 외에는 DB → JSON 반영 (단, 순환 방지)
                        if abs_path not in self.syncing_files:
                            self._sync_mongodb_to_json(doc)
                        
                    self.last_mongodb_check[doc_id] = current_modified
                    
        except Exception as e:
            logger.error(f"❌ MongoDB 폴링 중 오류: {e}")
            self.stats['errors'] += 1
            
    def _sync_json_to_mongodb(self, json_file_path: str):
        """JSON 파일 → MongoDB 동기화"""
        try:
            if not self.enable_json_to_mongodb:
                logger.debug("JSON → MongoDB 동기화 비활성화됨")
                return
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
        if not self.enable_mongodb_to_json:
            logger.debug("MongoDB → JSON 동기화 비활성화됨")
            return
        # MongoDB 문서에서 경로 추출 (None 대비)
        json_file_path = mongodb_doc.get('json_file_path')
        if not json_file_path:
            logger.debug("MongoDB → JSON 동기화 건너뜀: json_file_path가 없음 또는 None")
            return
        try:
            abs_path = os.path.abspath(os.fspath(json_file_path))
        except Exception:
            logger.debug(f"MongoDB → JSON 동기화 건너뜀: 잘못된 경로 형식 ({json_file_path!r})")
            return
        if self.IGNORE_PREFIX and abs_path.startswith(self.IGNORE_PREFIX):
            logger.debug(f"동기화 제외(무시 경로): {abs_path}")
            return
        if os.path.basename(abs_path).strip().lower() in self.ignore_mongodb_to_json_basenames:
            logger.debug(
                f"MongoDB → JSON 동기화 제외(무시 파일): {os.path.basename(abs_path)}"
            )
            return
        if not os.path.exists(abs_path):
            logger.debug(f"MongoDB → JSON 동기화 건너뜀: 파일 없음 ({abs_path})")
            return
        try:
            # 순환 동기화 방지
            self.syncing_files.add(abs_path)
            # JSON 파일 읽기
            with open(abs_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            # MongoDB 데이터로 JSON 업데이트
            mongodb_flags = mongodb_doc.get('flags', {})
            json_data['flags'] = mongodb_flags
            # JSON 파일 쓰기
            with open(abs_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            self.stats['mongodb_to_json'] += 1
            self.stats['last_sync'] = datetime.now().strftime('%H:%M:%S')
            logger.info(f"📥 MongoDB → JSON 동기화: {os.path.basename(abs_path)}")
            self.sync_completed.emit(abs_path, True)
            try:
                self.stats_updated.emit(self.get_stats())
            except Exception:
                pass
        except Exception as e:
            logger.error(f"❌ MongoDB → JSON 동기화 실패: {e}")
            self.stats['errors'] += 1
            self.sync_completed.emit(abs_path if 'abs_path' in locals() else (json_file_path or ''), False)
        finally:
            # 잠시 후 동기화 잠금 해제
            threading.Timer(2.0, lambda: self.syncing_files.discard(abs_path if 'abs_path' in locals() else (json_file_path or ''))).start()
            
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
            json_file_path = doc.get('json_file_path')
            if not json_file_path:
                continue
            try:
                abs_path = os.path.abspath(os.fspath(json_file_path))
            except Exception:
                continue
            if self.IGNORE_PREFIX and abs_path.startswith(self.IGNORE_PREFIX):
                logger.debug(f"manual_sync_all: 동기화 제외(무시 경로): {abs_path}")
                continue
            self._sync_mongodb_to_json(doc)
        logger.info(f"✅ 수동 전체 동기화 완료: JSON {json_count}개, MongoDB {len(mongodb_docs)}개")

    def sync_on_startup_once(self) -> bool:
        """앱 시작 시 한 번만 전체 동기화를 수행"""
        if self._startup_sync_done:
            logger.debug("시작 시 동기화는 이미 수행됨")
            return False
        if not self.annotation_manager:
            logger.error("❌ MongoDB 연결이 없어 시작 시 동기화를 수행하지 않음")
            return False
        self._startup_sync_done = True
        self.manual_sync_all()
        return True

    def sync_on_shutdown_once(self) -> bool:
        """앱 종료 직전에 한 번만 전체 동기화를 수행"""
        if self._shutdown_sync_done:
            logger.debug("종료 직전 동기화는 이미 수행됨")
            return False
        if not self.annotation_manager:
            logger.error("❌ MongoDB 연결이 없어 종료 전 동기화를 수행하지 않음")
            return False
        self._shutdown_sync_done = True
        self.manual_sync_all()
        return True
        
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

    # --- 추가 메서드: 감시 폴더 등록 ---
    def add_watch_directory(self, directory: str):
        """동기화 감시 대상 폴더 추가"""
        try:
            if not directory:
                return False
            directory = os.path.abspath(os.fspath(directory))
            if not os.path.isdir(directory):
                logger.debug(f"감시 폴더 추가 실패 (존재하지 않음): {directory}")
                return False
            if directory in self.watch_directories:
                return True
            self.watch_directories.append(directory)
            try:
                # 서비스가 이미 시작되었으면 즉시 감시 스케줄링
                if getattr(self.observer, 'is_alive', lambda: False)():
                    self.observer.schedule(self.file_handler, directory, recursive=True)
                    logger.info(f"📁 실시간 감시 추가: {directory}")
            except Exception as e:
                logger.debug(f"감시 스케줄 등록 실패: {e}")
            return True
        except Exception as e:
            logger.debug(f"감시 폴더 추가 중 예외: {e}")
            return False

    # --- 공개 메서드: 외부에서 단건 JSON→DB 요청 시 사용 ---
    def sync_json_to_mongodb(self, json_file_path: str) -> bool:
        try:
            self._sync_json_to_mongodb(json_file_path)
            return True
        except Exception as e:
            logger.debug(f"sync_json_to_mongodb 호출 실패: {e}")
            return False

    # --- 과거 호출 호환용 별칭 ---
    def sync_json_to_mongo(self, json_file_path: str) -> bool:
        return self.sync_json_to_mongodb(json_file_path)
