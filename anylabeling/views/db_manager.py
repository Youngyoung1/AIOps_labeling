"""MongoDB 관리 UI 컴포넌트"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import PyQt5.QtCore as QtCore
from PyQt5.QtGui import *
from datetime import datetime, timedelta
import os
import threading
import time
import json
from bson import ObjectId
from anylabeling.services.app_instance_manager import (
    open_file_with_instance_manager,
)

class DBManagerDialog(QDialog):
    """MongoDB 관리 메인 다이얼로그"""
    
    def __init__(self,  mongo_storage, parent=None):
        super().__init__(parent)
        self.mongo_storage = mongo_storage
        self.setWindowTitle("데이터베이스 관리")
        self.setMinimumSize(1200, 800)
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 탭 위젯 생성
        self.tab_widget = QTabWidget()
        
        # 1. 프로젝트 관리 탭
        self.tab_widget.addTab(self.create_project_tab(), "프로젝트")
        
        # 2. 이미지 관리 탭  
        self.tab_widget.addTab(self.create_image_tab(), "이미지")
        
        # 3. 어노테이션 관리 탭
        self.tab_widget.addTab(self.create_annotation_tab(), "어노테이션")
        
        # 4. 통계 탭
        self.tab_widget.addTab(self.create_stats_tab(), "통계")
        
        layout.addWidget(self.tab_widget)
        
        # 하단 버튼
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("새로고침")
        refresh_btn.clicked.connect(self.load_data)
        button_layout.addWidget(refresh_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def create_project_tab(self):
        """프로젝트 관리 탭"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 상단 툴바
        toolbar = QHBoxLayout()
        
        # 새 프로젝트 버튼
        new_btn = QPushButton("새 프로젝트")
        new_btn.clicked.connect(self.create_new_project)
        toolbar.addWidget(new_btn)
        
        # 검색바
        self.project_search_edit = QLineEdit()
        self.project_search_edit.setPlaceholderText("프로젝트 검색...")
        self.project_search_edit.textChanged.connect(self.search_projects)
        toolbar.addWidget(self.project_search_edit)
        
        toolbar.addStretch()
        
        layout.addLayout(toolbar)
        
        # 프로젝트 테이블
        self.project_table = QTableWidget()
        self.project_table.setColumnCount(6)
        self.project_table.setHorizontalHeaderLabels([
            "프로젝트명", "상태", "이미지 수", "진행률", "생성일", "작업"
        ])
        self.project_table.horizontalHeader().setStretchLastSection(True)
        self.project_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        layout.addWidget(self.project_table)
        
        widget.setLayout(layout)
        return widget
    
    def create_image_tab(self):
        """이미지 관리 탭"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 필터 영역
        filter_layout = QHBoxLayout()
        
        # 상태 필터
        self.status_combo = QComboBox()
        self.status_combo.addItems([
            "전체", "1차 검수 요청 전", "진행중", "완료", 
            "1차 검수 요청", "1차 검수 완료", 
            "2차 검수 요청", "2차 검수 완료", "최종 승인"
        ])
        self.status_combo.currentTextChanged.connect(self.filter_images)
        filter_layout.addWidget(QLabel("상태:"))
        filter_layout.addWidget(self.status_combo)
        
        # 검색
        self.image_search_edit = QLineEdit()
        self.image_search_edit.setPlaceholderText("파일명 검색...")
        self.image_search_edit.textChanged.connect(self.search_images)
        filter_layout.addWidget(self.image_search_edit)
        
        filter_layout.addStretch()
        
        # 배치 작업 버튼
        batch_btn = QPushButton("배치 작업")
        batch_btn.clicked.connect(self.show_batch_operations)
        filter_layout.addWidget(batch_btn)

        # 모두 보기 버튼: 캐시된 모든 이미지 파일을 인스턴스 매니저로 빠르게 연다
        open_all_btn = QPushButton("모두 보기")
        open_all_btn.clicked.connect(self.confirm_and_open_all_images)
        filter_layout.addWidget(open_all_btn)
        
        layout.addLayout(filter_layout)
        
        # 이미지 테이블
        self.image_table = QTableWidget()
        self.image_table.setColumnCount(6)
        self.image_table.setHorizontalHeaderLabels([
            "파일명", "상태", "크기", "업로드일", "어노테이션 수", "작업"
        ])
        self.image_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        layout.addWidget(self.image_table)
        
        widget.setLayout(layout)
        return widget
    
    def create_annotation_tab(self):
        """어노테이션 관리 탭"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 상단 검색 및 필터
        search_layout = QHBoxLayout()
        
        # 고급 검색
        search_btn = QPushButton("고급 검색")
        search_btn.clicked.connect(self.show_advanced_search)
        search_layout.addWidget(search_btn)
        
        # 카테고리 필터
        self.category_combo = QComboBox()
        self.category_combo.addItem("모든 카테고리")
        self.category_combo.currentTextChanged.connect(self.filter_annotations)
        search_layout.addWidget(QLabel("카테고리:"))
        search_layout.addWidget(self.category_combo)
        
        # 신뢰도 필터
        self.confidence_slider = QSlider(Qt.Horizontal)
        self.confidence_slider.setRange(0, 100)
        self.confidence_slider.setValue(0)
        self.confidence_label = QLabel("신뢰도: 0%+")
        self.confidence_slider.valueChanged.connect(self.update_confidence_filter)
        search_layout.addWidget(self.confidence_label)
        search_layout.addWidget(self.confidence_slider)
        
        search_layout.addStretch()
        
        # 내보내기 버튼
        export_btn = QPushButton("내보내기")
        export_btn.clicked.connect(self.export_annotations)
        search_layout.addWidget(export_btn)
        
        layout.addLayout(search_layout)
        
        # 어노테이션 테이블
        self.annotation_table = QTableWidget()
        self.annotation_table.setColumnCount(9)
        self.annotation_table.setHorizontalHeaderLabels([
            "이미지", "라벨", "카테고리", "신뢰도", "번호판", "검수 상태", "검수자", "생성일", "작업"
        ])
        
        layout.addWidget(self.annotation_table)
        
        widget.setLayout(layout)
        return widget
    
    def create_stats_tab(self):
        """통계 탭"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 통계 카드들
        stats_layout = QHBoxLayout()
        
        # 전체 통계 카드들
        self.total_images_card = self.create_stat_card("전체 이미지", "0")
        self.labeled_images_card = self.create_stat_card("라벨링 완료", "0")
        self.progress_card = self.create_stat_card("진행률", "0%")
        self.annotations_card = self.create_stat_card("총 어노테이션", "0")
        
        stats_layout.addWidget(self.total_images_card)
        stats_layout.addWidget(self.labeled_images_card) 
        stats_layout.addWidget(self.progress_card)
        stats_layout.addWidget(self.annotations_card)
        
        layout.addLayout(stats_layout)
        
        # 카테고리별 통계 테이블
        category_group = QGroupBox("카테고리별 통계")
        category_layout = QVBoxLayout()
        
        self.category_stats_table = QTableWidget()
        self.category_stats_table.setColumnCount(3)
        self.category_stats_table.setHorizontalHeaderLabels(["카테고리", "개수", "평균 신뢰도"])
        category_layout.addWidget(self.category_stats_table)
        
        category_group.setLayout(category_layout)
        layout.addWidget(category_group)
        
        # 번호판 통계 테이블
        plate_group = QGroupBox("번호판 카테고리 통계")
        plate_layout = QVBoxLayout()
        
        self.plate_stats_table = QTableWidget()
        self.plate_stats_table.setColumnCount(2)
        self.plate_stats_table.setHorizontalHeaderLabels(["번호판 타입", "개수"])
        plate_layout.addWidget(self.plate_stats_table)
        
        plate_group.setLayout(plate_layout)
        layout.addWidget(plate_group)
        
        # 검수 상태별 통계 테이블
        review_group = QGroupBox("검수 상태별 통계")
        review_layout = QVBoxLayout()
        
        self.review_stats_table = QTableWidget()
        self.review_stats_table.setColumnCount(2)
        self.review_stats_table.setHorizontalHeaderLabels(["검수 상태", "개수"])
        review_layout.addWidget(self.review_stats_table)
        
        review_group.setLayout(review_layout)
        layout.addWidget(review_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_stat_card(self, title, value):
        """통계 카드 생성"""
        card = QFrame()
        card.setFrameStyle(QFrame.Box)
        card.setStyleSheet("""
            QFrame {
                border: 1px solid #ddd;
                border-radius: 8px;
                background-color: white;
                padding: 16px;
                margin: 4px;
            }
        """)
        
        layout = QVBoxLayout()
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; color: #666; font-size: 12px;")
        
        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        card.setLayout(layout)
        card.value_label = value_label  # 나중에 업데이트할 수 있도록 참조 저장
        return card
    
    def load_data(self):
        """모든 탭의 데이터 로드"""
        self.load_projects()
        self.load_images()
        self.load_annotations()
        self.load_stats()
    
    def load_projects(self):
        """프로젝트 데이터 로드"""
        try:
            projects = self.mongo_storage.get_projects()
            self.project_table.setRowCount(len(projects))
            
            for i, project in enumerate(projects):
                self.project_table.setItem(i, 0, QTableWidgetItem(project.get('name', '')))
                self.project_table.setItem(i, 1, QTableWidgetItem(project.get('status', '')))
                self.project_table.setItem(i, 2, QTableWidgetItem(str(project.get('stats', {}).get('total_images', 0))))
                self.project_table.setItem(i, 3, QTableWidgetItem(f"{project.get('stats', {}).get('progress_percent', 0):.1f}%"))
                self.project_table.setItem(i, 4, QTableWidgetItem(str(project.get('created_at', ''))))
                
                # 작업 버튼
                action_btn = QPushButton("관리")
                self.project_table.setCellWidget(i, 5, action_btn)
            
            self.project_table.resizeColumnsToContents()
            
        except Exception as e:
            print(f"프로젝트 로드 오류: {e}")
    
    def load_images(self):
        """이미지 데이터 로드"""
        try:
            # 모든 이미지 조회 (제한적으로)
            images_cursor = self.mongo_storage.images.find().limit(100)
            images = list(images_cursor)
            # 현재 로드된 이미지 문서 캐시 (빠른 열기용)
            self.image_docs = images
            
            self.image_table.setRowCount(len(images))
            
            for i, image in enumerate(images):
                self.image_table.setItem(i, 0, QTableWidgetItem(image.get('filename', '')))
                self.image_table.setItem(i, 1, QTableWidgetItem(image.get('status', '')))
                self.image_table.setItem(i, 2, QTableWidgetItem(str(image.get('file_size', ''))))
                self.image_table.setItem(i, 3, QTableWidgetItem(str(image.get('uploaded_at', ''))))
                
                # 어노테이션 개수 조회
                ann_count = self.mongo_storage.annotations.count_documents({'image_id': image.get('image_id', '')})
                self.image_table.setItem(i, 4, QTableWidgetItem(str(ann_count)))
                
                # 작업 버튼: 보기 → 빠른 뷰어 실행 (인스턴스/신규 프로세스)
                action_btn = QPushButton("보기")
                # image_id 또는 file_path를 안전하게 캡처
                image_id = image.get('image_id') or image.get('_id')
                action_btn.clicked.connect(
                    lambda checked=False, iid=image_id: self.open_image_in_viewer(iid)
                )
                self.image_table.setCellWidget(i, 5, action_btn)
            
            self.image_table.resizeColumnsToContents()
            
        except Exception as e:
            print(f"이미지 로드 오류: {e}")

    def open_image_in_viewer(self, image_identifier):
        """선택한 이미지 문서를 조회해 빠른 뷰어(인스턴스/신규 프로세스)로 연다."""
        try:
            # image_identifier는 보통 image_id (str). 없으면 _id(ObjectId)일 수 있음.
            image_doc = None
            if isinstance(image_identifier, ObjectId):
                image_doc = self.mongo_storage.images.find_one({'_id': image_identifier})
            else:
                # 우선 image_id로 조회, 실패 시 _id로도 시도
                image_doc = self.mongo_storage.images.find_one({'image_id': image_identifier})
                if not image_doc:
                    try:
                        maybe_oid = ObjectId(image_identifier)
                        image_doc = self.mongo_storage.images.find_one({'_id': maybe_oid})
                    except Exception:
                        pass

            if not image_doc:
                QMessageBox.warning(self, "오류", "이미지 문서를 찾을 수 없습니다.")
                return

            # 파일 경로 결정: file_path 우선, 없으면 filename 사용 (절대경로 기대)
            file_path = image_doc.get('file_path') or image_doc.get('filename')
            if not file_path:
                QMessageBox.warning(self, "오류", "이미지 파일 경로가 없습니다.")
                return

            # 인스턴스 매니저 경유: 기존 인스턴스에 열기 시도 → 실패 시 초경량 새 프로세스
            success = open_file_with_instance_manager(str(file_path))
            # UI 업데이트: 상단 인덱스 텍스트 및 하단 경로 메시지
            try:
                main_win = self.window()
            except Exception:
                main_win = None

            def _update_ui_for_single(path):
                if main_win is None:
                    return
                try:
                    # 상단에 [1/1] filename 형태로 표시
                    if hasattr(main_win, 'set_top_file_index_text'):
                        # 현재 인덱스와 전체 개수 계산
                        total = len(self.image_docs) if hasattr(self, 'image_docs') else 1
                        # path에 해당하는 인덱스 찾기 (1-based)
                        current = 1
                        if hasattr(self, 'image_docs'):
                            for idx, img in enumerate(self.image_docs):
                                img_path = img.get('file_path') or img.get('filename')
                                if img_path == str(path):
                                    current = idx + 1
                                    break
                        main_win.set_top_file_index_text(f"[{current}/{total}] {os.path.basename(path)}")
                    # 하단 상태바에 전체 경로 표시
                    try:
                        if main_win.statusBar():
                            main_win.statusBar().showMessage(str(path), 5000)
                    except Exception:
                        pass
                except Exception:
                    pass

            if success:
                # 큐에 UI 업데이트 작업을 넣음 (메인 스레드에서 실행)
                try:
                    QtCore.QTimer.singleShot(0, lambda p=file_path: _update_ui_for_single(p))
                except Exception:
                    _update_ui_for_single(file_path)
            else:
                QMessageBox.information(self, "알림", "뷰어 실행에 실패했습니다. 경로를 확인해주세요.")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"뷰어 실행 중 오류: {e}")

    def confirm_and_open_all_images(self):
        """사용자 확인 후 캐시된 모든 이미지 파일을 인스턴스로 빠르게 연다."""
        if not hasattr(self, 'image_docs') or not self.image_docs:
            QMessageBox.information(self, "알림", "열 이미지 목록이 없습니다. 먼저 새로고침 해주세요.")
            return

        count = len(self.image_docs)
        reply = QMessageBox.question(
            self,
            "모두 보기 확인",
            f"현재 로드된 {count}개의 이미지를 모두 엽니다. 계속하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # 진행 다이얼로그
        progress = QProgressDialog("이미지 열기 중...", "취소", 0, count, self)
        progress.setWindowTitle("모두 보기")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(200)

        def _open_all():
            opened = 0
            for i, img in enumerate(list(self.image_docs)):
                if progress.wasCanceled():
                    break
                file_path = img.get('file_path') or img.get('filename')
                if not file_path:
                    progress.setValue(i + 1)
                    continue
                # 절대경로로 변환 시도
                try:
                    file_path = os.path.expanduser(str(file_path))
                except Exception:
                    pass

                # 존재 여부 확인
                if not os.path.exists(file_path):
                    progress.setValue(i + 1)
                    continue

                try:
                    success = open_file_with_instance_manager(str(file_path))
                    if success:
                        opened += 1
                        # 메인 윈도우 UI 업데이트 (index 및 상태바)
                        try:
                            main_win = self.window()
                        except Exception:
                            main_win = None

                        def _update(i_local, total_local, p_local):
                            if main_win is None:
                                return
                            try:
                                if hasattr(main_win, 'set_top_file_index_text'):
                                    main_win.set_top_file_index_text(f"[{i_local}/{total_local}] {os.path.basename(p_local)}")
                                try:
                                    if main_win.statusBar():
                                        main_win.statusBar().showMessage(str(p_local), 2000)
                                except Exception:
                                    pass
                            except Exception:
                                pass

                        try:
                            QtCore.QTimer.singleShot(0, lambda ii=i+1, tot=len(self.image_docs), p=file_path: _update(ii, tot, p))
                        except Exception:
                            _update(i+1, len(self.image_docs), file_path)
                except Exception:
                    pass

                progress.setValue(i + 1)
                # 작은 딜레이를 두어 시스템 부하 완화
                time.sleep(0.05)

            progress.close()
            QMessageBox.information(self, "완료", f"열기 시도 완료: {opened}개 열림(성공)")

        thread = threading.Thread(target=_open_all, daemon=True)
        thread.start()
    
    def load_annotations(self):
        """어노테이션 데이터 로드"""
        try:
            annotations = self.mongo_storage.find_annotations()[:100]  # 최대 100개
            
            self.annotation_table.setRowCount(len(annotations))
            
            # 카테고리 콤보박스 업데이트
            categories = set()
            
            for i, annotation in enumerate(annotations):
                # 이미지 정보 조회
                image_info = self.mongo_storage.images.find_one({'image_id': annotation.get('image_id', '')})
                filename = image_info.get('filename', '') if image_info else ''
                
                self.annotation_table.setItem(i, 0, QTableWidgetItem(filename))
                self.annotation_table.setItem(i, 1, QTableWidgetItem(annotation.get('label', '')))
                self.annotation_table.setItem(i, 2, QTableWidgetItem(annotation.get('category', '')))
                self.annotation_table.setItem(i, 3, QTableWidgetItem(f"{annotation.get('confidence', 0):.2f}"))
                
                plate_number = annotation.get('properties', {}).get('plate_number', '')
                self.annotation_table.setItem(i, 4, QTableWidgetItem(plate_number))
                
                # 검수 상태 정보
                review_status = annotation.get('review_status', '1차 검수 요청 전')
                reviewer = annotation.get('reviewer', '')
                self.annotation_table.setItem(i, 5, QTableWidgetItem(review_status))
                self.annotation_table.setItem(i, 6, QTableWidgetItem(reviewer))
                self.annotation_table.setItem(i, 7, QTableWidgetItem(str(annotation.get('created_at', ''))))
                
                # 작업 버튼
                action_layout = QHBoxLayout()
                
                # 검수 상태에 따른 버튼 구성
                if review_status in ['1차 검수 요청 전', '완료']:
                    review1_btn = QPushButton("1차 검수 요청")
                    review1_btn.clicked.connect(lambda checked, aid=annotation.get('_id'): self.request_first_review(aid))
                    action_layout.addWidget(review1_btn)
                elif review_status == '1차 검수 요청':
                    complete1_btn = QPushButton("1차 검수 완료")
                    complete1_btn.clicked.connect(lambda checked, aid=annotation.get('_id'): self.complete_first_review(aid))
                    action_layout.addWidget(complete1_btn)
                elif review_status == '1차 검수 완료':
                    review2_btn = QPushButton("2차 검수 요청")
                    review2_btn.clicked.connect(lambda checked, aid=annotation.get('_id'): self.request_second_review(aid))
                    action_layout.addWidget(review2_btn)
                elif review_status == '2차 검수 요청':
                    complete2_btn = QPushButton("2차 검수 완료")
                    complete2_btn.clicked.connect(lambda checked, aid=annotation.get('_id'): self.complete_second_review(aid))
                    action_layout.addWidget(complete2_btn)
                
                edit_btn = QPushButton("편집")
                delete_btn = QPushButton("삭제")
                action_layout.addWidget(edit_btn)
                action_layout.addWidget(delete_btn)
                
                action_widget = QWidget()
                action_widget.setLayout(action_layout)
                self.annotation_table.setCellWidget(i, 8, action_widget)
                
                # 카테고리 수집
                if annotation.get('category'):
                    categories.add(annotation.get('category'))
            
            # 카테고리 콤보박스 업데이트
            current_category = self.category_combo.currentText()
            self.category_combo.clear()
            self.category_combo.addItem("모든 카테고리")
            self.category_combo.addItems(sorted(categories))
            
            # 이전 선택 복원
            index = self.category_combo.findText(current_category)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
            
            self.annotation_table.resizeColumnsToContents()
            
        except Exception as e:
            print(f"어노테이션 로드 오류: {e}")
    
    def load_stats(self):
        """통계 데이터 로드"""
        try:
            stats = self.mongo_storage.get_database_stats()
            
            # 기본 통계 업데이트
            self.total_images_card.value_label.setText(str(stats.get('total_images', 0)))
            self.labeled_images_card.value_label.setText(str(stats.get('labeled_images', 0)))
            self.progress_card.value_label.setText(f"{stats.get('progress', 0):.1f}%")
            self.annotations_card.value_label.setText(str(stats.get('total_annotations', 0)))
            
            # 검수 상태별 통계 추가
            review_stats = self.mongo_storage.collection_annotations.aggregate([
                {
                    "$group": {
                        "_id": "$review_status",
                        "count": {"$sum": 1}
                    }
                }
            ])
            
            # 검수 상태별 카운트 초기화
            review_counts = {
                "1차 검수 요청 전": 0,
                "1차 검수 요청": 0,
                "1차 검수 완료": 0,
                "2차 검수 요청": 0,
                "2차 검수 완료": 0,
                "최종 승인": 0
            }
            
            # 실제 카운트로 업데이트
            for item in review_stats:
                status = item.get('_id') or "1차 검수 요청 전"
                if status in review_counts:
                    review_counts[status] = item.get('count', 0)
            
            # 검수 통계 표시
            print("검수 상태별 통계:", review_counts)
            
            # 검수 상태별 통계 테이블 업데이트
            self.review_stats_table.setRowCount(len(review_counts))
            for i, (status, count) in enumerate(review_counts.items()):
                self.review_stats_table.setItem(i, 0, QTableWidgetItem(status))
                self.review_stats_table.setItem(i, 1, QTableWidgetItem(str(count)))
            
            # 카테고리별 통계 테이블
            categories = stats.get('categories', [])
            self.category_stats_table.setRowCount(len(categories))
            
            for i, cat_stat in enumerate(categories):
                self.category_stats_table.setItem(i, 0, QTableWidgetItem(cat_stat.get('_id', '')))
                self.category_stats_table.setItem(i, 1, QTableWidgetItem(str(cat_stat.get('count', 0))))
                self.category_stats_table.setItem(i, 2, QTableWidgetItem(f"{cat_stat.get('avg_confidence', 0):.3f}"))
            
            # 번호판 통계 테이블
            plate_stats = stats.get('plate_categories', [])
            self.plate_stats_table.setRowCount(len(plate_stats))
            
            for i, plate_stat in enumerate(plate_stats):
                self.plate_stats_table.setItem(i, 0, QTableWidgetItem(plate_stat.get('_id', '')))
                self.plate_stats_table.setItem(i, 1, QTableWidgetItem(str(plate_stat.get('count', 0))))
            
        except Exception as e:
            print(f"통계 로드 오류: {e}")
    
    # 이벤트 핸들러들
    def create_new_project(self):
        """새 프로젝트 생성"""
        dialog = ProjectCreateDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, description = dialog.get_data()
            try:
                project_id = self.mongo_storage.create_project(name, description)
                if project_id:
                    QMessageBox.information(self, "성공", "프로젝트가 생성되었습니다.")
                    self.load_projects()
                else:
                    QMessageBox.warning(self, "오류", "프로젝트 생성에 실패했습니다.")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"프로젝트 생성 중 오류: {str(e)}")
    
    def search_projects(self, text):
        """프로젝트 검색"""
        for i in range(self.project_table.rowCount()):
            project_name = self.project_table.item(i, 0).text()
            if text.lower() in project_name.lower():
                self.project_table.setRowHidden(i, False)
            else:
                self.project_table.setRowHidden(i, True)
    
    def filter_images(self, status):
        """이미지 상태별 필터"""
        for i in range(self.image_table.rowCount()):
            if status == "전체":
                self.image_table.setRowHidden(i, False)
            else:
                image_status = self.image_table.item(i, 1).text()
                self.image_table.setRowHidden(i, status != image_status)
    
    def search_images(self, text):
        """이미지 파일명 검색"""
        for i in range(self.image_table.rowCount()):
            filename = self.image_table.item(i, 0).text()
            if text.lower() in filename.lower():
                self.image_table.setRowHidden(i, False)
            else:
                self.image_table.setRowHidden(i, True)
    
    def filter_annotations(self, category):
        """어노테이션 카테고리별 필터"""
        for i in range(self.annotation_table.rowCount()):
            if category == "모든 카테고리":
                self.annotation_table.setRowHidden(i, False)
            else:
                ann_category = self.annotation_table.item(i, 2).text()
                self.annotation_table.setRowHidden(i, category != ann_category)
    
    def update_confidence_filter(self, value):
        """신뢰도 필터 업데이트"""
        self.confidence_label.setText(f"신뢰도: {value}%+")
        threshold = value / 100.0
        
        for i in range(self.annotation_table.rowCount()):
            confidence_text = self.annotation_table.item(i, 3).text()
            try:
                confidence = float(confidence_text)
                self.annotation_table.setRowHidden(i, confidence < threshold)
            except:
                pass
    
    def show_advanced_search(self):
        """고급 검색 다이얼로그"""
        dialog = AdvancedSearchDialog(self.mongo_storage, self)
        if dialog.exec_() == QDialog.Accepted:
            results = dialog.get_results()
            # 검색 결과를 새 창에 표시
            self.show_search_results(results)
    
    def show_search_results(self, results):
        """검색 결과 표시"""
        dialog = SearchResultDialog(results, self)
        dialog.exec_()
    
    def show_batch_operations(self):
        """배치 작업 다이얼로그"""
        dialog = BatchOperationDialog(self.mongo_storage, self)
        dialog.exec_()
    
    def export_annotations(self):
        """어노테이션 내보내기"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "어노테이션 내보내기", "", 
            "JSON Files (*.json);;CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.json'):
                    data = self.mongo_storage.export_annotations(format='json')
                else:
                    data = self.mongo_storage.export_annotations(format='csv')
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(data)
                
                QMessageBox.information(self, "성공", "데이터가 내보내기 되었습니다.")
                
            except Exception as e:
                QMessageBox.critical(self, "오류", f"내보내기 실패: {str(e)}")


