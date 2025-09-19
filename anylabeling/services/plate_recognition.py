"""번호판 인식 서비스 - 네트워크 스토리지 지원"""

import requests
import time
import os
from datetime import datetime

def confirm_dangerous_operation(operation_type, target="", count=0):
    """위험한 작업에 대한 GUI 확인 다이얼로그"""
    try:
        from PyQt5.QtWidgets import QMessageBox, QApplication
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QIcon
        
        # QApplication이 없으면 생성
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # 메시지 박스 생성
        msg_box = QMessageBox()
        msg_box.setWindowTitle("⚠️ 번호판 인식 작업 확인")
        msg_box.setIcon(QMessageBox.Question)
        
        # 메시지 내용 구성
        message = f"<b>작업 유형:</b> {operation_type}<br>"
        if target:
            message += f"<b>대상:</b> {target}<br>"
        if count > 0:
            message += f"<b>처리할 이미지 수:</b> {count}개<br>"
        message += "<br><b>이 작업은 시간이 오래 걸릴 수 있으며<br>MongoDB에 대량의 데이터가 저장됩니다.</b><br>"
        message += "계속 진행하시겠습니까?"
        
        msg_box.setText(message)
        
        # 버튼 설정
        msg_box.addButton("진행", QMessageBox.YesRole)
        cancel_button = msg_box.addButton("취소", QMessageBox.NoRole)
        msg_box.setDefaultButton(cancel_button)
        
        # 스타일 설정
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #f8f9fa;
                font-size: 12px;
            }
            QMessageBox QPushButton {
                min-width: 80px;
                min-height: 30px;
                padding: 5px 15px;
                font-weight: bold;
            }
            QMessageBox QPushButton[text="진행"] {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QMessageBox QPushButton[text="취소"] {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
            }
        """)
        
        # 다이얼로그 실행
        result = msg_box.exec_()
        
        if result == 0:  # "진행" 선택
            print("✅ 사용자가 번호판 인식 작업 진행을 승인했습니다.")
            return True
        else:  # "취소" 선택
            print("❌ 사용자가 번호판 인식 작업을 취소했습니다.")
            return False
            
    except ImportError:
        # PyQt5가 없으면 터미널 입력으로 폴백
        print("\n" + "="*60)
        print("⚠️  번호판 인식 작업 확인")
        print("="*60)
        print(f"작업 유형: {operation_type}")
        if target:
            print(f"대상: {target}")
        if count > 0:
            print(f"처리할 이미지 수: {count}개")
        print("\n이 작업은 시간이 오래 걸릴 수 있으며 MongoDB에 대량의 데이터가 저장됩니다.")
        print("계속 진행하시겠습니까?")
        print("="*60)
        
        while True:
            response = input("계속하려면 'YES'를 입력하세요 (취소: 'NO' 또는 Enter): ").strip()
            if response.upper() == 'YES':
                print("✅ 작업을 계속합니다...")
                return True
            elif response.upper() == 'NO' or response == '':
                print("❌ 작업이 취소되었습니다.")
                return False
            else:
                print("'YES' 또는 'NO'를 입력해주세요.")
    except Exception as e:
        print(f"❌ 확인 다이얼로그 오류: {e}")
        # 오류 시 안전하게 False 반환 (작업 취소)
        return False


def demo_plate_recognition():
    """번호판 인식 데모"""
    service = PlateRecognitionService()
    
    # 서버 연결 테스트
    print("서버 연결 테스트...")
    if service.test_server_connection():
        print("✅ 서버 연결 성공")
    else:
        print("❌ 서버 연결 실패")
        return
    
    # 테스트 폴더 (사용자가 실제 경로로 변경해야 함)
    test_folder = input("이미지 폴더 경로를 입력하세요: ").strip()
    
    if not test_folder or not os.path.exists(test_folder):
        print("올바른 폴더 경로를 입력해주세요.")
        return
    
    project_name = input("프로젝트명을 입력하세요 (선택사항): ").strip()
    if not project_name:
        project_name = None
    
    # 인식 실행
    results = service.recognize_folder_and_save(test_folder, project_name)
    
    print("\n처리 완료!")


if __name__ == "__main__":
    demo_plate_recognition()
