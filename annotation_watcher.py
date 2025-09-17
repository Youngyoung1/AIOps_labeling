#!/usr/bin/env python3
"""JSON 파일 감시 및 자동 MongoDB 저장 시스템"""

import os
import json
import time
import threading
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from collections import defaultdict
import queue
import sys

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.getcwd())

class AnnotationFileHandler(FileSystemEventHandler):
    """JSON 어노테이션 파일 변경 감시 핸들러"""
    
    def __init__(self):
        super().__init__()
        self.annotation_manager = None
        self._init_annotation_manager()
        
        # 큐 기반 중복 방지 시스템
        self._file_queue = queue.Queue()
        self._last_events = defaultdict(float)  # 파일별 마지막 이벤트 시간
        self._debounce_delay = 3.0  # 디바운스 지연 시간 (초) - 더 증가
        
        # 강력한 중복 방지 시스템 추가
        self._processing_files = set()  # 현재 처리 중인 파일들
        self._file_hashes = {}  # 파일별 마지막 해시값
        self._processed_timestamps = {}  # 파일별 마지막 처리 완료 시간
        self._file_locks = defaultdict(threading.Lock)  # 파일별 락
        
        # 워커 스레드 시작
        self._shutdown = False  # shutdown 플래그 먼저 설정
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()
    
    def _init_annotation_manager(self):
        """AnnotationManager 초기화"""
        try:
            # AnnotationManager 직접 임포트
            import importlib.util
            import os
            
            # AnnotationManager 경로
            REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
            AM_PATH = os.path.join(REPO_ROOT, 'anylabeling', 'services', 'annotation_manager.py')
            
            spec = importlib.util.spec_from_file_location('annotation_manager', AM_PATH)
            am_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(am_mod)
            
            # AnnotationManager 인스턴스 생성
            AnnotationManager = am_mod.AnnotationManager
            self.annotation_manager = AnnotationManager(
                connection_string="mongodb://localhost:27017",
                db_name="labeling_db"
            )
            
            print("✅ AnnotationManager 초기화 성공")
            
        except Exception as e:
            print(f"❌ AnnotationManager 초기화 실패: {e}")
            self.annotation_manager = None
    
    def _worker(self):
        """파일 처리 워커 스레드 (강화된 중복 방지)"""
        while not self._shutdown:
            try:
                # 큐에서 파일 이벤트 가져오기 (최대 1초 대기)
                file_path, action, event_time = self._file_queue.get(timeout=1.0)
                abs_path = os.path.abspath(file_path)
                
                # 파일별 락 획득
                with self._file_locks[abs_path]:
                    # 1. 현재 처리 중인 파일인지 확인
                    if abs_path in self._processing_files:
                        print(f"⏳ 이미 처리 중인 파일 스킵: {os.path.basename(file_path)}")
                        self._file_queue.task_done()
                        continue
                    
                    # 2. 최신 이벤트인지 확인
                    if event_time < self._last_events[abs_path]:
                        print(f"⏭️ 오래된 이벤트 스킵: {os.path.basename(file_path)}")
                        self._file_queue.task_done()
                        continue
                    
                    # 3. 최근에 처리된 파일인지 확인
                    if self._is_recently_processed(abs_path):
                        print(f"🔄 최근 처리된 파일 스킵: {os.path.basename(file_path)}")
                        self._file_queue.task_done()
                        continue
                    
                    # 4. 처리 시작 표시
                    self._processing_files.add(abs_path)
                
                # 디바운스 대기 (락 밖에서 수행)
                time.sleep(self._debounce_delay)
                
                # 5. 다시 최신 이벤트인지 확인 (디바운스 후)
                if event_time < self._last_events[abs_path]:
                    print(f"⏭️ 디바운스 후 더 최신 이벤트 발견: {os.path.basename(file_path)}")
                    self._processing_files.discard(abs_path)
                    self._file_queue.task_done()
                    continue
                
                # 6. 실제 파일 처리
                try:
                    self._process_file_now(file_path, action)
                finally:
                    # 7. 처리 완료 표시
                    current_time = time.time()
                    self._processed_timestamps[abs_path] = current_time
                    current_hash = self._get_file_hash(abs_path)
                    if current_hash:
                        self._file_hashes[abs_path] = current_hash
                    self._processing_files.discard(abs_path)
                
                self._file_queue.task_done()
                
            except queue.Empty:
                continue  # 타임아웃 시 계속 실행
            except Exception as e:
                print(f"❌ 워커 스레드 오류: {e}")
                # 오류 시에도 처리 상태 정리
                try:
                    self._processing_files.discard(abs_path)
                except:
                    pass
    
    def _process_file_now(self, file_path, action):
        """실제 파일 처리 (중복 없이)"""
        try:
            if not os.path.exists(file_path):
                print(f"❌ 파일 없음: {file_path}")
                return
                
            # MongoDB에 저장
            if self._save_to_mongodb(file_path):
                print(f"📊 {action}: {os.path.basename(file_path)} → MongoDB 저장 완료 ✅")
            else:
                print(f"❌ {action}: {os.path.basename(file_path)} → MongoDB 저장 실패")
                
        except Exception as e:
            print(f"❌ 파일 처리 실패 {file_path}: {e}")
    
    def _get_file_hash(self, file_path):
        """파일 내용의 해시값 계산 (빠른 버전)"""
        try:
            import hashlib
            # 파일 크기와 수정 시간을 조합한 빠른 해시
            stat = os.stat(file_path)
            hash_input = f"{file_path}_{stat.st_size}_{stat.st_mtime}".encode()
            return hashlib.md5(hash_input).hexdigest()
        except Exception as e:
            print(f"❌ 파일 해시 계산 실패 {file_path}: {e}")
            return None
    
    def _is_recently_processed(self, file_path):
        """최근에 처리된 파일인지 확인"""
        abs_path = os.path.abspath(file_path)
        current_time = time.time()
        
        # 5초 이내에 처리된 경우 스킵
        last_processed = self._processed_timestamps.get(abs_path, 0)
        if current_time - last_processed < 5.0:
            return True
            
        # 해시가 동일한 경우 스킵
        current_hash = self._get_file_hash(abs_path)
        if current_hash and current_hash == self._file_hashes.get(abs_path):
            return True
            
        return False
    
    def _extract_annotation_features(self, json_data):
        """JSON 데이터에서 검색 최적화용 필드들 추출"""
        shapes = json_data.get('shapes', [])
        
        # labels 배열 생성 (중복 제거)
        labels = list(set([shape.get('label', '') for shape in shapes if shape.get('label')]))
        
        # shape_types 추출
        shape_types = list(set([shape.get('shape_type', '') for shape in shapes if shape.get('shape_type')]))
        
        # descriptions 추출 (비어있지 않은 것만)
        descriptions = [shape.get('description', '') for shape in shapes 
                      if shape.get('description') and shape.get('description').strip()]
        has_descriptions = len(descriptions) > 0
        
        # difficult 플래그 체크
        has_difficult = any(shape.get('difficult', False) for shape in shapes)
        
        # tag 정보 추출
        all_tags = []
        for shape in shapes:
            tags = shape.get('tag', [])
            if tags and isinstance(tags, list):
                all_tags.extend(tags)
        unique_tags = list(set(all_tags))
        has_tags = len(unique_tags) > 0
        
        # attributes 정보 추출
        has_attributes = any(shape.get('attributes', {}) for shape in shapes 
                           if isinstance(shape.get('attributes'), dict) and shape.get('attributes'))
        
        # flags 정보 추출 (전역 + shape별)
        global_flags = json_data.get("flags", {})
        has_global_flags = bool(global_flags)
        
        shape_flags = []
        for shape in shapes:
            if shape.get('flags') and shape.get('flags') is not None:
                if isinstance(shape.get('flags'), dict) and shape.get('flags'):
                    shape_flags.append(shape.get('flags'))
        has_shape_flags = len(shape_flags) > 0
        
        return {
            "labels": labels,
            "shape_types": shape_types,
            "tags": unique_tags,
            
            # 개수 정보
            "shape_count": len(shapes),
            "label_count": len(labels),
            "tag_count": len(unique_tags),
            "description_count": len(descriptions),
            
            # 플래그 정보
            "has_descriptions": has_descriptions,
            "has_difficult": has_difficult,
            "has_tags": has_tags,
            "has_attributes": has_attributes,
            "has_global_flags": has_global_flags,
            "has_shape_flags": has_shape_flags
        }
    
    def _save_to_mongodb(self, json_file_path):
        """JSON 파일을 MongoDB에 저장"""
        if not self.annotation_manager:
            return False
            
        try:
            # AnnotationManager를 사용하여 JSON 파일 삽입
            result = self.annotation_manager.insert_annotation(json_file_path=json_file_path)
            
            if result:
                print(f"✅ MongoDB 저장 성공: {os.path.basename(json_file_path)}")
                return True
            else:
                print(f"❌ MongoDB 저장 실패: {os.path.basename(json_file_path)}")
                return False
                
        except Exception as e:
            print(f"❌ MongoDB 저장 실패 {json_file_path}: {e}")
            return False
    
    def on_modified(self, event):
        """파일 수정 시 호출"""
        if event.is_directory:
            return
            
        if event.src_path.endswith('.json'):
            self._queue_file_event(event.src_path, "수정됨")
    
    def on_created(self, event):
        """파일 생성 시 호출"""
        if event.is_directory:
            return
            
        if event.src_path.endswith('.json'):
            self._queue_file_event(event.src_path, "생성됨")
    
    def _queue_file_event(self, file_path, action):
        """파일 이벤트를 큐에 추가"""
        try:
            current_time = time.time()
            abs_path = os.path.abspath(file_path)
            
            # 마지막 이벤트 시간 업데이트
            self._last_events[abs_path] = current_time
            
            # 큐에 이벤트 추가
            self._file_queue.put((file_path, action, current_time))
            print(f"📬 이벤트 큐에 추가: {os.path.basename(file_path)} ({action})")
            
        except Exception as e:
            print(f"❌ 이벤트 큐 추가 실패 {file_path}: {e}")

