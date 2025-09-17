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
)

from .image_gallery import ImageGallery
from ..app_info import __appdescription__, __appname__
from .labeling.label_wrapper import LabelingWrapper
try:
    from ..services.storage.mongo_provider import get_storage
except Exception:
    get_storage = None
from PyQt5.QtWidgets import QWidgetAction, QSizePolicy, QWidget

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

        self.review_window = None
        self.gallery_window = None
        # 공통 상수: 경로 필드 우선순위 (중복 제거)
        self.PATH_FIELDS = ("image_file_path", "imagePath", "file_path", "path")
        
        # 경로 캐시 (성능 최적화)
        self._path_cache = {}

    def set_top_file_index_text(self, text: str):
        if hasattr(self, 'file_index_label_top'):
            self.file_index_label_top.setText(text)

    # -------------------- 최적화된 헬퍼 함수들 --------------------

    def get_valid_image_paths_from_db(self, query_conditions, limit=None):
        """DB에서 유효한 이미지 경로들을 가져옴"""
        try:
            storage = self.mongo_storage
            if not storage or not storage.test_connection():
                return []

            cursor = storage.images.find(query_conditions)
            if limit:
                cursor = cursor.limit(limit)

            valid_paths = []
            seen_paths = set()

            for doc in cursor:
                path = self._extract_path(doc)
                if path and path not in seen_paths and os.path.exists(path):
                    valid_paths.append(path)
                    seen_paths.add(path)

            return valid_paths
        except Exception as e:
            print(f"[DEBUG] get_valid_image_paths_from_db 오류: {e}")
            return []

    def _extract_path(self, doc):
        """문서에서 경로 추출"""
        # 캐시 확인
        doc_id = str(doc.get('_id', ''))
        if doc_id in self._path_cache:
            cached_path = self._path_cache[doc_id]
            if os.path.exists(cached_path):
                return cached_path

        # 우선순위 필드에서 경로 추출
        for field in self.PATH_FIELDS:
            candidates = self._get_path_candidates(doc.get(field))
            for candidate in candidates:
                if self._is_image_path(candidate):
                    self._path_cache[doc_id] = candidate
                    return candidate

        # filename/image_id에서 추출
        for field in ('filename', 'image_id'):
            val = doc.get(field)
            if isinstance(val, str) and self._is_image_file(val):
                resolved = self._resolve_path(val)
                if resolved:
                    self._path_cache[doc_id] = resolved
                    return resolved
        return None

    def _get_path_candidates(self, value):
        """값에서 경로 후보 추출"""
        candidates = []
        if isinstance(value, str) and value.strip():
            candidates.append(value.strip())
        elif isinstance(value, list):
            candidates.extend([str(item).strip() for item in value if item])
        elif isinstance(value, dict):
            for key in ('path', 'file', 'url', 'image', 'src'):
                if key in value and value[key]:
                    candidates.append(str(value[key]).strip())
        return candidates

    def _is_image_path(self, path):
        """경로가 유효한 이미지인지 확인"""
        if not isinstance(path, str) or not path:
            return False
        if os.path.isabs(path) and os.path.exists(path):
            return self._is_image_file(path)
        resolved = self._resolve_path(path)
        return resolved is not None

    def _resolve_path(self, path):
        """상대 경로 resolve"""
        if os.path.isabs(path):
            return path if os.path.exists(path) else None

        search_dirs = [os.getcwd(), os.path.join(os.getcwd(), 'images'),
                      os.path.join(os.getcwd(), 'data'), os.path.join(os.getcwd(), 'assets')]
        basename = os.path.basename(path)
        for search_dir in search_dirs:
            candidate = os.path.join(search_dir, basename)
            if os.path.exists(candidate) and self._is_image_file(candidate):
                return candidate
        return None

    def _is_image_file(self, filename):
        """이미지 파일인지 확인"""
        if not isinstance(filename, str):
            return False
        basename = os.path.basename(filename).lower()
        return any(basename.endswith(ext) for ext in ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff'))

    def _filter_paths_by_json_status(self, paths, filter_type):
        """JSON 파일 상태에 따라 경로 필터링"""
        print(f"[DEBUG] JSON 필터링 시작: {filter_type}")
        filtered = []
        requested_aliases = ['requested', '요청', '1차 검수 요청']
        rejected_aliases = ['rejected', '반려']

        for path in paths:
            if self._check_json_status(path, filter_type, requested_aliases, rejected_aliases):
                filtered.append(path)
                print(f"[DEBUG] ✅ 필터 통과: {os.path.basename(path)}")
            else:
                print(f"[DEBUG] ❌ 필터 제외: {os.path.basename(path)}")

        print(f"[DEBUG] JSON 필터링 후: {len(filtered)}개")
        return filtered

    def _check_json_status(self, img_path, filter_type, requested_aliases, rejected_aliases):
        """JSON 파일에서 검수 상태 확인"""
        try:
            json_path = os.path.splitext(img_path)[0] + '.json'
            if not os.path.exists(json_path):
                return filter_type == '1차 검수 요청 전'

            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            review_status = self._get_review_status_from_json(data)

            if filter_type == '1차 검수 요청 전':
                return not review_status or review_status in ['', None] or review_status not in requested_aliases + rejected_aliases
            elif filter_type == '1차 검수 요청':
                return review_status in requested_aliases
            elif filter_type == '반려':
                return review_status in rejected_aliases

            return True
        except Exception as e:
            print(f"[DEBUG] JSON 상태 확인 오류: {e}")
            return filter_type == '1차 검수 요청 전'

    def _get_review_status_from_json(self, data):
        """JSON 데이터에서 검수 상태 추출"""
        # review_history 우선
        if 'review_history' in data and isinstance(data['review_history'], list) and data['review_history']:
            latest_review = data['review_history'][-1]
            status = latest_review.get('status')
            if status:
                return status

        # legacy 필드들
        status = data.get('review_status') or data.get('reviewStatus')
        if status:
            return status

        # nested review 객체
        if 'review' in data and isinstance(data['review'], dict):
            return data['review'].get('status')

        return None

    def closeEvent(self, event):
        self.labeling_widget.closeEvent(event)

    def setup_menu_bar(self):
        """메뉴바 설정 - DB 메뉴를 맨 오른쪽에 추가"""
        menubar = self.menuBar()

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        spacer_action = QWidgetAction(self)
        spacer_action.setDefaultWidget(spacer)
        menubar.addAction(spacer_action)

        db_menu = menubar.addMenu('DB')

        manage_action = QAction('데이터베이스 관리', self)
        manage_action.setShortcut('Ctrl+D')
        manage_action.triggered.connect(self.open_review_manager_with_check)
        db_menu.addAction(manage_action)

        gallery_action = QAction('사진 보기', self)
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

    # -------------------- DB 검수 관리 --------------------
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
        """MongoDB에서 description이 있는 이미지를 찾아 로드"""
        try:
            storage = self.mongo_storage
            if not storage or not storage.test_connection():
                return False

            current_path = self._get_current_filename_safe()

            if not current_path:
                # 현재 파일이 없으면 description이 있는 이미지 찾기
                query = {"description": {"$exists": True, "$ne": ""}}
                valid_paths = self.get_valid_image_paths_from_db(query, limit=1)
                if valid_paths:
                    self.load_file(valid_paths[0])
                    self.open_review_manager()
                    return True
                QMessageBox.information(self, "DB 검수", "MongoDB에서 검수 가능한 이미지를 찾지 못했습니다.")
                return False

            # 현재 파일의 description 확인
            image_id = os.path.basename(current_path)
            doc = storage.annotations.find_one({
                "$or": [
                    {"image_id": image_id},
                    {"imagePath": os.path.abspath(current_path)},
                    {"file_path": os.path.abspath(current_path)}
                ],
                "description": {"$exists": True, "$ne": ""}
            })

            if not doc:
                QMessageBox.information(self, "DB 검수", "MongoDB에 해당 이미지의 description이 없어 검수 창을 열 수 없습니다.")
                return False

            # 현재 파일이 유효한지 확인
            if os.path.exists(current_path):
                self.open_review_manager()
                return True

            # DB에서 유효한 경로 찾기
            valid_paths = self.get_valid_image_paths_from_db({"image_id": image_id}, limit=1)
            if valid_paths:
                self.load_file(valid_paths[0])
                self.open_review_manager()
                return True

            QMessageBox.information(self, "DB 검수", "MongoDB에 파일 경로 정보가 없거나 파일을 찾을 수 없습니다.")
            return False

        except Exception as e:
            QMessageBox.critical(self, "DB 검수", f"MongoDB 확인 중 오류: {str(e)}")
            return False

    def _find_any_image_path_with_description_in_db(self, storage) -> str:
        """description이 있는 이미지의 경로를 찾음 (최적화 버전)"""
        try:
            query = {"description": {"$exists": True, "$ne": ""}}
            valid_paths = self.get_valid_image_paths_from_db(query, limit=1)
            return valid_paths[0] if valid_paths else ""
        except Exception:
            return ""

    def _resolve_image_path_in_db(self, storage, current_path: str, image_id: str = None) -> str:
        """DB에서 이미지 경로를 resolve (최적화 버전)"""
        try:
            query_conditions = {}
            
            if image_id:
                query_conditions["image_id"] = image_id
            
            # 경로 기반 조건 추가
            if current_path:
                abs_path = os.path.abspath(current_path)
                path_conditions = [{"field": abs_path} for field in self.PATH_FIELDS]
                if path_conditions:
                    query_conditions["$or"] = path_conditions
            
            valid_paths = self.get_valid_image_paths_from_db(query_conditions, limit=1)
            return valid_paths[0] if valid_paths else ""
            
        except Exception:
            return ""

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
                self.review_window.raise_()
                self.review_window.activateWindow()
                return
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
                    self.review_window.show()
                    return
            # 경로가 없거나 클래스 로드 실패 시 안내
            QMessageBox.information(
                self,
                "검수 관리",
                "개선된 검수 위젯(improved_review_widgets.py)을 찾을 수 없습니다.\nDB 메뉴의 '데이터베이스 관리'를 사용하세요.",
            )
        except Exception as e:
            QMessageBox.critical(self, "검수 관리 오류", f"검수 관리 창을 여는 중 오류가 발생했습니다:\n{str(e)}")

    def show_image_gallery(self):
        """DB에서 description이 있는 이미지 목록을 가져와 갤러리 형태로 보여줍니다."""
        try:
            storage = getattr(self, 'mongo_storage', None)
            if not storage or not storage.test_connection():
                QMessageBox.warning(self, "DB 오류", "MongoDB에 연결할 수 없습니다.")
                return

            # --- 검수 상태 필터 선택 ---
            filter_options = [
                '전체 (description 있음)',
                '1차 검수 요청 전',
                '1차 검수 요청',
                '반려',
            ]
            selected, ok = QInputDialog.getItem(
                self,
                '사진 보기 - 상태 선택',
                '표시할 검수 상태를 선택하세요:',
                filter_options,
                0,
                False,
            )
            if not ok:
                return

            # 상태별 쿼리 구성 (JSON 필터링에서 사용할 별칭 정의)
            requested_aliases = ['requested', '요청', '1차 검수 요청']
            rejected_aliases = ['rejected', '반려']
            
            status_cond = None
            use_json_status_filter = False  # 기본값
            json_status_filter_type = None
            
            if selected == '1차 검수 요청':
                print(f"[DEBUG] 1차 검수 요청 선택됨 - JSON 파일 기반으로 검색")
                use_json_status_filter = True
                json_status_filter_type = '1차 검수 요청'
            elif selected == '반려':
                print(f"[DEBUG] 반려 선택됨 - JSON 파일 기반으로 검색")
                use_json_status_filter = True
                json_status_filter_type = '반려'
            elif selected == '1차 검수 요청 전':
                print(f"[DEBUG] 1차 검수 요청 전 선택됨 - JSON 파일 기반으로 직접 검색")
                use_json_status_filter = True
                json_status_filter_type = '1차 검수 요청 전'
                print(f"[DEBUG] JSON 기반 상태 필터링 활성화: {json_status_filter_type}")
            # '전체 (description 있음)' 선택 시에는 상태 필터링 없음

            # JSON description 존재 조건 추가 (annotations 컬렉션에서 description이 있는 이미지)
            def _get_image_ids_with_description():
                """description이 있는 이미지들의 image_id 수집"""
                try:
                    storage = self.mongo_storage
                    query = {"description": {"$exists": True, "$ne": ""}}
                    docs = storage.annotations.find(query, {"image_id": 1, "filename": 1})

                    image_ids = set()
                    for doc in docs:
                        candidates = []
                        if doc.get('image_id'):
                            candidates.append(str(doc['image_id']))
                        if doc.get('filename'):
                            candidates.append(os.path.splitext(os.path.basename(doc['filename']))[0])

                        for candidate in candidates:
                            if candidate and candidate.strip():
                                image_ids.add(candidate.strip())

                    return list(image_ids)
                except Exception as e:
                    print(f"[DEBUG] _get_image_ids_with_description 오류: {e}")
                    return []
            
            annotated_image_ids = _get_image_ids_with_description()
            if not annotated_image_ids:
                QMessageBox.information(self, "사진 보기", "description이 있는 이미지를 찾을 수 없습니다.\n\n콘솔 출력을 확인하여 디버깅 정보를 확인하세요.")
                return

            # description 조건을 기존 쿼리에 추가
            annotation_cond = {"image_id": {"$in": annotated_image_ids}}
            
            # 디버깅: images 컬렉션에 해당 image_id들이 실제로 있는지 확인
            try:
                # 1) images 컬렉션의 전체 문서 수와 image_id 샘플
                total_images = storage.images.count_documents({})
                print(f"[DEBUG] 전체 images 문서 수: {total_images}")
                
                sample_images = list(storage.images.find({}, {"image_id": 1}).limit(5))
                sample_image_ids = [doc.get('image_id') for doc in sample_images]
                print(f"[DEBUG] 샘플 images의 image_id들: {sample_image_ids}")
                
                # 2) annotations에서 찾은 image_id들이 실제로 images 컬렉션에 있는지 확인
                matching_count = storage.images.count_documents(annotation_cond)
                print(f"[DEBUG] annotations의 image_id가 images에서 매칭되는 수: {matching_count}")
                
                if matching_count == 0:
                    print("[DEBUG] 매칭 문제 발생! annotations와 images 컬렉션의 image_id 형식이 다를 수 있습니다.")
                    
                    # 3) 대안: annotations에서 직접 경로 정보 수집 시도
                    print("[DEBUG] annotations 컬렉션에서 직접 경로 수집을 시도합니다...")
                    
                    # annotations에서 description이 있으면서 경로 정보도 있는 문서들을 직접 사용
                    extended_fields_for_ann = list(self._PATH_FIELDS) + ["filename", "image_id", "imagePath"]
                    direct_ann_query = {
                        "$and": [
                            {"description": {"$exists": True, "$ne": ""}},
                            {"$or": [{field: {"$exists": True, "$ne": ""}} for field in extended_fields_for_ann]}
                        ]
                    }
                    
                    direct_ann_count = storage.annotations.count_documents(direct_ann_query)
                    print(f"[DEBUG] annotations에서 직접 경로+description 조건 만족하는 문서 수: {direct_ann_count}")
                    
                    if direct_ann_count > 0:
                        print("[DEBUG] annotations 컬렉션을 직접 사용합니다.")
                        # images 컬렉션 대신 annotations 컬렉션 직접 사용
                        all_images = storage.annotations.find(direct_ann_query)
                        using_annotations_directly = True
                    else:
                        print("[DEBUG] annotations에서도 경로 정보를 찾을 수 없습니다.")
                        using_annotations_directly = False
                else:
                    using_annotations_directly = False
                    
            except Exception as e:
                print(f"[DEBUG] images-annotations 매칭 확인 오류: {e}")
                using_annotations_directly = False

            # -------------------- 헬퍼: 경로 추출 --------------------
            def _extract_path_candidates_from_value(v):
                candidates = []
                try:
                    print(f"[DEBUG] _extract_path_candidates_from_value 호출됨, 값: {v} (타입: {type(v)})")
                    if isinstance(v, str) and v.strip():
                        candidates.append(v.strip())
                        print(f"[DEBUG] 문자열에서 후보 추가: {v.strip()}")
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, str) and item.strip():
                                candidates.append(item.strip())
                                print(f"[DEBUG] 리스트에서 후보 추가: {item.strip()}")
                    elif isinstance(v, dict):
                        # 흔한 키 우선 검색
                        for k in ("path", "file", "url", "image", "src"):
                            val = v.get(k)
                            if isinstance(val, str) and val.strip():
                                candidates.append(val.strip())
                                print(f"[DEBUG] 딕셔너리 키 {k}에서 후보 추가: {val.strip()}")
                                break
                except Exception as e:
                    print(f"[DEBUG] _extract_path_candidates_from_value 오류: {e}")
                print(f"[DEBUG] 최종 후보들: {candidates}")
                return candidates

            def _extract_first_path(doc, fields):
                print(f"[DEBUG] _extract_first_path 호출됨, 문서 ID: {doc.get('_id', 'N/A')}")
                # 1) 우선순위 필드들 순회하며 문자열/리스트/딕셔너리에서 경로 후보를 추출
                for field in fields:
                    if field in doc:
                        field_value = doc.get(field)
                        print(f"[DEBUG] 필드 {field}: {field_value} (타입: {type(field_value)})")
                        vals = _extract_path_candidates_from_value(field_value)
                        print(f"[DEBUG] 필드 {field}에서 추출된 후보들: {vals}")
                        if vals:
                            return vals[0]
                # 2) 마지막 시도: 파일명/ID가 이미지 파일명처럼 보이면 그대로 사용
                for field in ("filename", "image_id", "imageId", "name"):
                    val = doc.get(field)
                    if isinstance(val, str) and any(val.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff")):
                        print(f"[DEBUG] 이미지 확장자 필드 {field}에서 반환: {val}")
                        return val
                print(f"[DEBUG] 경로를 찾을 수 없음")
                return None

            # DB에서 모든 이미지 경로 가져오기
            image_paths = []
            seen_paths = set()
            
            # 인덱스를 활용하여 경로/식별자 필드가 존재하는 문서만 조회
            extended_fields = list(self._PATH_FIELDS) + ["filename", "image_id"]
            path_filter = {"$or": [{field: {"$exists": True, "$ne": ""}} for field in extended_fields]}
            
            # 최종 쿼리 조합: 경로 필터 + JSON 어노테이션 필터 + 상태 필터
            if not locals().get('using_annotations_directly', False):
                # 기존 방식: images 컬렉션 사용
                query_conditions = [path_filter, annotation_cond]
                if status_cond:
                    query_conditions.append(status_cond)
                
                final_query = {"$and": query_conditions}
                print(f"[DEBUG] images 컬렉션 사용 - 최종 쿼리 조건 수: {len(query_conditions)}")
                print(f"[DEBUG] 상태 필터 적용됨: {status_cond is not None}")
                
                all_images = storage.images.find(final_query)
                
                # 쿼리 결과 수 확인
                try:
                    query_result_count = storage.images.count_documents(final_query)
                    print(f"[DEBUG] images 컬렉션 최종 쿼리 결과 문서 수: {query_result_count}")
                except Exception as e:
                    print(f"[DEBUG] 쿼리 결과 수 확인 오류: {e}")
            else:
                # 대안: annotations 컬렉션에서 직접 사용 (이미 all_images가 설정됨)
                print(f"[DEBUG] annotations 컬렉션 직접 사용")
                try:
                    # 상태 필터가 있다면 annotations에는 적용하지 않음 (images 컬렉션 전용)
                    if status_cond:
                        print(f"[DEBUG] 주의: 상태 필터는 annotations 컬렉션에서 무시됩니다")
                except Exception:
                    pass
            
            # 처리할 문서 수 미리 확인
            doc_count = 0
            all_images_list = list(all_images)  # 커서를 리스트로 변환
            total_docs = len(all_images_list)
            print(f"[DEBUG] 처리할 총 문서 수: {total_docs}")
            
            for doc_idx, doc in enumerate(all_images_list):
                doc_count += 1
                print(f"[DEBUG] === 문서 {doc_idx + 1}/{total_docs} 처리 중 ===")
                print(f"[DEBUG] 문서 _id: {doc.get('_id', 'N/A')}")
                print(f"[DEBUG] 문서 image_id: {doc.get('image_id', 'N/A')}")
                
                found_path_for_doc = _extract_first_path(doc, extended_fields)
                print(f"[DEBUG] 문서에서 추출된 경로: {found_path_for_doc}")
                
                # 유효하고 실제 존재하며 아직 추가되지 않은 경로만 추가
                if isinstance(found_path_for_doc, str) and found_path_for_doc:
                    print(f"[DEBUG] 경로 유효성 확인: {found_path_for_doc}")
                    if found_path_for_doc not in seen_paths:
                        if os.path.exists(found_path_for_doc):
                            print(f"[DEBUG] ✅ 파일 존재 확인됨, 추가: {found_path_for_doc}")
                            image_paths.append(found_path_for_doc)
                            seen_paths.add(found_path_for_doc)
                        else:
                            print(f"[DEBUG] ❌ 파일 존재하지 않음: {found_path_for_doc}")
                            # 상대 경로나 다른 위치에 있을 가능성 체크
                            import os.path as osp
                            basename = osp.basename(found_path_for_doc)
                            print(f"[DEBUG]    베이스명으로 재시도: {basename}")
                            
                            # 현재 작업 디렉토리와 일반적인 이미지 폴더들에서 찾아보기
                            search_dirs = [
                                os.getcwd(),
                                osp.join(os.getcwd(), 'assets'),
                                osp.join(os.getcwd(), 'assets', 'demo'),
                                osp.join(os.getcwd(), 'images'),
                                osp.join(os.getcwd(), 'data'),
                            ]
                            
                            found_alternative = False
                            for search_dir in search_dirs:
                                alt_path = osp.join(search_dir, basename)
                                if os.path.exists(alt_path):
                                    print(f"[DEBUG] ✅ 대안 경로에서 발견: {alt_path}")
                                    image_paths.append(alt_path)
                                    seen_paths.add(alt_path)
                                    found_alternative = True
                                    break
                            
                            if not found_alternative:
                                print(f"[DEBUG] ❌ 대안 경로에서도 찾지 못함")
                    else:
                        print(f"[DEBUG] 이미 추가된 경로 건너뜀: {found_path_for_doc}")
                else:
                    print(f"[DEBUG] ❌ 유효하지 않은 경로: {found_path_for_doc} (타입: {type(found_path_for_doc)})")
                    # 문서의 모든 필드 확인
                    doc_fields = list(doc.keys()) if hasattr(doc, 'keys') else 'N/A'
                    print(f"[DEBUG] 문서 필드들: {doc_fields}")
                    for field in extended_fields:
                        if field in doc:
                            val = doc.get(field)
                            print(f"[DEBUG] {field}: {val} (타입: {type(val)})")
            
            print(f"[DEBUG] === 문서 처리 완료: {doc_count}개 처리됨 ===")
            
            print(f"[DEBUG] 최종 수집된 이미지 경로 수: {len(image_paths)}")
            if image_paths:
                print(f"[DEBUG] 수집된 경로들: {image_paths[:3]}...")  # 처음 3개만 표시
            
            # JSON 파일 기반 상태 필터링 적용
            if locals().get('use_json_status_filter', False):
                image_paths = self._filter_paths_by_json_status(image_paths, json_status_filter_type)
            
            # '전체' 선택 시에는 초기 결과가 있어도 동적 키 및 annotations 병합을 시도하여 더 많은 경로를 수집
            if status_cond is None and selected == '전체 (description 있음)':
                # 1차 우회: images 컬렉션의 샘플 문서에서 'path/file/url'이 포함된 키를 동적으로 추론하여 재시도
                try:
                    sample = storage.images.find_one({}) or {}
                    dynamic_fields = [
                        k for k in sample.keys()
                        if isinstance(k, str) and any(p in k.lower() for p in ("path", "file", "url"))
                    ]
                    dynamic_fields = [f for f in dynamic_fields if f not in extended_fields]
                    if dynamic_fields:
                        dyn_query = {"$and": [
                            {"$or": [{f: {"$exists": True, "$ne": ""}} for f in dynamic_fields]},
                            annotation_cond
                        ]}
                        for doc in storage.images.find(dyn_query):
                            found = _extract_first_path(doc, dynamic_fields)
                            if (isinstance(found, str) and found and found not in seen_paths and 
                                os.path.exists(found)):
                                image_paths.append(found)
                                seen_paths.add(found)
                except Exception:
                    pass

            if status_cond is None and selected == '전체 (description 있음)':
                # 2차 폴백: annotations 컬렉션에서 동일한 필드들로 수집 (일부 스키마는 경로가 annotations에만 존재)
                try:
                    ann_query = {
                        "$and": [
                            {"$or": [{field: {"$exists": True, "$ne": ""}} for field in extended_fields]},
                            {"description": {"$exists": True, "$ne": ""}}
                        ]
                    }
                    for doc in storage.annotations.find(ann_query):
                        found = _extract_first_path(doc, extended_fields)
                        if (isinstance(found, str) and found and found not in seen_paths and 
                            os.path.exists(found)):
                            image_paths.append(found)
                            seen_paths.add(found)
                except Exception:
                    pass

            # 상태 필터가 있는 경우, 결과 없음이면 명확하게 안내 후 종료
            if not image_paths and status_cond is not None:
                QMessageBox.information(self, "사진 보기", f"선택한 상태('{selected}')에 해당하는 이미지가 없습니다.\n다른 상태를 선택하거나 '전체'를 선택해 보세요.")
                return

            if not image_paths:
                # 진단 정보: 어떤 필드에 값이 있는 문서가 얼마나 있는지 보여줌
                try:
                    counts = {}
                    for f in extended_fields:
                        try:
                            counts[f] = storage.images.count_documents({f: {"$exists": True, "$ne": ""}})
                        except Exception:
                            counts[f] = 0
                    # 샘플 문서 키 목록
                    sample = storage.images.find_one({}) or {}
                    sample_keys = ", ".join(list(sample.keys())[:15]) if sample else "<none>"
                    msg = (
                        "DB에서 유효한 이미지 경로 문자열을 가진 문서를 찾지 못했습니다.\n\n"
                        "필드별 문서 수 (exists & not empty):\n"
                        f" - image_file_path: {counts.get('image_file_path', 0)}\n"
                        f" - imagePath: {counts.get('imagePath', 0)}\n"
                        f" - file_path: {counts.get('file_path', 0)}\n"
                        f" - path: {counts.get('path', 0)}\n"
                        f" - filename: {counts.get('filename', 0)}\n"
                        f" - image_id: {counts.get('image_id', 0)}\n\n"
                        f"샘플 문서 키: {sample_keys}\n"
                        "힌트: images/annotations 컬렉션에서 경로 필드명이 다르면 해당 필드를 코드에 추가해야 합니다."
                    )
                    QMessageBox.information(self, "사진 보기", msg)
                except Exception:
                    QMessageBox.information(self, "사진 보기", "DB에서 유효한 이미지 파일을 찾을 수 없습니다.")
                return

            # 갤러리 창 표시
            if self.gallery_window is None:
                self.gallery_window = ImageGallery(image_paths, self)
                self.gallery_window.imageSelected.connect(self.load_files_batch)
                self.gallery_window.finished.connect(self.on_gallery_closed)
            else:
                # 기존 갤러리가 있으면 새 경로 목록으로 업데이트
                self.gallery_window.update_image_paths(image_paths)
            # 선택한 필터를 제목에 표시
            try:
                title_suffix = selected if selected else '전체'
                count_info = f" ({len(image_paths)}개)"
                self.gallery_window.setWindowTitle(f"사진 보기 (DB) - {title_suffix}{count_info}")
            except Exception:
                pass
            self.gallery_window.show()
            self.gallery_window.raise_()
            self.gallery_window.activateWindow()

        except Exception as e:
            QMessageBox.critical(self, "사진 보기 오류", f"이미지 갤러리를 여는 중 오류가 발생했습니다:\n{str(e)}")

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
            inner_widget = None
            for attr in ('view', 'widget', 'labeling_widget'):
                if hasattr(self.labeling_widget, attr):
                    inner_widget = getattr(self.labeling_widget, attr)
                    break
            
            if inner_widget is None:
                inner_widget = self.labeling_widget

            if hasattr(inner_widget, 'load_file'):
                return inner_widget.load_file(filename)
        
        QMessageBox.warning(self, "파일 로딩 오류", "파일 로딩 기능을 찾을 수 없습니다.")
        return False
