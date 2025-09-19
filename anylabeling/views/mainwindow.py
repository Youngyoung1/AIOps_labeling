import os
import importlib.util
import json
import os.path as osp

from PyQt5.QtWidgets import (
    QMainWindow,
    QStatusBar,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QLabel,
    QAction,
    QInputDialog,
    QMessageBox,
    QFileDialog,
    QSizePolicy,
    QWidgetAction,
    QDialog,
    QComboBox,
    QPushButton,
    QFrame,
)

from .image_gallery import ImageGallery
from ..app_info import __appdescription__, __appname__
from .labeling.label_wrapper import LabelingWrapper
try:
    from ..services.storage.mongo_provider import get_storage
except Exception:
    get_storage = None


class BaseImagePickerDialog(QDialog):
    """이미지 선택 다이얼로그의 기본 클래스"""
    def __init__(self, parent=None, title="", icon="🖼️", description="", primary_color="#007bff", storage=None):
        super().__init__(parent)
        self.primary_color = primary_color
        self.storage = storage
        self.setWindowTitle(f"{icon} {title}")
        self.setFixedSize(500, 340)
        self.setup_ui(icon, title, description)
        
    def setup_ui(self, icon, title, description):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #f8f9fa;
                border-radius: 10px;
            }}
            QLabel {{
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                margin: 5px;
            }}
            QComboBox {{
                font-size: 13px;
                padding: 8px 12px;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                background-color: white;
                selection-background-color: {self.primary_color};
                min-height: 20px;
            }}
            QComboBox:hover {{
                border-color: {self.primary_color};
            }}
            QComboBox:focus {{
                border-color: {self.get_darker_color()};
                outline: none;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #6c757d;
                margin-right: 5px;
            }}
            QPushButton {{
                font-size: 13px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 8px;
                border: none;
                min-width: 100px;
                min-height: 35px;
            }}
            QPushButton#viewBtn {{
                background-color: {self.primary_color};
                color: white;
            }}
            QPushButton#viewBtn:hover {{
                background-color: {self.get_darker_color()};
            }}
            QPushButton#viewBtn:pressed {{
                background-color: {self.get_darkest_color()};
            }}
            QPushButton#closeBtn {{
                background-color: #6c757d;
                color: white;
            }}
            QPushButton#closeBtn:hover {{
                background-color: #545b62;
            }}
            QPushButton#closeBtn:pressed {{
                background-color: #3d4145;
            }}
            QFrame#headerFrame {{
                background-color: white;
                border-radius: 8px;
                margin: 10px;
                padding: 15px;
                border: 1px solid #dee2e6;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # 헤더 프레임
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        
        # 제목
        title_label = QLabel(f"📂 {title}")
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        """)
        header_layout.addWidget(title_label)
        
        # 설명
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("""
            font-size: 12px;
            color: #6c757d;
            font-weight: normal;
            line-height: 1.4;
        """)
        header_layout.addWidget(desc_label)
        
        layout.addWidget(header_frame)
        
        # 선택 영역
        select_frame = QFrame()
        select_layout = QVBoxLayout(select_frame)
        select_layout.setContentsMargins(10, 0, 10, 0)
        select_layout.setSpacing(8)
        
        select_label = QLabel(self.get_select_label())
        select_layout.addWidget(select_label)
        
        self.combo = QComboBox()
        self.combo.setStyleSheet(self.combo.styleSheet() + f"""
            QComboBox QAbstractItemView {{
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
                selection-background-color: {self.get_light_color()};
                selection-color: {self.get_darkest_color()};
                padding: 4px;
            }}
        """)
        self.load_combo_items()
        select_layout.addWidget(self.combo)
        
        layout.addWidget(select_frame)
        
        # 버튼 영역
        btn_frame = QFrame()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(10, 10, 10, 0)
        btn_layout.setSpacing(10)
        
        self.view_btn = QPushButton("🖼️ 사진 보기")
        self.view_btn.setObjectName("viewBtn")
        
        self.close_btn = QPushButton("❌ 닫기")
        self.close_btn.setObjectName("closeBtn")
        
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.view_btn)
        btn_layout.addWidget(self.close_btn)
        
        layout.addWidget(btn_frame)
        
        self.close_btn.clicked.connect(self.reject)
        
    def get_darker_color(self):
        """기본 색상보다 어두운 색상 반환"""
        color_map = {
            "#007bff": "#0056b3",
            "#28a745": "#1e7e34"
        }
        return color_map.get(self.primary_color, "#333333")
        
    def get_darkest_color(self):
        """가장 어두운 색상 반환"""
        color_map = {
            "#007bff": "#004085",
            "#28a745": "#155724"
        }
        return color_map.get(self.primary_color, "#222222")
        
    def get_light_color(self):
        """밝은 색상 반환 (선택 배경용)"""
        color_map = {
            "#007bff": "#e3f2fd",
            "#28a745": "#d4edda"
        }
        return color_map.get(self.primary_color, "#f0f0f0")
        
    # 하위 클래스에서 구현해야 할 추상 메서드들
    def get_select_label(self):
        raise NotImplementedError("하위 클래스에서 구현해야 합니다")
        
    def load_combo_items(self):
        raise NotImplementedError("하위 클래스에서 구현해야 합니다")


class TagPicker(BaseImagePickerDialog):
    def __init__(self, parent=None, storage=None):
        super().__init__(
            parent=parent,
            title="태그별로 이미지를 탐색하세요",
            icon="🏷️",
            description="데이터베이스에서 태그가 지정된 이미지들을 확인할 수 있습니다",
            primary_color="#007bff",
            storage=storage
        )
        
    def get_select_label(self):
        return "🏷️ 태그 선택:"

    def load_combo_items(self):
        self.load_available_tags()
    
    def load_available_tags(self):
        try:
            # MongoDB에서 모든 고유한 태그 수집
            pipeline = [
                {"$match": {"tags": {"$exists": True, "$ne": []}}},
                {"$unwind": "$tags"},
                {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            tags_result = list(self.storage.annotations.aggregate(pipeline))
            
            self.combo.addItem("전체 태그")
            for tag_doc in tags_result:
                tag_name = tag_doc.get('_id', '')
                count = tag_doc.get('count', 0)
                if tag_name:
                    self.combo.addItem(f"{tag_name} ({count}개)")
            
            if not tags_result:
                self.combo.addItem("태그가 있는 이미지가 없습니다")
                
        except Exception as e:
            print(f"[DEBUG] load_available_tags error: {e}")
            self.combo.addItem("태그 로드 실패")


class StatusPicker(BaseImagePickerDialog):
    def __init__(self, parent=None, storage=None):
        super().__init__(
            parent=parent,
            title="검수 상태별로 이미지를 확인하세요",
            icon="🔍",
            description="Description이 포함된 이미지들을 검수 상태별로 분류하여 볼 수 있습니다",
            primary_color="#28a745",
            storage=storage
        )
        
    def get_select_label(self):
        return "📊 검수 상태:"
        
    def load_combo_items(self):
        self.combo.addItems(["전체", "1차 검수 요청 전", "1차 검수 요청 후", "반려"])


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(
        self,
        app,
        config=None,
        filename=None,
        output=None,
        output_file=None,
        output_dir=None,
    ):
        super().__init__()
        self.app = app
        self.config = config

        self.setContentsMargins(0, 0, 0, 0)
        self.setWindowTitle(__appname__)

        # Initialize MongoDB storage
        self.mongo_storage = None
        try:
            if get_storage:
                self.mongo_storage = get_storage()
        except Exception:
            self.mongo_storage = None

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Top file index bar
        self.top_info_bar = QHBoxLayout()
        self.top_info_bar.setContentsMargins(0, 0, 4, 6)
        self.file_index_label_top = QLabel("[ - / - ]")
        self.file_index_label_top.setStyleSheet(
            "color:#2b6; font-weight:bold; padding:2px 6px; border:1px solid #3a3a3a; border-radius:4px;"
        )
        self.top_info_bar.addWidget(self.file_index_label_top)

        self.top_info_bar.addStretch(1)
        main_layout.addLayout(self.top_info_bar)
        self.labeling_widget = LabelingWrapper(
            self,
            config=config,
            filename=filename,
            output=output,
            output_file=output_file,
            output_dir=output_dir,
        )
        main_layout.addWidget(self.labeling_widget)
        widget = QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)
        self.setup_menu_bar()

        status_bar = QStatusBar()
        try:
            db_ok = self.mongo_storage.test_connection() if self.mongo_storage else False
        except Exception:
            db_ok = False
        db_txt = '연결 성공' if db_ok else '연결 실패'
        status_bar.showMessage(f"{__appname__} - {__appdescription__} | DB: {db_txt}")
        self.setStatusBar(status_bar)

        self.review_window = None
        self.gallery_window = None
        self._PATH_FIELDS = ("image_file_path", "imagePath", "file_path", "path")

    def set_top_file_index_text(self, text: str):
        if hasattr(self, 'file_index_label_top'):
            self.file_index_label_top.setText(text)

    def closeEvent(self, event):
        self.labeling_widget.closeEvent(event)

    def setup_menu_bar(self):
        """Set up the menu bar, adding the DB menu to the far right."""
        menubar = self.menuBar()
        
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        spacer_action = QWidgetAction(self)
        spacer_action.setDefaultWidget(spacer)
        menubar.addAction(spacer_action)

        db_menu = menubar.addMenu('DB')

        manage_action = QAction('데이터베이스 관리', self)
        manage_action.setShortcut('Ctrl+Shift+D')
        manage_action.triggered.connect(self.open_db_manager_dialog)
        db_menu.addAction(manage_action)

        improved_action = QAction('태그 사진', self)
        improved_action.triggered.connect(self.open_review_manager_with_check)
        db_menu.addAction(improved_action)

        gallery_action = QAction('검수 사진', self)
        gallery_action.setShortcut('Ctrl+Shift+F')
        gallery_action.triggered.connect(self.show_image_gallery)
        db_menu.addAction(gallery_action)

        db_menu.addSeparator()

        search_action = QAction('빠른 검색', self)
        search_action.setShortcut('Ctrl+F')
        search_action.triggered.connect(self.search_db)
        db_menu.addAction(search_action)
        
        stats_action = QAction('통계 보기', self)
        stats_action.triggered.connect(self.show_db_stats)
        db_menu.addAction(stats_action)
        
        db_menu.addSeparator()
        
        settings_action = QAction('DB 설정', self)
        settings_action.triggered.connect(self.show_db_settings)
        db_menu.addAction(settings_action)
        
        db_menu.addSeparator()
        sync_action = QAction('JSON 동기화 상태', self)
        sync_action.triggered.connect(self.show_sync_status)
        db_menu.addAction(sync_action)
        
        manual_sync_action = QAction('수동 동기화', self)
        manual_sync_action.triggered.connect(self.manual_sync_current_directory)
        db_menu.addAction(manual_sync_action)

    # -------------------- DB Review Management --------------------
    def open_db_manager_dialog(self):
        """Opens the built-in DB manager dialog."""
        try:
            storage = getattr(self, 'mongo_storage', None)
            if not storage or not storage.test_connection():
                QMessageBox.warning(self, 'DB 관리', 'MongoDB에 연결할 수 없습니다. 설정을 확인하세요.')
                return

            from anylabeling.views.db_manager import DBManagerDialog

            if hasattr(self, 'db_manager_dialog') and self.db_manager_dialog is not None:
                try:
                    if not self.db_manager_dialog.isVisible():
                        self.db_manager_dialog.show()
                    self.db_manager_dialog.raise_()
                    self.db_manager_dialog.activateWindow()
                    return
                except Exception:
                    self.db_manager_dialog = None

            self.db_manager_dialog = DBManagerDialog(storage, self)
            self.db_manager_dialog.show()
            self.db_manager_dialog.raise_()
            self.db_manager_dialog.activateWindow()
            try:
                self.db_manager_dialog.destroyed.connect(lambda: setattr(self, 'db_manager_dialog', None))
            except Exception:
                pass
        except Exception as e:
            QMessageBox.critical(self, 'DB 관리 오류', f'DB 관리 창을 여는 중 오류가 발생했습니다:\n{str(e)}')

    def open_review_manager_with_check(self):
        """태그별 사진 보기"""
        try:
            self._pre_sync_json_changes()
        except Exception as e:
            print(f"[DEBUG] Pre-sync error (open_review_manager_with_check): {e}")

        storage = getattr(self, 'mongo_storage', None)
        if not storage or not storage.test_connection():
            QMessageBox.critical(self, "오류", "데이터베이스에 연결할 수 없습니다.")
            return



        def _resolve_image_path(doc):
            for key in ('image_file_path', 'imagePath'):
                path = doc.get(key)
                if path and isinstance(path, str) and os.path.exists(path): 
                    return path
            
            img_dir, img_name = doc.get('image_directory'), doc.get('image_file_name')
            if img_dir and img_name:
                candidate = os.path.normpath(os.path.join(str(img_dir), str(img_name)))
                if os.path.exists(candidate): 
                    return candidate
            
            json_path = doc.get('json_file_path') or doc.get('jsonPath')
            path = doc.get('imagePath')
            if path and json_path and isinstance(json_path, str) and not os.path.isabs(path):
                candidate = os.path.normpath(os.path.join(os.path.dirname(json_path), path))
                if os.path.exists(candidate): 
                    return candidate
            
            if json_path and isinstance(json_path, str):
                base_path, _ = os.path.splitext(json_path)
                for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif']:
                    potential_path = base_path + ext
                    if os.path.exists(potential_path): 
                        return potential_path
            return None

        def _get_tagged_image_paths(selected_tag):
            try:
                if selected_tag == "전체 태그":
                    # 태그가 하나라도 있는 모든 이미지
                    query = {"tags": {"$exists": True, "$ne": []}}
                else:
                    # 특정 태그를 가진 이미지만
                    tag_name = selected_tag.split(' (')[0] if ' (' in selected_tag else selected_tag
                    query = {"tags": tag_name}
                
                docs = list(storage.annotations.find(query))
                if not docs: 
                    return []
                
                image_paths = [path for doc in docs if (path := _resolve_image_path(doc))]
                return image_paths
                
            except Exception as e:
                print(f"[DEBUG] _get_tagged_image_paths error: {e}")
                return []

        picker = TagPicker(self, storage)
        def open_gallery_for_tag():
            selected_tag = picker.combo.currentText().strip()
            if "태그가 있는 이미지가 없습니다" in selected_tag or "태그 로드 실패" in selected_tag:
                QMessageBox.information(self, "태그 사진", "사용 가능한 태그가 없습니다.")
                return
                
            image_paths = _get_tagged_image_paths(selected_tag)
            
            if not image_paths:
                QMessageBox.information(self, "태그 사진", f"선택한 태그에 해당하는 이미지가 없습니다.\n\n태그: {selected_tag}")
                return
            
            gallery = ImageGallery(image_paths, parent=self)
            try:
                gallery.imageSelected.connect(self.load_files_batch)
            except Exception as e:
                print(f"[DEBUG] Gallery signal connection error: {e}")
            
            gallery.exec_()
            picker.accept()

        picker.view_btn.clicked.connect(open_gallery_for_tag)
        picker.exec_()

    def _get_current_filename_safe(self) -> str:
        """Safely returns the file path of the currently loaded image."""
        try:
            lw = getattr(self, 'labeling_widget', None)
            if not lw: return ''

            inner = None
            for attr in ('labeling_widget', 'widget', 'view'):
                if hasattr(lw, attr):
                    inner = getattr(lw, attr)
                    break
            if inner is None: inner = lw

            for name_attr in ('filename', 'image_path'):
                if hasattr(inner, name_attr):
                    val = getattr(inner, name_attr)
                    if isinstance(val, str) and val:
                        return val
            return ''
        except Exception:
            return ''

    def _open_from_mongo_if_description_present(self) -> bool:
        """Checks for a description in MongoDB for the current image and opens the review window."""
        try:
            storage = getattr(self, 'mongo_storage', None)
            if not storage or not storage.test_connection():
                return False

            current_path = self._get_current_filename_safe()
            if not current_path:
                db_any_path = self._find_any_image_path_with_description_in_db(storage)
                if self._is_existing_path(db_any_path):
                    try:
                        self.load_file(db_any_path)
                        self.open_review_manager()
                        return True
                    except Exception as e:
                        QMessageBox.warning(self, "DB 검수", f"DB에서 찾은 파일을 여는 데 실패했습니다.\n경로: {db_any_path}\n오류: {e}")
                else:
                    QMessageBox.information(self, "DB 검수", "MongoDB에서 검수 가능한 이미지를 찾지 못했습니다.")
                return False

            image_id = os.path.basename(current_path)
            doc = storage.annotations.find_one({"image_id": image_id, "description": {"$exists": True, "$ne": ""}})
            if not doc:
                or_queries = [{field: osp.abspath(current_path)} for field in self._PATH_FIELDS]
                if or_queries:
                    doc = storage.annotations.find_one({"$or": or_queries, "description": {"$exists": True, "$ne": ""}})
            
            if not doc:
                QMessageBox.information(self, "DB 검수", "MongoDB에 해당 이미지의 description이 없어 검수 창을 열 수 없습니다.")
                return False

            db_file_path = self._resolve_image_path_in_db(storage, current_path, image_id)
            target_path = db_file_path if self._is_existing_path(db_file_path) else (current_path if self._is_existing_path(current_path) else None)

            if target_path:
                if osp.abspath(target_path) != osp.abspath(current_path):
                    try:
                        self.load_file(target_path)
                    except Exception:
                        QMessageBox.warning(self, "DB 검수", f"파일을 여는 데 실패했습니다. 경로: {target_path}")
                self.open_review_manager()
                return True
            else:
                QMessageBox.information(self, "DB 검수", "MongoDB에 파일 경로 정보가 없거나 파일을 찾을 수 없습니다.")
                return False
        except Exception as e:
            QMessageBox.critical(self, "DB 검수", f"MongoDB 확인 중 오류가 발생했습니다:\n{str(e)}")
            return False

    def _find_any_image_path_with_description_in_db(self, storage) -> str:
        """Finds and returns the file path of any image with a description in MongoDB."""
        try:
            doc = None
            try:
                doc = storage.annotations.find_one({"description": {"$exists": True, "$ne": ""}}, sort=[("created_at", -1)])
            except Exception:
                doc = storage.annotations.find_one({"description": {"$exists": True, "$ne": ""}})

            if not doc: return ''

            for key in self._PATH_FIELDS:
                val = doc.get(key)
                if isinstance(val, str) and val and os.path.exists(val):
                    return val

            image_id = doc.get("image_id") or doc.get("filename")
            if image_id:
                img = storage.images.find_one({"image_id": image_id})
                if not img and isinstance(image_id, str):
                    abs_candidate = osp.abspath(image_id)
                    for field in self._PATH_FIELDS:
                        found = storage.images.find_one({field: abs_candidate})
                        if found:
                            img = found
                            break
                if img:
                    for key in self._PATH_FIELDS:
                        val = img.get(key)
                        if isinstance(val, str) and val and os.path.exists(val):
                            return val
            return ''
        except Exception:
            return ''

    def _resolve_image_path_in_db(self, storage, current_path: str, image_id: str = None) -> str:
        """Resolves and returns the optimal absolute image path from MongoDB."""
        try:
            abs_path = osp.abspath(current_path) if current_path else ''
            candidates = []
            if image_id:
                img = storage.images.find_one({"image_id": image_id})
                if img: candidates.append(img)

            for field in self._PATH_FIELDS:
                try:
                    doc = storage.images.find_one({field: abs_path})
                    if doc: candidates.append(doc)
                except Exception:
                    continue

            for img in candidates:
                for key in self._PATH_FIELDS:
                    val = img.get(key)
                    if isinstance(val, str) and val:
                        return val
            return ''
        except Exception:
            return ''

    def get_current_image_path_from_db(self) -> str:
        """Returns the absolute image path from MongoDB for the currently open file."""
        try:
            storage = getattr(self, 'mongo_storage', None)
            if not storage or not storage.test_connection(): return ''
            current_path = self._get_current_filename_safe()
            if not current_path: return ''
            image_id = os.path.basename(current_path)
            return self._resolve_image_path_in_db(storage, current_path, image_id)
        except Exception:
            return ''

    def _is_existing_path(self, path: str) -> bool:
        return isinstance(path, str) and bool(path) and os.path.exists(path)

    def open_review_manager(self):
        """Dynamically loads and displays improved_review_widgets.LabelMeReviewSearch."""
        if self.review_window is not None:
            try:
                if not self.review_window.isVisible():
                    self.review_window.show()
                self.review_window.raise_()
                self.review_window.activateWindow()
                return
            except Exception:
                self.review_window = None

        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        review_path = os.path.join(repo_root, "improved_review_widgets.py")

        try:
            if os.path.exists(review_path):
                spec = importlib.util.spec_from_file_location("improved_review_widgets", review_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    ReviewCls = getattr(module, "LabelMeReviewSearch", None)
                    if ReviewCls is None: raise AttributeError("LabelMeReviewSearch 클래스가 없습니다")
                    
                    self.review_window = ReviewCls()
                    try:
                        self.review_window.destroyed.connect(lambda: setattr(self, 'review_window', None))
                    except Exception:
                        pass
                    self.review_window.show()
                    self.review_window.raise_()
                    self.review_window.activateWindow()
                    return
            QMessageBox.information(self, "검수 관리", "개선된 검수 위젯(improved_review_widgets.py)을 찾을 수 없습니다.\nDB 메뉴의 '데이터베이스 관리'를 사용하세요.")
        except Exception as e:
            QMessageBox.critical(self, "검수 관리 오류", f"검수 관리 창을 여는 중 오류가 발생했습니다:\n{str(e)}")

    def show_image_gallery(self, status_cond=None, use_json_status_filter=False):
        try:
            try:
                self._pre_sync_json_changes()
            except Exception as e:
                print(f"[DEBUG] Pre-sync error (show_image_gallery): {e}")

            storage = getattr(self, 'mongo_storage', None)
            if not storage or not storage.test_connection():
                QMessageBox.critical(self, "오류", "데이터베이스에 연결할 수 없습니다.")
                return

            def _get_effective_status_from_doc(doc):
                status = doc.get('review_status') or doc.get('reviewStatus')
                if status:
                    status_str = str(status).strip().lower()
                    if status_str == 'requested': return '1차 검수 요청 후'
                    if status_str == 'rejected': return '반려'
                    return '1차 검수 요청 전'

                def _resolve_json_path_from_doc(d):
                    for key in ('json_file_path', 'jsonPath', 'annotation_path', 'json_path', 'jsonFile'):
                        jp = d.get(key)
                        if isinstance(jp, str) and os.path.exists(jp): return jp
                    for key in ('image_file_path', 'imagePath', 'file_path', 'path'):
                        ip = d.get(key)
                        if isinstance(ip, str) and ip:
                            cand = osp.splitext(ip)[0] + '.json'
                            if os.path.exists(cand): return cand
                    image_id = d.get('image_id') or d.get('filename')
                    img_dir = d.get('image_directory')
                    if isinstance(image_id, str) and isinstance(img_dir, str):
                        cand = osp.normpath(osp.join(img_dir, osp.splitext(image_id)[0] + '.json'))
                        if os.path.exists(cand): return cand
                    return None

                def _read_json_fields(jpath):
                    if not jpath or not os.path.exists(jpath): return None
                    try:
                        with open(jpath, 'r', encoding='utf-8') as f: j = json.load(f)
                        return {
                            'status': j.get('review_status') or j.get('reviewStatus') or (j.get('review', {}) or {}).get('status'),
                            'history': j.get('review_history') if isinstance(j.get('review_history'), list) else None,
                        }
                    except Exception: return None

                review_history = doc.get('review_history', [])
                if not review_history or review_history is None:
                    json_path = _resolve_json_path_from_doc(doc)
                    if storage and json_path and os.path.exists(json_path) and not doc.get('json_file_path') and '_id' in doc:
                        try:
                            storage.annotations.update_one({'_id': doc['_id']}, {'$set': {'json_file_path': json_path}})
                        except Exception: pass
                    json_info = _read_json_fields(json_path)
                    if json_info: review_history = json_info.get('history') or []

                if isinstance(review_history, list) and review_history:
                    last_entry = review_history[-1]
                    if isinstance(last_entry, dict):
                        status = last_entry.get('status', '').strip().lower()
                        if status == 'requested': return '1차 검수 요청 후'
                        if status == 'rejected': return '반려'
                        return '1차 검수 요청 전'

                review = doc.get('review', {})
                if isinstance(review, dict):
                    status = review.get('status')
                    if status:
                        status_str = str(status).strip().lower()
                        if status_str == 'requested': return '1차 검수 요청 후'
                        if status_str == 'rejected': return '반려'
                        return '1차 검수 요청 전'

                json_info_fb = _read_json_fields(_resolve_json_path_from_doc(doc))
                if json_info_fb:
                    jstatus = json_info_fb.get('status')
                    if isinstance(jstatus, str) and jstatus.strip():
                        norm = jstatus.strip().lower()
                        if norm == 'requested': return '1차 검수 요청 후'
                        if norm == 'rejected': return '반려'
                
                return '1차 검수 요청 전'

            def _resolve_image_path(doc):
                for key in ('image_file_path', 'imagePath'):
                    path = doc.get(key)
                    if path and isinstance(path, str) and os.path.exists(path): return path
                
                img_dir, img_name = doc.get('image_directory'), doc.get('image_file_name')
                if img_dir and img_name:
                    candidate = os.path.normpath(os.path.join(str(img_dir), str(img_name)))
                    if os.path.exists(candidate): return candidate
                
                json_path = doc.get('json_file_path') or doc.get('jsonPath')
                path = doc.get('imagePath')
                if path and json_path and isinstance(json_path, str) and not os.path.isabs(path):
                    candidate = os.path.normpath(os.path.join(os.path.dirname(json_path), path))
                    if os.path.exists(candidate): return candidate
                
                if json_path and isinstance(json_path, str):
                    base_path, _ = os.path.splitext(json_path)
                    for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif']:
                        potential_path = base_path + ext
                        if os.path.exists(potential_path): return potential_path
                return None

            def _get_filtered_image_paths(selected_status):
                try:
                    base_query = {"shapes": {"$elemMatch": {"description": {"$exists": True}}}}
                    docs = list(storage.annotations.find(base_query))
                    if not docs: return []
                    
                    filtered_docs = [doc for doc in docs if selected_status == "전체" or _get_effective_status_from_doc(doc) == selected_status]
                    
                    image_paths = [path for doc in filtered_docs if (path := _resolve_image_path(doc))]
                    return image_paths
                except Exception as e:
                    print(f"[DEBUG] _get_filtered_image_paths error: {e}")
                    return []

            picker = StatusPicker(self, storage)
            def open_gallery_for_current():
                selected_status = picker.combo.currentText().strip()
                image_paths = _get_filtered_image_paths(selected_status)
                
                if not image_paths:
                    QMessageBox.information(self, "검수 사진", f"선택한 상태에 해당하는 이미지가 없습니다.\n\n상태: {selected_status}\n\n※ shape-level description이 있는 이미지만 표시됩니다.")
                    return
                
                gallery = ImageGallery(image_paths, parent=self)
                try:
                    gallery.imageSelected.connect(self.load_files_batch)
                except Exception as e:
                    print(f"[DEBUG] Gallery signal connection error: {e}")
                
                gallery.exec_()
                picker.accept()

            picker.view_btn.clicked.connect(open_gallery_for_current)
            picker.exec_()

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "오류", f"갤러리를 여는 중 오류가 발생했습니다:\n{str(e)}")

    # -------------------- Json 파일 동기화 --------------------
    def _pre_sync_json_changes(self):
        """Syncs recently modified JSON files to the DB before UI actions."""
        try:
            sync_service = getattr(self, '_json_mongodb_sync_service', None)
            annotation_manager = getattr(self, 'annotation_manager', None)
            if not annotation_manager:
                try:
                    from anylabeling.services.annotation_manager import AnnotationManager
                    self.annotation_manager = annotation_manager = AnnotationManager()
                except Exception:
                    annotation_manager = None

            if not annotation_manager or not getattr(annotation_manager, 'collection', None):
                return

            candidate_dirs = set()
            lw = self.labeling_widget
            if lw:
                if hasattr(lw, 'image_path') and lw.image_path: candidate_dirs.add(os.path.dirname(lw.image_path))
                if hasattr(lw, 'output_dir') and lw.output_dir: candidate_dirs.add(lw.output_dir)
                if hasattr(lw, 'image_list'):
                    for p in lw.image_list[:100]:
                        try: candidate_dirs.add(os.path.dirname(p))
                        except Exception: pass
            
            synced, scanned, errors = 0, 0, 0
            filtered_dirs = [d for d in list(candidate_dirs)[:10] if "X-AnyLabeling" not in d]
            
            for d in filtered_dirs:
                try:
                    for name in os.listdir(d):
                        if not name.lower().endswith('.json'): continue
                        scanned += 1
                        json_path = os.path.join(d, name)
                        try:
                            json_mtime = os.path.getmtime(json_path)
                        except Exception: continue

                        db_doc = annotation_manager.collection.find_one({"json_file_path": os.path.abspath(json_path)}, {"updated_at": 1})
                        db_updated_ts = db_doc['updated_at'].timestamp() if db_doc and db_doc.get('updated_at') and hasattr(db_doc['updated_at'], 'timestamp') else None

                        if (db_updated_ts is None) or (json_mtime - (db_updated_ts or 0) > 1.0):
                            try:
                                ok = sync_service.sync_json_to_mongo(json_path) if sync_service else annotation_manager.sync_json_to_db(json_path)[0]
                                if ok: synced += 1
                                else: errors += 1
                            except Exception:
                                errors += 1
                except Exception: pass
            if scanned: print(f"[DEBUG] Pre-sync scan: {scanned} JSONs, synced: {synced}, errors: {errors}")
        except Exception as e:
            print(f"[DEBUG] _pre_sync_json_changes error: {e}")

    def _get_inner_labeling_widget(self):
        """Returns the actual LabelingWidget inside the LabelingWrapper."""
        if hasattr(self, 'labeling_widget') and self.labeling_widget:
            for attr in ('view', 'widget', 'labeling_widget'):
                if hasattr(self.labeling_widget, attr):
                    inner = getattr(self.labeling_widget, attr)
                    if hasattr(inner, 'set_file_list') or hasattr(inner, 'load_file'):
                        return inner
            return self.labeling_widget
        return None

    def load_files_batch(self, selected_path, all_paths, selected_index):
        """Loads a list of files into the labeling view at once."""
        lw = self._get_inner_labeling_widget()
        batch_loaded = False
        last_exc = None
        
        batch_methods = ('set_file_list', 'load_files', 'load_file_list')
        for method in batch_methods:
            if lw and hasattr(lw, method):
                fn = getattr(lw, method)
                try:
                    if method == 'set_file_list': fn(all_paths, selected_index)
                    else: fn(all_paths)
                    batch_loaded = True
                    break
                except Exception as e:
                    last_exc = (method, e)
        
        if not batch_loaded:
            if last_exc:
                method, e = last_exc
                QMessageBox.warning(self, "Image Batch Load Error", f"Error in '{method}':\n\n{type(e).__name__}: {e}\n\nLoading single file instead.")
            try:
                candidate = selected_path if self._is_existing_path(selected_path) else next((p for p in (all_paths or []) if self._is_existing_path(p)), selected_path)
                if candidate: self.load_file(candidate)
            except Exception as e:
                QMessageBox.critical(self, "Image Load Error", f"Failed to load selected file.\n\nPath: {selected_path}\n{type(e).__name__}: {e}")

    def on_gallery_closed(self):
        self.gallery_window = None

    def search_db(self):
        """Quick DB search."""
        query, ok = QInputDialog.getText(self, 'DB 빠른 검색', '검색어를 입력하세요 (번호판, 카테고리, 라벨):')
        if ok and query:
            try:
                results = self.mongo_storage.multi_field_search(query)
                if results:
                    self.show_search_results(results, query)
                else:
                    QMessageBox.information(self, '검색 결과', f'"{query}"에 대한 검색 결과가 없습니다.')
            except Exception as e:
                QMessageBox.critical(self, '검색 오류', f'검색 중 오류가 발생했습니다:\n{str(e)}')

    def show_db_stats(self):
        """간단한 통계 정보 표시"""
        try:
            stats = self.mongo_storage.get_database_stats()
            if not stats:
                QMessageBox.information(self, 'DB 통계', '통계 정보를 가져올 수 없습니다.')
                return

            def summarize(list_of_dicts, key='_id'):
                if not isinstance(list_of_dicts, list) or not list_of_dicts: return '없음'
                parts = [f"{item.get(key, 'N/A')}: {item.get('count', 0)}" for item in list_of_dicts[:10]]
                extra = f" 외 {len(list_of_dicts)-10}개" if len(list_of_dicts) > 10 else ""
                return ', '.join(parts) + extra

            msg = (
                f"총 이미지: {stats.get('total_images', 0)}\n"
                f"라벨 완료 이미지: {stats.get('labeled_images', 0)}\n"
                f"총 어노테이션: {stats.get('total_annotations', 0)}\n"
                f"진행률: {stats.get('progress', 0):.2f}%\n\n"
                f"카테고리별: {summarize(stats.get('categories', []))}\n"
                f"번호판 카테고리별: {summarize(stats.get('plate_categories', []))}"
            )
            QMessageBox.information(self, 'DB 통계', msg)
        except Exception as e:
            QMessageBox.critical(self, 'DB 통계 오류', f'통계 조회 중 오류가 발생했습니다:\n{str(e)}')

    def show_db_settings(self):
        """DB 세팅 및 접속 상태 표시"""
        try:
            uri = getattr(self.mongo_storage, 'uri', 'mongodb://localhost:27017/')
            ok = self.mongo_storage.test_connection()
            status = '성공' if ok else '실패'
            QMessageBox.information(self, 'DB 설정', f"연결 URI: {uri}\n연결 테스트: {status}")
        except Exception as e:
            QMessageBox.critical(self, 'DB 설정 오류', f'설정 표시 중 오류가 발생했습니다:\n{str(e)}')
    
    # -------------------- JSON <-> MongoDB 동기화 --------------------
    
    def show_sync_status(self):
        """Displays the JSON -> MongoDB sync status."""
        try:
            sync_service = getattr(self, '_json_mongodb_sync_service', None)
            if not sync_service:
                QMessageBox.information(self, '동기화 상태', 'JSON → MongoDB 동기화 서비스가 실행되지 않았습니다.')
                return
            
            stats = sync_service.get_stats()
            watch_dirs = sync_service.watch_directories
            
            status_text = f"동기화 서비스 상태: {'실행 중' if sync_service.is_running else '중지됨'}\n\n"
            status_text += f"총 동기화: {stats['total_syncs']}, 성공: {stats['successful_syncs']}, 실패: {stats['failed_syncs']}\n"
            status_text += f"감시 디렉토리 ({len(watch_dirs)}개):\n"
            status_text += "\n".join([f"{i}. {d}" for i, d in enumerate(watch_dirs[:5], 1)])
            if len(watch_dirs) > 5: status_text += f"\n... 외 {len(watch_dirs) - 5}개"
            
            QMessageBox.information(self, 'JSON → MongoDB 동기화 상태', status_text)
        except Exception as e:
            QMessageBox.critical(self, '동기화 상태 오류', f'상태 확인 중 오류:\n{str(e)}')
    
    def _is_valid_sync_directory(self, path, app_root):
        return path and isinstance(path, str) and os.path.exists(path) and os.path.normpath(path) != app_root

    def _get_current_labeling_directory(self, app_root):
        """Finds the current labeling directory."""
        lw = self._get_inner_labeling_widget()
        if not lw: return None
            
        paths_to_check = []
        image_list = getattr(lw, 'image_list', [])
        current_index = getattr(lw, 'current_index', None)
        
        if current_index is not None and 0 <= current_index < len(image_list):
            paths_to_check.append(image_list[current_index])
        paths_to_check.extend(image_list[:3])
        for attr in ('output_dir', 'image_path', 'current_dir', 'working_dir'):
            if val := getattr(lw, attr, None): paths_to_check.append(val)
        if cur := self._get_current_filename_safe(): paths_to_check.append(cur)
        
        for path in paths_to_check:
            if isinstance(path, str) and os.path.exists(path):
                candidate_dir = path if os.path.isdir(path) else os.path.dirname(path)
                if self._is_valid_sync_directory(candidate_dir, app_root):
                    return candidate_dir
        return None

    def _calculate_app_root(self):
        """Calculates the app root directory."""
        path_parts = os.path.abspath(__file__).split(os.sep)
        for i, part in enumerate(path_parts):
            if "X-AnyLabeling" in part:
                return os.path.normpath(os.sep.join(path_parts[:i+1]))
        return os.path.normpath(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

    def manual_sync_current_directory(self):
        """Manually syncs JSON files to MongoDB."""
        try:
            app_root = self._calculate_app_root()
            current_dir = self._get_current_labeling_directory(app_root)
            
            if not current_dir:
                current_dir = QFileDialog.getExistingDirectory(self, '동기화할 폴더 선택')
                if not current_dir or not self._is_valid_sync_directory(current_dir, app_root):
                    QMessageBox.warning(self, '수동 동기화', '선택한 폴더는 동기화할 수 없습니다.')
                    return
                if QMessageBox.question(self, '수동 동기화 확인', f'다음 디렉토리의 모든 JSON 파일을 MongoDB에 동기화하시겠습니까?\n\n{current_dir}', QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                    return
            
            sync_service = getattr(self, '_json_mongodb_sync_service', None)
            if not sync_service:
                from anylabeling.services.json_mongodb_sync import JSONMongoDBSyncService
                sync_service = JSONMongoDBSyncService(self)
            
            stats = sync_service.manual_sync_directory(current_dir)
            
            result_msg = f"수동 동기화 완료\n\n디렉토리: {current_dir}\n총 JSON: {stats['total']}, 성공: {stats['success']}, 실패: {stats['failed']}"
            if stats['failed'] > 0: QMessageBox.warning(self, '수동 동기화 결과', result_msg)
            else: QMessageBox.information(self, '수동 동기화 결과', result_msg)
        except Exception as e:
            QMessageBox.critical(self, '수동 동기화 오류', f'동기화 중 오류:\n{str(e)}')
    
    def set_json_mongodb_sync_service(self, sync_service):
        self._json_mongodb_sync_service = sync_service
        if sync_service:
            sync_service.syncCompleted.connect(self._on_sync_completed)
    
    def set_bidirectional_sync_service(self, sync_service):
        self._bidirectional_sync_service = sync_service
        if sync_service:
            sync_service.sync_completed.connect(self._on_bidirectional_sync_completed)
            sync_service.stats_updated.connect(self._on_sync_stats_updated)

    def add_sync_watch_directory(self, dir_path):
        """Adds a directory to the sync watch list and performs an immediate sync."""
        sync_service = getattr(self, '_bidirectional_sync_service', None)
        if sync_service and dir_path and os.path.isdir(dir_path):
            sync_service.add_watch_directory(dir_path)
            sync_service.manual_sync_all()
            self.statusBar().showMessage(f"동기화 폴더 추가 및 즉시 동기화: {dir_path}", 3000)
    
    def _on_bidirectional_sync_completed(self, file_path: str, success: bool):
        """Called on bidirectional sync completion."""
        msg = f"✅ 양방향 동기화 완료: {os.path.basename(file_path)}" if success else f"❌ 양방향 동기화 실패: {os.path.basename(file_path)}"
        self.statusBar().showMessage(msg, 3000 if success else 5000)
    
    def _on_sync_stats_updated(self, stats: dict):
        """Called when sync stats are updated."""
        status_msg = f"동기화 통계: JSON→DB {stats.get('json_to_mongodb', 0)}, DB→JSON {stats.get('mongodb_to_json', 0)}, 오류 {stats.get('errors', 0)}"
        self.statusBar().showMessage(status_msg, 2000)
    
    def _on_sync_completed(self, file_path: str, success: bool):
        """Slot called on sync completion."""
        try:
            if success and hasattr(self, 'statusBar'):
                self.statusBar().showMessage(f"✅ MongoDB 동기화: {os.path.basename(file_path)}", 3000)
        except Exception as e:
            from anylabeling.views.labeling.logger import logger
            logger.debug(f"Sync completion handling error: {e}")

    def load_file(self, filename=None):
        """Wrapper function to delegate file loading to the labeling_widget."""
        inner_widget = self._get_inner_labeling_widget()
        if inner_widget and hasattr(inner_widget, 'load_file'):
            return inner_widget.load_file(filename)
        
        QMessageBox.warning(self, "파일 로딩 오류", "파일 로딩 기능을 찾을 수 없습니다.")
        return False
