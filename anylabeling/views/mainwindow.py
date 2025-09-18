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
    QMenuBar,
    QAction,
    QInputDialog,
    QMessageBox,
    QCheckBox,
    QSizePolicy,
    QWidgetAction,
    QDialog,
    QComboBox,
    QPushButton,
)

from .image_gallery import ImageGallery
from ..app_info import __appdescription__, __appname__
from .labeling.label_wrapper import LabelingWrapper
try:
    from ..services.storage.mongo_provider import get_storage
except Exception:
    get_storage = None
from PyQt5.QtWidgets import QWidgetAction, QSizePolicy, QWidget
from PyQt5.QtCore import Qt

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

        # MongoDB 스토리지 초기화 (프로바이더 기반)
        self.mongo_storage = None
        try:
            if get_storage:
                self.mongo_storage = get_storage()
        except Exception:
            self.mongo_storage = None

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 상단 파일 인덱스 영역
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

        # 외부 리뷰 창 핸들러
        self.review_window = None
        self.gallery_window = None
        # 공통 상수: 경로 필드 우선순위
        self._PATH_FIELDS = ("image_file_path", "imagePath", "file_path", "path")

    # 도크 위젯: 레거시 의존성 제거됨 (LabelDock/FileDock/AnnotationDock 미정의)
    # 필요 시, labeling.label_widget 내부의 도크들을 사용하세요.

    def set_top_file_index_text(self, text: str):
        if hasattr(self, 'file_index_label_top'):
            self.file_index_label_top.setText(text)

    def closeEvent(self, event):
        self.labeling_widget.closeEvent(event)

    def setup_menu_bar(self):
        """메뉴바 설정 - DB 메뉴를 맨 오른쪽에 추가"""
        menubar = self.menuBar()
        
        # 스페이서를 추가하여 DB 메뉴를 오른쪽으로 밀어냄
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        spacer_action = QWidgetAction(self)
        spacer_action.setDefaultWidget(spacer)
        menubar.addAction(spacer_action)

        # DB 메뉴를 마지막에 추가하여 맨 오른쪽에 위치시킴
        db_menu = menubar.addMenu('DB')

        # DB 관리 액션 (내장 DBManagerDialog 열기)
        manage_action = QAction('데이터베이스 관리', self)
        # Ctrl+D는 도형 복제 등 다른 기능과 충돌 가능성이 높아 Ctrl+Shift+D로 조정
        manage_action.setShortcut('Ctrl+Shift+D')
        manage_action.triggered.connect(self.open_db_manager_dialog)
        db_menu.addAction(manage_action)
        
        # 사진 보기 액션
        gallery_action = QAction('사진 보기', self)
        gallery_action.triggered.connect(self.show_image_gallery)
        db_menu.addAction(gallery_action)
        
        db_menu.addSeparator()

        # (선택) 개선된 검수 위젯 열기 - 실험적
        improved_action = QAction('개선된 검수(실험적)', self)
        improved_action.triggered.connect(self.open_review_manager_with_check)
        db_menu.addAction(improved_action)

        # 빠른 검색 액션
        search_action = QAction('빠른 검색', self)
        search_action.setShortcut('Ctrl+F')
        search_action.triggered.connect(self.search_db)
        db_menu.addAction(search_action)
        
        # 통계 보기 액션
        stats_action = QAction('통계 보기', self)
        stats_action.triggered.connect(self.show_db_stats)
        db_menu.addAction(stats_action)
        
        db_menu.addSeparator()
        
        # 설정 액션
        settings_action = QAction('DB 설정', self)
        settings_action.triggered.connect(self.show_db_settings)
        db_menu.addAction(settings_action)
        
        # JSON → MongoDB 동기화 메뉴 추가
        db_menu.addSeparator()
        sync_action = QAction('JSON 동기화 상태', self)
        sync_action.triggered.connect(self.show_sync_status)
        db_menu.addAction(sync_action)
        
        manual_sync_action = QAction('수동 동기화', self)
        manual_sync_action.triggered.connect(self.manual_sync_current_directory)
        db_menu.addAction(manual_sync_action)

    # -------------------- DB 검수 관리 --------------------
    def open_db_manager_dialog(self):
        """내장 DB 관리 다이얼로그를 연다."""
        try:
            storage = getattr(self, 'mongo_storage', None)
            if not storage:
                QMessageBox.warning(self, 'DB 관리', 'MongoDB 스토리지 핸들이 없습니다. 설정을 확인하세요.')
                return
            if not storage.test_connection():
                QMessageBox.warning(self, 'DB 관리', 'MongoDB에 연결할 수 없습니다. DB 설정을 확인하세요.')
                return

            # 지연 임포트로 순환 참조/로딩 비용 최소화
            from anylabeling.views.db_manager import DBManagerDialog

            # 이미 떠 있다면 포커스만
            if hasattr(self, 'db_manager_dialog') and self.db_manager_dialog is not None:
                try:
                    # 숨겨져 있으면 다시 보여주기
                    if hasattr(self.db_manager_dialog, 'isVisible') and not self.db_manager_dialog.isVisible():
                        self.db_manager_dialog.show()
                    self.db_manager_dialog.raise_()
                    self.db_manager_dialog.activateWindow()
                    return
                except Exception:
                    # C++ 객체가 이미 파괴된 경우가 있으므로 참조 해제 후 재생성 경로로 진행
                    try:
                        self.db_manager_dialog = None
                    except Exception:
                        pass

            self.db_manager_dialog = DBManagerDialog(storage, self)
            # 모달이 필요 없도록 show, 필요 시 exec_()로 변경 가능
            self.db_manager_dialog.show()
            self.db_manager_dialog.raise_()
            self.db_manager_dialog.activateWindow()
            # 창이 닫히면 참조를 None으로 돌려 다음 호출 시 재생성되도록 함
            try:
                self.db_manager_dialog.destroyed.connect(lambda: setattr(self, 'db_manager_dialog', None))
            except Exception:
                pass
        except Exception as e:
            QMessageBox.critical(self, 'DB 관리 오류', f'DB 관리 창을 여는 중 오류가 발생했습니다:\n{str(e)}')
    def open_review_manager_with_check(self):
        """'데이터베이스 관리' 메뉴 클릭 시 호출됩니다. description 존재 여부를 확인하고 검수 창을 엽니다."""
        # 1) MongoDB에서 먼저 확인하고, 파일 경로를 찾아 열어준 뒤 리뷰 창을 연다
        if self._open_from_mongo_if_description_present():
            return

        # 2) MongoDB가 없거나 접속 실패 시, 이전 로컬 JSON 기준 폴백 검사를 수행
        current_file = self._get_current_filename_safe()
        if not current_file:
            QMessageBox.information(self, "DB 검수", "먼저 이미지 파일을 열어주세요.")
            return

        json_path = osp.splitext(current_file)[0] + '.json'
        try:
            if not osp.exists(json_path):
                QMessageBox.information(self, "DB 검수", "현재 파일의 JSON이 없거나 'description'이 없습니다.")
                return
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('description'):
                self.open_review_manager()
                return
            QMessageBox.information(self, "DB 검수", "현재 파일의 JSON에 'description' 필드가 없어 DB 검수 창을 열 수 없습니다.")
            return
        except (json.JSONDecodeError, IOError) as e:
            QMessageBox.warning(self, "DB 검수", f"JSON 파일을 읽는 중 오류가 발생했습니다:\n{e}")
            return

    def _get_current_filename_safe(self) -> str:
        """현재 로드된 이미지의 파일 경로를 안전하게 반환합니다.
        - LabelingWrapper(.widget/.labeling_widget/.view) 아래의 LabelingWidget.filename 우선
        - 없으면 image_path 사용
        - 실패 시 빈 문자열 반환
        """
        try:
            lw = getattr(self, 'labeling_widget', None)
            if not lw:
                return ''

            # Try common aliases first (we also expose these in LabelingWrapper)
            inner = None
            for attr in ('labeling_widget', 'widget', 'view'):
                if hasattr(lw, attr):
                    inner = getattr(lw, attr)
                    break

            # If not found, maybe MainWindow.labeling_widget is already the inner widget
            if inner is None:
                inner = lw

            # Prefer filename if available, fall back to image_path
            for name_attr in ('filename', 'image_path'):
                if hasattr(inner, name_attr):
                    val = getattr(inner, name_attr)
                    if isinstance(val, str) and val:
                        return val
            return ''
        except Exception:
            return ''

    def _open_from_mongo_if_description_present(self) -> bool:
        """MongoDB에서 현재 파일(이미지)의 어노테이션에 description이 있는지 먼저 확인하고,
        DB에 저장된 파일 경로가 있으면 해당 파일을 열어준 뒤 리뷰 창을 연다.
        Returns True if review was opened based on MongoDB; otherwise False.
        """
        try:
            storage = getattr(self, 'mongo_storage', None)
            if not storage:
                return False
            try:
                if not storage.test_connection():
                    return False
            except Exception:
                return False

            current_path = self._get_current_filename_safe()
            if not current_path:
                # 현재 열린 파일이 없다면, DB에서 description이 있는 최신 항목을 찾아 해당 파일을 연다
                db_any_path = self._find_any_image_path_with_description_in_db(storage)
                if self._is_existing_path(db_any_path):
                    try:
                        self.load_file(db_any_path)
                        self.open_review_manager()
                        return True
                    except Exception as e:
                        QMessageBox.warning(self, "DB 검수", f"DB에서 찾은 파일을 여는 데 실패했습니다.\n경로: {db_any_path}\n오류: {e}")
                        return False
                else:
                    QMessageBox.information(self, "DB 검수", "MongoDB에서 검수 가능한 이미지를 찾지 못했습니다.")
                    return False

            image_id = os.path.basename(current_path)

            # 어노테이션에 description이 존재하는지 확인 (image_id로 1차 확인)
            doc = storage.annotations.find_one({
                "image_id": image_id,
                "description": {"$exists": True, "$ne": ""}
            })
            # image_id로 실패하면 경로 기반 보조 검색(imagePath, image_file_path, file_path 등)을 시도
            if not doc:
                or_queries = []
                for field in ("imagePath", "image_file_path", "file_path", "path"):
                    or_queries.append({field: osp.abspath(current_path)})
                if or_queries:
                    doc = storage.annotations.find_one({
                        "$or": or_queries,
                        "description": {"$exists": True, "$ne": ""}
                    })
            if not doc:
                QMessageBox.information(self, "DB 검수", "MongoDB에 해당 이미지의 description이 없어 검수 창을 열 수 없습니다.")
                return False
            # 이미지 컬렉션에서 파일 경로 확인: 통합 헬퍼 사용
            db_file_path = self._resolve_image_path_in_db(storage, current_path, image_id)

            # DB 경로가 있고 접근 가능하면 해당 파일을 연다. 아니면 현재 열린 파일 유지
            target_path = db_file_path if self._is_existing_path(db_file_path) else (current_path if self._is_existing_path(current_path) else None)

            if target_path:
                try:
                    # 현재 열려있는 파일과 다르면 로드
                    if osp.abspath(target_path) != osp.abspath(current_path):
                        self.load_file(target_path)
                except Exception:
                    # 파일 열기 실패 시에도 검수창은 열어주되, 메시지 안내
                    QMessageBox.warning(self, "DB 검수", f"파일을 여는 데 실패했습니다. 경로: {target_path}")

                # 최종적으로 검수 창 오픈
                self.open_review_manager()
                return True
            else:
                QMessageBox.information(self, "DB 검수", "MongoDB에 파일 경로 정보가 없거나 파일을 찾을 수 없습니다.")
                return False

        except Exception as e:
            QMessageBox.critical(self, "DB 검수", f"MongoDB 확인 중 오류가 발생했습니다:\n{str(e)}")
            return False

    def _find_any_image_path_with_description_in_db(self, storage) -> str:
        """현재 열린 파일이 없을 때, MongoDB에서 description이 존재하는 임의(가능하면 최신)의 항목을 찾아
        해당 이미지의 실제 파일 경로를 반환한다. 없으면 빈 문자열.
        우선순위: annotation 문서 내 경로 필드 → images 컬렉션의 경로 필드.
        """
        try:
            # description이 있는 최신 어노테이션 조회 시도
            doc = None
            try:
                doc = storage.annotations.find_one({
                    "description": {"$exists": True, "$ne": ""}
                }, sort=[("created_at", -1)])
            except Exception:
                doc = storage.annotations.find_one({
                    "description": {"$exists": True, "$ne": ""}
                })

            if not doc:
                return ''

            # 1) 어노테이션 문서 자체에 경로 필드가 있을 경우 우선 사용
            for key in ("image_file_path", "imagePath", "file_path", "path"):
                val = doc.get(key)
                if isinstance(val, str) and val and os.path.exists(val):
                    return val

            # 2) images 컬렉션에서 보조 조회
            image_id = doc.get("image_id") or doc.get("filename")
            if image_id:
                img = storage.images.find_one({"image_id": image_id})
                if not img and isinstance(image_id, str):
                    # 혹시 image_id가 절대경로일 수 있으므로 경로 기반 조회도 시도
                    abs_candidate = osp.abspath(image_id)
                    for field in ("imagePath", "image_file_path", "file_path", "path"):
                        found = storage.images.find_one({field: abs_candidate})
                        if found:
                            img = found
                            break
                if img:
                    for key in ("image_file_path", "imagePath", "file_path", "path"):
                        val = img.get(key)
                        if isinstance(val, str) and val and os.path.exists(val):
                            return val
            return ''
        except Exception:
            return ''

    def _resolve_image_path_in_db(self, storage, current_path: str, image_id: str = None) -> str:
        """MongoDB(images)에서 다양한 필드(imagePath, image_file_path, file_path, path, filename)로
        현재 파일과 매칭되는 문서를 찾아, 최적의 imagePath(절대 경로)를 반환합니다. 없으면 빈 문자열.
        우선순위: image_file_path > imagePath > file_path > path > (filename과 current_path 디렉토리 조합은 생략)
        """
        try:
            abs_path = osp.abspath(current_path) if current_path else ''
            candidates = []
            # 1) image_id로 1차 조회
            if image_id:
                img = storage.images.find_one({"image_id": image_id})
                if img:
                    candidates.append(img)

            # 2) 경로 기반 조회 (인덱스가 있다면 빠르게 동작)
            for field in ("imagePath", "image_file_path", "file_path", "path"):
                try:
                    doc = storage.images.find_one({field: abs_path})
                    if doc:
                        candidates.append(doc)
                except Exception:
                    continue

            # 후보들에서 가장 적합한 경로 필드를 선택
            for img in candidates:
                for key in self._PATH_FIELDS:
                    val = img.get(key)
                    if isinstance(val, str) and val:
                        return val
            return ''
        except Exception:
            return ''

    # 외부에서 현재 파일 기준의 imagePath를 얻고 싶을 때 사용할 수 있는 공개 헬퍼
    def get_current_image_path_from_db(self) -> str:
        """현재 열린 파일을 기준으로 MongoDB에서 imagePath(절대 경로)를 찾아 반환. 없으면 빈 문자열."""
        try:
            storage = getattr(self, 'mongo_storage', None)
            if not storage or not storage.test_connection():
                return ''
            current_path = self._get_current_filename_safe()
            if not current_path:
                return ''
            image_id = os.path.basename(current_path)
            return self._resolve_image_path_in_db(storage, current_path, image_id)
        except Exception:
            return ''

    def _is_existing_path(self, path: str) -> bool:
        return isinstance(path, str) and bool(path) and os.path.exists(path)

    def open_review_manager(self):
        """improved_review_widgets.LabelMeReviewSearch를 동적 로드하여 표시"""
        # 이미 열려 있으면 포커스만
        if self.review_window is not None:
            try:
                # 숨겨져 있다면 다시 보여주기
                if hasattr(self.review_window, 'isVisible') and not self.review_window.isVisible():
                    self.review_window.show()
                self.review_window.raise_()
                self.review_window.activateWindow()
                return
            except Exception:
                # 이미 파괴되었을 수 있으므로 참조를 초기화하고 재생성 경로로 진행
                try:
                    self.review_window = None
                except Exception:
                    pass

        # 레포 루트에서 improved_review_widgets.py 경로 계산
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        review_path = os.path.join(repo_root, "improved_review_widgets.py")

        try:
            if os.path.exists(review_path):
                spec = importlib.util.spec_from_file_location("improved_review_widgets", review_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    ReviewCls = getattr(module, "LabelMeReviewSearch", None)
                    if ReviewCls is None:
                        raise AttributeError("LabelMeReviewSearch 클래스가 없습니다")
                    self.review_window = ReviewCls()
                    # 닫힌 뒤 두 번째 클릭에서도 열리도록 destroyed 시 참조 해제
                    try:
                        self.review_window.destroyed.connect(lambda: setattr(self, 'review_window', None))
                    except Exception:
                        pass
                    self.review_window.show()
                    self.review_window.raise_()
                    self.review_window.activateWindow()
                    return
            # 경로가 없거나 클래스 로드 실패 시 안내
            QMessageBox.information(
                self,
                "검수 관리",
                "개선된 검수 위젯(improved_review_widgets.py)을 찾을 수 없습니다.\nDB 메뉴의 '데이터베이스 관리'를 사용하세요.",
            )
        except Exception as e:
            QMessageBox.critical(self, "검수 관리 오류", f"검수 관리 창을 여는 중 오류가 발생했습니다:\n{str(e)}")

    def show_image_gallery(self, status_cond=None, use_json_status_filter=False):
        """라벨미 검수 프로그램과 동일한 로직으로 DB에서 이미지를 찾아 갤러리 형태로 보여줍니다."""
        try:
            storage = getattr(self, 'mongo_storage', None)
            if not storage:
                QMessageBox.critical(self, "오류", "데이터베이스에 연결할 수 없습니다.")
                return
            try:
                if not storage.test_connection():
                    QMessageBox.critical(self, "오류", "MongoDB 연결 테스트에 실패했습니다.")
                    return
            except Exception:
                QMessageBox.critical(self, "오류", "MongoDB 연결 확인 중 오류가 발생했습니다.")
                return

            # 상태 선택 다이얼로그 - 라벨미 검수와 동일한 옵션
            class StatusPicker(QDialog):
                def __init__(self, parent=None):
                    super().__init__(parent)
                    self.setWindowTitle("사진 보기 - 상태 필터")
                    self.setFixedSize(300, 150)
                    layout = QVBoxLayout(self)
                    
                    row = QHBoxLayout()
                    row.addWidget(QLabel("검수 상태:"))
                    self.combo = QComboBox()
                    self.combo.addItems([
                        "전체",
                        "1차 검수 요청 전", 
                        "1차 검수 요청 후",
                        "반려"
                    ])
                    row.addWidget(self.combo)
                    layout.addLayout(row)

                    btn_row = QHBoxLayout()
                    self.view_btn = QPushButton("보기")
                    self.close_btn = QPushButton("닫기")
                    btn_row.addStretch(1)
                    btn_row.addWidget(self.view_btn)
                    btn_row.addWidget(self.close_btn)
                    layout.addLayout(btn_row)

                    self.close_btn.clicked.connect(self.reject)

            def _get_effective_status_from_doc(doc):
                """단순화된 상태 판별 로직 - JSON 파일도 함께 확인"""
                # 디버그: 실제 데이터 구조 확인
                image_path = doc.get('image_file_path', doc.get('imagePath', 'Unknown'))
                print(f"\n[DEBUG] === 문서 분석: {image_path} ===")
                
                review_history = doc.get('review_history', [])
                print(f"  MongoDB review_history: {review_history}")
                
                # MongoDB에 review_history가 없으면 JSON 파일에서 직접 읽기
                if not review_history or review_history is None:
                    print(f"  MongoDB에 review_history 없음, JSON 파일 확인 시도...")
                    json_path = doc.get('json_file_path')
                    if json_path and isinstance(json_path, str) and os.path.exists(json_path):
                        try:
                            with open(json_path, 'r', encoding='utf-8') as f:
                                json_data = json.load(f)
                                review_history = json_data.get('review_history', [])
                                print(f"  JSON 파일에서 읽은 review_history: {review_history}")
                        except Exception as e:
                            print(f"  JSON 파일 읽기 실패: {e}")
                            review_history = []
                    else:
                        print(f"  JSON 파일 경로 없음 또는 파일 없음: {json_path}")
                
                # review_history 상태 판별
                if isinstance(review_history, list) and review_history:
                    last_entry = review_history[-1]
                    print(f"  마지막 항목: {last_entry}")
                    
                    if isinstance(last_entry, dict):
                        status = last_entry.get('status', '').strip()
                        print(f"  최신 status: '{status}'")
                        
                        if status.lower() == 'requested':
                            print(f"  → 1차 검수 요청 후")
                            return '1차 검수 요청 후'
                        elif status.lower() == 'rejected':
                            print(f"  → 반려")
                            return '반려'
                        elif not status or status == '':
                            print(f"  → 1차 검수 요청 전 (빈 상태)")
                            return '1차 검수 요청 전'
                        else:
                            print(f"  → 알 수 없는 상태: '{status}' → 1차 검수 요청 전")
                            return '1차 검수 요청 전'
                    else:
                        print(f"  마지막 항목이 dict가 아님: {type(last_entry)}")
                else:
                    print(f"  review_history가 없거나 비어있음")
                
                # MongoDB의 다른 상태 필드 확인
                status = doc.get('review_status') or doc.get('reviewStatus')
                if status:
                    status_str = str(status).strip()
                    print(f"  review_status: '{status_str}'")
                    if status_str.lower() == 'requested':
                        print(f"  → review_status에서 1차 검수 요청 후")
                        return '1차 검수 요청 후'
                    elif status_str.lower() == 'rejected':
                        print(f"  → review_status에서 반려")
                        return '반려'
                    else:
                        print(f"  → review_status 알 수 없는 상태: {status_str}")
                        return '1차 검수 요청 전'
                
                # review.status (nested) 확인
                review = doc.get('review', {})
                if isinstance(review, dict):
                    status = review.get('status')
                    if status:
                        status_str = str(status).strip()
                        print(f"  review.status: '{status_str}'")
                        if status_str.lower() == 'requested':
                            print(f"  → review.status에서 1차 검수 요청 후")
                            return '1차 검수 요청 후'
                        elif status_str.lower() == 'rejected':
                            print(f"  → review.status에서 반려")
                            return '반려'
                        else:
                            print(f"  → review.status 알 수 없는 상태: {status_str}")
                            return '1차 검수 요청 전'
                
                # 기본값
                print(f"  → 모든 상태 필드 없음, 기본값: 1차 검수 요청 전")
                return '1차 검수 요청 전'

            def _normalize_status(status_value):
                """상태값을 정규화 - 라벨미와 동일한 별칭 처리"""
                if not status_value:
                    return '1차 검수 요청 전'
                
                norm = str(status_value).strip().lower()
                
                # 요청 계열 (더 많은 변형 추가)
                if norm in ['requested', 'request', '요청', '1차 검수 요청', '1차 검수 요청 후', 'pending', 'submitted']:
                    return '1차 검수 요청 후'
                
                # 반려 계열 (더 많은 변형 추가)
                if norm in ['rejected', 'reject', '반려', 'declined', 'denied', 'failed']:
                    return '반려'
                
                # 완료 계열
                if norm in ['completed', 'complete', '완료', '1차 검수 완료', 'done', 'finished']:
                    return '1차 검수 완료'
                
                # 승인 계열
                if norm in ['approved', 'approve', '승인', '최종 승인', 'accepted', 'passed']:
                    return '최종 승인'
                
                # 알 수 없는 상태값도 로그에 남기기
                print(f"[DEBUG] 알 수 없는 상태값: '{status_value}' (normalized: '{norm}')")
                
                # 기본값
                return '1차 검수 요청 전'

            def _resolve_image_path(doc):
                """라벨미 검수 위젯과 동일한 파일 경로 해석 로직"""
                # 1순위: image_file_path (절대경로)
                path = doc.get('image_file_path')
                if path and isinstance(path, str) and os.path.exists(path):
                    return path
                
                # 2순위: image_directory + image_file_name 조합
                img_dir = doc.get('image_directory')
                img_name = doc.get('image_file_name')
                if img_dir and img_name:
                    candidate = os.path.normpath(os.path.join(str(img_dir), str(img_name)))
                    if os.path.exists(candidate):
                        return candidate
                
                # 3순위: imagePath (절대경로)
                path = doc.get('imagePath')
                if path and isinstance(path, str):
                    if os.path.isabs(path) and os.path.exists(path):
                        return path
                
                # 4순위: imagePath (상대경로) + json_file_path 기준 재구성
                json_path = (
                    doc.get('json_file_path') or 
                    doc.get('jsonPath') or 
                    doc.get('annotation_path') or
                    doc.get('json_path') or
                    doc.get('jsonFile')
                )
                
                if path and json_path and isinstance(json_path, str):
                    if not os.path.isabs(path):
                        candidate = os.path.normpath(os.path.join(os.path.dirname(json_path), path))
                        if os.path.exists(candidate):
                            return candidate
                
                # 5순위: json_file_path에서 확장자 변경으로 이미지 추정
                if json_path and isinstance(json_path, str):
                    base_path, _ = os.path.splitext(json_path)
                    for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif']:
                        potential_path = base_path + ext
                        if os.path.exists(potential_path):
                            return potential_path
                return None

            def _get_filtered_image_paths(selected_status):
                """선택된 상태에 따라 필터링된 이미지 경로 목록 반환"""
                try:
                    print(f"[DEBUG] 상태 필터링 시작: {selected_status}")
                    
                    # shape-level description이 있는 문서들만 조회
                    base_query = {
                        "shapes": {
                            "$elemMatch": {
                                "description": {
                                    "$exists": True,
                                    "$ne": None,
                                    "$ne": "",
                                    "$type": "string",
                                    "$regex": r"\S"
                                }
                            }
                        }
                    }
                    
                    docs = list(storage.annotations.find(base_query))
                    print(f"[DEBUG] shape-level description이 있는 문서 수: {len(docs)}")
                    
                    if not docs:
                        return []
                    
                    # 각 문서의 상태를 판별하고 필터링
                    filtered_docs = []
                    status_counts = {}
                    
                    for doc in docs:
                        # 라벨미와 동일한 상태 판별
                        eff_status = _get_effective_status_from_doc(doc)
                        status_counts[eff_status] = status_counts.get(eff_status, 0) + 1
                        
                        # 선택된 상태에 맞는지 확인
                        if selected_status == "전체" or eff_status == selected_status:
                            filtered_docs.append(doc)
                    
                    print(f"[DEBUG] 상태별 문서 수: {status_counts}")
                    print(f"[DEBUG] '{selected_status}' 필터 적용 후 문서 수: {len(filtered_docs)}")
                    
                    # 각 문서에서 이미지 경로 추출
                    image_paths = []
                    path_resolution_stats = {'success': 0, 'failed': 0}
                    
                    for doc in filtered_docs:
                        resolved_path = _resolve_image_path(doc)
                        if resolved_path:
                            image_paths.append(resolved_path)
                            path_resolution_stats['success'] += 1
                        else:
                            path_resolution_stats['failed'] += 1
                    
                    print(f"[DEBUG] 경로 해석 통계: {path_resolution_stats}")
                    print(f"[DEBUG] 최종 이미지 경로 수: {len(image_paths)}")
                    
                    if image_paths:
                        print(f"[DEBUG] 샘플 경로: {image_paths[:3]}")
                    
                    return image_paths
                    
                except Exception as e:
                    print(f"[DEBUG] _get_filtered_image_paths 오류: {e}")
                    import traceback
                    traceback.print_exc()
                    return []

            # 상태 선택 다이얼로그 표시
            picker = StatusPicker(self)

            def open_gallery_for_current():
                selected_status = picker.combo.currentText().strip()
                print(f"[DEBUG] 선택된 상태: '{selected_status}'")
                
                # 상태에 따른 이미지 경로 가져오기
                image_paths = _get_filtered_image_paths(selected_status)
                
                if not image_paths:
                    QMessageBox.information(
                        self, 
                        "사진 보기", 
                        f"선택한 상태에 해당하는 이미지가 없습니다.\n\n상태: {selected_status}\n\n※ shape-level description이 있는 이미지만 표시됩니다."
                    )
                    return
                
                # 갤러리 열기
                gallery = ImageGallery(image_paths, parent=self)
                try:
                    gallery.imageSelected.connect(self.load_files_batch)
                except Exception as e:
                    print(f"[DEBUG] 갤러리 시그널 연결 오류: {e}")
                
                gallery.exec_()

            picker.view_btn.clicked.connect(open_gallery_for_current)
            picker.exec_()

        except Exception as e:
            print(f"[ERROR] show_image_gallery 전체 오류: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "오류", f"갤러리를 여는 중 오류가 발생했습니다:\n{str(e)}")

    def _get_inner_labeling_widget(self):
        """LabelingWrapper 내부의 실제 LabelingWidget(view)을 반환한다."""
        if hasattr(self, 'labeling_widget') and self.labeling_widget:
            # LabelingWrapper(view/widget/labeling_widget) 경로 중 존재하는 것을 우선 사용
            for attr in ('view', 'widget', 'labeling_widget'):
                if hasattr(self.labeling_widget, attr):
                    inner = getattr(self.labeling_widget, attr)
                    # 최소한 set_file_list 또는 load_file이 있어야 실제 위젯으로 간주
                    if hasattr(inner, 'set_file_list') or hasattr(inner, 'load_file'):
                        return inner
            # 그래도 없으면 Wrapper 자체 반환 (호환용)
            return self.labeling_widget
        return None

    def load_files_batch(self, selected_path, all_paths, selected_index):
        """
        이미지 갤러리에서 선택 시 전체 파일 리스트를 라벨링 뷰에 한 번에 로드하고, 선택 인덱스부터 보여줌.
        에러 발생 시 사용자에게 명확한 안내를 제공.
        """
        import os
        norm_sel = os.path.normpath(str(selected_path)) if selected_path else selected_path
        norm_list = [os.path.normpath(str(p)) for p in (all_paths or [])]
        print(f"[load_files_batch] called: selected_path={norm_sel}, all_paths={norm_list}, selected_index={selected_index}")

        lw = None
        if hasattr(self, 'labeling_widget') and hasattr(self.labeling_widget, 'view'):
            lw = self.labeling_widget.view
        else:
            # fallback
            lw = self._get_inner_labeling_widget()
        # 메서드별 시그니처가 다르므로 호출 인자를 분기한다
        batch_methods = ('set_file_list', 'load_files', 'load_file_list')
        batch_loaded = False
        last_exc = None
        for method in batch_methods:
            if lw and hasattr(lw, method):
                print(f"[load_files_batch] try method: {method}")
                fn = getattr(lw, method)
                try:
                    if method == 'set_file_list':
                        fn(all_paths, selected_index)
                    else:
                        # load_files / load_file_list 유형은 보통 (file_list)만 받음
                        fn(all_paths)
                    print(f"[load_files_batch] {method} success")
                    batch_loaded = True
                    break
                except Exception as e:
                    print(f"[load_files_batch] {method} exception: {e}")
                    last_exc = (method, e)
        if not batch_loaded:
            # 일괄 로드 실패 시 사용자에게 안내
            if last_exc:
                method, e = last_exc
                QMessageBox.warning(self, "이미지 일괄 로드 오류", f"라벨링 뷰의 '{method}' 메서드에서 오류가 발생했습니다.\n\n{type(e).__name__}: {e}\n\n개별 파일만 로드합니다.")
            # 아니면 선택 파일만 로드 (이것도 실패할 수 있으니 예외 처리)
            try:
                # 우선 존재하는 경로를 하나 찾아서 로드 시도
                candidate = None
                # 1) 선택된 경로가 실제로 존재하면 우선 사용
                if self._is_existing_path(selected_path):
                    candidate = selected_path
                else:
                    # 2) 전체 리스트에서 존재하는 첫 경로를 사용
                    for p in (all_paths or []):
                        if self._is_existing_path(p):
                            candidate = p
                            break
                if candidate is None:
                    # 3) 모두 존재하지 않으면 그대로 선택 경로를 사용 (에러 메시지는 아래 except가 처리)
                    candidate = selected_path
                print(f"[load_files_batch] fallback: load_file({os.path.normpath(str(candidate)) if candidate else candidate})")
                self.load_file(candidate)
            except Exception as e:
                print(f"[load_files_batch] load_file exception: {e}")
                QMessageBox.critical(self, "이미지 로드 오류", f"선택한 파일을 로드하는 중 오류가 발생했습니다.\n\n경로: {selected_path}\n{type(e).__name__}: {e}")

    def on_gallery_closed(self):
        """갤러리 창이 닫힐 때 호출됩니다."""
        self.gallery_window = None

    def search_db(self):
        """빠른 DB 검색"""
        query, ok = QInputDialog.getText(
            self, 'DB 빠른 검색', 
            '검색어를 입력하세요 (번호판, 카테고리, 라벨):'
        )
        
        if ok and query:
            try:
                # 다중 필드 검색
                results = self.mongo_storage.multi_field_search(query)
                
                if results:
                    # 검색 결과 표시 다이얼로그
                    self.show_search_results(results, query)
                else:
                    QMessageBox.information(
                        self, '검색 결과', 
                        f'"{query}"에 대한 검색 결과가 없습니다.'
                    )
                    
            except Exception as e:
                QMessageBox.critical(
                    self, '검색 오류', 
                    f'검색 중 오류가 발생했습니다:\n{str(e)}'
                )

    def show_db_stats(self):
        """MongoDB에 저장된 통계 정보를 간단히 표시"""
        try:
            stats = self.mongo_storage.get_database_stats()
            if not stats:
                QMessageBox.information(self, 'DB 통계', '통계 정보를 가져올 수 없습니다.')
                return

            total_images = stats.get('total_images', 0)
            labeled_images = stats.get('labeled_images', 0)
            total_annotations = stats.get('total_annotations', 0)
            progress = stats.get('progress', 0)

            # 카테고리/번호판 카테고리 요약 문자열 생성
            def summarize(list_of_dicts, key='_id'):
                if not isinstance(list_of_dicts, list) or not list_of_dicts:
                    return '없음'
                parts = []
                for item in list_of_dicts[:10]:  # 최대 10개만 요약
                    name = str(item.get(key, 'N/A'))
                    cnt = item.get('count', 0)
                    parts.append(f"{name}: {cnt}")
                extra = '' if len(list_of_dicts) <= 10 else f" 외 {len(list_of_dicts)-10}개"
                return ', '.join(parts) + extra

            categories_txt = summarize(stats.get('categories', []))
            plate_categories_txt = summarize(stats.get('plate_categories', []))

            msg = (
                f"총 이미지: {total_images}\n"
                f"라벨 완료 이미지: {labeled_images}\n"
                f"총 어노테이션: {total_annotations}\n"
                f"진행률: {progress:.2f}%\n\n"
                f"카테고리별: {categories_txt}\n"
                f"번호판 카테고리별: {plate_categories_txt}"
            )
            QMessageBox.information(self, 'DB 통계', msg)
        except Exception as e:
            QMessageBox.critical(self, 'DB 통계 오류', f'통계 조회 중 오류가 발생했습니다:\n{str(e)}')

    def show_db_settings(self):
        """현재 DB 설정을 간단히 표시하고 연결 테스트 결과를 알려줍니다."""
        try:
            uri = getattr(self.mongo_storage, 'uri', 'mongodb://localhost:27017/')
            ok = self.mongo_storage.test_connection()
            status = '성공' if ok else '실패'
            QMessageBox.information(
                self,
                'DB 설정',
                f"연결 URI: {uri}\n연결 테스트: {status}"
            )
        except Exception as e:
            QMessageBox.critical(self, 'DB 설정 오류', f'설정 표시 중 오류가 발생했습니다:\n{str(e)}')
    
    # -------------------- JSON → MongoDB 동기화 관련 --------------------
    
    def show_sync_status(self):
        """JSON → MongoDB 동기화 상태 표시"""
        try:
            # JSON 동기화 서비스 찾기
            sync_service = getattr(self, '_json_mongodb_sync_service', None)
            
            if not sync_service:
                QMessageBox.information(
                    self,
                    '동기화 상태',
                    'JSON → MongoDB 동기화 서비스가 실행되지 않았습니다.\n앱을 다시 시작해주세요.'
                )
                return
            
            # 통계 정보 가져오기
            stats = sync_service.get_stats()
            is_running = sync_service.is_running
            watch_dirs = sync_service.watch_directories
            
            status_text = f"동기화 서비스 상태: {'실행 중' if is_running else '중지됨'}\n\n"
            status_text += f"총 동기화 횟수: {stats['total_syncs']}\n"
            status_text += f"성공: {stats['successful_syncs']}\n"
            status_text += f"실패: {stats['failed_syncs']}\n"
            status_text += f"성공률: {stats['success_rate']}%\n\n"
            status_text += f"감시 디렉토리 ({len(watch_dirs)}개):\n"
            
            for i, directory in enumerate(watch_dirs[:5], 1):  # 최대 5개만 표시
                status_text += f"{i}. {directory}\n"
            
            if len(watch_dirs) > 5:
                status_text += f"... 외 {len(watch_dirs) - 5}개\n"
            
            QMessageBox.information(self, 'JSON → MongoDB 동기화 상태', status_text)
            
        except Exception as e:
            QMessageBox.critical(self, '동기화 상태 오류', f'상태 확인 중 오류:\n{str(e)}')
    
    def manual_sync_current_directory(self):
        """현재 디렉토리의 JSON 파일들을 수동으로 MongoDB에 동기화"""
        try:
            # 현재 작업 디렉토리 확인
            current_dir = None
            
            if hasattr(self, 'labeling_widget') and self.labeling_widget:
                widget = self.labeling_widget
                
                # 현재 이미지의 디렉토리 사용
                if hasattr(widget, 'image_path') and widget.image_path:
                    current_dir = os.path.dirname(widget.image_path)
                
                # 또는 출력 디렉토리 사용
                elif hasattr(widget, 'output_dir') and widget.output_dir:
                    current_dir = widget.output_dir
            
            # 디렉토리가 없으면 기본 디렉토리 사용
            if not current_dir or not os.path.exists(current_dir):
                current_dir = r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file"
            
            if not os.path.exists(current_dir):
                QMessageBox.warning(
                    self,
                    '수동 동기화',
                    f'동기화할 디렉토리를 찾을 수 없습니다:\n{current_dir}'
                )
                return
            
            # 사용자 확인
            reply = QMessageBox.question(
                self,
                '수동 동기화 확인',
                f'다음 디렉토리의 모든 JSON 파일을 MongoDB에 동기화하시겠습니까?\n\n{current_dir}',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # JSON 동기화 서비스 찾기
            sync_service = getattr(self, '_json_mongodb_sync_service', None)
            
            if not sync_service:
                # 임시 동기화 서비스 생성
                from anylabeling.services.json_mongodb_sync import JSONMongoDBSyncService
                sync_service = JSONMongoDBSyncService(self)
            
            # 수동 동기화 실행
            stats = sync_service.manual_sync_directory(current_dir)
            
            # 결과 표시
            result_msg = f"수동 동기화 완료\n\n"
            result_msg += f"디렉토리: {current_dir}\n"
            result_msg += f"총 JSON 파일: {stats['total']}개\n"
            result_msg += f"성공: {stats['success']}개\n"
            result_msg += f"실패: {stats['failed']}개"
            
            if stats['failed'] > 0:
                QMessageBox.warning(self, '수동 동기화 결과', result_msg)
            else:
                QMessageBox.information(self, '수동 동기화 결과', result_msg)
            
        except Exception as e:
            QMessageBox.critical(self, '수동 동기화 오류', f'동기화 중 오류:\n{str(e)}')
    
    def set_json_mongodb_sync_service(self, sync_service):
        """JSON → MongoDB 동기화 서비스 설정 (app.py에서 호출) - 이전 버전 호환성"""
        self._json_mongodb_sync_service = sync_service
        
        # 동기화 완료 시그널 연결
        if sync_service:
            sync_service.syncCompleted.connect(self._on_sync_completed)
    
    def set_bidirectional_sync_service(self, sync_service):
        """양방향 JSON ↔ MongoDB 동기화 서비스 설정 (app.py에서 호출)"""
        self._bidirectional_sync_service = sync_service
        
        # 동기화 완료 시그널 연결
        if sync_service:
            sync_service.sync_completed.connect(self._on_bidirectional_sync_completed)
            sync_service.stats_updated.connect(self._on_sync_stats_updated)

    def add_sync_watch_directory(self, dir_path):
        """폴더를 동기화 감시 대상에 추가하고 즉시 동기화 수행"""
        sync_service = getattr(self, '_bidirectional_sync_service', None)
        if sync_service and dir_path and os.path.isdir(dir_path):
            sync_service.add_watch_directory(dir_path)
            # 바로 동기화
            sync_service.manual_sync_all()
            self.statusBar().showMessage(f"동기화 폴더 추가 및 즉시 동기화: {dir_path}", 3000)
    
    def _on_bidirectional_sync_completed(self, file_path: str, success: bool):
        """양방향 동기화 완료 시 호출"""
        if success:
            self.statusBar().showMessage(f"✅ 양방향 동기화 완료: {os.path.basename(file_path)}", 3000)
        else:
            self.statusBar().showMessage(f"❌ 양방향 동기화 실패: {os.path.basename(file_path)}", 5000)
    
    def _on_sync_stats_updated(self, stats: dict):
        """동기화 통계 업데이트 시 호출"""
        json_to_mongo = stats.get('json_to_mongodb', 0)
        mongo_to_json = stats.get('mongodb_to_json', 0)
        errors = stats.get('errors', 0)
        last_sync = stats.get('last_sync', 'N/A')
        
        status_msg = f"동기화 통계: JSON→DB {json_to_mongo}, DB→JSON {mongo_to_json}, 오류 {errors}, 마지막 {last_sync}"
        self.statusBar().showMessage(status_msg, 2000)
    
    def _on_sync_completed(self, file_path: str, success: bool):
        """동기화 완료 시 호출되는 슬롯"""
        try:
            if success:
                # 상태바에 성공 메시지 표시 (선택적)
                if hasattr(self, 'statusBar'):
                    filename = os.path.basename(file_path)
                    self.statusBar().showMessage(f"✅ MongoDB 동기화: {filename}", 3000)
            else:
                # 실패 시에도 로그만 기록 (너무 많은 팝업 방지)
                from anylabeling.views.labeling.logger import logger
                logger.debug(f"JSON → MongoDB 동기화 실패: {file_path}")
                
        except Exception as e:
            from anylabeling.views.labeling.logger import logger
            logger.debug(f"동기화 완료 처리 오류: {e}")

    def load_file(self, filename=None):
        """파일 로딩을 labeling_widget에 위임하는 래퍼 함수"""
        if hasattr(self, 'labeling_widget') and self.labeling_widget:
            # LabelingWrapper는 내부적으로 view 또는 widget 속성을 통해 LabelingWidget에 접근합니다.
            # LabelingWidget 자체에 load_file이 있습니다.
            inner_widget = None
            for attr in ('view', 'widget', 'labeling_widget'):
                if hasattr(self.labeling_widget, attr):
                    inner_widget = getattr(self.labeling_widget, attr)
                    break
            
            if inner_widget is None:
                inner_widget = self.labeling_widget

            if hasattr(inner_widget, 'load_file'):
                return inner_widget.load_file(filename)
        
        # 폴백: 에러 메시지
        QMessageBox.warning(self, "파일 로딩 오류", "파일 로딩 기능을 찾을 수 없습니다.")
        return False
