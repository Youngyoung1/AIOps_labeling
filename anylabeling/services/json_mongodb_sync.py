#!/usr/bin/env python3
"""
JSON → MongoDB 자동 동기화 서비스
labeling app에서 JSON 파일이 변경되면 자동으로 MongoDB에 반영하는 서비스
"""

import os
import json
import time
import threading
from datetime import datetime
from typing import Dict, Set, Optional
from pathlib import Path

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from anylabeling.views.labeling.logger import logger


class JSONFileHandler(FileSystemEventHandler):
    """JSON 파일 변경 감지 핸들러"""
    
    def __init__(self, sync_service):
        super().__init__()
        self.sync_service = sync_service
        
        # 중복 처리 방지
        self._processing_files: Set[str] = set()
        self._debounce_delay = 1.0  # 1초 디바운스
        self._timers: Dict[str, QTimer] = {}
    
    def on_modified(self, event):
        """파일 수정 시 호출"""
        if event.is_directory:
            return
        
        if event.src_path.endswith('.json'):
            self._schedule_sync(event.src_path)
    
    def on_created(self, event):
        """파일 생성 시 호출"""
        if event.is_directory:
            return
        
        if event.src_path.endswith('.json'):
            self._schedule_sync(event.src_path)
    
    def _schedule_sync(self, json_path: str):
        """동기화 스케줄링 (디바운스)"""
        try:
            # 이전 타이머가 있으면 취소
            if json_path in self._timers:
                self._timers[json_path].stop()
                self._timers[json_path].deleteLater()
            
            # 새 타이머 생성
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: self._sync_file(json_path))
            timer.start(int(self._debounce_delay * 1000))  # 밀리초 단위
            
            self._timers[json_path] = timer
            
        except Exception as e:
            logger.debug(f"동기화 스케줄링 오류 ({json_path}): {e}")
    
    def _sync_file(self, json_path: str):
        """실제 파일 동기화 실행"""
        try:
            # 타이머 정리
            if json_path in self._timers:
                self._timers[json_path].deleteLater()
                del self._timers[json_path]
            
            # 중복 처리 방지
            if json_path in self._processing_files:
                return
            
            self._processing_files.add(json_path)
            
            try:
                # 동기화 서비스에 요청
                self.sync_service.sync_json_to_mongodb(json_path)
                
            finally:
                self._processing_files.discard(json_path)
                
        except Exception as e:
            logger.warning(f"JSON 파일 동기화 실패 ({json_path}): {e}")
            self._processing_files.discard(json_path)


