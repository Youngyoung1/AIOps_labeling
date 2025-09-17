"""고급 안전 확인 다이얼로그"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QTextEdit, QCheckBox, QProgressBar,
                           QFrame, QApplication)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap

class SafetyConfirmDialog(QDialog):
    """고급 안전 확인 다이얼로그"""
    
    def __init__(self, operation_type, details=None, count=0, parent=None):
        super().__init__(parent)
        self.operation_type = operation_type
        self.details = details or {}
        self.count = count
        self.countdown_seconds = 1  # 5초 대기
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_countdown)
        
        self.setup_ui()
        self.start_countdown()
        
    def setup_ui(self):
        """UI 설정"""
        self.setWindowTitle("⚠️ 위험한 작업 확인")
        self.setFixedSize(450, 350)
        self.setModal(True)
        
        # 메인 레이아웃
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # 경고 아이콘과 제목
        title_layout = QHBoxLayout()
        
        # 경고 아이콘
        icon_label = QLabel("⚠️")
        icon_label.setFont(QFont("Arial", 24))
        icon_label.setStyleSheet("color: #ff6b35; margin-right: 10px;")
        
        # 제목
        title_label = QLabel("위험한 작업이 감지되었습니다")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setStyleSheet("color: #d73527;")
        
        title_layout.addWidget(icon_label)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #ddd;")
        
        # 작업 정보
        info_label = QLabel("작업 정보:")
        info_label.setFont(QFont("Arial", 10, QFont.Bold))
        
        # 상세 정보 텍스트
        details_text = QTextEdit()
        details_text.setReadOnly(True)
        details_text.setMaximumHeight(120)
        
        info_content = f"• 작업 유형: {self.operation_type}\n"
        if self.details.get('target'):
            info_content += f"• 대상: {self.details['target']}\n"
        if self.count > 0:
            info_content += f"• 영향받는 항목: {self.count}개\n"
        if self.details.get('warning'):
            info_content += f"• 주의사항: {self.details['warning']}\n"
            
        details_text.setPlainText(info_content)
        details_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', monospace;
                font-size: 9pt;
            }
        """)
        
        # 확인 체크박스
        self.confirm_checkbox = QCheckBox("위 내용을 확인했으며, 작업을 계속 진행하겠습니다.")
        self.confirm_checkbox.setStyleSheet("font-weight: bold; color: #495057;")
        self.confirm_checkbox.stateChanged.connect(self.on_checkbox_changed)
        
        # 카운트다운 라벨
        self.countdown_label = QLabel()
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.update_countdown_text()
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        
        self.proceed_button = QPushButton("계속 진행")
        self.proceed_button.setEnabled(False)
        self.proceed_button.clicked.connect(self.accept)
        self.proceed_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:enabled:hover {
                background-color: #c82333;
            }
            QPushButton:disabled {
                background-color: #adb5bd;
            }
        """)
        
        cancel_button = QPushButton("취소")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(self.proceed_button)
        
        # 레이아웃에 위젯 추가
        layout.addLayout(title_layout)
        layout.addWidget(line)
        layout.addWidget(info_label)
        layout.addWidget(details_text)
        layout.addWidget(self.confirm_checkbox)
        layout.addWidget(self.countdown_label)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 전체 스타일
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 2px solid #dc3545;
                border-radius: 8px;
            }
        """)
    
    def start_countdown(self):
        """카운트다운 시작"""
        self.timer.start(1000)  # 1초마다
        
    def update_countdown(self):
        """카운트다운 업데이트"""
        self.countdown_seconds -= 1
        self.update_countdown_text()
        
        if self.countdown_seconds <= 0:
            self.timer.stop()
            self.countdown_label.hide()
            
    def update_countdown_text(self):
        """카운트다운 텍스트 업데이트"""
        if self.countdown_seconds > 0:
            self.countdown_label.setText(f"⏰ {self.countdown_seconds}초 후 확인 가능")
            self.countdown_label.setStyleSheet("color: #dc3545; font-weight: bold;")
        else:
            self.countdown_label.setText("✅ 이제 확인할 수 있습니다")
            self.countdown_label.setStyleSheet("color: #28a745; font-weight: bold;")
            
    def on_checkbox_changed(self, state):
        """체크박스 상태 변경"""
        if self.countdown_seconds <= 0 and state == Qt.Checked:
            self.proceed_button.setEnabled(True)
        else:
            self.proceed_button.setEnabled(False)

def show_safety_dialog(operation_type, target="", count=0, warning=""):
    """안전 확인 다이얼로그 표시"""
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
            
        details = {
            'target': target,
            'warning': warning or "이 작업은 데이터에 영구적인 변경을 가할 수 있습니다."
        }
        
        dialog = SafetyConfirmDialog(operation_type, details, count)
        result = dialog.exec_()
        
        return result == QDialog.Accepted
        
    except Exception as e:
        print(f"❌ 안전 다이얼로그 오류: {e}")
        return False

# 간단한 확인 다이얼로그 (기존 호환성)
def confirm_dangerous_operation(operation_type, target="", count=0):
    """간단한 GUI 확인 다이얼로그"""
    try:
        from PyQt5.QtWidgets import QMessageBox, QApplication
        
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        msg_box = QMessageBox()
        msg_box.setWindowTitle("⚠️ 작업 확인")
        msg_box.setIcon(QMessageBox.Warning)
        
        message = f"작업 유형: {operation_type}\n"
        if target:
            message += f"대상: {target}\n"
        if count > 0:
            message += f"영향받는 항목: {count}개\n"
        message += "\n계속 진행하시겠습니까?"
        
        msg_box.setText(message)
        msg_box.addButton("진행", QMessageBox.YesRole)
        cancel_button = msg_box.addButton("취소", QMessageBox.NoRole)
        msg_box.setDefaultButton(cancel_button)
        
        result = msg_box.exec_()
        return result == 0
        
    except Exception as e:
        print(f"❌ 확인 다이얼로그 오류: {e}")
        return False
