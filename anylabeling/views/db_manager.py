"""MongoDB 관리 UI 컴포넌트."""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import PyQt5.QtCore as QtCore
from PyQt5.QtGui import *
from datetime import datetime
import os
import threading
import time
from bson import ObjectId
from anylabeling.services.app_instance_manager import (
    open_file_with_instance_manager,
)

class DBManagerDialog(QDialog):
    """MongoDB 관리 메인 다이얼로그."""
    
    def __init__(self, mongo_storage, parent=None):
        super().__init__(parent)
        self.mongo_storage = mongo_storage
        self.setWindowTitle("데이터베이스 관리")
        self.setMinimumSize(1200, 800)
        self.image_docs = []  # 이미지 문서 캐시
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        """UI를 설정합니다."""
        layout = QVBoxLayout(self)
        
        # 탭 위젯 생성
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_project_tab(), "프로젝트")
        self.tab_widget.addTab(self.create_image_tab(), "이미지")
        self.tab_widget.addTab(self.create_annotation_tab(), "어노테이션")
        self.tab_widget.addTab(self.create_stats_tab(), "통계")
        layout.addWidget(self.tab_widget)
        
        # 하단 버튼 레이아웃
        button_layout = QHBoxLayout()
        refresh_btn = QPushButton("새로고침")
        refresh_btn.clicked.connect(self.load_data)
        button_layout.addWidget(refresh_btn)
        button_layout.addStretch()
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
    
    def create_project_tab(self):
        """프로젝트 관리 탭을 생성합니다."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 툴바
        toolbar = QHBoxLayout()
        new_btn = QPushButton("새 프로젝트")
        new_btn.clicked.connect(self.create_new_project)
        toolbar.addWidget(new_btn)
        self.project_search_edit = QLineEdit()
        self.project_search_edit.setPlaceholderText("프로젝트 검색...")
        self.project_search_edit.textChanged.connect(self.search_projects)
        toolbar.addWidget(self.project_search_edit)
        layout.addLayout(toolbar)
        
        # 프로젝트 테이블
        self.project_table = QTableWidget()
        self.project_table.setColumnCount(6)
        self.project_table.setHorizontalHeaderLabels(["프로젝트명", "상태", "이미지 수", "진행률", "생성일", "작업"])
        self.project_table.horizontalHeader().setStretchLastSection(True)
        self.project_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.project_table)
        
        return widget
    
    def create_image_tab(self):
        """이미지 관리 탭을 생성합니다."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 필터 레이아웃
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("상태:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["전체", "1차 검수 요청 전", "진행중", "완료", "1차 검수 요청", "1차 검수 완료"])
        self.status_combo.currentTextChanged.connect(self.filter_images)
        filter_layout.addWidget(self.status_combo)
        self.image_search_edit = QLineEdit()
        self.image_search_edit.setPlaceholderText("파일명 검색...")
        self.image_search_edit.textChanged.connect(self.search_images)
        filter_layout.addWidget(self.image_search_edit)
        filter_layout.addStretch()
        batch_btn = QPushButton("배치 작업")
        batch_btn.clicked.connect(self.show_batch_operations)
        filter_layout.addWidget(batch_btn)
        layout.addLayout(filter_layout)
        
        # 이미지 테이블
        self.image_table = QTableWidget()
        self.image_table.setColumnCount(6)
        self.image_table.setHorizontalHeaderLabels(["파일명", "상태", "크기", "업로드일", "어노테이션 수", "작업"])
        self.image_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.image_table)
        
        return widget
    
    def create_annotation_tab(self):
        """어노테이션 관리 탭을 생성합니다."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 검색 레이아웃
        search_layout = QHBoxLayout()
        search_btn = QPushButton("고급 검색")
        search_btn.clicked.connect(self.show_advanced_search)
        search_layout.addWidget(search_btn)
        search_layout.addWidget(QLabel("카테고리:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("모든 카테고리")
        self.category_combo.currentTextChanged.connect(self.filter_annotations)
        search_layout.addWidget(self.category_combo)
        search_layout.addStretch()
        export_btn = QPushButton("내보내기")
        export_btn.clicked.connect(self.export_annotations)
        search_layout.addWidget(export_btn)
        layout.addLayout(search_layout)
        
        # 어노테이션 테이블
        self.annotation_table = QTableWidget()
        self.annotation_table.setColumnCount(9)
        self.annotation_table.setHorizontalHeaderLabels(["이미지", "라벨", "카테고리", "신뢰도", "번호판", "검수 상태", "검수자", "생성일", "작업"])
        layout.addWidget(self.annotation_table)
        
        return widget
    
    def create_stats_tab(self):
        """통계 탭을 생성합니다."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 통계 카드 레이아웃
        stats_layout = QHBoxLayout()
        self.total_images_card = self.create_stat_card("전체 이미지", "0")
        self.labeled_images_card = self.create_stat_card("라벨링 완료", "0")
        self.progress_card = self.create_stat_card("진행률", "0%")
        self.annotations_card = self.create_stat_card("총 어노테이션", "0")
        stats_layout.addWidget(self.total_images_card)
        stats_layout.addWidget(self.labeled_images_card) 
        stats_layout.addWidget(self.progress_card)
        stats_layout.addWidget(self.annotations_card)
        layout.addLayout(stats_layout)
        
        # 통계 테이블 그룹
        layout.addWidget(self.create_stats_groupbox("카테고리별 통계", ["카테고리", "개수", "평균 신뢰도"]))
        layout.addWidget(self.create_stats_groupbox("번호판 카테고리 통계", ["번호판 타입", "개수"]))
        layout.addWidget(self.create_stats_groupbox("검수 상태별 통계", ["검수 상태", "개수"]))
        
        return widget

    def create_stats_groupbox(self, title, headers):
        """통계 그룹박스와 테이블을 생성합니다."""
        groupbox = QGroupBox(title)
        layout = QVBoxLayout(groupbox)
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        layout.addWidget(table)
        
        if "카테고리" in title:
            self.category_stats_table = table
        elif "번호판" in title:
            self.plate_stats_table = table
        elif "검수 상태" in title:
            self.review_stats_table = table
            
        return groupbox

    def create_stat_card(self, title, value):
        """통계 정보를 보여주는 카드를 생성합니다."""
        card = QFrame()
        card.setFrameStyle(QFrame.Box)
        card.setStyleSheet("QFrame { border: 1px solid #ddd; border-radius: 8px; background-color: white; padding: 16px; margin: 4px; }")
        
        layout = QVBoxLayout(card)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; color: #666; font-size: 12px;")
        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        card.value_label = value_label
        return card
    
    def load_data(self):
        """모든 탭의 데이터를 로드합니다."""
        self.load_projects()
        self.load_images()
        self.load_annotations()
        self.load_stats()
    
    def load_projects(self):
        """프로젝트 데이터를 로드하여 테이블에 표시합니다."""
        try:
            projects = self.mongo_storage.get_projects()
            self.project_table.setRowCount(len(projects))
            
            for i, project in enumerate(projects):
                self.project_table.setItem(i, 0, QTableWidgetItem(project.get('name', '')))
                self.project_table.setItem(i, 1, QTableWidgetItem(project.get('status', '')))
                self.project_table.setItem(i, 2, QTableWidgetItem(str(project.get('stats', {}).get('total_images', 0))))
                self.project_table.setItem(i, 3, QTableWidgetItem(f"{project.get('stats', {}).get('progress_percent', 0):.1f}%"))
                self.project_table.setItem(i, 4, QTableWidgetItem(str(project.get('created_at', ''))))
                
                action_btn = QPushButton("관리")
                self.project_table.setCellWidget(i, 5, action_btn)
            
            self.project_table.resizeColumnsToContents()
        except Exception as e:
            print(f"프로젝트 로드 오류: {e}")
    
    def load_images(self):
        """'description'이 있는 어노테이션을 기반으로 이미지 데이터를 로드합니다."""
        try:
            query = {"shapes": {"$elemMatch": {"description": {"$exists": True, "$ne": ""}}}}
            annotations = list(self.mongo_storage.annotations.find(query).limit(500))
            
            self.image_docs.clear()
            found_items = []

            for ann in annotations:
                path = self._resolve_image_path(ann)
                if path:
                    found_items.append((path, ann))

            self.image_table.setRowCount(len(found_items))
            for i, (path, ann) in enumerate(found_items):
                self.image_docs.append({'file_path': path, 'annotation': ann})
                
                # 테이블 아이템 설정
                self.image_table.setItem(i, 0, QTableWidgetItem(os.path.basename(path)))
                status = ann.get('review_status') or ann.get('status') or ""
                self.image_table.setItem(i, 1, QTableWidgetItem(status))
                size = str(os.path.getsize(path)) if os.path.exists(path) else '-'
                self.image_table.setItem(i, 2, QTableWidgetItem(size))
                self.image_table.setItem(i, 3, QTableWidgetItem(str(ann.get('created_at', ''))))
                
                desc_count = sum(1 for s in ann.get('shapes', []) if s.get('description'))
                self.image_table.setItem(i, 4, QTableWidgetItem(str(max(1, desc_count))))

                action_btn = QPushButton("보기")
                image_id = ann.get('image_id') or ann.get('_id')
                action_btn.clicked.connect(lambda _, iid=image_id: self.open_image_in_viewer(iid))
                self.image_table.setCellWidget(i, 5, action_btn)

            self.image_table.resizeColumnsToContents()
        except Exception as e:
            print(f"이미지 로드 오류: {e}")

    def _resolve_image_path(self, annotation_doc):
        """어노테이션 문서에서 이미지 파일의 실제 경로를 찾습니다."""
        # 다양한 경로 필드 후보
        candidates = [
            annotation_doc.get(key) for key in 
            ['imagePath', 'image_file_path', 'file_path', 'filename', 'image_file_name', 'image_file']
            if annotation_doc.get(key)
        ]
        
        # 후보 경로 확인
        for cand in candidates:
            if os.path.isabs(cand) and os.path.exists(cand):
                return os.path.normpath(cand)
            
            # 작업 디렉토리 기준 상대 경로 시도
            abs_path = os.path.abspath(os.path.expanduser(cand))
            if os.path.exists(abs_path):
                return os.path.normpath(abs_path)

        return None

    def open_image_in_viewer(self, image_identifier):
        """선택한 이미지를 뷰어에서 엽니다."""
        try:
            image_doc = self._find_image_document(image_identifier)
            if not image_doc:
                QMessageBox.warning(self, "오류", "이미지 문서를 찾을 수 없습니다.")
                return

            file_path = image_doc.get('file_path') or image_doc.get('filename')
            if not file_path:
                QMessageBox.warning(self, "오류", "이미지 파일 경로가 없습니다.")
                return

            if open_file_with_instance_manager(str(file_path)):
                self._update_main_window_ui(file_path)
            else:
                QMessageBox.information(self, "알림", "뷰어 실행에 실패했습니다. 경로를 확인해주세요.")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"뷰어 실행 중 오류: {e}")

    def _find_image_document(self, identifier):
        """이미지 ID 또는 ObjectId로 이미지 문서를 찾습니다."""
        if isinstance(identifier, ObjectId):
            return self.mongo_storage.images.find_one({'_id': identifier})
        
        doc = self.mongo_storage.images.find_one({'image_id': str(identifier)})
        if not doc:
            try:
                doc = self.mongo_storage.images.find_one({'_id': ObjectId(identifier)})
            except Exception:
                pass
        return doc

    def _update_main_window_ui(self, file_path):
        """메인 윈도우의 UI(파일 인덱스, 상태바)를 업데이트합니다."""
        main_win = self.window()
        if not main_win:
            return
            
        try:
            total = len(self.image_docs)
            current = next((i + 1 for i, img in enumerate(self.image_docs) if (img.get('file_path') or img.get('filename')) == file_path), 1)
            
            if hasattr(main_win, 'set_top_file_index_text'):
                main_win.set_top_file_index_text(f"[{current}/{total}] {os.path.basename(file_path)}")
            if main_win.statusBar():
                main_win.statusBar().showMessage(str(file_path), 5000)
        except Exception as e:
            print(f"UI 업데이트 오류: {e}")

    def confirm_and_open_all_images(self):
        """로드된 모든 이미지를 열지 사용자에게 확인받고 실행합니다."""
        if not self.image_docs:
            QMessageBox.information(self, "알림", "열 이미지 목록이 없습니다.")
            return

        count = len(self.image_docs)
        reply = QMessageBox.question(self, "모두 보기 확인", f"현재 로드된 {count}개의 이미지를 모두 엽니다. 계속하시겠습니까?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        progress = QProgressDialog("이미지 여는 중...", "취소", 0, count, self)
        progress.setWindowModality(Qt.WindowModal)
        
        # 별도 스레드에서 이미지 열기 실행
        thread = threading.Thread(target=self._open_all_images_thread, args=(progress,), daemon=True)
        thread.start()

    def _open_all_images_thread(self, progress):
        """백그라운드 스레드에서 모든 이미지를 엽니다."""
        opened_count = 0
        for i, img_doc in enumerate(self.image_docs):
            if progress.wasCanceled():
                break
            
            file_path = img_doc.get('file_path') or img_doc.get('filename')
            if file_path and os.path.exists(file_path):
                if open_file_with_instance_manager(str(file_path)):
                    opened_count += 1
                    # UI 업데이트는 메인 스레드에서 실행
                    QtCore.QTimer.singleShot(0, lambda p=file_path: self._update_main_window_ui(p))
            
            progress.setValue(i + 1)
            time.sleep(0.05) # 시스템 부하 완화

        progress.close()
        QtCore.QTimer.singleShot(0, lambda: QMessageBox.information(self, "완료", f"총 {opened_count}개의 이미지를 열었습니다."))

    def show_description_dialog(self, annotation_doc, image_path):
        """Shape의 Description 목록을 보여주는 다이얼로그를 엽니다."""
        try:
            dlg = QDialog(self)
            dlg.setWindowTitle("설명(Description) 보기")
            dlg.resize(700, 500)
            layout = QVBoxLayout(dlg)

            # 파일 정보
            layout.addWidget(QLabel(f"<b>{os.path.basename(image_path)}</b>"))
            path_label = QLabel(image_path)
            path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            layout.addWidget(path_label)

            # Description 테이블
            table = QTableWidget()
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["#", "라벨", "설명", "포인트 수"])
            
            rows = [s for s in annotation_doc.get('shapes', []) if s.get('description', '').strip()]
            table.setRowCount(len(rows))

            for i, shape in enumerate(rows):
                table.setItem(i, 0, QTableWidgetItem(str(i)))
                table.setItem(i, 1, QTableWidgetItem(shape.get('label', '')))
                table.setItem(i, 2, QTableWidgetItem(shape.get('description', '')))
                table.setItem(i, 3, QTableWidgetItem(str(len(shape.get('points', [])))))

            table.resizeColumnsToContents()
            layout.addWidget(table)

            # 하단 버튼
            button_box = QDialogButtonBox(QDialogButtonBox.Open | QDialogButtonBox.Close)
            button_box.accepted.connect(dlg.accept)
            button_box.rejected.connect(dlg.reject)
            button_box.button(QDialogButtonBox.Open).clicked.connect(lambda: self.open_image_in_viewer(annotation_doc.get('image_id') or annotation_doc.get('_id')))
            layout.addWidget(button_box)

            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "오류", f"설명 보기 중 오류: {e}")
    
    def load_annotations(self):
        """어노테이션 데이터를 로드하여 테이블에 표시합니다."""
        try:
            annotations = self.mongo_storage.find_annotations()[:100]
            self.annotation_table.setRowCount(len(annotations))
            
            categories = set()
            for i, ann in enumerate(annotations):
                image_info = self.mongo_storage.images.find_one({'image_id': ann.get('image_id', '')})
                filename = image_info.get('filename', '') if image_info else ''
                
                self.annotation_table.setItem(i, 0, QTableWidgetItem(filename))
                self.annotation_table.setItem(i, 1, QTableWidgetItem(ann.get('label', '')))
                self.annotation_table.setItem(i, 2, QTableWidgetItem(ann.get('category', '')))
                self.annotation_table.setItem(i, 3, QTableWidgetItem(f"{ann.get('confidence', 0):.2f}"))
                self.annotation_table.setItem(i, 4, QTableWidgetItem(ann.get('properties', {}).get('plate_number', '')))
                
                review_status = ann.get('review_status', '1차 검수 요청 전')
                self.annotation_table.setItem(i, 5, QTableWidgetItem(review_status))
                self.annotation_table.setItem(i, 6, QTableWidgetItem(ann.get('reviewer', '')))
                self.annotation_table.setItem(i, 7, QTableWidgetItem(str(ann.get('created_at', ''))))
                
                self.annotation_table.setCellWidget(i, 8, self._create_annotation_action_widget(ann))
                
                if ann.get('category'):
                    categories.add(ann.get('category'))
            
            self._update_category_combobox(categories)
            self.annotation_table.resizeColumnsToContents()
        except Exception as e:
            print(f"어노테이션 로드 오류: {e}")

    def _create_annotation_action_widget(self, annotation):
        """어노테이션 상태에 따른 액션 버튼 위젯을 생성합니다."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        review_status = annotation.get('review_status', '1차 검수 요청 전')
        ann_id = annotation.get('_id')

        buttons = {
            '1차 검수 요청 전': ("1차 검수 요청", lambda: self.update_review_status(ann_id, "1차 검수 요청")),
            '완료': ("1차 검수 요청", lambda: self.update_review_status(ann_id, "1차 검수 요청")),
            '1차 검수 요청': ("1차 검수 완료", lambda: self.update_review_status(ann_id, "1차 검수 완료")),
            '1차 검수 완료': ("2차 검수 요청", lambda: self.update_review_status(ann_id, "2차 검수 요청")),
            '2차 검수 요청': ("2차 검수 완료", lambda: self.update_review_status(ann_id, "2차 검수 완료")),
        }

        if review_status in buttons:
            text, func = buttons[review_status]
            btn = QPushButton(text)
            btn.clicked.connect(func)
            layout.addWidget(btn)

        edit_btn = QPushButton("편집")
        delete_btn = QPushButton("삭제")
        layout.addWidget(edit_btn)
        layout.addWidget(delete_btn)
        
        return widget

    def _update_category_combobox(self, categories):
        """카테고리 콤보박스를 업데이트합니다."""
        current_text = self.category_combo.currentText()
        self.category_combo.clear()
        self.category_combo.addItem("모든 카테고리")
        self.category_combo.addItems(sorted(list(categories)))
        index = self.category_combo.findText(current_text)
        if index != -1:
            self.category_combo.setCurrentIndex(index)

    def update_review_status(self, annotation_id, new_status):
        """어노테이션의 검수 상태를 업데이트합니다."""
        try:
            update_doc = {
                "review_status": new_status,
                f"{new_status.replace(' ', '_')}_time": datetime.now(),
                "reviewer": "current_user" # TODO: 실제 사용자 정보로 변경
            }
            self.mongo_storage.annotations.update_one(
                {"_id": ObjectId(annotation_id)},
                {"$set": update_doc}
            )
            QMessageBox.information(self, "완료", f"'{new_status}' 상태로 변경되었습니다.")
            self.load_annotations()
        except Exception as e:
            QMessageBox.critical(self, "오류", f"상태 변경 중 오류: {e}")

    def load_stats(self):
        """통계 데이터를 로드하여 표시합니다."""
        try:
            stats = self.mongo_storage.get_database_stats()
            
            # 기본 통계 카드 업데이트
            self.total_images_card.value_label.setText(str(stats.get('total_images', 0)))
            self.labeled_images_card.value_label.setText(str(stats.get('labeled_images', 0)))
            self.progress_card.value_label.setText(f"{stats.get('progress', 0):.1f}%")
            self.annotations_card.value_label.setText(str(stats.get('total_annotations', 0)))
            
            # 테이블 통계 업데이트
            self._update_stats_table(self.category_stats_table, stats.get('categories', []), ['_id', 'count', 'avg_confidence'])
            self._update_stats_table(self.plate_stats_table, stats.get('plate_categories', []), ['_id', 'count'])
            
            # 검수 상태별 통계
            review_stats = list(self.mongo_storage.annotations.aggregate([{"$group": {"_id": "$review_status", "count": {"$sum": 1}}}]))
            self._update_stats_table(self.review_stats_table, review_stats, ['_id', 'count'])
            
        except Exception as e:
            print(f"통계 로드 오류: {e}")

    def _update_stats_table(self, table, data, keys):
        """통계 테이블을 데이터로 채웁니다."""
        table.setRowCount(len(data))
        for i, item in enumerate(data):
            for j, key in enumerate(keys):
                value = item.get(key, '')
                if isinstance(value, float):
                    value = f"{value:.3f}"
                table.setItem(i, j, QTableWidgetItem(str(value)))
    
    # 이벤트 핸들러
    def create_new_project(self):
        """새 프로젝트 생성 다이얼로그를 엽니다."""
        dialog = ProjectCreateDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, description = dialog.get_data()
            try:
                if self.mongo_storage.create_project(name, description):
                    QMessageBox.information(self, "성공", "프로젝트가 생성되었습니다.")
                    self.load_projects()
                else:
                    QMessageBox.warning(self, "오류", "프로젝트 생성에 실패했습니다.")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"프로젝트 생성 중 오류: {e}")
    
    def search_projects(self, text):
        """프로젝트 테이블을 검색합니다."""
        for i in range(self.project_table.rowCount()):
            item = self.project_table.item(i, 0)
            self.project_table.setRowHidden(i, text.lower() not in item.text().lower())
    
    def filter_images(self, status):
        """이미지 테이블을 상태별로 필터링합니다."""
        for i in range(self.image_table.rowCount()):
            if status == "전체":
                self.image_table.setRowHidden(i, False)
            else:
                item = self.image_table.item(i, 1)
                self.image_table.setRowHidden(i, status != item.text())
    
    def search_images(self, text):
        """이미지 테이블을 파일명으로 검색합니다."""
        for i in range(self.image_table.rowCount()):
            item = self.image_table.item(i, 0)
            self.image_table.setRowHidden(i, text.lower() not in item.text().lower())
    
    def filter_annotations(self, category):
        """어노테이션 테이블을 카테고리별로 필터링합니다."""
        for i in range(self.annotation_table.rowCount()):
            if category == "모든 카테고리":
                self.annotation_table.setRowHidden(i, False)
            else:
                item = self.annotation_table.item(i, 2)
                self.annotation_table.setRowHidden(i, category != item.text())

    def show_advanced_search(self):
        """고급 검색 다이얼로그를 엽니다."""
        dialog = AdvancedSearchDialog(self.mongo_storage, self)
        if dialog.exec_() == QDialog.Accepted:
            self.show_search_results(dialog.get_results())
    
    def show_search_results(self, results):
        """검색 결과 다이얼로그를 엽니다."""
        dialog = SearchResultDialog(results, self)
        dialog.exec_()
    
    def show_batch_operations(self):
        """배치 작업 다이얼로그를 엽니다."""
        dialog = BatchOperationDialog(self.mongo_storage, self)
        dialog.exec_()
    
    def export_annotations(self):
        """어노테이션을 파일로 내보냅니다."""
        file_path, _ = QFileDialog.getSaveFileName(self, "어노테이션 내보내기", "", "JSON Files (*.json);;CSV Files (*.csv)")
        if not file_path:
            return
            
        try:
            format = 'json' if file_path.endswith('.json') else 'csv'
            data = self.mongo_storage.export_annotations(format=format)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(data)
            QMessageBox.information(self, "성공", "데이터를 내보냈습니다.")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"내보내기 실패: {e}")


class ProjectCreateDialog(QDialog):
    """프로젝트 생성을 위한 다이얼로그."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("새 프로젝트 생성")
        self.setFixedSize(400, 200)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("프로젝트명:"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)
        
        layout.addWidget(QLabel("설명:"))
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        layout.addWidget(self.description_edit)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_data(self):
        """입력된 프로젝트 이름과 설명을 반환합니다."""
        return self.name_edit.text(), self.description_edit.toPlainText()


