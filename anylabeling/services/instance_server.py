"""
X-AnyLabeling 인스턴스 서버
기존 앱 인스턴스에서 새로운 파일 열기 요청을 처리
"""

import json
import socket
import threading
from datetime import datetime
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication

import logging
logger = logging.getLogger(__name__)

class InstanceServer(QObject):
    """앱 인스턴스 서버 - 외부에서 파일 열기 요청 수신"""
    
    file_open_requested = pyqtSignal(str)  # 파일 경로
    
    def __init__(self, main_window, port: int = 9900):
        super().__init__()
        self.main_window = main_window
        self.port = port
        self.server_socket = None
        self.server_thread = None
        self.running = False
        
        # 신호 연결
        self.file_open_requested.connect(self._open_file_in_main_thread)
    
    def start(self) -> bool:
        """서버 시작"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('localhost', self.port))
            self.server_socket.listen(5)
            
            self.running = True
            self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
            self.server_thread.start()
            
            logger.info(f"인스턴스 서버 시작: 포트 {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"인스턴스 서버 시작 실패: {e}")
            return False
    
    def stop(self):
        """서버 중지"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        if self.server_thread:
            self.server_thread.join(timeout=1)
        
        logger.info("인스턴스 서버 중지")
    
    def _server_loop(self):
        """서버 메인 루프"""
        while self.running:
            try:
                self.server_socket.settimeout(1)  # 1초마다 running 체크
                client_socket, address = self.server_socket.accept()
                
                # 새 스레드에서 클라이언트 처리
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket,),
                    daemon=True
                )
                client_thread.start()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"서버 루프 오류: {e}")
                break
    
    def _handle_client(self, client_socket):
        """클라이언트 요청 처리"""
        try:
            # 메시지 길이 받기
            length_data = client_socket.recv(4)
            if len(length_data) != 4:
                return
            
            message_length = int.from_bytes(length_data, byteorder='big')
            
            # 메시지 받기
            message_data = b''
            while len(message_data) < message_length:
                chunk = client_socket.recv(message_length - len(message_data))
                if not chunk:
                    break
                message_data += chunk
            
            if len(message_data) != message_length:
                return
            
            # 메시지 파싱
            message = json.loads(message_data.decode('utf-8'))
            
            response = self._process_message(message)
            
            # 응답 전송
            response_data = json.dumps(response).encode('utf-8')
            client_socket.sendall(len(response_data).to_bytes(4, byteorder='big'))
            client_socket.sendall(response_data)
            
        except Exception as e:
            logger.error(f"클라이언트 처리 오류: {e}")
            try:
                error_response = {
                    'status': 'error',
                    'message': str(e)
                }
                response_data = json.dumps(error_response).encode('utf-8')
                client_socket.sendall(len(response_data).to_bytes(4, byteorder='big'))
                client_socket.sendall(response_data)
            except:
                pass
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    def _process_message(self, message: dict) -> dict:
        """메시지 처리"""
        action = message.get('action')
        
        if action == 'open_file':
            file_path = message.get('file_path')
            if file_path:
                # 메인 스레드에서 파일 열기 요청
                self.file_open_requested.emit(file_path)
                
                return {
                    'status': 'success',
                    'message': f'파일 열기 요청: {file_path}',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'error',
                    'message': '파일 경로가 없습니다'
                }
        
        elif action == 'ping':
            return {
                'status': 'success',
                'message': 'pong',
                'timestamp': datetime.now().isoformat()
            }
        
        else:
            return {
                'status': 'error',
                'message': f'알 수 없는 액션: {action}'
            }
    
    def _open_file_in_main_thread(self, file_path: str):
        """메인 스레드에서 파일 열기"""
        try:
            logger.info(f"인스턴스 서버를 통한 파일 열기: {file_path}")
            
            # 기존 MainWindow의 파일 열기 기능 사용
            if hasattr(self.main_window, 'labeling_widget'):
                # 윈도우를 앞으로 가져오기
                self.main_window.raise_()
                self.main_window.activateWindow()
                
                # 파일 로드
                QTimer.singleShot(100, lambda: self._load_file_delayed(file_path))
            
        except Exception as e:
            logger.error(f"파일 열기 실패: {e}")
    
    def _load_file_delayed(self, file_path: str):
        """지연된 파일 로드"""
        try:
            if hasattr(self.main_window, 'labeling_widget'):
                self.main_window.labeling_widget.load_file(file_path)
            else:
                logger.warning("labeling_widget을 찾을 수 없음")
        except Exception as e:
            logger.error(f"지연된 파일 로드 실패: {e}")
    
    def __del__(self):
        """소멸자"""
        self.stop()