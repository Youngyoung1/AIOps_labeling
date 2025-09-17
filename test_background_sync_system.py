#!/usr/bin/env python3
"""
백그라운드 동기화 시스템 테스트
- 지능형 + 플래그 기반 동기화 테스트
- 실제 MongoDB와 JSON 파일 사용
"""

import os
import sys
import json
import time
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit, QHBoxLayout
from PyQt5.QtCore import QTimer, pyqtSlot

# X-AnyLabeling 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
anylabeling_dir = os.path.join(current_dir, '..')
sys.path.insert(0, anylabeling_dir)

from anylabeling.services.background_sync_system import BackgroundSyncSystem, BackgroundSyncWidget
from anylabeling.services.annotation_manager import AnnotationManager


class BackgroundSyncTestWindow(QMainWindow):
    """백그라운드 동기화 시스템 테스트 윈도우"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("🔄 백그라운드 동기화 시스템 테스트")
        self.setGeometry(100, 100, 900, 700)
        
        # 백그라운드 동기화 시스템 생성
        self.sync_system = BackgroundSyncSystem()
        
        # 테스트 디렉토리 설정
        self.test_directory = r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file"
        self.sync_system.add_watch_directory(self.test_directory)
        
        self.setup_ui()
        self.connect_signals()
        
        # MongoDB 연결 확인
        self.annotation_manager = AnnotationManager()
        
        print(f"🔄 백그라운드 동기화 시스템 테스트 시작")
        print(f"📁 테스트 디렉토리: {self.test_directory}")
        
    def setup_ui(self):
        """UI 설정"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # 제어 위젯 추가
        self.sync_widget = BackgroundSyncWidget(self.sync_system)
        layout.addWidget(self.sync_widget)
        
        # 테스트 버튼들
        test_buttons_layout = QHBoxLayout()
        
        self.test_json_to_db_button = QPushButton("📤 JSON→DB 테스트")
        self.test_db_to_json_button = QPushButton("📥 DB→JSON 테스트")
        self.create_test_flag_button = QPushButton("🚩 테스트 플래그 생성")
        self.clear_flags_button = QPushButton("🧹 플래그 정리")
        
        test_buttons_layout.addWidget(self.test_json_to_db_button)
        test_buttons_layout.addWidget(self.test_db_to_json_button)
        test_buttons_layout.addWidget(self.create_test_flag_button)
        test_buttons_layout.addWidget(self.clear_flags_button)
        
        layout.addLayout(test_buttons_layout)
        
        # 로그 출력
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(300)
        layout.addWidget(self.log_text)
        
        # 통계 출력 타이머
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats_log)
        self.stats_timer.start(15000)  # 15초마다
        
    def connect_signals(self):
        """시그널 연결"""
        # 시스템 시그널
        self.sync_system.sync_event.connect(self.on_sync_event)
        self.sync_system.status_changed.connect(self.on_status_changed)
        
        # 테스트 버튼
        self.test_json_to_db_button.clicked.connect(self.test_json_to_db)
        self.test_db_to_json_button.clicked.connect(self.test_db_to_json)
        self.create_test_flag_button.clicked.connect(self.create_test_flag)
        self.clear_flags_button.clicked.connect(self.clear_all_flags)
        
    @pyqtSlot(str, str, bool)
    def on_sync_event(self, file_path: str, mode: str, success: bool):
        """동기화 이벤트 처리"""
        if file_path:
            filename = os.path.basename(file_path)
            status = "✅" if success else "❌"
            message = f"{datetime.now().strftime('%H:%M:%S')} {status} {mode}: {filename}"
        else:
            status = "✅" if success else "❌"
            message = f"{datetime.now().strftime('%H:%M:%S')} {status} {mode}"
            
        self.log_text.append(message)
        print(message)
        
    @pyqtSlot(str)
    def on_status_changed(self, status: str):
        """상태 변경 처리"""
        message = f"{datetime.now().strftime('%H:%M:%S')} {status}"
        self.log_text.append(message)
        print(message)
        
    def test_json_to_db(self):
        """JSON → DB 동기화 테스트"""
        try:
            # 테스트 JSON 파일 수정
            test_files = [f for f in os.listdir(self.test_directory) if f.endswith('.json')]
            
            if not test_files:
                self.log_text.append("❌ 테스트할 JSON 파일이 없습니다")
                return
                
            test_file = os.path.join(self.test_directory, test_files[0])
            
            # JSON 파일 수정
            with open(test_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 테스트 플래그 추가
            if 'flags' not in data:
                data['flags'] = {}
                
            data['flags']['json_to_db_test'] = True
            data['flags']['test_timestamp'] = datetime.now().isoformat()
            data['description'] = f"JSON→DB 테스트 - {datetime.now().strftime('%H:%M:%S')}"
            
            with open(test_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            self.log_text.append(f"📝 JSON 파일 수정됨: {os.path.basename(test_file)}")
            print(f"📝 JSON 파일 수정됨: {test_file}")
            
        except Exception as e:
            self.log_text.append(f"❌ JSON→DB 테스트 실패: {e}")
            print(f"❌ JSON→DB 테스트 실패: {e}")
            
    def test_db_to_json(self):
        """DB → JSON 동기화 테스트"""
        try:
            # MongoDB에서 문서 직접 수정
            docs = list(self.annotation_manager.collection.find({
                'json_file_path': {'$regex': self.test_directory.replace('\\', '/')}
            }).limit(3))
            
            if not docs:
                self.log_text.append("❌ 테스트할 MongoDB 문서가 없습니다")
                return
                
            for doc in docs:
                # MongoDB에서 플래그 수정
                update_data = {
                    'flags.db_to_json_test': True,
                    'flags.mongodb_update_time': datetime.now().isoformat(),
                    'description': f"DB→JSON 테스트 - {datetime.now().strftime('%H:%M:%S')}",
                    'sync_needed': True  # 플래그 기반 동기화용
                }
                
                result = self.annotation_manager.collection.update_one(
                    {'_id': doc['_id']},
                    {'$set': update_data}
                )
                
                if result.modified_count > 0:
                    json_file = doc.get('json_file_path', '')
                    filename = os.path.basename(json_file) if json_file else str(doc['_id'])
                    self.log_text.append(f"🔄 MongoDB 문서 수정됨: {filename}")
                    print(f"🔄 MongoDB 문서 수정됨: {json_file}")
                    
            self.log_text.append(f"📊 총 {len(docs)}개 문서에 동기화 플래그 설정됨")
            
        except Exception as e:
            self.log_text.append(f"❌ DB→JSON 테스트 실패: {e}")
            print(f"❌ DB→JSON 테스트 실패: {e}")
            
    def create_test_flag(self):
        """테스트 동기화 플래그 생성"""
        try:
            # 여러 파일에 플래그 설정
            docs = list(self.annotation_manager.collection.find({
                'json_file_path': {'$regex': self.test_directory.replace('\\', '/')}
            }).limit(5))
            
            flagged_count = 0
            for doc in docs:
                result = self.annotation_manager.collection.update_one(
                    {'_id': doc['_id']},
                    {
                        '$set': {
                            'sync_needed': True,
                            'sync_marked_time': datetime.now(),
                            'flags.test_flag_created': datetime.now().isoformat()
                        }
                    }
                )
                
                if result.modified_count > 0:
                    flagged_count += 1
                    
            self.log_text.append(f"🚩 {flagged_count}개 파일에 동기화 플래그 설정됨")
            print(f"🚩 {flagged_count}개 파일에 동기화 플래그 설정됨")
            
        except Exception as e:
            self.log_text.append(f"❌ 플래그 생성 실패: {e}")
            print(f"❌ 플래그 생성 실패: {e}")
            
    def clear_all_flags(self):
        """모든 동기화 플래그 정리"""
        try:
            result = self.annotation_manager.collection.update_many(
                {'sync_needed': {'$exists': True}},
                {'$unset': {'sync_needed': ""}}
            )
            
            message = f"🧹 {result.modified_count}개 동기화 플래그 정리됨"
            self.log_text.append(message)
            print(message)
            
        except Exception as e:
            self.log_text.append(f"❌ 플래그 정리 실패: {e}")
            print(f"❌ 플래그 정리 실패: {e}")
            
    def update_stats_log(self):
        """통계 로그 업데이트"""
        try:
            stats = self.sync_system.get_comprehensive_stats()
            
            # 플래그된 파일 개수 확인
            flagged_count = self.annotation_manager.collection.count_documents({
                'sync_needed': True
            })
            
            log_lines = [
                f"📊 === 동기화 통계 ({datetime.now().strftime('%H:%M:%S')}) ===",
                f"모드: {stats.get('system', {}).get('sync_mode', '?')}",
                f"실행중: {stats.get('system', {}).get('is_running', False)}",
                f"플래그 대기 파일: {flagged_count}개"
            ]
            
            smart_stats = stats.get('smart_stats', {})
            if smart_stats:
                log_lines.append(f"스마트 동기화: JSON→DB {smart_stats.get('json_to_mongodb', 0)}건, DB→JSON {smart_stats.get('mongodb_to_json', 0)}건")
                
            flag_stats = stats.get('flag_stats', {})
            if flag_stats:
                log_lines.append(f"플래그 동기화: 누적 {flag_stats.get('total_synced', 0)}건")
                
            log_lines.append("=" * 50)
            
            for line in log_lines:
                self.log_text.append(line)
                
        except Exception as e:
            self.log_text.append(f"❌ 통계 업데이트 실패: {e}")
            
    def closeEvent(self, event):
        """창 닫기 이벤트"""
        self.sync_system.stop()
        event.accept()


def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    
    # 테스트 윈도우 생성
    window = BackgroundSyncTestWindow()
    window.show()
    
    # 자동으로 스마트 모드로 시작
    window.sync_system.start('smart')
    
    print("🚀 백그라운드 동기화 시스템 테스트 앱 시작됨")
    print("=" * 60)
    print("테스트 방법:")
    print("1. '📤 JSON→DB 테스트' 버튼으로 JSON 파일 변경 테스트")
    print("2. '📥 DB→JSON 테스트' 버튼으로 MongoDB 변경 테스트")
    print("3. '🚩 테스트 플래그 생성' 버튼으로 플래그 기반 동기화 테스트")
    print("4. 동기화 모드를 'flag' 또는 'hybrid'로 변경하여 테스트")
    print("=" * 60)
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()