class AdvancedSearchDialog(QDialog):
    """어노테이션 고급 검색을 위한 다이얼로그."""
    
    def __init__(self, mongo_storage, parent=None):
        super().__init__(parent)
        self.mongo_storage = mongo_storage
        self.setWindowTitle("고급 검색")
        self.setMinimumSize(500, 400)
        self.results = []
        
        layout = QVBoxLayout(self)
        self.conditions_layout = QVBoxLayout()
        layout.addLayout(self.conditions_layout)
        
        add_btn = QPushButton("조건 추가")
        add_btn.clicked.connect(self.add_search_condition)
        layout.addWidget(add_btn)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("검색")
        button_box.accepted.connect(self.perform_search)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.add_search_condition()
    
    def add_search_condition(self):
        """검색 조건 한 줄을 추가합니다."""
        condition_layout = QHBoxLayout()
        
        field_combo = QComboBox()
        field_combo.addItems(["label", "category", "plate_number", "confidence", "filename"])
        condition_layout.addWidget(field_combo)
        
        operator_combo = QComboBox()
        operator_combo.addItems(["포함", "정확히", ">", "<", ">=", "<="])
        condition_layout.addWidget(operator_combo)
        
        value_edit = QLineEdit()
        condition_layout.addWidget(value_edit)
        
        delete_btn = QPushButton("삭제")
        condition_layout.addWidget(delete_btn)
        
        # 위젯들을 레이아웃에 추가하고, 삭제 버튼에 람다 함수를 연결합니다.
        # 이렇게 하면 버튼 클릭 시 해당 레이아웃이 삭제됩니다.
        container_widget = QWidget()
        container_widget.setLayout(condition_layout)
        delete_btn.clicked.connect(lambda: container_widget.deleteLater())
        
        self.conditions_layout.addWidget(container_widget)

    def perform_search(self):
        """입력된 조건으로 검색을 수행합니다."""
        try:
            query = self._build_query()
            if not query:
                QMessageBox.information(self, "알림", "검색 조건을 입력하세요.")
                return

            # 'filename' 필드는 images 컬렉션에서, 나머지는 annotations 컬렉션에서 검색
            if "filename" in query:
                images = list(self.mongo_storage.images.find(query).limit(50))
                image_ids = [img.get('image_id') for img in images]
                self.results = self.mongo_storage.find_annotations({"image_id": {"$in": image_ids}})
            else:
                self.results = self.mongo_storage.find_annotations(query)
            
            if self.results:
                self.accept()
            else:
                QMessageBox.information(self, "검색 결과", "검색 결과가 없습니다.")
                
        except Exception as e:
            QMessageBox.critical(self, "검색 오류", f"검색 중 오류: {e}")

    def _build_query(self):
        """UI에서 MongoDB 쿼리를 생성합니다."""
        query = {}
        # conditions_layout의 모든 조건 위젯을 순회
        for i in range(self.conditions_layout.count()):
            widget = self.conditions_layout.itemAt(i).widget()
            if not widget: continue
            
            field = widget.findChild(QComboBox, "").currentText()
            op = widget.findChild(QComboBox, "", Qt.FindChildrenRecursively)[1].currentText()
            value = widget.findChild(QLineEdit).text()

            if not value: continue

            # 연산자에 따라 쿼리 조건 생성
            if op == "포함":
                query[field] = {"$regex": value, "$options": "i"}
            elif op == "정확히":
                query[field] = value
            else: # 숫자 연산
                try:
                    num_value = float(value)
                    op_map = {">": "$gt", "<": "$lt", ">=": "$gte", "<=": "$lte"}
                    query[field] = {op_map[op]: num_value}
                except ValueError:
                    pass # 숫자 변환 실패 시 무시
        
        # 'plate_number'는 'properties' 하위 필드
        if "plate_number" in query:
            query["properties.plate_number"] = query.pop("plate_number")
            
        return query

    def get_results(self):
        """검색 결과를 반환합니다."""
        return self.results