class JSONMongoDBSyncService(QObject):
    """JSON → MongoDB 자동 동기화 서비스"""
    
    # 동기화 완료 시그널
    syncCompleted = pyqtSignal(str, bool)  # (file_path, success)
    
    def __init__(self, main_window, watch_directories=None):
        """
        Args:
            main_window: MainWindow 인스턴스 (MongoDB 연결 포함)
            watch_directories: 감시할 디렉토리 목록 (None이면 자동 감지)
        """
        super().__init__()
        self.main_window = main_window
        self.watch_directories = watch_directories or []
        
        # 파일 감시
        self.observer = Observer()
        self.handler = JSONFileHandler(self)
        self.is_running = False
        
        # MongoDB 연결 확인
        self.annotation_manager = None
        self._check_mongodb_connection()
        
        # 통계
        self._sync_count = 0
        self._success_count = 0
        self._error_count = 0
        
        logger.info("🔄 JSON → MongoDB 동기화 서비스 초기화됨")
    
    def _check_mongodb_connection(self):
        """MongoDB 연결 확인 및 AnnotationManager 설정"""
        try:
            # MainWindow에서 AnnotationManager 가져오기
            if hasattr(self.main_window, 'annotation_manager'):
                self.annotation_manager = self.main_window.annotation_manager
            
            # 없으면 새로 생성
            if not self.annotation_manager:
                from anylabeling.services.annotation_manager import AnnotationManager
                self.annotation_manager = AnnotationManager()
            
            logger.info("✅ MongoDB 연결 확인됨")
            
        except Exception as e:
            logger.warning(f"MongoDB 연결 확인 실패: {e}")
            self.annotation_manager = None
    
    def _detect_watch_directories(self):
        """자동으로 감시할 디렉토리 감지"""
        directories = set()
        
        try:
            # LabelingWidget에서 현재 작업 디렉토리 가져오기
            if hasattr(self.main_window, 'labeling_widget'):
                widget = self.main_window.labeling_widget
                
                # 현재 이미지 경로의 디렉토리
                if hasattr(widget, 'image_path') and widget.image_path:
                    image_dir = os.path.dirname(widget.image_path)
                    directories.add(image_dir)
                
                # 출력 디렉토리
                if hasattr(widget, 'output_dir') and widget.output_dir:
                    directories.add(widget.output_dir)
                
                # 파일 목록의 디렉토리들
                if hasattr(widget, 'image_list') and widget.image_list:
                    for image_path in widget.image_list:
                        image_dir = os.path.dirname(image_path)
                        directories.add(image_dir)
            
            # 기본 감시 디렉토리 추가
            default_dirs = [
                r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file",
                os.getcwd()
            ]
            
            for dir_path in default_dirs:
                if os.path.exists(dir_path):
                    directories.add(dir_path)
            
        except Exception as e:
            logger.debug(f"감시 디렉토리 자동 감지 오류: {e}")
        
        return list(directories)
    
    def start(self):
        """동기화 서비스 시작"""
        if self.is_running:
            return
        
        if not self.annotation_manager:
            logger.warning("⚠️ MongoDB 연결이 없어 동기화 서비스를 시작할 수 없음")
            return
        
        try:
            # 감시할 디렉토리 설정
            if not self.watch_directories:
                self.watch_directories = self._detect_watch_directories()
            
            if not self.watch_directories:
                logger.warning("⚠️ 감시할 디렉토리가 없음")
                return
            
            # 각 디렉토리에 대해 감시 설정
            for directory in self.watch_directories:
                if os.path.exists(directory):
                    self.observer.schedule(self.handler, directory, recursive=False)
                    logger.info(f"📁 JSON 파일 감시 시작: {directory}")
                else:
                    logger.debug(f"디렉토리가 존재하지 않음: {directory}")
            
            # Observer 시작
            self.observer.start()
            self.is_running = True
            
            logger.info(f"🔄 JSON → MongoDB 동기화 서비스 시작됨 ({len(self.watch_directories)}개 디렉토리 감시)")
            
        except Exception as e:
            logger.error(f"동기화 서비스 시작 실패: {e}")
            self.is_running = False
    
    def stop(self):
        """동기화 서비스 중지"""
        if not self.is_running:
            return
        
        try:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.is_running = False
            
            logger.info(f"🛑 JSON → MongoDB 동기화 서비스 중지됨 (성공: {self._success_count}, 실패: {self._error_count})")
            
        except Exception as e:
            logger.debug(f"동기화 서비스 중지 오류: {e}")
    
    def sync_json_to_mongodb(self, json_path: str) -> bool:
        """JSON 파일을 MongoDB에 동기화"""
        if not self.annotation_manager:
            return False
        
        try:
            self._sync_count += 1
            
            # JSON 파일 존재 확인
            if not os.path.exists(json_path):
                logger.debug(f"JSON 파일이 존재하지 않음: {json_path}")
                return False
            
            # JSON 파일 읽기 및 검증
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # 유효한 어노테이션 JSON인지 확인
            if not self._is_valid_annotation_json(json_data):
                logger.debug(f"유효하지 않은 어노테이션 JSON: {json_path}")
                return False
            
            # AnnotationManager로 MongoDB에 저장
            result = self.annotation_manager.insert_annotation(json_file_path=json_path)
            
            if result:
                self._success_count += 1
                logger.info(f"✅ JSON → MongoDB 동기화 성공: {os.path.basename(json_path)}")
                self.syncCompleted.emit(json_path, True)
                return True
            else:
                self._error_count += 1
                logger.warning(f"❌ JSON → MongoDB 동기화 실패: {os.path.basename(json_path)}")
                self.syncCompleted.emit(json_path, False)
                return False
                
        except Exception as e:
            self._error_count += 1
            logger.warning(f"JSON → MongoDB 동기화 오류 ({os.path.basename(json_path)}): {e}")
            self.syncCompleted.emit(json_path, False)
            return False
    
    def _is_valid_annotation_json(self, json_data: Dict) -> bool:
        """유효한 어노테이션 JSON인지 확인"""
        try:
            # 필수 필드 확인
            required_fields = ['version', 'shapes', 'imagePath']
            for field in required_fields:
                if field not in json_data:
                    return False
            
            # shapes가 리스트인지 확인
            if not isinstance(json_data['shapes'], list):
                return False
            
            # imagePath가 유효한지 확인
            image_path = json_data.get('imagePath')
            if not image_path or not isinstance(image_path, str):
                return False
            
            return True
            
        except Exception:
            return False
    
    def add_watch_directory(self, directory: str):
        """감시 디렉토리 추가"""
        if directory not in self.watch_directories and os.path.exists(directory):
            self.watch_directories.append(directory)
            
            if self.is_running:
                try:
                    self.observer.schedule(self.handler, directory, recursive=False)
                    logger.info(f"📁 새 디렉토리 감시 추가: {directory}")
                except Exception as e:
                    logger.debug(f"디렉토리 감시 추가 실패 ({directory}): {e}")
    
    def get_stats(self) -> Dict[str, int]:
        """동기화 통계 반환"""
        return {
            'total_syncs': self._sync_count,
            'successful_syncs': self._success_count,
            'failed_syncs': self._error_count,
            'success_rate': round(self._success_count / max(self._sync_count, 1) * 100, 1)
        }
    
    def manual_sync_directory(self, directory: str) -> Dict[str, int]:
        """디렉토리의 모든 JSON 파일 수동 동기화"""
        stats = {'total': 0, 'success': 0, 'failed': 0}
        
        try:
            if not os.path.exists(directory):
                logger.warning(f"디렉토리가 존재하지 않음: {directory}")
                return stats
            
            # 디렉토리의 모든 JSON 파일 찾기
            json_files = []
            for filename in os.listdir(directory):
                if filename.endswith('.json'):
                    json_path = os.path.join(directory, filename)
                    json_files.append(json_path)
            
            stats['total'] = len(json_files)
            
            # 각 파일 동기화
            for json_path in json_files:
                if self.sync_json_to_mongodb(json_path):
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
            
            logger.info(f"📁 디렉토리 수동 동기화 완료: {directory} (성공: {stats['success']}/{stats['total']})")
            
        except Exception as e:
            logger.error(f"디렉토리 수동 동기화 오류 ({directory}): {e}")
        
        return stats