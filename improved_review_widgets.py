# -*- coding: utf-8 -*-
import sys
import json
import random
import time
import os
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, 
                            QComboBox, QLineEdit, QLabel, QDateEdit, QGroupBox, 
                            QFormLayout, QHeaderView, QMessageBox, QProgressBar,
                            QFrame, QSizePolicy, QSpacerItem, QTextEdit, QCheckBox)
from PyQt5.QtCore import Qt, QDate, QTimer, pyqtSignal, QPointF
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap, QIcon, QPainter, QPen, QPolygonF

# MongoDB AnnotationManager 연동
try:
    # 현재 파일 위치에서 상대 경로로 AnnotationManager import
    from anylabeling.services.annotation_manager import AnnotationManager
except Exception as e:
    print(f"AnnotationManager import 실패: {e}")
    AnnotationManager = None

class StatusBadgeWidget(QWidget):
    """검수 상태 배지 위젯"""
    def __init__(self, status):
        super().__init__()
        self.status = status
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)
        
        label = QLabel(self.status)
        label.setAlignment(Qt.AlignCenter)
        label.setMinimumWidth(140)
        label.setMaximumHeight(25)
        
        # 상태별 스타일 설정 - 대기중 제거, 1차 검수 요청 전 추가
        styles = {
            "1차 검수 요청 전": "background: #fef3c7; color: #d97706; border-radius: 12px; padding: 4px 12px; font-weight: bold; border: 2px solid #f59e0b;",
            "1차 검수 요청": "background: #dbeafe; color: #1d4ed8; border-radius: 12px; padding: 4px 12px; font-weight: bold; border: 2px solid #3b82f6;",
            "반려": "background: #fee2e2; color: #dc2626; border-radius: 12px; padding: 4px 12px; font-weight: bold; border: 2px solid #ef4444;",
            "1차 검수 완료": "background: #d1fae5; color: #059669; border-radius: 12px; padding: 4px 12px; font-weight: bold; border: 2px solid #10b981;",
            "2차 검수 요청": "background: #e0e7ff; color: #4338ca; border-radius: 12px; padding: 4px 12px; font-weight: bold; border: 2px solid #6366f1;",
            "2차 검수 완료": "background: #dcfce7; color: #16a34a; border-radius: 12px; padding: 4px 12px; font-weight: bold; border: 2px solid #22c55e;",
            "최종 승인": "background: #f3e8ff; color: #7c2d12; border-radius: 12px; padding: 4px 12px; font-weight: bold; border: 2px solid #a855f7;"
        }
        
        # 기본 스타일은 1차 검수 요청 전으로 설정
        label.setStyleSheet(styles.get(self.status, styles["1차 검수 요청 전"]))
        layout.addWidget(label)
        self.setLayout(layout)

class ActionButtonWidget(QWidget):
    """작업 버튼 위젯 - 대기중 상태 제거 및 워크플로우 개선"""
    review_requested = pyqtSignal(str, str)  # annotation_id, action_type
    
    def __init__(self, annotation_id, status):
        super().__init__()
        self.annotation_id = annotation_id
        self.status = status
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)
        
        # 상태에 따른 버튼 생성 - 대기중 제거
        if self.status == '1차 검수 요청 전':
            btn = QPushButton("1차 검수 요청")
            btn.setStyleSheet("""
                QPushButton { 
                    background: #3b82f6; 
                    color: white; 
                    border: none; 
                    padding: 8px 16px; 
                    border-radius: 6px; 
                    font-weight: bold; 
                    font-size: 12px;
                    min-width: 100px;
                } 
                QPushButton:hover { 
                    background: #2563eb; 
                }
                QPushButton:pressed {
                    background: #1d4ed8;
                }
            """)
            btn.clicked.connect(lambda: self.review_requested.emit(self.annotation_id, "request_first"))
            layout.addWidget(btn)
            
        elif self.status == '1차 검수 요청':
            # 1차 검수 완료 버튼
            complete_btn = QPushButton("1차 검수 완료")
            complete_btn.setStyleSheet("""
                QPushButton { 
                    background: #10b981; 
                    color: white; 
                    border: none; 
                    padding: 8px 16px; 
                    border-radius: 6px; 
                    font-weight: bold; 
                    font-size: 12px;
                    min-width: 100px;
                } 
                QPushButton:hover { 
                    background: #059669; 
                }
                QPushButton:pressed {
                    background: #047857;
                }
            """)
            complete_btn.clicked.connect(lambda: self.review_requested.emit(self.annotation_id, "complete_first"))
            layout.addWidget(complete_btn)
            
            # (반려 버튼은 공통 버튼 영역에서 추가)
            
        elif self.status == '1차 검수 완료':
            btn = QPushButton("2차 검수 요청")
            btn.setStyleSheet("""
                QPushButton { 
                    background: #6366f1; 
                    color: white; 
                    border: none; 
                    padding: 8px 16px; 
                    border-radius: 6px; 
                    font-weight: bold; 
                    font-size: 12px;
                    min-width: 100px;
                } 
                QPushButton:hover { 
                    background: #4f46e5; 
                }
                QPushButton:pressed {
                    background: #4338ca;
                }
            """)
            btn.clicked.connect(lambda: self.review_requested.emit(self.annotation_id, "request_second"))
            layout.addWidget(btn)
            
        elif self.status == '2차 검수 요청':
            # 2차 검수 완료 버튼
            complete_btn = QPushButton("2차 검수 완료")
            complete_btn.setStyleSheet("""
                QPushButton { 
                    background: #16a34a; 
                    color: white; 
                    border: none; 
                    padding: 8px 16px; 
                    border-radius: 6px; 
                    font-weight: bold; 
                    font-size: 12px;
                    min-width: 100px;
                } 
                QPushButton:hover { 
                    background: #15803d; 
                }
                QPushButton:pressed {
                    background: #166534;
                }
            """)
            complete_btn.clicked.connect(lambda: self.review_requested.emit(self.annotation_id, "complete_second"))
            layout.addWidget(complete_btn)
            
            # 거부 버튼
            reject_btn = QPushButton("거부")
            reject_btn.setStyleSheet("""
                QPushButton { 
                    background: #ef4444; 
                    color: white; 
                    border: none; 
                    padding: 8px 16px; 
                    border-radius: 6px; 
                    font-weight: bold; 
                    font-size: 12px;
                    min-width: 60px;
                } 
                QPushButton:hover { 
                    background: #dc2626; 
                }
            """)
            reject_btn.clicked.connect(lambda: self.review_requested.emit(self.annotation_id, "reject_second"))
            layout.addWidget(reject_btn)
            
        elif self.status == '2차 검수 완료':
            btn = QPushButton("최종 승인")
            btn.setStyleSheet("""
                QPushButton { 
                    background: #7c2d12; 
                    color: white; 
                    border: none; 
                    padding: 8px 16px; 
                    border-radius: 6px; 
                    font-weight: bold; 
                    font-size: 12px;
                    min-width: 100px;
                } 
                QPushButton:hover { 
                    background: #92400e; 
                }
                QPushButton:pressed {
                    background: #78350f;
                }
            """)
            btn.clicked.connect(lambda: self.review_requested.emit(self.annotation_id, "final_approve"))
            layout.addWidget(btn)
            
        elif self.status == '최종 승인':
            # 최종 승인된 경우 상태 표시만
            status_label = QLabel("✅ 승인 완료")
            status_label.setStyleSheet("""
                QLabel {
                    background: #dcfce7;
                    color: #16a34a;
                    border: 2px solid #22c55e;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-size: 12px;
                }
            """)
            layout.addWidget(status_label)
        
        # 공통 버튼들 (최종 승인 상태가 아닌 경우에만)
        if self.status != '최종 승인':
            # 구분선
            if layout.count() > 0:
                separator = QFrame()
                separator.setFrameShape(QFrame.VLine)
                separator.setStyleSheet("color: #e5e7eb;")
                layout.addWidget(separator)

            # 반려 버튼 (한 단계 이전으로 되돌림)
            reject_flow_btn = QPushButton("⏮ 반려")
            reject_flow_btn.setStyleSheet("""
                QPushButton { 
                    background: #ef4444; 
                    color: white; 
                    border: none; 
                    padding: 8px 14px; 
                    border-radius: 6px; 
                    font-weight: bold; 
                    font-size: 12px;
                    min-width: 80px;
                } 
                QPushButton:hover { 
                    background: #dc2626; 
                }
            """)
            reject_flow_btn.clicked.connect(lambda: self.review_requested.emit(self.annotation_id, "reject_flow"))

            # 검수 사진 보기 버튼
            view_btn = QPushButton("검수 사진 보기")
            view_btn.setStyleSheet("""
                QPushButton { 
                    background: #f59e0b; 
                    color: white; 
                    border: none; 
                    padding: 8px 16px; 
                    border-radius: 6px; 
                    font-weight: bold; 
                    font-size: 12px;
                    min-width: 80px;
                } 
                QPushButton:hover { 
                    background: #d97706; 
                }
            """)

            view_btn.clicked.connect(lambda: self.review_requested.emit(self.annotation_id, "view_image"))
            
            # 삭제 버튼
            delete_btn = QPushButton("🗑️")
            delete_btn.setToolTip("삭제")
            delete_btn.setStyleSheet("""
                QPushButton { 
                    background: #ef4444; 
                    color: white; 
                    border: none; 
                    padding: 8px 10px; 
                    border-radius: 6px; 
                    font-weight: bold; 
                    font-size: 12px;
                    min-width: 35px;
                    max-width: 35px;
                } 
                QPushButton:hover { 
                    background: #dc2626; 
                }
            """)
            delete_btn.clicked.connect(lambda: self.review_requested.emit(self.annotation_id, "delete"))
            
            layout.addWidget(reject_flow_btn)
            layout.addWidget(view_btn)
            layout.addWidget(delete_btn)
        
        self.setLayout(layout)