class ProjectCreateDialog(QDialog):
    """프로젝트 생성 다이얼로그"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("새 프로젝트 생성")
        self.setFixedSize(400, 200)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 프로젝트명
        layout.addWidget(QLabel("프로젝트명:"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)
        
        # 설명
        layout.addWidget(QLabel("설명:"))
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        layout.addWidget(self.description_edit)
        
        # 버튼들
        button_layout = QHBoxLayout()
        
        create_btn = QPushButton("생성")
        create_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(create_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def get_data(self):
        return self.name_edit.text(), self.description_edit.toPlainText()


class AdvancedSearchDialog(QDialog):
    """고급 검색 다이얼로그"""
    
    def __init__(self, mongo_storage, parent=None):
        super().__init__(parent)
        self.mongo_storage = mongo_storage
        self.setWindowTitle("고급 검색")
        self.setMinimumSize(500, 400)
        self.results = []
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 검색 조건들
        self.conditions_layout = QVBoxLayout()
        
        # 첫 번째 조건 추가
        self.add_search_condition()
        
        layout.addLayout(self.conditions_layout)
        
        # 조건 추가 버튼
        add_btn = QPushButton("조건 추가")
        add_btn.clicked.connect(self.add_search_condition)
        layout.addWidget(add_btn)
        
        # 버튼들
        button_layout = QHBoxLayout()
        
        search_btn = QPushButton("검색")
        search_btn.clicked.connect(self.perform_search)
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(search_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def add_search_condition(self):
        """검색 조건 추가"""
        condition_layout = QHBoxLayout()
        
        # 필드 선택
        field_combo = QComboBox()
        field_combo.addItems([
            "label", "category", "plate_number", "confidence", "filename"
        ])
        condition_layout.addWidget(field_combo)
        
        # 연산자 선택
        operator_combo = QComboBox()
        operator_combo.addItems(["포함", "정확히", ">", "<", ">=", "<="])
        condition_layout.addWidget(operator_combo)
        
        # 값 입력
        value_edit = QLineEdit()
        condition_layout.addWidget(value_edit)
        
        # 삭제 버튼
        delete_btn = QPushButton("삭제")
        delete_btn.clicked.connect(
            lambda: self.remove_condition(condition_layout)
        )
        condition_layout.addWidget(delete_btn)
        
        self.conditions_layout.addLayout(condition_layout)
    
    def remove_condition(self, layout):
        """검색 조건 제거"""
        for i in reversed(range(layout.count())):
            layout.itemAt(i).widget().setParent(None)
        self.conditions_layout.removeItem(layout)
    
    def perform_search(self):
        """검색 수행"""
        try:
            # 검색 조건들을 수집하여 MongoDB 쿼리 생성
            query = {}
            
            # 간단한 구현: 첫 번째 조건만 사용
            if self.conditions_layout.count() > 0:
                first_condition = self.conditions_layout.itemAt(0)
                if first_condition:
                    layout = first_condition.layout()
                    if layout and layout.count() >= 3:
                        field_combo = layout.itemAt(0).widget()
                        operator_combo = layout.itemAt(1).widget()
                        value_edit = layout.itemAt(2).widget()
                        
                        field = field_combo.currentText()
                        operator = operator_combo.currentText()
                        value = value_edit.text()
                        
                        if value:
                            if operator == "포함":
                                query[field] = {"$regex": value, "$options": "i"}
                            elif operator == "정확히":
                                query[field] = value
                            elif operator in [">", "<", ">=", "<="]:
                                try:
                                    num_value = float(value)
                                    if operator == ">":
                                        query[field] = {"$gt": num_value}
                                    elif operator == "<":
                                        query[field] = {"$lt": num_value}
                                    elif operator == ">=":
                                        query[field] = {"$gte": num_value}
                                    elif operator == "<=":
                                        query[field] = {"$lte": num_value}
                                except ValueError:
                                    pass
            
            # 검색 실행
            if field == "filename":
                # 이미지에서 검색한 후 관련 어노테이션 찾기
                images = list(self.mongo_storage.images.find(query).limit(50))
                image_ids = [img.get('image_id') for img in images]
                self.results = self.mongo_storage.find_annotations({"image_id": {"$in": image_ids}})
            else:
                # 어노테이션에서 직접 검색
                if field == "plate_number":
                    query = {"properties.plate_number": query.get(field, "")}
                
                self.results = self.mongo_storage.find_annotations(query)
            
            if self.results:
                self.accept()
            else:
                QMessageBox.information(self, "검색 결과", "검색 결과가 없습니다.")
                
        except Exception as e:
            QMessageBox.critical(self, "검색 오류", f"검색 중 오류: {str(e)}")
    
    def get_results(self):
        return self.results


class SearchResultDialog(QDialog):
    """검색 결과 표시 다이얼로그"""
    
    def __init__(self, results, parent=None):
        super().__init__(parent)
        self.results = results
        self.setWindowTitle(f"검색 결과 ({len(results)}개)")
        self.setMinimumSize(800, 600)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 결과 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "이미지", "라벨", "카테고리", "신뢰도", "번호판", "생성일"
        ])
        
        self.table.setRowCount(len(self.results))
        
        for i, result in enumerate(self.results):
            self.table.setItem(i, 0, QTableWidgetItem(result.get('image_id', '')))
            self.table.setItem(i, 1, QTableWidgetItem(result.get('label', '')))
            self.table.setItem(i, 2, QTableWidgetItem(result.get('category', '')))
            self.table.setItem(i, 3, QTableWidgetItem(f"{result.get('confidence', 0):.3f}"))
            self.table.setItem(i, 4, QTableWidgetItem(result.get('properties', {}).get('plate_number', '')))
            self.table.setItem(i, 5, QTableWidgetItem(str(result.get('created_at', ''))))
        
        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)
        
        # 닫기 버튼
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)


class BatchOperationDialog(QDialog):
    """배치 작업 다이얼로그"""
    
    def __init__(self, mongo_storage, parent=None):
        super().__init__(parent)
        self.mongo_storage = mongo_storage
        self.setWindowTitle("배치 작업")
        self.setMinimumSize(400, 300)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 작업 선택
        layout.addWidget(QLabel("수행할 작업을 선택하세요:"))
        
        self.operation_group = QButtonGroup()
        
        operations = [
            ("상태 변경", "change_status"),
            ("카테고리 변경", "change_category"), 
            ("삭제", "delete"),
            ("내보내기", "export")
        ]
        
        for text, value in operations:
            radio = QRadioButton(text)
            radio.setProperty("value", value)
            self.operation_group.addButton(radio)
            layout.addWidget(radio)
        
        # 매개변수 입력 영역
        self.params_widget = QWidget()
        self.params_layout = QVBoxLayout(self.params_widget)
        layout.addWidget(self.params_widget)
        
        # 버튼들
        button_layout = QHBoxLayout()
        
        execute_btn = QPushButton("실행")
        execute_btn.clicked.connect(self.execute_batch)
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(execute_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # 작업 선택 시 매개변수 UI 업데이트
        self.operation_group.buttonClicked.connect(self.update_params_ui)
    
    def update_params_ui(self, button):
        """선택된 작업에 따라 매개변수 UI 업데이트"""
        # 기존 위젯들 제거
        for i in reversed(range(self.params_layout.count())):
            self.params_layout.itemAt(i).widget().setParent(None)
        
        operation = button.property("value")
        
        if operation == "change_status":
            self.params_layout.addWidget(QLabel("새 상태:"))
            self.status_combo = QComboBox()
            self.status_combo.addItems(["pending", "in_progress", "completed", "verified"])
            self.params_layout.addWidget(self.status_combo)
            
        elif operation == "change_category":
            self.params_layout.addWidget(QLabel("새 카테고리:"))
            self.category_edit = QLineEdit()
            self.params_layout.addWidget(self.category_edit)
    
    def execute_batch(self):
        """배치 작업 실행"""
        checked_button = self.operation_group.checkedButton()
        if not checked_button:
            QMessageBox.warning(self, "경고", "작업을 선택해주세요.")
            return
        
        operation = checked_button.property("value")
        
        try:
            if operation == "change_status":
                new_status = self.status_combo.currentText()
                # 실제로는 선택된 이미지들의 ID를 받아야 함
                # 여기서는 예시로 빈 리스트 사용
                count = self.mongo_storage.batch_update_status([], new_status)
                QMessageBox.information(self, "완료", f"{count}개 항목의 상태가 변경되었습니다.")
                
            elif operation == "change_category":
                new_category = self.category_edit.text()
                if new_category:
                    # 실제로는 선택된 어노테이션들의 ID를 받아야 함
                    count = self.mongo_storage.batch_update_category([], new_category)
                    QMessageBox.information(self, "완료", f"{count}개 항목의 카테고리가 변경되었습니다.")
                
            elif operation == "delete":
                reply = QMessageBox.question(
                    self, "확인", "정말로 삭제하시겠습니까?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    # 실제로는 선택된 항목들을 삭제
                    count = self.mongo_storage.batch_delete_annotations([])
                    QMessageBox.information(self, "완료", f"{count}개 항목이 삭제되었습니다.")
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"배치 작업 실행 중 오류: {str(e)}")
    
    def request_first_review(self, annotation_id):
        """1차 검수 요청"""
        try:
            # 어노테이션 상태를 '1차 검수 요청'으로 변경
            self.mongo_storage.collection_annotations.update_one(
                {"_id": ObjectId(annotation_id)},
                {
                    "$set": {
                        "review_status": "1차 검수 요청",
                        "request_time": datetime.now(),
                        "requester": "current_user"  # 실제로는 현재 사용자 정보
                    }
                }
            )
            QMessageBox.information(self, "완료", "1차 검수 요청이 완료되었습니다.")
            self.load_annotations()  # 테이블 새로고침
        except Exception as e:
            QMessageBox.critical(self, "오류", f"1차 검수 요청 중 오류: {str(e)}")
    
    def complete_first_review(self, annotation_id):
        """1차 검수 완료"""
        try:
            # 어노테이션 상태를 '1차 검수 완료'로 변경
            self.mongo_storage.collection_annotations.update_one(
                {"_id": ObjectId(annotation_id)},
                {
                    "$set": {
                        "review_status": "1차 검수 완료",
                        "first_review_time": datetime.now(),
                        "first_reviewer": "current_user"  # 실제로는 현재 검수자 정보
                    }
                }
            )
            QMessageBox.information(self, "완료", "1차 검수가 완료되었습니다.")
            self.load_annotations()  # 테이블 새로고침
        except Exception as e:
            QMessageBox.critical(self, "오류", f"1차 검수 완료 중 오류: {str(e)}")
    
    def request_second_review(self, annotation_id):
        """2차 검수 요청"""
        try:
            # 어노테이션 상태를 '2차 검수 요청'으로 변경
            self.mongo_storage.collection_annotations.update_one(
                {"_id": ObjectId(annotation_id)},
                {
                    "$set": {
                        "review_status": "2차 검수 요청",
                        "second_request_time": datetime.now()
                    }
                }
            )
            QMessageBox.information(self, "완료", "2차 검수 요청이 완료되었습니다.")
            self.load_annotations()  # 테이블 새로고침
        except Exception as e:
            QMessageBox.critical(self, "오류", f"2차 검수 요청 중 오류: {str(e)}")
    
    def complete_second_review(self, annotation_id):
        """2차 검수 완료"""
        try:
            # 어노테이션 상태를 '2차 검수 완료'로 변경
            self.mongo_storage.collection_annotations.update_one(
                {"_id": ObjectId(annotation_id)},
                {
                    "$set": {
                        "review_status": "2차 검수 완료",
                        "second_review_time": datetime.now(),
                        "second_reviewer": "current_user",  # 실제로는 현재 검수자 정보
                        "final_approval": True
                    }
                }
            )
            QMessageBox.information(self, "완료", "2차 검수가 완료되었습니다.")
            self.load_annotations()  # 테이블 새로고침
        except Exception as e:
            QMessageBox.critical(self, "오류", f"2차 검수 완료 중 오류: {str(e)}")
