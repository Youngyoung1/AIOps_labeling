"""
X-AnyLabeling 앱 인스턴스 관리자 (최적화된 버전)
매번 새로운 프로세스를 실행하는 대신 기존 인스턴스를 재사용하여 성능 향상
"""

import os
import sys
import time
import json
import socket
import subprocess
from pathlib import Path
from datetime import datetime

import logging
logger = logging.getLogger(__name__)

class AppInstanceManager:
    """X-AnyLabeling 앱 인스턴스 관리자 (경량화)"""
    
    def __init__(self, port_range=(9900, 9920)):  # 포트 범위 줄임
        self.port_range = port_range
        self.active_instances = {}
        self.last_used_port = None
        self.max_instances = 2  # 최대 인스턴스 수 줄임
    
    def find_available_port(self):
        """사용 가능한 포트 빠르게 찾기"""
        for port in range(*self.port_range):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(('127.0.0.1', port))
                    return port
            except OSError:
                continue
        return None
    
    def is_port_alive(self, port):
        """포트가 살아있는지 빠르게 확인"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)  # 타임아웃 줄임
                return s.connect_ex(('127.0.0.1', port)) == 0
        except:
            return False
    
    def send_file_command(self, port, file_path):
        """기존 인스턴스에 파일 명령 전송"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)  # 타임아웃 줄임
                s.connect(('127.0.0.1', port))
                
                cmd = {'action': 'open_file', 'file_path': file_path}
                data = json.dumps(cmd).encode('utf-8')
                
                s.sendall(len(data).to_bytes(4, 'big'))
                s.sendall(data)
                
                # 간단한 응답만 확인
                resp_len = int.from_bytes(s.recv(4), 'big')
                if resp_len > 0:
                    resp_data = s.recv(resp_len)
                    return json.loads(resp_data.decode('utf-8')).get('status') == 'success'
                
        except Exception as e:
            logger.debug(f"파일 명령 전송 실패 (포트 {port}): {e}")
        return False
    
    def cleanup_dead_instances(self):
        """죽은 인스턴스 빠르게 정리"""
        dead_ports = [p for p in self.active_instances if not self.is_port_alive(p)]
        for port in dead_ports:
            del self.active_instances[port]
            if self.last_used_port == port:
                self.last_used_port = None
    
    def get_ready_instance(self):
        """준비된 인스턴스 포트 반환"""
        self.cleanup_dead_instances()
        
        # 마지막 사용 포트 우선
        if self.last_used_port and self.is_port_alive(self.last_used_port):
            return self.last_used_port
        
        # 아무 살아있는 인스턴스
        for port in self.active_instances:
            if self.is_port_alive(port):
                self.last_used_port = port
                return port
        
        # 새 인스턴스 생성
        return self.create_new_instance()
    
    def create_new_instance(self):
        """새 인스턴스 빠르게 생성"""
        if len(self.active_instances) >= self.max_instances:
            return None
        
        port = self.find_available_port()
        if not port:
            return None
        
        try:
            app_path = Path(__file__).parent.parent / 'app.py'
            if not app_path.exists():
                return None
            
            # 최소 플래그로 빠른 시작
            cmd = [sys.executable, str(app_path), '--instance-mode', '--port', str(port), '--minimal-init']
            
            process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 빠른 시작 대기 (최대 3초)
            for _ in range(15):  # 0.2초씩 15번 = 3초
                if self.is_port_alive(port):
                    self.active_instances[port] = {'process': process, 'started': datetime.now()}
                    self.last_used_port = port
                    return port
                time.sleep(0.2)
            
            process.terminate()
            
        except Exception as e:
            logger.debug(f"인스턴스 생성 실패: {e}")
        
        return None
    
    def open_file_fast(self, file_path):
        """파일 빠르게 열기"""
        if not os.path.exists(file_path):
            return False
        
        # 기존 인스턴스 시도
        port = self.get_ready_instance()
        if port and self.send_file_command(port, file_path):
            return True
        
        # 폴백: 직접 실행
        try:
            app_path = Path(__file__).parent.parent / 'app.py'
            if app_path.exists():
                subprocess.Popen([sys.executable, str(app_path), file_path])
            else:
                subprocess.Popen([sys.executable, '-m', 'anylabeling.app', file_path])
            return True
        except:
            return False

# 전역 인스턴스 (싱글톤)
_manager = None

def get_instance_manager():
    global _manager
    if _manager is None:
        _manager = AppInstanceManager()
    return _manager

def open_file_with_instance_manager(file_path):
    """빠른 파일 열기 (단순화된 API)"""
    return get_instance_manager().open_file_fast(file_path)

if __name__ == "__main__":
    # 테스트
    manager = AppInstanceManager()
    test_file = r"C:\path\to\test\image.jpg"  # 테스트용 경로
    success = manager.open_file_fast(test_file)
    print(f"파일 열기 결과: {success}")