class AnnotationDetailDialog(QMessageBox):
    """어노테이션 상세 정보 다이얼로그"""
    def __init__(self, annotation_data, parent=None):
        super().__init__(parent)
        self.annotation_data = annotation_data
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("어노테이션 상세 정보")
        self.setIcon(QMessageBox.Information)
        
        # 상세 정보 구성
        details = []
        details.append(f"파일명: {self.annotation_data.get('imagePath', 'N/A')}")
        details.append(f"이미지 크기: {self.annotation_data.get('imageWidth', 0)} x {self.annotation_data.get('imageHeight', 0)}")
        details.append(f"라벨메이트 버전: {self.annotation_data.get('version', 'N/A')}")
        details.append(f"검수 상태: {self.annotation_data.get('review_status', '1차 검수 요청 전')}")
        details.append(f"검수자: {self.annotation_data.get('reviewer', '-')}")
        
        # shapes 정보
        shapes = self.annotation_data.get('shapes', [])
        details.append("\n=== 검출된 객체 ({}개) ===".format(len(shapes)))
        
        for i, shape in enumerate(shapes):
            details.append("\n[객체 {}]".format(i+1))
            details.append(f"  라벨: {shape.get('label', 'N/A')}")
            details.append(f"  형태: {shape.get('shape_type', 'N/A')}")
            details.append(f"  어려움: {'예' if shape.get('difficult', False) else '아니오'}")
            
            # 좌표 정보
            points = shape.get('points', [])
            if points and len(points) >= 2:
                x1, y1 = points[0] if len(points[0]) >= 2 else (0, 0)
                x2, y2 = points[2] if len(points) >= 3 and len(points[2]) >= 2 else (0, 0)
                width = abs(x2 - x1)
                height = abs(y2 - y1)
                details.append(f"  위치: ({x1:.0f}, {y1:.0f})")
                details.append(f"  크기: {width:.0f} x {height:.0f}")
            
            # 설명
            description = shape.get('description', '')
            if description:
                details.append(f"  설명: {description}")
        
        self.setText("\n".join(details))

