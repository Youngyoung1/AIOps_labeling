# -*- coding: utf-8 -*-
import sys
import json
import random
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, 
                            QComboBox, QLineEdit, QLabel, QDateEdit, QGroupBox, 
                            QFormLayout, QHeaderView, QMessageBox, QProgressBar,
                            QFrame, QSizePolicy, QSpacerItem, QTextEdit)
from PyQt5.QtCore import Qt, QDate, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap, QIcon

# MongoDB 스토리지 연동 (가능하면 사용)
try:
    from anylabeling.services.storage.mongodb_client import MongoStorage
except Exception:
    MongoStorage = None

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
            
            # 거부 버튼 추가
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
            reject_btn.clicked.connect(lambda: self.review_requested.emit(self.annotation_id, "reject_first"))
            layout.addWidget(reject_btn)
            
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
            
            # 사진 보기 버튼
            view_btn = QPushButton("사진 보기")
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
        details.append(f"\n=== 검출된 객체 ({len(shapes)}개) ===")
        
        for i, shape in enumerate(shapes):
            details.append(f"\n[객체 {i+1}]")
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
        # 데이터 소스 초기화 (Mongo 우선, 실패시 샘플)
        self.sample_data = []
        self.filtered_data = []
        self.mongo = None
        self._init_mongo_and_load()
        self.setup_ui()
    
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
        
        # 초기 데이터 로드
        self.load_table_data()
        # 라벨 필터 동적 갱신
        self._refresh_label_filter_items()
        
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
            "모든 상태", "1차 검수 요청 전", "1차 검수 요청", "1차 검수 완료", 
            "2차 검수 요청", "2차 검수 완료"
        ])
        self.review_status_combo.currentTextChanged.connect(self.filter_data)
        
        # 라벨 (검출된 객체)
        self.label_combo = QComboBox()
        # 최초엔 기본값만, 데이터 로드 후 동적으로 채움
        self.label_combo.addItems(["모든 라벨"]) 
        self.label_combo.currentTextChanged.connect(self.filter_data)
        
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
        
        # 폼에 추가
        layout.addRow("검수 상태:", self.review_status_combo)
        layout.addRow("객체 라벨:", self.label_combo)
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
        
        stats_btn = QPushButton("📊 통계 보기")
        stats_btn.clicked.connect(self.show_statistics)
        stats_btn.setStyleSheet(self.get_button_style("#7c2d12", "#6b21a8"))
        
        button_layout.addWidget(search_btn)
        button_layout.addWidget(reset_btn)
        button_layout.addWidget(export_btn)
        button_layout.addWidget(stats_btn)
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
    def _init_mongo_and_load(self):
        """Mongo 연결 시도 후 데이터 로드. 실패 시 샘플 데이터 사용"""
        try:
            if MongoStorage is None:
                raise RuntimeError("MongoStorage 사용 불가")
            self.mongo = MongoStorage()
            if not self.mongo.test_connection():
                raise RuntimeError("MongoDB 연결 실패")
            self._load_data_from_mongo()
        except Exception:
            # 폴백: 샘플 데이터
            self.sample_data = self.generate_labelme_data()
            self.filtered_data = [
                item for item in self.sample_data
                if item.get('review_status', '') != '최종 승인'
            ]

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
        """MongoDB에서 이미지 기준으로 데이터 집계 후 self.sample_data 채움"""
        from datetime import datetime as _dt
        pipeline = [
            {"$lookup": {
                "from": "images",
                "localField": "image_id",
                "foreignField": "image_id",
                "as": "image_info"
            }},
            {"$unwind": {"path": "$image_info", "preserveNullAndEmptyArrays": True}},
            {"$project": {
                "image_id": 1,
                "label": 1,
                "review_status": 1,
                "created_at": 1,
                "imagePath": {"$ifNull": ["$image_info.filename", "$image_id"]},
                "file_path": {"$ifNull": ["$image_info.file_path", "$image_info.path"]}
            }},
            {"$group": {
                "_id": "$image_id",
                "labels": {"$push": "$label"},
                "statuses": {"$push": "$review_status"},
                "created_at": {"$min": "$created_at"},
                "imagePath": {"$first": "$imagePath"},
                "file_path": {"$first": "$file_path"}
            }}
        ]
        try:
            aggr = list(self.mongo.annotations.aggregate(pipeline)) if self.mongo else []
        except Exception:
            aggr = []
        items = []
        for doc in aggr:
            statuses = [s for s in (doc.get("statuses") or []) if s]
            overall = self._resolve_overall_status(statuses)
            if overall == "최종 승인":
                continue  # UI에서 숨김
            labels = doc.get("labels") or []
            item = {
                "_id": str(doc.get("_id")),  # image_id를 행 ID로 사용
                "shapes": [{"label": l} for l in labels],
                "imagePath": doc.get("imagePath") or str(doc.get("_id")),
                "file_path": doc.get("file_path") or "",
                "review_status": overall,
                "created_at": doc.get("created_at") or _dt.now(),
                "reviewer": "",
            }
            items.append(item)
        # 없으면 폴백
        if not items:
            self.sample_data = self.generate_labelme_data()
            self.filtered_data = [
                item for item in self.sample_data
                if item.get('review_status', '') != '최종 승인'
            ]
        else:
            self.sample_data = items
            self.filtered_data = items[:]

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
        self.table.setRowCount(len(self.filtered_data))
        
        for i, item in enumerate(self.filtered_data):
            # 파일명
            self.table.setItem(i, 0, QTableWidgetItem(item.get('imagePath', '')))
            
            # 주요 라벨 (가장 많은 라벨)
            labels = [shape.get('label', '') for shape in item.get('shapes', [])]
            main_label = max(set(labels), key=labels.count) if labels else "없음"
            self.table.setItem(i, 1, QTableWidgetItem(main_label))
            
            # 상태 배지
            status_widget = StatusBadgeWidget(item.get('review_status', '1차 검수 요청 전'))
            self.table.setCellWidget(i, 2, status_widget)
            
            # 생성일시
            created_at = item.get('created_at', datetime.now())
            self.table.setItem(i, 3, QTableWidgetItem(created_at.strftime('%Y-%m-%d %H:%M')))
            
            # 작업 버튼
            action_widget = ActionButtonWidget(item['_id'], item.get('review_status', '1차 검수 요청 전'))
            action_widget.review_requested.connect(self.handle_action)
            self.table.setCellWidget(i, 4, action_widget)
        
        # 컬럼 크기 조정
        self.table.resizeColumnsToContents()
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
    
    def filter_data(self):
        """데이터 필터링"""
        filtered = []
        
        for item in self.sample_data:
            # 승인 완료 항목은 항상 숨김
            if item.get('review_status', '') == '최종 승인':
                continue
            # 검수 상태 필터
            if (self.review_status_combo.currentText() != "모든 상태" and 
                item.get('review_status', '1차 검수 요청 전') != self.review_status_combo.currentText()):
                continue
            
            # 라벨 필터
            if self.label_combo.currentText() != "모든 라벨":
                labels = [shape.get('label', '') for shape in item.get('shapes', [])]
                if self.label_combo.currentText() not in labels:
                    continue
            
            # 파일명 필터
            if (self.filename_edit.text().strip() and 
                self.filename_edit.text().strip().lower() not in item.get('imagePath', '').lower()):
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
                if self.mongo:
                    self.mongo.delete_multiple_annotations({"image_id": target.get('_id')})
            except Exception:
                pass
            self.sample_data = [x for x in self.sample_data if x.get('_id') != target.get('_id')]
            self.filter_data()
            QMessageBox.information(self, "삭제 완료", "어노테이션이 삭제되었습니다.")
            return

        if new_status:
            try:
                if self.mongo:
                    self.mongo.annotations.update_many(
                        {"image_id": target.get('_id')},
                        {"$set": {"review_status": new_status, "updated_at": now}}
                    )
            except Exception:
                pass
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
        """MongoDB 경로를 이용해 라벨링 툴 실행"""
        import os
        import subprocess
        try:
            # DB에서 저장한 실제 경로 우선
            file_path = annotation_data.get('file_path') or ""
            if not file_path and self.mongo:
                filename = annotation_data.get('imagePath')
                img_doc = self.mongo.images.find_one({"filename": filename})
                if img_doc:
                    file_path = img_doc.get('file_path') or img_doc.get('path')
            if not file_path:
                QMessageBox.warning(self, "경로 없음", "이미지 경로를 찾을 수 없습니다.")
                return
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "파일 없음", f"파일을 찾을 수 없습니다:\n{file_path}")
                return
            # anylabeling/app.py 실행
            repo_root = os.path.dirname(os.path.abspath(__file__))
            app_path = os.path.join(repo_root, 'anylabeling', 'app.py')
            if os.path.exists(app_path):
                subprocess.Popen([sys.executable, app_path, file_path])
            else:
                subprocess.Popen([sys.executable, '-m', 'anylabeling.app', file_path])
        except Exception as e:
            QMessageBox.critical(self, "오류", f"라벨링 툴 실행 중 오류: {str(e)}")
    
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
