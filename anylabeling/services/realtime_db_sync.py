"""
실시간 MongoDB 연동을 위한 백그라운드 저장 시스템

라벨링 작업 시 실시간으로 MongoDB에 자동 저장하는 시스템입니다.
QThread를 사용하여 UI 블로킹 없이 백그라운드에서 처리합니다.
"""

import time
import json
import threading
from queue import Queue, Empty
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from PyQt5.QtCore import QThread, pyqtSignal, QTimer, QObject
from PyQt5.QtWidgets import QApplication

from anylabeling.views.labeling.logger import logger

@dataclass
class SaveTask:
    """저장 작업을 나타내는 데이터 클래스"""
    task_id: str
    task_type: str  # 'annotation', 'flag', 'image_status'
    data: Dict[str, Any]
    priority: int = 0  # 0=낮음, 1=보통, 2=높음
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class BackgroundSaveWorker(QThread):
    """백그라운드에서 MongoDB 저장을 처리하는 워커 스레드"""
    
    # 신호 정의
    save_completed = pyqtSignal(str, bool, str)  # task_id, success, message
    batch_completed = pyqtSignal(int, int)       # total_tasks, successful_tasks
    error_occurred = pyqtSignal(str, str)        # task_id, error_message
    
    def __init__(self, annotation_manager=None):
        super().__init__()
        self.annotation_manager = annotation_manager
        self.task_queue = Queue()
        self.is_running = True
        self.batch_size = 5  # 한 번에 처리할 작업 수
        self.retry_limit = 3
        self.failed_tasks = []
        
        # 통계
        self.total_processed = 0
        self.successful_saves = 0
        self.failed_saves = 0
        
    def add_task(self, task: SaveTask):
        """저장 작업을 큐에 추가"""
        try:
            self.task_queue.put(task, timeout=1.0)
            logger.debug(f"저장 작업 추가됨: {task.task_type} - {task.task_id}")
        except Exception as e:
            logger.error(f"작업 큐 추가 실패: {e}")
    
    def stop(self):
        """워커 스레드 중지"""
        self.is_running = False
        # 종료 신호 작업 추가
        self.task_queue.put(None)
        
    def run(self):
        """메인 처리 루프"""
        logger.info("BackgroundSaveWorker 시작됨")
        
        while self.is_running:
            try:
                # 배치 단위로 작업 수집
                batch_tasks = self._collect_batch_tasks()
                
                if not batch_tasks:
                    continue
                
                if batch_tasks[0] is None:  # 종료 신호
                    break
                
                # 배치 처리
                self._process_batch(batch_tasks)
                
            except Exception as e:
                logger.error(f"BackgroundSaveWorker 오류: {e}")
                time.sleep(1)  # 오류 시 잠시 대기
        
        logger.info("BackgroundSaveWorker 종료됨")
    
    def _collect_batch_tasks(self) -> List[SaveTask]:
        """배치 단위로 작업을 수집"""
        tasks = []
        
        try:
            # 첫 번째 작업 대기 (블로킹)
            first_task = self.task_queue.get(timeout=2.0)
            if first_task is None:  # 종료 신호
                return [None]
            
            tasks.append(first_task)
            
            # 추가 작업들 수집 (논블로킹)
            for _ in range(self.batch_size - 1):
                try:
                    task = self.task_queue.get_nowait()
                    if task is None:  # 종료 신호
                        tasks.append(None)
                        break
                    tasks.append(task)
                except Empty:
                    break
                    
        except Empty:
            # 타임아웃 - 정상적인 상황
            pass
        except Exception as e:
            logger.error(f"작업 수집 오류: {e}")
        
        return tasks
    
    def _process_batch(self, tasks: List[SaveTask]):
        """작업 배치 처리"""
        if not self.annotation_manager:
            logger.warning("AnnotationManager가 없어 저장을 건너뜁니다")
            return
        
        successful_count = 0
        
        # 우선순위별로 정렬 (높은 우선순위 먼저)
        tasks.sort(key=lambda x: x.priority if x else -1, reverse=True)
        
        for task in tasks:
            if task is None:
                continue
                
            success = self._process_single_task(task)
            if success:
                successful_count += 1
        
        # 배치 완료 신호 발송
        self.batch_completed.emit(len(tasks), successful_count)
        
    def _process_single_task(self, task: SaveTask) -> bool:
        """단일 작업 처리"""
        try:
            self.total_processed += 1
            
            if task.task_type == 'annotation':
                success = self._save_annotation(task)
            elif task.task_type == 'flag':
                success = self._save_flag(task)
            elif task.task_type == 'image_status':
                success = self._save_image_status(task)
            else:
                logger.warning(f"알 수 없는 작업 타입: {task.task_type}")
                success = False
            
            if success:
                self.successful_saves += 1
                self.save_completed.emit(task.task_id, True, "저장 완료")
                logger.debug(f"저장 성공: {task.task_id}")
            else:
                self.failed_saves += 1
                self._handle_failed_task(task)
                
            return success
            
        except Exception as e:
            error_msg = f"작업 처리 오류: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(task.task_id, error_msg)
            self._handle_failed_task(task)
            return False
    
    def _save_annotation(self, task: SaveTask) -> bool:
        """어노테이션 저장"""
        try:
            data = task.data
            json_data = data.get('json_data')
            
            if json_data:
                result = self.annotation_manager.insert_annotation(json_data=json_data)
                return result is not None
            else:
                logger.warning(f"어노테이션 데이터가 없음: {task.task_id}")
                return False
                
        except Exception as e:
            logger.error(f"어노테이션 저장 실패: {e}")
            return False
    
    def _save_flag(self, task: SaveTask) -> bool:
        """플래그 저장"""
        try:
            data = task.data
            image_id = data.get('image_id')
            flags = data.get('flags', {})
            
            if not image_id:
                return False
            
            # 이미지 문서 업데이트
            update_data = {
                'flags': flags,
                'flag_updated_at': datetime.now()
            }
            
            # AnnotationManager를 통해 업데이트
            # 임시로 직접 MongoDB 접근 (AnnotationManager에 업데이트 메서드가 없는 경우)
            if hasattr(self.annotation_manager, 'collection'):
                collection = self.annotation_manager.collection
                result = collection.update_one(
                    {'imagePath': image_id},
                    {'$set': update_data}
                )
                return result.modified_count > 0
            
            return False
            
        except Exception as e:
            logger.error(f"플래그 저장 실패: {e}")
            return False
    
    def _save_image_status(self, task: SaveTask) -> bool:
        """이미지 상태 저장"""
        try:
            data = task.data
            image_id = data.get('image_id')
            status = data.get('status')
            
            if not image_id or not status:
                return False
            
            update_data = {
                'status': status,
                'status_updated_at': datetime.now()
            }
            
            # AnnotationManager를 통해 업데이트
            if hasattr(self.annotation_manager, 'collection'):
                collection = self.annotation_manager.collection
                result = collection.update_one(
                    {'imagePath': image_id},
                    {'$set': update_data}
                )
                return result.modified_count > 0
                
            return False
            
        except Exception as e:
            logger.error(f"이미지 상태 저장 실패: {e}")
            return False
    
    def _handle_failed_task(self, task: SaveTask):
        """실패한 작업 처리"""
        self.failed_tasks.append(task)
        self.error_occurred.emit(
            task.task_id, 
            f"저장 실패: {task.task_type}"
        )
        
        # 실패한 작업이 너무 많으면 정리
        if len(self.failed_tasks) > 100:
            self.failed_tasks = self.failed_tasks[-50:]  # 최근 50개만 유지
    
    def get_statistics(self) -> Dict[str, int]:
        """통계 정보 반환"""
        return {
            'total_processed': self.total_processed,
            'successful_saves': self.successful_saves,
            'failed_saves': self.failed_saves,
            'queue_size': self.task_queue.qsize(),
            'failed_task_count': len(self.failed_tasks)
        }