class LabelMeReviewSearch(QMainWindow):
    def __init__(self):
        super().__init__()
        # 데이터 소스 초기화 (AnnotationManager 기반)
        self.sample_data = []
        self.filtered_data = []
        self.annotation_manager = None  # AnnotationManager 인스턴스
        # JSON 상태 캐시: { json_path: (mtime, status_str) }
        self._json_status_cache = {}

        # UI 먼저 띄우고, 이후 데이터 로드(초기 체감 반응 개선)
        self.setup_ui()

        # 시작 시 MongoDB AnnotationManager를 통해 데이터 로드
        def _startup_loader():
            self.result_label.setText("검색 결과: 0개 (로딩 중…)")
            try:
                # PyMongo 설치 여부 사전 점검
                try:
                    import pymongo  # noqa: F401
                except ImportError:
                    raise RuntimeError("PyMongo 미설치: requirements에 pymongo 추가 및 설치 필요")
                
                # AnnotationManager 초기화
                self._init_annotation_manager()
                
                if not self.annotation_manager:
                    raise RuntimeError("AnnotationManager 초기화 실패")
                
                # MongoDB에서 데이터 로드
                self._load_data_from_mongo()
                self.filtered_data = [
                    item for item in self.sample_data
                    if item.get('review_status', '') != '최종 승인'
                ]
                self.load_table_data()
                self._refresh_label_filter_items()
                self.result_label.setText(f"검색 결과: {len(self.filtered_data)}개")
                return
            except Exception as e:
                # 구체 원인 포함 안내
                print(f"MongoDB 데이터 로드 실패: {e}")
                QMessageBox.critical(self, "DB 연결 실패", "MongoDB 데이터 로드에 실패하였습니다.\n사유: " + str(e))
                # 실패 시에는 샘플 데이터 사용하지 않고 빈 상태로 둠
                self.sample_data = []
                self.filtered_data = []
                self.load_table_data()
                self._refresh_label_filter_items()
                self.result_label.setText("DB 연결에 실패하였습니다.")

        # 타이머에서 호출되는 초기 로더를 위 함수로 대체
        self._init_mongo_and_load_and_refresh = _startup_loader
        QTimer.singleShot(0, self._init_mongo_and_load_and_refresh)
    
    def setup_ui(self):
        self.setWindowTitle("LabelMe 어노테이션 검수 관리 시스템 (개선된 워크플로우)")
        self.setGeometry(100, 100, 1600, 900)

        # 메인 위젯
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # 메인 레이아웃
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)

        # 헤더
        header = self.create_header()
        main_layout.addWidget(header)

        # 검색 패널
        search_panel = self.create_search_panel()
        main_layout.addWidget(search_panel)

        # 결과 정보
        self.result_label = QLabel("검색 결과: 20개")
        self.result_label.setStyleSheet("""
            QLabel {
                background: #ecfdf5;
                border: 2px solid #a7f3d0;
                border-radius: 8px;
                padding: 12px 16px;
                color: #065f46;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        main_layout.addWidget(self.result_label)

        # 테이블
        self.table = self.create_table()
        main_layout.addWidget(self.table)

        # 필터 디바운서(입력 중 과도한 재계산 방지)
        self.filter_timer = QTimer(self)
        self.filter_timer.setSingleShot(True)
        self.filter_timer.setInterval(250)
        self.filter_timer.timeout.connect(self._apply_filter)

        # 초기 텍스트
        self.result_label.setText("검색 결과: 0개 (로딩 중…)")

        # 스타일 적용
        self.apply_styles()
    
    def create_header(self):
        """헤더 생성"""
        header = QWidget()
        header.setFixedHeight(80)
        header.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #4f46e5, stop:1 #7c3aed);
                border-radius: 10px;
            }
        """)
        
        layout = QVBoxLayout()
        title = QLabel("LabelMe 어노테이션 검수 관리 시스템 (개선된 워크플로우)")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
                background: transparent;
            }
        """)
        layout.addWidget(title)
        header.setLayout(layout)
        return header
    
    def create_search_panel(self):
        """검색 패널 생성 - 대기중 상태 제거"""
        group = QGroupBox()
        group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                margin: 6px 0 8px 0;
                padding: 12px 12px 10px 12px;
                background: #f8fafc;
            }
            QGroupBox::title {
                subcontrol-origin: padding;
                left: 10px;
                padding: 0 6px;
                color: #1e293b;
            }
        """)

        layout = QFormLayout()

        # 검수 상태 - 대기중 제거
        self.review_status_combo = QComboBox()
        self.review_status_combo.addItems([
            "모든 상태", "1차 검수 요청 전", "1차 검수 요청", "반려", "1차 검수 완료", 
            "2차 검수 요청", "2차 검수 완료"
        ])
        self.review_status_combo.currentTextChanged.connect(self.filter_data)

        # 라벨 (검출된 객체)
        self.label_combo = QComboBox()
        # 최초엔 기본값만, 데이터 로드 후 동적으로 채움
        self.label_combo.addItems(["모든 라벨"]) 
        self.label_combo.currentTextChanged.connect(self.filter_data)
        
        # 라벨 상세 정보 버튼 추가
        label_widget = QWidget()
        label_layout = QHBoxLayout()
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.addWidget(self.label_combo)
        
        label_detail_btn = QPushButton("📋")
        label_detail_btn.setToolTip("선택된 라벨의 상세 정보 보기")
        label_detail_btn.setMaximumWidth(30)
        label_detail_btn.clicked.connect(self.show_label_detail)
        label_detail_btn.setStyleSheet("""
            QPushButton {
                background: #3b82f6; color: white; border: none;
                border-radius: 4px; font-weight: bold; font-size: 12px;
            }
            QPushButton:hover { background: #2563eb; }
        """)
        label_layout.addWidget(label_detail_btn)
        label_widget.setLayout(label_layout)

    # 파일명
        self.filename_edit = QLineEdit()
        self.filename_edit.setPlaceholderText("파일명을 입력하세요 (예: 231012)")
        self.filename_edit.textChanged.connect(self.filter_data)

        # 날짜 범위
        date_widget = QWidget()
        date_layout = QHBoxLayout()
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(QLabel(" ~ "))
        date_layout.addWidget(self.end_date)
        date_widget.setLayout(date_layout)

        # JSON 상태 우선 토글 (기본: 켜짐)
        self.json_status_first = QCheckBox("JSON 상태 우선")
        self.json_status_first.setChecked(True)
        self.json_status_first.setToolTip("JSON 파일(review_history/legacy 필드)의 상태를 우선 사용해 필터링/표시합니다.")
        self.json_status_first.stateChanged.connect(self.filter_data)

        # 폼에 추가
        layout.addRow("검수 상태:", self.review_status_combo)
        layout.addRow("상태 소스:", self.json_status_first)
        layout.addRow("객체 라벨:", label_widget)
        layout.addRow("파일명:", self.filename_edit)
        layout.addRow("생성 날짜:", date_widget)

        # 버튼들
        button_layout = QHBoxLayout()

        search_btn = QPushButton("🔍 검색")
        search_btn.clicked.connect(self.manual_search)
        search_btn.setStyleSheet(self.get_button_style("#4f46e5", "#3730a3"))

        reset_btn = QPushButton("🔄 초기화")
        reset_btn.clicked.connect(self.reset_filters)
        reset_btn.setStyleSheet(self.get_button_style("#6b7280", "#4b5563"))

        export_btn = QPushButton("📤 JSON 내보내기")
        export_btn.clicked.connect(self.export_json)
        export_btn.setStyleSheet(self.get_button_style("#059669", "#047857"))

        stats_btn = QPushButton("📊 어노테이션 통계")
        stats_btn.clicked.connect(self.show_annotation_statistics)
        stats_btn.setStyleSheet(self.get_button_style("#7c2d12", "#6b21a8"))
        
        search_advanced_btn = QPushButton("🔍 고급 검색")
        search_advanced_btn.clicked.connect(self.show_advanced_search)
        search_advanced_btn.setStyleSheet(self.get_button_style("#059669", "#047857"))

        button_layout.addWidget(search_btn)
        button_layout.addWidget(reset_btn)
        button_layout.addWidget(export_btn)
        button_layout.addWidget(stats_btn)
        button_layout.addWidget(search_advanced_btn)
        button_layout.addStretch()

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(button_layout)
        group.setLayout(main_layout)

        return group
    
    def get_button_style(self, bg_color, hover_color):
        """버튼 스타일 생성"""
        return f"""
            QPushButton {{
                background: {bg_color};
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }}
            QPushButton:hover {{
                background: {hover_color};
            }}
            QPushButton:pressed {{
                background: {hover_color};
            }}
        """
    
    def create_table(self):
        """테이블 생성"""
        table = QTableWidget()
        headers = ["파일명", "주요 라벨", "검수상태", "생성일시", "작업"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        
        # 테이블 스타일
        table.setStyleSheet("""
            QTableWidget {
                border: none;
                border-radius: 10px;
                background: white;
                gridline-color: #e5e7eb;
                selection-background-color: #f3f4f6;
            }
            QTableWidget::item {
                padding: 12px;
                border-bottom: 1px solid #e5e7eb;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #1e293b, stop:1 #334155);
                color: white;
                border: none;
                padding: 15px 12px;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        
        # 헤더 설정
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        
        # 행 높이 설정
        table.verticalHeader().setDefaultSectionSize(60)
        table.verticalHeader().setVisible(False)
        
        # 더블클릭 이벤트
        table.itemDoubleClicked.connect(self.show_annotation_detail)
        
        return table

    # -------------------- JSON 상태 판별 헬퍼 --------------------
    def _read_status_from_json(self, item):
        """주어진 어노테이션 항목에서 JSON 파일을 찾아 상태 문자열을 반환.
        우선순위: review_history 최신 → review_status/ReviewStatus → review.status
        매핑: 요청(request/requested/요청/1차 검수 요청)→ '1차 검수 요청', 반려(reject/rejected/반려) → '반려'.
        없으면 None(=요청 전으로 취급).
        캐시 사용(파일 mtime 기반).
        """
        try:
            # 1) JSON 경로 결정
            json_path = item.get('json_file_path') or ''
            if not json_path:
                # 이미지 경로에서 유추
                base = (
                    item.get('image_file_path')
                    or item.get('imagePath')
                    or item.get('image_file_name')
                    or ''
                )
                if base:
                    root, _ = os.path.splitext(str(base))
                    json_path = root + '.json'

            if not json_path or not os.path.exists(json_path):
                return None

            # 2) 캐시 확인
            try:
                mtime = os.path.getmtime(json_path)
            except Exception:
                mtime = None
            cached = self._json_status_cache.get(json_path)
            if cached and cached[0] == mtime:
                return cached[1]

            # 3) JSON 읽기
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            status = None
            # review_history 최신 항목 우선
            try:
                rh = data.get('review_history')
                if isinstance(rh, list) and rh:
                    last = rh[-1]
                    if isinstance(last, dict):
                        status = last.get('status') or last.get('state')
            except Exception:
                pass

            # legacy 필드들
            if not status:
                status = data.get('review_status') or data.get('reviewStatus')

            # nested review 객체
            if not status and isinstance(data.get('review'), dict):
                status = data['review'].get('status')

            # 정규화 매핑
            norm = (str(status).strip().lower() if status is not None else None)
            requested_aliases = {'requested', 'request', '요청', '1차 검수 요청'}
            rejected_aliases = {'rejected', 'reject', '반려'}

            mapped = None
            if norm in requested_aliases:
                mapped = '1차 검수 요청'
            elif norm in rejected_aliases:
                mapped = '반려'
            else:
                # 이미 한국어 정식 상태일 수 있음 → 그대로 사용
                mapped = status if status else None

            # 캐시 저장
            self._json_status_cache[json_path] = (mtime, mapped)
            return mapped
        except Exception:
            return None

    def _get_effective_status(self, item):
        """체크박스가 켜져 있으면 JSON에서 읽은 상태를 우선 적용하고, 없으면 DB 상태.
        JSON에 상태가 전혀 없으면 '1차 검수 요청 전'으로 취급."""
        try:
            use_json = hasattr(self, 'json_status_first') and self.json_status_first.isChecked()
        except Exception:
            use_json = False

        if use_json:
            js = self._read_status_from_json(item)
            if js is None or js == '':
                return '1차 검수 요청 전'
            return js
        return item.get('review_status', '1차 검수 요청 전')
    
    def generate_labelme_data(self):
        """LabelMe 형식의 샘플 데이터 생성 - 대기중 제거"""
        statuses = ["1차 검수 요청 전", "1차 검수 요청", "1차 검수 완료", "2차 검수 요청", "2차 검수 완료", "최종 승인"]
        labels = ["person_01", "person_02", "person_03", "vehicle", "face"]
        reviewers = ["김검수", "이검수", "박검수", "최검수", ""]
        
        data = []
        for i in range(20):
            # 랜덤한 객체 개수
            num_objects = random.randint(1, 5)
            shapes = []
            
            for j in range(num_objects):
                # 랜덤한 박스 좌표 생성
                x1 = random.randint(100, 800)
                y1 = random.randint(100, 600)
                x2 = x1 + random.randint(50, 200)
                y2 = y1 + random.randint(50, 200)
                
                shape = {
                    "label": random.choice(labels),
                    "score": None,
                    "points": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
                    "group_id": None,
                    "description": "어두워서 잘 안보임" if random.random() < 0.3 else None,
                    "difficult": random.random() < 0.2,
                    "tag": [],
                    "shape_type": "rectangle",
                    "flags": None,
                    "attributes": {},
                    "kie_linking": []
                }
                shapes.append(shape)
            
            status = random.choice(statuses)
            reviewer = random.choice(reviewers) if status != "1차 검수 요청 전" else ""
            
            annotation = {
                "_id": f"68c12c8e5dfac31e473bf{i:03d}",
                "version": "3.2.2",
                "flags": {},
                "shapes": shapes,
                "imagePath": f"23101{i%10}_060258_{random.randint(0,9)}_side{random.randint(1,4)}.jpg",
                "imageData": None,
                "imageHeight": random.choice([720, 1080, 1440]),
                "imageWidth": random.choice([1280, 1440, 1920]),
                # 검수 관련 추가 필드
                "review_status": status,
                "reviewer": reviewer,
                "created_at": datetime.now() - timedelta(days=random.randint(0, 30)),
                "updated_at": datetime.now() - timedelta(days=random.randint(0, 5))
            }
            
            data.append(annotation)
        
        return data

    # -------------------- Mongo 연동 --------------------
    def _init_mongo_and_load_and_refresh(self):
        """UI 표시 후 데이터를 로드하고 화면을 갱신"""
        self.result_label.setText("검색 결과: 0개 (로딩 중…)")
        self._init_mongo_and_load()
        # 승인 완료 제외 리스트로 초기화
        self.filtered_data = [
            item for item in self.sample_data
            if item.get('review_status', '') != '최종 승인'
        ]
        self.load_table_data()
        self._refresh_label_filter_items()
        self.result_label.setText(f"검색 결과: {len(self.filtered_data)}개")
    def _init_annotation_manager(self):
        """AnnotationManager 초기화"""
        try:
            if not AnnotationManager:
                print("Warning: AnnotationManager를 import할 수 없습니다.")
                return
            
            # 기본 설정으로 AnnotationManager 초기화
            self.annotation_manager = AnnotationManager()
            print("AnnotationManager 초기화 완료")
                
        except Exception as e:
            print(f"AnnotationManager 초기화 실패: {e}")
            self.annotation_manager = None

    def _init_mongo_and_load(self):
        """AnnotationManager를 통한 데이터 로드"""
        try:
            # AnnotationManager 초기화
            self._init_annotation_manager()
            
            if not self.annotation_manager:
                raise RuntimeError("AnnotationManager 초기화 실패")
            
            # MongoDB에서 데이터 로드
            self._load_data_from_mongo()
            
        except Exception as e:
            print(f"데이터 로드 실패: {e}")
            # 실패 시 빈 상태 유지
            self.sample_data = []
            self.filtered_data = []

    def _resolve_overall_status(self, statuses):
        """여러 어노테이션 상태로부터 대표 상태 결정"""
        order = [
            "1차 검수 요청 전",
            "1차 검수 요청",
            "1차 검수 완료",
            "2차 검수 요청",
            "2차 검수 완료",
            "최종 승인",
        ]
        for s in order:
            if s in statuses:
                return s
        return "1차 검수 요청 전"

    def _load_data_from_mongo(self):
        """MongoDB AnnotationManager에서 실제 데이터를 가져와서 self.sample_data 채움"""
        from datetime import datetime as _dt
        
        try:
            if not self.annotation_manager:
                raise RuntimeError("AnnotationManager가 초기화되지 않았습니다")
            
            # AnnotationManager를 통해 모든 어노테이션 데이터 가져오기
            # 검색 조건 없이 모든 데이터 조회 (빈 조건으로 검색)
            all_annotations = self.annotation_manager.search_annotations({})
            
            if not all_annotations:
                raise RuntimeError("DB에 어노테이션 데이터가 없습니다")
            
            items = []
            for doc in all_annotations:
                # MongoDB 문서를 UI에서 사용할 형태로 변환 (안전한 처리)
                item = {
                    "_id": str(doc.get("_id", "")),
                    "version": doc.get("version", ""),
                    "flags": doc.get("flags", {}),
                    "shapes": doc.get("shapes", []),
                    # imagePath가 None인 경우 안전하게 처리
                    "imagePath": doc.get("imagePath") or doc.get("json_file_name", "알 수 없는 파일"),
                    "imageData": doc.get("imageData"),
                    "imageHeight": doc.get("imageHeight", 0),
                    "imageWidth": doc.get("imageWidth", 0),
                    
                    # 🔧 이미지 경로 관련 필드들 추가 (사진 보기 기능을 위해 필수)
                    "image_file_path": doc.get("image_file_path", ""),
                    "image_file_name": doc.get("image_file_name", ""),
                    "image_directory": doc.get("image_directory", ""),
                    "image_exists": doc.get("image_exists", False),
                    
                    # JSON 파일 관련 필드들
                    "json_file_path": doc.get("json_file_path", ""),
                    "json_file_name": doc.get("json_file_name", ""),
                    "json_directory": doc.get("json_directory", ""),
                    "same_directory": doc.get("same_directory", True),
                    
                    # 기존 필드명 호환성 유지
                    "file_path": doc.get("json_file_path", ""),
                    
                    # 검수 관련 필드 (기본값 설정)
                    "review_status": doc.get("review_status", "1차 검수 요청 전"),
                    "reviewer": doc.get("reviewer", ""),
                    "created_at": doc.get("created_at", _dt.now()),
                    "updated_at": doc.get("updated_at", _dt.now()),
                    
                    # 추가 검색 최적화 필드들
                    "labels": doc.get("labels", []),
                    "shape_count": doc.get("shape_count", 0),
                    "label_count": doc.get("label_count", 0),
                    "has_descriptions": doc.get("has_descriptions", False),
                    "has_tags": doc.get("has_tags", False),
                    "has_attributes": doc.get("has_attributes", False),
                    "shape_types": doc.get("shape_types", []),
                    "tags": doc.get("tags", [])
                }
                items.append(item)
            
            print(f"MongoDB에서 {len(items)}개의 어노테이션 데이터를 로드했습니다.")
            
            self.sample_data = items
            self.filtered_data = items[:]
            
        except Exception as e:
            print(f"MongoDB 데이터 로드 실패: {e}")
            # 폴백으로 빈 데이터 사용
            self.sample_data = []
            self.filtered_data = []

    def _refresh_label_filter_items(self):
        """현재 데이터 기반으로 라벨 콤보 갱신"""
        try:
            labels = set()
            for item in self.sample_data:
                for s in item.get('shapes', []) or []:
                    lbl = s.get('label')
                    if lbl:
                        labels.add(lbl)
            current = self.label_combo.currentText() if hasattr(self, 'label_combo') else "모든 라벨"
            self.label_combo.blockSignals(True)
            self.label_combo.clear()
            self.label_combo.addItem("모든 라벨")
            for lbl in sorted(labels):
                self.label_combo.addItem(lbl)
            # 기존 선택 유지
            if current in [self.label_combo.itemText(i) for i in range(self.label_combo.count())]:
                self.label_combo.setCurrentText(current)
            self.label_combo.blockSignals(False)
        except Exception:
            pass

    def load_table_data(self):
        """테이블 데이터 로드"""
        # 대량 갱신 최적화
        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)
        self.table.clearContents()
        self.table.setRowCount(len(self.filtered_data))

        for i, item in enumerate(self.filtered_data):
            # 파일명 (안전한 처리)
            image_path = item.get('imagePath') or 'N/A'
            self.table.setItem(i, 0, QTableWidgetItem(str(image_path)))

            # 주요 라벨 (가장 많은 라벨)
            labels = [shape.get('label', '') for shape in item.get('shapes', []) if shape.get('label')]
            main_label = max(set(labels), key=labels.count) if labels else "없음"
            self.table.setItem(i, 1, QTableWidgetItem(main_label))

            # 상태 배지 (JSON 우선 적용)
            show_status = self._get_effective_status(item)
            status_widget = StatusBadgeWidget(show_status)
            self.table.setCellWidget(i, 2, status_widget)

            # 생성일시 (안전한 처리)
            created_at = item.get('created_at')
            if created_at and hasattr(created_at, 'strftime'):
                date_str = created_at.strftime('%Y-%m-%d %H:%M')
            else:
                date_str = '날짜 없음'
            self.table.setItem(i, 3, QTableWidgetItem(date_str))

            # 작업 버튼
            item_id = item.get('_id', f'unknown_{i}')
            action_widget = ActionButtonWidget(str(item_id), item.get('review_status', '1차 검수 요청 전'))
            action_widget.review_requested.connect(self.handle_action)
            self.table.setCellWidget(i, 4, action_widget)

        # 컬럼 폭은 고정값으로(매번 계산 비용 제거)
        self.table.setColumnWidth(0, 220)  # 파일명
        self.table.setColumnWidth(1, 140)  # 주요 라벨
        self.table.setColumnWidth(2, 160)  # 검수상태
        self.table.setColumnWidth(3, 160)  # 생성일시
        self.table.setColumnWidth(4, 320)  # 작업
        # 결과 라벨 갱신
        if hasattr(self, 'result_label'):
            self.result_label.setText(f"검색 결과: {len(self.filtered_data)}개")
        # 라벨 콤보 갱신
        if hasattr(self, 'label_combo'):
            self._refresh_label_filter_items()

        # 갱신 재개
        self.table.setUpdatesEnabled(True)
        self.table.setSortingEnabled(True)
        self.table.viewport().update()
    
    def filter_data(self):
        """데이터 필터링(디바운스 스케줄)"""
        if hasattr(self, 'filter_timer'):
            self.filter_timer.start()
        else:
            self._apply_filter()

    def _apply_filter(self):
        """실제 필터 로직 수행"""
        filtered = []

        for item in self.sample_data:
            # 승인 완료 항목은 항상 숨김
            # JSON 우선 모드일 경우, 효과적 상태 기준으로 판단
            eff_status_for_exclude = self._get_effective_status(item)
            if eff_status_for_exclude == '최종 승인' or item.get('review_status', '') == '최종 승인':
                continue
            # 검수 상태 필터
            current_status_filter = self.review_status_combo.currentText()
            eff_status = self._get_effective_status(item)
            if (current_status_filter != "모든 상태" and eff_status != current_status_filter):
                continue

            # 라벨 필터
            if self.label_combo.currentText() != "모든 라벨":
                labels = [shape.get('label', '') for shape in item.get('shapes', [])]
                if self.label_combo.currentText() not in labels:
                    continue

            # 파일명 필터
            if self.filename_edit.text().strip():
                search_text = self.filename_edit.text().strip().lower()
                image_path = item.get('imagePath') or ""
                if search_text not in image_path.lower():
                    continue

            filtered.append(item)

        self.filtered_data = filtered
        self.load_table_data()
        self.result_label.setText(f"검색 결과: {len(filtered)}개")
    
    def manual_search(self):
        """수동 검색 실행"""
        self.result_label.setText("검색 중...")
        QApplication.processEvents()
        QTimer.singleShot(500, self.filter_data)
    
    def reset_filters(self):
        """필터 초기화"""
        self.review_status_combo.setCurrentText("모든 상태")
        self.label_combo.setCurrentText("모든 라벨")
        self.filename_edit.clear()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.end_date.setDate(QDate.currentDate())
        
        # 승인 완료 항목 제외한 초기 리스트로 복원
        self.filtered_data = [
            item for item in self.sample_data
            if item.get('review_status', '') != '최종 승인'
        ]
        self.load_table_data()
        self.result_label.setText(f"검색 결과: {len(self.filtered_data)}개")
    
    def export_json(self):
        """JSON 내보내기"""
        try:
            filename = f"labelme_annotations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.filtered_data, f, ensure_ascii=False, indent=2, default=str)
            
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("내보내기 완료")
            msg.setText(f"검색 결과 {len(self.filtered_data)}개를 {filename}로 내보냈습니다.")
            msg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "내보내기 오류", f"파일 저장 중 오류가 발생했습니다: {str(e)}")
    
    def show_advanced_search(self):
        """고급 검색 기능 다이얼로그"""
        if not self.annotation_manager:
            QMessageBox.information(self, "정보", "AnnotationManager가 연결되지 않았습니다.")
            return
        
        # 간단한 고급 검색 다이얼로그
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFormLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("고급 검색")
        dialog.setGeometry(300, 300, 500, 400)
        
        layout = QVBoxLayout()
        
        # 검색 조건들
        form_layout = QFormLayout()
        
        # Shape 타입 검색
        shape_combo = QComboBox()
        try:
            shape_types = self.annotation_manager.get_all_shape_types()
            shape_combo.addItem("-- 모든 타입 --")
            shape_combo.addItems(shape_types)
        except:
            shape_combo.addItem("-- 모든 타입 --")
        form_layout.addRow("Shape 타입:", shape_combo)
        
        # 태그 검색
        tag_combo = QComboBox()
        try:
            tags = self.annotation_manager.get_all_tags()
            tag_combo.addItem("-- 모든 태그 --")
            tag_combo.addItems(tags)
        except:
            tag_combo.addItem("-- 모든 태그 --")
        form_layout.addRow("태그:", tag_combo)
        
        # 플래그 옵션들
        from PyQt5.QtWidgets import QCheckBox
        desc_check = QCheckBox("설명이 있는 어노테이션만")
        difficult_check = QCheckBox("Difficult 표시된 어노테이션만")
        attrs_check = QCheckBox("Attributes가 있는 어노테이션만")
        
        form_layout.addRow("필터 옵션:", desc_check)
        form_layout.addRow("", difficult_check)
        form_layout.addRow("", attrs_check)
        
        layout.addLayout(form_layout)
        
        # 결과 표시 영역
        result_text = QTextEdit()
        result_text.setMaximumHeight(200)
        result_text.setPlaceholderText("검색 버튼을 클릭하면 결과가 표시됩니다.")
        layout.addWidget(result_text)
        
        # 버튼들
        button_layout = QHBoxLayout()
        
        search_btn = QPushButton("검색")
        search_btn.clicked.connect(lambda: self._perform_advanced_search(
            shape_combo.currentText(), tag_combo.currentText(),
            desc_check.isChecked(), difficult_check.isChecked(), attrs_check.isChecked(),
            result_text
        ))
        
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(dialog.close)
        
        button_layout.addWidget(search_btn)
        button_layout.addWidget(close_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.exec_()
    
    def _perform_advanced_search(self, shape_type, tag, has_desc, has_difficult, has_attrs, result_widget):
        """고급 검색 수행"""
        try:
            results = []
            
            # 조건에 따라 검색
            if shape_type and shape_type != "-- 모든 타입 --":
                results = self.annotation_manager.find_by_shape_type(shape_type)
            
            if tag and tag != "-- 모든 태그 --":
                if results:
                    results = [r for r in results if tag in r.get('tags', [])]
                else:
                    results = self.annotation_manager.find_by_tag(tag)
            
            if has_desc:
                if results:
                    results = [r for r in results if r.get('has_descriptions')]
                else:
                    results = self.annotation_manager.find_with_descriptions()
            
            if has_difficult:
                if results:
                    results = [r for r in results if r.get('has_difficult')]
                else:
                    results = self.annotation_manager.find_difficult_annotations()
            
            if has_attrs:
                if results:
                    results = [r for r in results if r.get('has_attributes')]
                else:
                    results = self.annotation_manager.find_with_attributes()
            
            # 결과 표시
            if not any([shape_type and shape_type != "-- 모든 타입 --", 
                       tag and tag != "-- 모든 태그 --",
                       has_desc, has_difficult, has_attrs]):
                result_widget.setPlainText("검색 조건을 선택해주세요.")
                return
            
            result_lines = []
            result_lines.append("=== 검색 결과: {}개 ===\n".format(len(results)))
            
            if results:
                # 라벨별 통계
                label_counts = {}
                for r in results:
                    for label in r.get('labels', []):
                        label_counts[label] = label_counts.get(label, 0) + 1
                
                result_lines.append("라벨별 분포:")
                for label, count in sorted(label_counts.items(), key=lambda x: x[1], reverse=True):
                    result_lines.append(f"  {label}: {count}개")
                
                result_lines.append("\n처음 10개 결과:")
                for i, r in enumerate(results[:10]):
                    result_lines.append(f"{i+1}. {r.get('imagePath', 'N/A')}")
                    result_lines.append(f"   라벨: {', '.join(r.get('labels', []))}")
                    if r.get('description'):
                        result_lines.append(f"   설명: {r.get('description')[:50]}...")
                
                if len(results) > 10:
                    result_lines.append("\n... 및 {}개 더".format(len(results) - 10))
            else:
                result_lines.append("조건에 맞는 어노테이션을 찾을 수 없습니다.")
            
            result_widget.setPlainText("\n".join(result_lines))
            
        except Exception as e:
            result_widget.setPlainText("검색 중 오류가 발생했습니다:\n" + str(e))

    def show_label_detail(self):
        """선택된 라벨의 상세 정보 표시"""
        if not self.annotation_manager:
            QMessageBox.information(self, "정보", "AnnotationManager가 연결되지 않았습니다.")
            return
        
        selected_label = self.label_combo.currentText()
        if not selected_label or selected_label == "모든 라벨":
            QMessageBox.information(self, "안내", "특정 라벨을 선택해주세요.")
            return
        
        try:
            # AnnotationManager를 통해 라벨별 데이터 조회
            label_annotations = self.annotation_manager.find_by_label(selected_label)
            
            detail_text = []
            detail_text.append(f"=== 라벨 '{selected_label}' 상세 정보 ===\n")
            detail_text.append(f"총 어노테이션 수: {len(label_annotations)}개")
            
            # 이미지별 통계
            image_counts = {}
            shape_types = set()
            has_descriptions = 0
            has_difficult = 0
            
            for ann in label_annotations:
                image_path = ann.get('imagePath', '')
                if image_path:
                    image_counts[image_path] = image_counts.get(image_path, 0) + 1
                
                # Shape 타입 수집
                shape_types.update(ann.get('shape_types', []))
                
                # 플래그 정보
                if ann.get('has_descriptions'):
                    has_descriptions += 1
                if ann.get('has_difficult'):
                    has_difficult += 1
            
            detail_text.append(f"관련 이미지 수: {len(image_counts)}개")
            detail_text.append(f"평균 객체/이미지: {len(label_annotations)/max(1, len(image_counts)):.1f}개")
            detail_text.append(f"설명 있는 어노테이션: {has_descriptions}개")
            detail_text.append(f"Difficult 표시: {has_difficult}개")
            
            if shape_types:
                detail_text.append(f"\nShape 타입: {', '.join(shape_types)}")
            
            # 가장 많이 나타나는 이미지들 (Top 10)
            if image_counts:
                detail_text.append(f"\n=== 가장 많이 나타나는 이미지 (Top 10) ===")
                sorted_images = sorted(image_counts.items(), key=lambda x: x[1], reverse=True)
                for img, count in sorted_images[:10]:
                    detail_text.append(f"{img}: {count}개")
            
            # 현재 화면에서의 해당 라벨 정보
            current_count = sum(1 for item in self.filtered_data 
                              for shape in item.get('shapes', []) 
                              if shape.get('label') == selected_label)
            detail_text.append(f"\n현재 화면에 표시된 '{selected_label}': {current_count}개")
            
            # 다이얼로그 표시
            detail_dialog = QMessageBox()
            detail_dialog.setWindowTitle(f"라벨 '{selected_label}' 상세 정보")
            detail_dialog.setIcon(QMessageBox.Information)
            detail_dialog.setText("\n".join(detail_text))
            detail_dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"라벨 상세 정보 조회 중 오류:\n{str(e)}")

    def show_annotation_statistics(self):
        """AnnotationManager를 활용한 확장 통계 정보 표시"""
        if not self.annotation_manager:
            # AnnotationManager가 없으면 기존 통계 사용
            self.show_statistics()
            return
        
        try:
            # AnnotationManager에서 통계 가져오기
            ann_stats = self.annotation_manager.get_annotation_statistics()  # 올바른 메서드명 사용
            all_labels = self.annotation_manager.get_all_labels()
            all_tags = self.annotation_manager.get_all_tags()
            all_shape_types = self.annotation_manager.get_all_shape_types()
            label_distribution = self.annotation_manager.get_label_distribution()
            
            # 현재 화면 데이터 통계
            current_stats = self.calculate_statistics()
            
            # 통계 다이얼로그 생성
            stats_dialog = QMessageBox()
            stats_dialog.setWindowTitle("어노테이션 통계 (MongoDB 연동)")
            stats_dialog.setIcon(QMessageBox.Information)
            
            stats_text = []
            
            # MongoDB 전체 통계
            stats_text.append("=== MongoDB 전체 통계 ===")
            stats_text.append(f"전체 파일: {ann_stats.get('total_files', 0):,}개")
            stats_text.append(f"전체 Shape: {ann_stats.get('total_shapes', 0):,}개")
            stats_text.append(f"고유 라벨: {ann_stats.get('unique_labels', 0):,}개")
            stats_text.append(f"평균 Shape/파일: {ann_stats.get('avg_shapes_per_file', 0):.1f}개")
            stats_text.append(f"설명 있는 파일: {ann_stats.get('files_with_descriptions', 0):,}개")
            stats_text.append(f"태그 있는 파일: {ann_stats.get('files_with_tags', 0):,}개")
            stats_text.append(f"최근 7일 파일: {ann_stats.get('recent_files', 0):,}개")
            
            # 현재 화면 통계 (비교용)
            stats_text.append(f"\n=== 현재 검수 화면 통계 ===")
            stats_text.append(f"표시된 어노테이션: {current_stats['total_annotations']:,}개")
            stats_text.append(f"표시된 이미지: {len(set(item['imagePath'] for item in self.filtered_data)):,}개")
            stats_text.append(f"표시된 객체: {current_stats['total_objects']:,}개")
            stats_text.append(f"평균 객체 수: {current_stats['avg_objects_per_image']:.1f}개/이미지")
            
            # 라벨 분포 (MongoDB 전체)
            stats_text.append(f"\n=== 라벨 분포 (상위 15개) ===")
            sorted_labels = sorted(label_distribution.items(), key=lambda x: x[1], reverse=True)
            for i, (label, count) in enumerate(sorted_labels[:15]):
                # 현재 화면에서의 해당 라벨 개수
                current_count = current_stats['labels'].get(label, 0)
                stats_text.append(f"{label}: {count}개 (전체) / {current_count}개 (화면)")
            if len(label_distribution) > 15:
                stats_text.append(f"... 및 {len(label_distribution) - 15}개 더")
            
            # Shape 타입 통계
            if all_shape_types:
                stats_text.append(f"\n=== Shape 타입 (총 {len(all_shape_types)}개) ===")
                for shape_type in all_shape_types:
                    stats_text.append(f"- {shape_type}")
            
            # 태그 통계
            if all_tags:
                stats_text.append(f"\n=== 태그 (총 {len(all_tags)}개) ===")
                for i, tag in enumerate(all_tags[:10]):  # 최대 10개만 표시
                    stats_text.append(f"- {tag}")
                if len(all_tags) > 10:
                    stats_text.append(f"... 및 {len(all_tags) - 10}개 더")
            
            # 검수 상태별 통계 (현재 화면)
            stats_text.append(f"\n=== 검수 상태별 (현재 화면) ===")
            for status, count in current_stats['review_status'].items():
                stats_text.append(f"{status}: {count}개")
            
            # 검색 기능 안내
            stats_text.append(f"\n=== 고급 검색 기능 ===")
            stats_text.append("• 라벨별 검색 가능")
            stats_text.append("• Shape 타입별 검색 가능")
            stats_text.append("• 태그별 검색 가능")
            stats_text.append("• 설명/Attributes/플래그 여부로 필터링 가능")
            stats_text.append("\n※ MongoDB에서 실시간으로 데이터를 가져옵니다.")
            
            stats_dialog.setText("\n".join(stats_text))
            stats_dialog.exec_()
            
        except Exception as e:
            print(f"어노테이션 통계 조회 실패: {e}")
            # 폴백: 기존 통계 표시
            self.show_statistics()
    
    def show_statistics(self):
        """통계 정보 표시"""
        # 현재 필터된 데이터(승인 완료 제외 포함)를 기준으로 통계 계산
        stats = self.calculate_statistics()

        stats_dialog = QMessageBox()
        stats_dialog.setWindowTitle("어노테이션 통계")
        stats_dialog.setIcon(QMessageBox.Information)

        stats_text = []
        stats_text.append("=== 전체 통계 ===")
        stats_text.append(f"총 어노테이션: {stats['total_annotations']}개")
        stats_text.append(f"총 이미지: {len(set(item['imagePath'] for item in self.filtered_data))}개")
        stats_text.append(f"총 객체: {stats['total_objects']}개")
        stats_text.append(f"평균 객체 수: {stats['avg_objects_per_image']:.1f}개/이미지")

        stats_text.append("\n=== 검수 상태별 ===")
        for status, count in stats['review_status'].items():
            stats_text.append(f"{status}: {count}개")

        stats_text.append("\n=== 라벨별 통계 ===")
        for label, count in stats['labels'].items():
            stats_text.append(f"{label}: {count}개")

        # 불필요 항목 제거: 이미지 크기, 어려운 객체, 설명 있는 객체

        stats_dialog.setText("\n".join(stats_text))
        stats_dialog.exec_()
    
    def calculate_statistics(self):
        """통계 계산 - 현재 화면 기준(승인 완료 제외)"""
        data = self.filtered_data
        stats = {
            'total_annotations': len(data),
            'total_objects': 0,
            'review_status': {},
            'labels': {},
        }
        
        for item in data:
            # 객체 수 계산
            shapes = item.get('shapes', [])
            stats['total_objects'] += len(shapes)
            
            # 검수 상태별 집계
            status = item.get('review_status', '1차 검수 요청 전')
            stats['review_status'][status] = stats['review_status'].get(status, 0) + 1
            
            # 라벨별 집계
            for shape in shapes:
                label = shape.get('label', '알 수 없음')
                stats['labels'][label] = stats['labels'].get(label, 0) + 1
        
        # 평균 계산
        stats['avg_objects_per_image'] = stats['total_objects'] / max(1, stats['total_annotations'])
        
        return stats
    
    def show_annotation_detail(self, item):
        """어노테이션 상세 정보 표시 (테이블 더블클릭)"""
        row = item.row()
        if row < len(self.filtered_data):
            annotation_data = self.filtered_data[row]
            dialog = AnnotationDetailDialog(annotation_data, self)
            dialog.exec_()
    
    def handle_action(self, annotation_id, action_type):
        """작업 버튼 처리 - 개선된 워크플로우 (Mongo 반영)"""
        target = next((x for x in self.sample_data if x.get('_id') == annotation_id), None)
        if not target:
            return
        now = datetime.now()
        new_status = None
        if action_type == "request_first":
            new_status = "1차 검수 요청"
        elif action_type == "complete_first":
            new_status = "1차 검수 완료"
        elif action_type == "reject_first":
            new_status = "1차 검수 요청 전"
        elif action_type == "request_second":
            new_status = "2차 검수 요청"
        elif action_type == "complete_second":
            new_status = "2차 검수 완료"
        elif action_type == "reject_second":
            new_status = "1차 검수 완료"
        elif action_type == "final_approve":
            new_status = "최종 승인"
        elif action_type == "view_image":
            self.open_image_and_label(target)
            return
        elif action_type == "delete":
            reply = QMessageBox.question(
                self, "삭제 확인",
                f"이미지 {target.get('imagePath', 'N/A')}의 모든 어노테이션을 삭제하시겠습니까?"
            )
            if reply != QMessageBox.Yes:
                return
            try:
                # AnnotationManager를 통해 삭제
                if self.annotation_manager and target.get('imagePath'):
                    self.annotation_manager.delete_annotation(target.get('imagePath'))
            except Exception as e:
                print(f"MongoDB 삭제 실패: {e}")
            self.sample_data = [x for x in self.sample_data if x.get('_id') != target.get('_id')]
            self.filter_data()
            QMessageBox.information(self, "삭제 완료", "어노테이션이 삭제되었습니다.")
            return

        # '반려' 요청 처리 (이전 단계로 되돌림)
        if action_type == "reject_flow":
            cur = target.get('review_status', '1차 검수 요청 전')
            prev_map = {
                '1차 검수 요청 전': '1차 검수 요청 전',  # 더 이전 단계 없음
                '1차 검수 요청': '1차 검수 요청 전',
                '1차 검수 완료': '1차 검수 요청',
                '2차 검수 요청': '1차 검수 완료',
                '2차 검수 완료': '2차 검수 요청',
            }
            new_status = prev_map.get(cur, '1차 검수 요청 전')
        
        if new_status:
            try:
                # AnnotationManager를 통해 MongoDB 업데이트
                if self.annotation_manager and target.get('imagePath'):
                    # 어노테이션 데이터에 검수 상태 추가
                    updated_annotation = target.copy()
                    updated_annotation['review_status'] = new_status
                    updated_annotation['updated_at'] = now
                    
                    # MongoDB 업데이트
                    self.annotation_manager.update_annotation(
                        target.get('imagePath'), 
                        updated_annotation
                    )
            except Exception as e:
                print(f"MongoDB 상태 업데이트 실패: {e}")
            
            # 로컬 데이터 업데이트
            target['review_status'] = new_status
            target['updated_at'] = now
            if new_status == "최종 승인":
                self.sample_data = [x for x in self.sample_data if x.get('_id') != target.get('_id')]
            self.filter_data()
            
            feedback = {
                "1차 검수 요청": (QMessageBox.Information, "검수 요청", "1차 검수가 요청되었습니다."),
                "1차 검수 완료": (QMessageBox.Information, "검수 완료", "1차 검수가 완료되었습니다."),
                "2차 검수 요청": (QMessageBox.Information, "검수 요청", "2차 검수가 요청되었습니다."),
                "2차 검수 완료": (QMessageBox.Information, "검수 완료", "2차 검수가 완료되었습니다."),
                "1차 검수 요청 전": (QMessageBox.Warning, "검수 거부", "1차 검수가 거부되어 다시 요청 전 상태로 돌아갑니다."),
                "최종 승인": (QMessageBox.Information, "최종 승인", "어노테이션이 최종 승인되었습니다."),
            }.get(new_status)
            if feedback:
                icon, title, text = feedback
                QMessageBox(icon, title, text, parent=self).exec_()
    
    def open_image_and_label(self, annotation_data):
        """🚀 최적화된 이미지 경로 조회 및 라벨링 툴 실행"""
        import os
        import subprocess
        try:
            print(f"\n🔍 DB 검수 파일 열기 - 디버깅 정보:")
            print(f"  annotation_data keys: {list(annotation_data.keys())}")
            print(f"  imagePath: {annotation_data.get('imagePath')}")
            print(f"  image_file_path: {annotation_data.get('image_file_path')}")
            print(f"  image_exists: {annotation_data.get('image_exists')}")
            print(f"  json_file_path: {annotation_data.get('json_file_path')}")
            
            # 🚀 Ultra Fast 파일 경로 찾기 (강화된 버전)
            
            # 1️⃣ 캐시된 데이터에서 먼저 확인 (가장 빠름)
            file_path = annotation_data.get('image_file_path', '')
            image_exists = annotation_data.get('image_exists', None)
            
            if file_path and image_exists is True:
                print(f"✅ 캐시된 경로 사용: {file_path}")
                if os.path.exists(file_path):
                    self._launch_labeling_tool(file_path)
                    return
                else:
                    print(f"⚠️ 캐시된 정보와 다름 - 파일이 실제로 없음: {file_path}")
            
            # 2️⃣ imagePath 직접 확인 (빠름)
            image_path = annotation_data.get('imagePath')
            if image_path and os.path.exists(image_path):
                print(f"✅ imagePath 직접 사용: {image_path}")
                self._launch_labeling_tool(image_path)
                return
            
            # 3️⃣ 다양한 경로 패턴 시도 (강화된 검색)
            possible_paths = []
            
            # JSON 파일에서 이미지 경로 추정
            json_path = annotation_data.get('json_file_path', '')
            if json_path:
                # JSON과 같은 디렉토리에서 이미지 찾기
                json_dir = os.path.dirname(json_path)
                json_name = os.path.splitext(os.path.basename(json_path))[0]
                
                # 일반적인 이미지 확장자들
                image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']
                for ext in image_extensions:
                    possible_paths.append(os.path.join(json_dir, json_name + ext))
            
            # imagePath가 있지만 파일이 없는 경우, 다른 확장자 시도
            if image_path:
                base_path = os.path.splitext(image_path)[0]
                image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']
                for ext in image_extensions:
                    possible_paths.append(base_path + ext)
            
            # 가능한 경로들 확인
            for path in possible_paths:
                if path and os.path.exists(path):
                    print(f"✅ 추정 경로에서 발견: {path}")
                    self._launch_labeling_tool(path)
                    return
            
            print(f"🔍 모든 경로 시도 실패, 가능한 경로들:")
            for i, path in enumerate(possible_paths[:10]):  # 처음 10개만 표시
                print(f"  {i+1}. {path} {'✅' if os.path.exists(path) else '❌'}")
            
            # 4️⃣ MongoDB에서 빠른 조회 (인덱스 활용)
            if self.annotation_manager:
                image_path_key = annotation_data.get('imagePath') or annotation_data.get('json_file_name', '')
                if image_path_key:
                    print(f"🔍 MongoDB에서 경로 조회 중: {image_path_key}")
                    
                    # 빠른 경로 조회 (인덱스 활용)
                    path_info = self.annotation_manager.get_image_path_fast(
                        image_path_key, 
                        "imagePath" if annotation_data.get('imagePath') else "json_file_name"
                    )
                    
                    if path_info:
                        file_path = path_info.get('image_file_path', '')
                        if file_path and path_info.get('image_exists', False):
                            print(f"✅ DB에서 경로 발견: {file_path}")
                            if os.path.exists(file_path):
                                self._launch_labeling_tool(file_path)
                                return
                            else:
                                print(f"⚠️ DB 정보와 다름 - 파일이 실제로 없음: {file_path}")
            
            # 5️⃣ 폴백: 경로 추정 및 파일 시스템 검색 (느림)
            print("⚠️ 폴백 모드: 파일 시스템 검색")
            
            # JSON 파일 경로에서 이미지 파일 경로 추정
            json_path = annotation_data.get('json_file_path', '')
            if json_path and os.path.exists(json_path):
                json_dir = os.path.dirname(json_path)
                image_name = os.path.basename(annotation_data.get('imagePath', ''))
                if image_name:
                    possible_path = os.path.join(json_dir, image_name)
                    if os.path.exists(possible_path):
                        print(f"✅ 추정 경로에서 발견: {possible_path}")
                        self._launch_labeling_tool(possible_path)
                        return
            
            # 🚨 모든 방법 실패 - 사용자 친화적 에러 메시지
            print(f"❌ 모든 경로 검색 실패")
            
            error_msg = (
                f"🔍 DB 검수 파일을 찾을 수 없습니다.\n\n"
                f"� 검색된 정보:\n"
                f"• imagePath: {annotation_data.get('imagePath', 'N/A')}\n"
                f"• image_file_path: {annotation_data.get('image_file_path', 'N/A')}\n"
                f"• json_file_path: {annotation_data.get('json_file_path', 'N/A')}\n"
                f"• image_exists 캐시: {annotation_data.get('image_exists', 'N/A')}\n\n"
                f"� 해결 방법:\n"
                f"1. 이미지 파일이 실제로 존재하는지 확인\n"
                f"2. JSON 파일과 이미지 파일이 같은 폴더에 있는지 확인\n"
                f"3. 파일 경로에 특수문자나 한글이 포함되어 있지 않은지 확인\n"
                f"4. 파일 권한 문제가 없는지 확인\n\n"
                f"💡 Ultra Fast 시스템이 파일을 찾기 위해 모든 가능한 경로를 검색했지만,\n"
                f"   해당 파일을 발견할 수 없었습니다."
            )
            
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "DB 검수 파일 찾기 실패", error_msg)
                
        except Exception as e:
            print(f"❌ open_image_and_label 에러: {str(e)}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "DB 검수 파일 열기 오류", f"DB 검수 파일 열기 중 오류가 발생했습니다:\n{str(e)}")
    
    def _launch_labeling_tool(self, file_path):
        """🚀 Ultra Fast 라벨링 툴 실행 (최적화된 버전)"""
        import os
        import time
        import sys
        import subprocess
        
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"파일이 존재하지 않습니다: {file_path}")
            
            start_time = time.time()
            print(f"\n🚀 Ultra Fast DB 검수 파일 열기: {file_path}")
            
            # 1. 🔥 Ultra Fast 인스턴스 관리자 우선 시도 (가장 빠름)
            try:
                # anylabeling 패키지 경로 추가
                repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if repo_root not in sys.path:
                    sys.path.insert(0, repo_root)
                
                from anylabeling.services.app_instance_manager import open_file_with_instance_manager
                
                success = open_file_with_instance_manager(file_path)
                if success:
                    elapsed = time.time() - start_time
                    print(f"✅ Ultra Fast 인스턴스 실행 완료 ({elapsed:.2f}초)")
                    
                    QMessageBox.information(
                        self, 
                        "🚀 Ultra Fast DB 검수", 
                        f"Ultra Fast 모드로 DB 검수 파일이 즉시 열렸습니다! ⚡\n\n"
                        f"📁 파일: {os.path.basename(file_path)}\n"
                        f"📍 경로: {file_path}\n"
                        f"⏱️ 실행 시간: {elapsed:.2f}초\n\n"
                        f"💡 기존 인스턴스 재사용으로 초고속 실행!"
                    )
                    return
                    
            except Exception as e:
                print(f"⚠️ Ultra Fast 인스턴스 실행 실패, 기본 방식 사용: {e}")
            
            # 2. 폴백: 기본 방식 (하지만 Ultra Fast 최적화 적용)
            print("📌 기본 방식으로 실행 (Ultra Fast 최적화 적용)")
            
            # anylabeling 앱 실행 (Ultra Fast 모드)
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            app_path = os.path.join(repo_root, 'anylabeling', 'app.py')
            
            if os.path.exists(app_path):
                # Ultra Fast 플래그는 없지만 이미 최적화되어 있음
                subprocess.Popen([sys.executable, app_path, file_path])
            else:
                # 대안: anylabeling 모듈로 실행
                subprocess.Popen([sys.executable, '-m', 'anylabeling.app', file_path])
            
            elapsed = time.time() - start_time
            print(f"✅ 기본 방식 실행 완료 ({elapsed:.2f}초)")
            
            QMessageBox.information(
                self, 
                "DB 검수 파일 열기", 
                f"Ultra Fast 최적화가 적용된 라벨링 툴이 실행되었습니다.\n\n"
                f"📁 파일: {os.path.basename(file_path)}\n"
                f"📍 경로: {file_path}\n"
                f"⏱️ 실행 시간: {elapsed:.2f}초\n\n"
                f"� Ultra Fast 최적화로 빠르게 시작됩니다!"
            )
                
        except Exception as e:
            print(f"❌ DB 검수 파일 열기 실패: {e}")
            QMessageBox.critical(
                self, 
                "DB 검수 파일 열기 실패", 
                f"DB 검수 파일을 열 수 없습니다:\n{str(e)}\n\n"
                f"파일: {file_path}\n\n"
                f"💡 파일 경로와 권한을 확인해주세요."
            )
            raise Exception(f"라벨링 툴 실행 실패: {str(e)}")
    
    def edit_annotation(self, annotation_data):
        """어노테이션 편집 다이얼로그"""
        dialog = AnnotationEditDialog(annotation_data, self)
        if dialog.exec_() == dialog.Accepted:
            # 편집된 내용을 반영
            self.filter_data()
    
    def apply_styles(self):
        """전체 스타일 적용"""
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #667eea, stop:1 #764ba2);
            }
            QWidget {
                font-family: 'Malgun Gothic', sans-serif;
            }
            QComboBox, QLineEdit, QDateEdit {
                padding: 10px;
                border: 2px solid #d1d5db;
                border-radius: 8px;
                font-size: 14px;
                background: white;
                min-height: 20px;
            }
            QComboBox:focus, QLineEdit:focus, QDateEdit:focus {
                border-color: #4f46e5;
            }
            QLabel {
                font-size: 14px;
                font-weight: 500;
                color: #374151;
            }
        """)

class AnnotationEditDialog(QMessageBox):
    """어노테이션 편집 다이얼로그"""
    def __init__(self, annotation_data, parent=None):
        super().__init__(parent)
        self.annotation_data = annotation_data
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("어노테이션 편집")
        self.setIcon(QMessageBox.Question)
        self.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        
        # 편집 가능한 정보만 표시
        edit_info = []
        edit_info.append(f"파일명: {self.annotation_data.get('imagePath', 'N/A')}")
        edit_info.append(f"현재 검수 상태: {self.annotation_data.get('review_status', '1차 검수 요청 전')}")
        edit_info.append(f"검수자: {self.annotation_data.get('reviewer', '-')}")
        edit_info.append(f"객체 개수: {len(self.annotation_data.get('shapes', []))}")
        edit_info.append("\n편집 기능은 실제 구현에서 더 상세한 폼을 제공할 수 있습니다.")
        edit_info.append("예: 라벨 수정, 박스 좌표 조정, 설명 추가/수정 등")
        
        self.setText("\n".join(edit_info))

def main():
    app = QApplication(sys.argv)
    
    # 한글 폰트 설정
    font = QFont("Malgun Gothic", 9)
    app.setFont(font)
    
    window = LabelMeReviewSearch()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
