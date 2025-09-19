"""Advanced safety confirmation dialog."""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QTextEdit, QCheckBox,
                           QFrame, QApplication)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

class SafetyConfirmDialog(QDialog):
    """Advanced safety confirmation dialog."""
    def __init__(self, operation_type, details=None, count=0, parent=None):
        super().__init__(parent)
        self.operation_type = operation_type
        self.details = details or {}
        self.count = count
        self.countdown_seconds = 1  # Countdown duration
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_countdown)
        
        self.setup_ui()
        self.start_countdown()
        
    def setup_ui(self):
        """Set up the UI."""
        self.setWindowTitle("⚠️ 위험한 작업 확인")
        self.setFixedSize(450, 350)
        self.setModal(True)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        title_layout = QHBoxLayout()
        
        icon_label = QLabel("⚠️")
        icon_label.setFont(QFont("Arial", 24))
        icon_label.setStyleSheet("color: #ff6b35; margin-right: 10px;")
        
        title_label = QLabel("위험한 작업이 감지되었습니다")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setStyleSheet("color: #d73527;")
        
        title_layout.addWidget(icon_label)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #ddd;")
        
        info_label = QLabel("작업 정보:")
        info_label.setFont(QFont("Arial", 10, QFont.Bold))
        
        details_text = QTextEdit()
        details_text.setReadOnly(True)
        details_text.setMaximumHeight(120)
        
        info_content = f"• 작업 유형: {self.operation_type}\n"
        if self.details.get('target'):
            info_content += f"• 대상: {self.details['target']}\n"
        if self.count > 0:
            info_content += f"• 영향받는 항목: {self.count}\n"
        if self.details.get('warning'):
            info_content += f"• 주의사항: {self.details['warning']}\n"
            
        details_text.setPlainText(info_content)
        details_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px;
                padding: 8px; font-family: 'Consolas', monospace; font-size: 9pt;
            }
        """)
        
        self.confirm_checkbox = QCheckBox("위 내용을 확인했으며, 작업을 계속 진행하겠습니다.")
        self.confirm_checkbox.setStyleSheet("font-weight: bold; color: #495057;")
        self.confirm_checkbox.stateChanged.connect(self.on_checkbox_changed)
        
        self.countdown_label = QLabel()
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.update_countdown_text()
        
        button_layout = QHBoxLayout()
        
        self.proceed_button = QPushButton("계속 진행")
        self.proceed_button.setEnabled(False)
        self.proceed_button.clicked.connect(self.accept)
        self.proceed_button.setStyleSheet("""
            QPushButton { background-color: #dc3545; color: white; border: none; padding: 10px 20px; border-radius: 4px; font-weight: bold; min-width: 100px; }
            QPushButton:enabled:hover { background-color: #c82333; }
            QPushButton:disabled { background-color: #adb5bd; }
        """)
        
        cancel_button = QPushButton("취소")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet("""
            QPushButton { background-color: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 4px; font-weight: bold; min-width: 100px; }
            QPushButton:hover { background-color: #5a6268; }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(self.proceed_button)
        
        layout.addLayout(title_layout)
        layout.addWidget(line)
        layout.addWidget(info_label)
        layout.addWidget(details_text)
        layout.addWidget(self.confirm_checkbox)
        layout.addWidget(self.countdown_label)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        self.setStyleSheet("""
            QDialog { background-color: white; border: 2px solid #dc3545; border-radius: 8px; }
        """)
    
    def start_countdown(self):
        """Start the countdown timer."""
        self.timer.start(1000)
        
    def update_countdown(self):
        """Update the countdown state."""
        self.countdown_seconds -= 1
        self.update_countdown_text()
        
        if self.countdown_seconds <= 0:
            self.timer.stop()
            self.countdown_label.hide()
            
    def update_countdown_text(self):
        """Update the countdown label text."""
        if self.countdown_seconds > 0:
            self.countdown_label.setText(f"⏰ {self.countdown_seconds}초 후 확인 가능")
            self.countdown_label.setStyleSheet("color: #dc3545; font-weight: bold;")
        else:
            self.countdown_label.setText("✅ 이제 확인할 수 있습니다")
            self.countdown_label.setStyleSheet("color: #28a745; font-weight: bold;")
            
    def on_checkbox_changed(self, state):
        """Enable the proceed button only if the checkbox is checked after the countdown."""
        self.proceed_button.setEnabled(self.countdown_seconds <= 0 and state == Qt.Checked)

def show_safety_dialog(operation_type, target="", count=0, warning=""):
    """Display the safety confirmation dialog."""
    try:
        app = QApplication.instance() or QApplication([])
            
        details = {
            'target': target,
            'warning': warning or "이 작업은 데이터에 영구적인 변경을 가할 수 있습니다."
        }
        
        dialog = SafetyConfirmDialog(operation_type, details, count)
        return dialog.exec_() == QDialog.Accepted
        
    except Exception as e:
        print(f"❌ 안전 다이얼로그 오류: {e}")
        return False

def confirm_dangerous_operation(operation_type, target="", count=0):
    """Simple GUI confirmation dialog (for backward compatibility)."""
    try:
        from PyQt5.QtWidgets import QMessageBox
        
        app = QApplication.instance() or QApplication([])
        
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
        
        return msg_box.exec_() == 0
        
    except Exception as e:
        print(f"❌ 확인 다이얼로그 오류: {e}")
        return False