class RealTimeDBSync(QObject):
    """실시간 데이터베이스 동기화 관리자"""
    
    def __init__(self, annotation_manager=None, parent=None):
        super().__init__(parent)
        self.annotation_manager = annotation_manager
        self.worker = None
        self.is_active = False
        
        # 설정
        self.auto_save_interval = 5000  # 5초마다 자동 저장 확인
        self.batch_threshold = 10       # 배치 처리 임계값
        
        # 타이머 설정
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self._check_auto_save)
        
        # 지연 저장을 위한 임시 저장소
        self.pending_saves = {}
        
        logger.info("RealTimeDBSync 초기화 완료")
    
    def start(self):
        """실시간 동기화 시작"""
        if self.is_active:
            logger.warning("이미 실시간 동기화가 활성화되어 있습니다")
            return
        
        if not self.annotation_manager:
            logger.error("AnnotationManager가 없어 실시간 동기화를 시작할 수 없습니다")
            return
        
        # 워커 스레드 시작
        self.worker = BackgroundSaveWorker(self.annotation_manager)
        self.worker.save_completed.connect(self._on_save_completed)
        self.worker.batch_completed.connect(self._on_batch_completed)
        self.worker.error_occurred.connect(self._on_error_occurred)
        self.worker.start()
        
        # 자동 저장 타이머 시작
        self.auto_save_timer.start(self.auto_save_interval)
        
        self.is_active = True
        logger.info("실시간 DB 동기화 시작됨")
    
    def stop(self):
        """실시간 동기화 중지"""
        if not self.is_active:
            return
        
        self.auto_save_timer.stop()
        
        if self.worker:
            self.worker.stop()
            self.worker.wait(3000)  # 3초 대기
            self.worker = None
        
        self.is_active = False
        logger.info("실시간 DB 동기화 중지됨")
    
    def save_annotation_async(self, json_data: Dict[str, Any], task_id: str = None, priority: int = 1):
        """어노테이션 비동기 저장"""
        if not self.is_active or not self.worker:
            logger.warning("실시간 동기화가 비활성화되어 있습니다")
            return False
        
        if task_id is None:
            task_id = f"annotation_{int(time.time() * 1000)}"
        
        task = SaveTask(
            task_id=task_id,
            task_type='annotation',
            data={'json_data': json_data},
            priority=priority
        )
        
        self.worker.add_task(task)
        logger.debug(f"어노테이션 비동기 저장 요청: {task_id}")
        return True
    
    def save_flags_async(self, image_id: str, flags: Dict[str, Any], task_id: str = None):
        """플래그 비동기 저장"""
        if not self.is_active or not self.worker:
            logger.warning("실시간 동기화가 비활성화되어 있습니다")
            return False
        
        if task_id is None:
            task_id = f"flag_{image_id}_{int(time.time() * 1000)}"
        
        task = SaveTask(
            task_id=task_id,
            task_type='flag',
            data={'image_id': image_id, 'flags': flags},
            priority=0  # 플래그는 낮은 우선순위
        )
        
        self.worker.add_task(task)
        logger.debug(f"플래그 비동기 저장 요청: {task_id}")
        return True
    
    def save_image_status_async(self, image_id: str, status: str, task_id: str = None):
        """이미지 상태 비동기 저장"""
        if not self.is_active or not self.worker:
            logger.warning("실시간 동기화가 비활성화되어 있습니다")
            return False
        
        if task_id is None:
            task_id = f"status_{image_id}_{int(time.time() * 1000)}"
        
        task = SaveTask(
            task_id=task_id,
            task_type='image_status',
            data={'image_id': image_id, 'status': status},
            priority=1  # 상태 변경은 보통 우선순위
        )
        
        self.worker.add_task(task)
        logger.debug(f"이미지 상태 비동기 저장 요청: {task_id}")
        return True
    
    def save_annotation_delayed(self, json_data: Dict[str, Any], delay_ms: int = 2000):
        """지연 저장 (디바운싱)"""
        image_path = json_data.get('imagePath', '')
        
        # 기존 지연 저장 취소
        if image_path in self.pending_saves:
            old_timer = self.pending_saves[image_path]['timer']
            old_timer.stop()
            old_timer.deleteLater()
        
        # 새 지연 저장 타이머 설정
        timer = QTimer()
        timer.setSingleShot(True)
        
        def delayed_save():
            if image_path in self.pending_saves:
                data = self.pending_saves[image_path]['data']
                self.save_annotation_async(data, priority=2)  # 높은 우선순위
                del self.pending_saves[image_path]
        
        timer.timeout.connect(delayed_save)
        
        self.pending_saves[image_path] = {
            'timer': timer,
            'data': json_data
        }
        
        timer.start(delay_ms)
        logger.debug(f"어노테이션 지연 저장 설정: {image_path} ({delay_ms}ms)")
    
    def _check_auto_save(self):
        """자동 저장 확인 (주기적 호출)"""
        if not self.worker:
            return
        
        # 통계 정보 로깅
        stats = self.worker.get_statistics()
        if stats['total_processed'] > 0 and stats['total_processed'] % 50 == 0:
            logger.info(f"저장 통계 - 총: {stats['total_processed']}, "
                       f"성공: {stats['successful_saves']}, "
                       f"실패: {stats['failed_saves']}, "
                       f"대기: {stats['queue_size']}")
    
    def _on_save_completed(self, task_id: str, success: bool, message: str):
        """저장 완료 시 호출"""
        logger.debug(f"저장 완료: {task_id} - {message}")
    
    def _on_batch_completed(self, total_tasks: int, successful_tasks: int):
        """배치 완료 시 호출"""
        if total_tasks > 0:
            success_rate = (successful_tasks / total_tasks) * 100
            logger.debug(f"배치 완료: {successful_tasks}/{total_tasks} ({success_rate:.1f}%)")
    
    def _on_error_occurred(self, task_id: str, error_message: str):
        """오류 발생 시 호출"""
        logger.warning(f"저장 오류 [{task_id}]: {error_message}")
    
    def get_status(self) -> Dict[str, Any]:
        """현재 상태 반환"""
        status = {
            'is_active': self.is_active,
            'worker_running': self.worker.isRunning() if self.worker else False,
            'pending_saves': len(self.pending_saves),
            'auto_save_interval': self.auto_save_interval
        }
        
        if self.worker:
            status.update(self.worker.get_statistics())
        
        return status

# 전역 인스턴스 (싱글톤 패턴)
_realtime_db_sync_instance = None

def get_realtime_db_sync(annotation_manager=None) -> RealTimeDBSync:
    """RealTimeDBSync 싱글톤 인스턴스 반환"""
    global _realtime_db_sync_instance
    
    if _realtime_db_sync_instance is None:
        _realtime_db_sync_instance = RealTimeDBSync(annotation_manager)
    elif annotation_manager and not _realtime_db_sync_instance.annotation_manager:
        _realtime_db_sync_instance.annotation_manager = annotation_manager
    
    return _realtime_db_sync_instance

def cleanup_realtime_db_sync():
    """전역 인스턴스 정리"""
    global _realtime_db_sync_instance
    
    if _realtime_db_sync_instance:
        _realtime_db_sync_instance.stop()
        _realtime_db_sync_instance = None