class SearchResultDialog(QDialog):
    """검색 결과를 테이블 형태로 보여주는 다이얼로그."""
    
    def __init__(self, results, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"검색 결과 ({len(results)}개)")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(self)
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["이미지", "라벨", "카테고리", "신뢰도", "번호판", "생성일"])
        table.setRowCount(len(results))
        
        for i, res in enumerate(results):
            table.setItem(i, 0, QTableWidgetItem(res.get('image_id', '')))
            table.setItem(i, 1, QTableWidgetItem(res.get('label', '')))
            table.setItem(i, 2, QTableWidgetItem(res.get('category', '')))
            table.setItem(i, 3, QTableWidgetItem(f"{res.get('confidence', 0):.3f}"))
            table.setItem(i, 4, QTableWidgetItem(res.get('properties', {}).get('plate_number', '')))
            table.setItem(i, 5, QTableWidgetItem(str(res.get('created_at', ''))))
        
        table.resizeColumnsToContents()
        layout.addWidget(table)
        
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class BatchOperationDialog(QDialog):
    """이미지 또는 어노테이션에 대한 배치 작업을 수행하는 다이얼로그."""
    
    def __init__(self, mongo_storage, parent=None):
        super().__init__(parent)
        self.mongo_storage = mongo_storage
        self.setWindowTitle("배치 작업")
        self.setMinimumSize(400, 300)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("수행할 작업을 선택하세요:"))
        
        self.operation_group = QButtonGroup(self)
        operations = [("상태 변경", "change_status"), ("카테고리 변경", "change_category"), ("삭제", "delete"), ("내보내기", "export")]
        
        for text, value in operations:
            radio = QRadioButton(text)
            radio.setProperty("value", value)
            self.operation_group.addButton(radio)
            layout.addWidget(radio)
        
        self.params_widget = QWidget()
        self.params_layout = QVBoxLayout(self.params_widget)
        layout.addWidget(self.params_widget)
        
        self.operation_group.buttonClicked.connect(self.update_params_ui)
        # TODO: 나머지 UI 및 로직 구현 필요
    
    def update_params_ui(self, button):
        """선택된 작업에 따라 파라미터 UI를 업데이트합니다."""
        # 기존 위젯 제거
        for i in reversed(range(self.params_layout.count())): 
            self.params_layout.itemAt(i).widget().setParent(None)

        op_value = button.property("value")
        if op_value == "change_status":
            self.params_layout.addWidget(QLabel("새 상태:"))
            combo = QComboBox()
            combo.addItems(["1차 검수 요청 전", "진행중", "완료", "1차 검수 요청", "1차 검수 완료"])
            self.params_layout.addWidget(combo)
        elif op_value == "change_category":
            self.params_layout.addWidget(QLabel("새 카테고리:"))
            self.params_layout.addWidget(QLineEdit())
        # '삭제'나 '내보내기'는 추가 파라미터가 필요 없을 수 있음
        
    # TODO: 실제 배치 작업 실행 로직 구현 필요
    
