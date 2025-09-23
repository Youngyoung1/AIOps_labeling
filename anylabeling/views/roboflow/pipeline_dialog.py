"""
로컬 YOLO 데이터셋 생성 다이얼로그

사용자가 MongoDB 데이터를 로컬 YOLO 형식 데이터셋으로 변환할 수 있는 UI
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QProgressBar,
    QCheckBox, QSpinBox, QDoubleSpinBox, QGroupBox, QMessageBox,
    QFileDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from typing import Dict, Any, Optional
import os
import time

from ...services.roboflow.pipeline_automation import PipelineStatus


class PipelineWorker(QThread):
    """파이프라인 실행 워커 스레드"""
    progress_updated = pyqtSignal(int, str)
    status_changed = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, pipeline_automation, mongo_storage, config, query=None):
        super().__init__()
        self.pipeline_automation = pipeline_automation
        self.mongo_storage = mongo_storage
        self.config = config
        self.query = query
    
    def run(self):
        try:
            # 상태 콜백 설정
            self.pipeline_automation.set_status_callback(self._on_status_change)
            
            # 파이프라인 실행
            success = self.pipeline_automation.run_full_pipeline(
                self.mongo_storage, self.config, self.query
            )
            
            if success:
                output_path = self.pipeline_automation.get_output_directory()
                self.finished.emit(True, f"로컬 YOLO 데이터셋이 성공적으로 생성되었습니다!\n\n경로: {output_path}")
            else:
                self.finished.emit(False, "데이터셋 생성에 실패했습니다.")
                
        except Exception as e:
            self.finished.emit(False, f"데이터셋 생성 중 오류: {str(e)}")
    
    def _on_status_change(self, status: PipelineStatus, progress: int, message: str):
        self.progress_updated.emit(progress, message)
        self.status_changed.emit(status.value)


class LocalYoloDatasetDialog(QDialog):
    """로컬 YOLO 데이터셋 생성 다이얼로그"""
    
    def __init__(self, parent=None, mongo_storage=None):
        super().__init__(parent)
        self.mongo_storage = mongo_storage
        self.pipeline_worker: Optional[PipelineWorker] = None
        self.pipeline_automation = None
        
        self.setWindowTitle("� 로컬 YOLO 데이터셋 생성기")
        self.setFixedSize(600, 750)
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 제목
        title_label = QLabel("� 로컬 YOLO 데이터셋 생성기")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        """)
        layout.addWidget(title_label)
        
        # 설명
        desc_label = QLabel("MongoDB의 어노테이션 데이터를 YOLO 형식 데이터셋으로 변환하여 로컬에 저장합니다.")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #6c757d; font-size: 12px; margin-bottom: 20px;")
        layout.addWidget(desc_label)
        
        # 출력 설정
        output_group = QGroupBox("� 출력 설정")
        output_layout = QFormLayout(output_group)
        
        # 출력 디렉토리 선택
        output_dir_layout = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("데이터셋을 저장할 폴더를 선택하세요")
        default_output = os.path.join(os.path.expanduser("~"), "Desktop", "yolo_datasets")
        self.output_dir_edit.setText(default_output)
        
        self.browse_button = QPushButton("📁 찾아보기")
        self.browse_button.clicked.connect(self.browse_output_directory)
        
        output_dir_layout.addWidget(self.output_dir_edit)
        output_dir_layout.addWidget(self.browse_button)
        output_layout.addRow("출력 폴더:", output_dir_layout)
        
        self.dataset_name_edit = QLineEdit()
        self.dataset_name_edit.setPlaceholderText("예: my_detection_dataset")
        default_name = "yolo_dataset_" + str(int(time.time()))
        self.dataset_name_edit.setText(default_name)
        output_layout.addRow("데이터셋 이름:", self.dataset_name_edit)
        
        layout.addWidget(output_group)
        
        # 데이터 분할 설정
        split_group = QGroupBox("📈 데이터 분할 설정")
        split_layout = QFormLayout(split_group)
        
        self.train_ratio_spin = QDoubleSpinBox()
        self.train_ratio_spin.setRange(0.1, 0.9)
        self.train_ratio_spin.setValue(0.7)
        self.train_ratio_spin.setSingleStep(0.1)
        self.train_ratio_spin.setDecimals(1)
        split_layout.addRow("훈련 비율:", self.train_ratio_spin)
        
        self.val_ratio_spin = QDoubleSpinBox()
        self.val_ratio_spin.setRange(0.1, 0.9)
        self.val_ratio_spin.setValue(0.2)
        self.val_ratio_spin.setSingleStep(0.1)
        self.val_ratio_spin.setDecimals(1)
        split_layout.addRow("검증 비율:", self.val_ratio_spin)
        
        self.test_ratio_spin = QDoubleSpinBox()
        self.test_ratio_spin.setRange(0.1, 0.9)
        self.test_ratio_spin.setValue(0.1)
        self.test_ratio_spin.setSingleStep(0.1)
        self.test_ratio_spin.setDecimals(1)
        split_layout.addRow("테스트 비율:", self.test_ratio_spin)
        
        layout.addWidget(split_group)
        
        # 추가 옵션
        options_group = QGroupBox("⚙️ 추가 옵션")
        options_layout = QVBoxLayout(options_group)
        
        self.copy_images_check = QCheckBox("이미지 파일을 데이터셋 폴더로 복사 (체크 해제 시 어노테이션만 생성)")
        self.copy_images_check.setChecked(True)
        options_layout.addWidget(self.copy_images_check)
        
        self.create_subfolders_check = QCheckBox("train/val/test 하위 폴더 생성")
        self.create_subfolders_check.setChecked(True)
        options_layout.addWidget(self.create_subfolders_check)
        
        layout.addWidget(options_group)
        
        # 진행률 표시
        progress_group = QGroupBox("📊 진행률")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("대기 중...")
        self.status_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        progress_layout.addWidget(self.status_label)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(120)
        self.log_text.setVisible(False)
        progress_layout.addWidget(self.log_text)
        
        layout.addWidget(progress_group)
        
        # 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.start_button = QPushButton("🚀 데이터셋 생성 시작")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.start_button.clicked.connect(self.start_pipeline)
        button_layout.addWidget(self.start_button)
        
        self.close_button = QPushButton("❌ 닫기")
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def browse_output_directory(self):
        """출력 디렉토리 선택"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "데이터셋 저장 폴더 선택",
            self.output_dir_edit.text() or os.path.expanduser("~")
        )
        if directory:
            self.output_dir_edit.setText(directory)
    
    def set_pipeline_automation(self, pipeline_automation):
        """파이프라인 자동화 객체 설정"""
        self.pipeline_automation = pipeline_automation
    
    def start_pipeline(self):
        """파이프라인 시작"""
        if not self.mongo_storage:
            QMessageBox.warning(self, "오류", "MongoDB 연결이 필요합니다.")
            return
        
        if not self.pipeline_automation:
            QMessageBox.warning(self, "오류", "데이터셋 생성 파이프라인이 초기화되지 않았습니다.")
            return
        
        dataset_name = self.dataset_name_edit.text().strip()
        output_directory = self.output_dir_edit.text().strip()
        
        if not dataset_name:
            QMessageBox.warning(self, "오류", "데이터셋 이름을 입력하세요.")
            return
        
        if not output_directory:
            QMessageBox.warning(self, "오류", "출력 폴더를 선택하세요.")
            return
        
        # 비율 합계 검증
        total_ratio = self.train_ratio_spin.value() + self.val_ratio_spin.value() + self.test_ratio_spin.value()
        if abs(total_ratio - 1.0) > 0.01:
            QMessageBox.warning(self, "오류", f"데이터 분할 비율의 합이 1.0이 되어야 합니다. (현재: {total_ratio:.1f})")
            return
        
        # 출력 디렉토리 생성
        try:
            os.makedirs(output_directory, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "오류", f"출력 폴더를 생성할 수 없습니다:\n{str(e)}")
            return
        
        # 설정 생성
        from ...services.roboflow.pipeline_automation import PipelineConfig
        config = PipelineConfig(
            dataset_name=dataset_name,
            output_directory=output_directory,
            description=f"X-AnyLabeling에서 생성된 YOLO 데이터셋",
            train_ratio=self.train_ratio_spin.value(),
            val_ratio=self.val_ratio_spin.value(),
            test_ratio=self.test_ratio_spin.value(),
            copy_images=self.copy_images_check.isChecked(),
            create_subfolders=self.create_subfolders_check.isChecked()
        )
        
        # UI 상태 변경
        self.start_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.log_text.setVisible(True)
        self.log_text.clear()
        
        # 워커 스레드 시작
        self.pipeline_worker = PipelineWorker(
            self.pipeline_automation,
            self.mongo_storage,
            config,
            {"shapes": {"$exists": True, "$ne": []}}  # 기본 쿼리
        )
        
        self.pipeline_worker.progress_updated.connect(self.update_progress)
        self.pipeline_worker.status_changed.connect(self.update_status)
        self.pipeline_worker.finished.connect(self.on_pipeline_finished)
        
        self.pipeline_worker.start()
    
    def update_progress(self, progress: int, message: str):
        """진행률 업데이트"""
        self.progress_bar.setValue(progress)
        self.log_text.append(f"[{progress}%] {message}")
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def update_status(self, status: str):
        """상태 업데이트"""
        status_map = {
            "idle": "대기 중",
            "preparing": "준비 중",
            "converting": "변환 중",
            "completed": "완료",
            "error": "오류"
        }
        self.status_label.setText(f"상태: {status_map.get(status, status)}")
    
    def on_pipeline_finished(self, success: bool, message: str):
        """파이프라인 완료"""
        self.start_button.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "완료", message)
            self.log_text.append(f"✅ {message}")
            
            # 생성된 폴더 열기 옵션 제공
            reply = QMessageBox.question(self, "폴더 열기", 
                "생성된 데이터셋 폴더를 열어보시겠습니까?",
                QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                try:
                    output_path = self.pipeline_automation.get_output_directory()
                    if os.path.exists(output_path):
                        os.startfile(output_path)  # Windows
                except Exception as e:
                    print(f"폴더 열기 실패: {e}")
        else:
            QMessageBox.critical(self, "오류", message)
            self.log_text.append(f"❌ {message}")
        
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )


# 기존 이름과의 호환성을 위한 별칭
RoboflowPipelineDialog = LocalYoloDatasetDialog