class AnnotationWatcher:
    """어노테이션 파일 감시 클래스"""
    
    def __init__(self, watch_directory=None):
        self.watch_directory = watch_directory or os.getcwd()
        self.observer = Observer()
        self.handler = AnnotationFileHandler()
        self.is_running = False
    
    def start(self):
        """감시 시작"""
        if self.is_running:
            print("⚠️ 이미 실행 중입니다.")
            return
        
        print(f"🔍 어노테이션 파일 감시 시작: {self.watch_directory}")
        print("📁 감시 대상: *.json 파일")
        print("🔄 변경/생성 시 자동으로 MongoDB에 저장됩니다.")
        print("⏹️ 중지하려면 Ctrl+C를 누르세요.\n")
        
        self.observer.schedule(self.handler, self.watch_directory, recursive=True)
        self.observer.start()
        self.is_running = True
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """감시 중지"""
        if not self.is_running:
            return
            
        print("\n🛑 어노테이션 파일 감시 중지 중...")
        self.observer.stop()
        self.observer.join()
        
        if self.handler.client:
            self.handler.client.close()
            print("🔐 MongoDB 연결 종료")
        
        self.is_running = False
        print("✅ 어노테이션 파일 감시 완료")

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JSON 어노테이션 파일 감시 및 MongoDB 자동 저장")
    parser.add_argument("--directory", "-d", default=".", help="감시할 디렉토리 (기본: 현재 디렉토리)")
    parser.add_argument("--test", action="store_true", help="현재 디렉토리의 모든 JSON 파일을 한 번에 처리")
    
    args = parser.parse_args()
    
    if args.test:
        # 테스트 모드: 현재 디렉토리의 모든 JSON 파일 처리
        handler = AnnotationFileHandler()
        json_files = [f for f in os.listdir(args.directory) if f.endswith('.json')]
        
        print(f"🧪 테스트 모드: {len(json_files)}개 JSON 파일 처리")
        
        for json_file in json_files:
            file_path = os.path.join(args.directory, json_file)
            if handler._save_to_mongodb(file_path):
                print(f"✅ 처리 완료: {json_file}")
            else:
                print(f"❌ 처리 실패: {json_file}")
        
        if handler.client:
            handler.client.close()
        
        print("🎉 테스트 완료!")
    else:
        # 일반 모드: 파일 감시
        watcher = AnnotationWatcher(args.directory)
        watcher.start()

if __name__ == "__main__":
    main()
