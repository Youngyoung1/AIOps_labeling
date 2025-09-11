"""This module defines the main application window"""

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
)

from ..app_info import __appdescription__, __appname__
from .labeling.label_wrapper import LabelingWrapper
from ..services.storage.mongodb_client import MongoStorage
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

        # MongoDB 스토리지 초기화
        self.mongo_storage = MongoStorage()

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
            db_ok = self.mongo_storage.test_connection()
        except Exception:
            db_ok = False
        db_txt = '연결 성공' if db_ok else '연결 실패'
        status_bar.showMessage(f"{__appname__} - {__appdescription__} | DB: {db_txt}")
        self.setStatusBar(status_bar)

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

        # DB 관리 액션
        manage_action = QAction('데이터베이스 관리', self)
        manage_action.setShortcut('Ctrl+D')

        try:
            manage_action.triggered.connect(self.open_db_manager)
        except AttributeError:
            manage_action.triggered.connect(self._open_db_manager_not_available)
        db_menu.addAction(manage_action)
        
        db_menu.addSeparator()

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

    def _open_db_manager_not_available(self):
        """Fallback handler when DB manager UI is not available in this build."""
        QMessageBox.information(
            self,
            'DB 관리자',
            'DB 관리자 UI가 현재 빌드에서 사용 불가합니다. MongoDB 연결 및 관리 기능은 서비스 레이어에서 사용할 수 있습니다.'
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

    def show_search_results(self, results, query):
        """간단한 텍스트 형태로 검색 결과를 보여줍니다."""
        try:
            if not results:
                QMessageBox.information(self, '검색 결과', f'"{query}"에 대한 결과가 없습니다.')
                return

            lines = []
            for i, doc in enumerate(results[:20], start=1):  # 최대 20개 요약
                filename = doc.get('filename') or doc.get('image_info', {}).get('filename', '')
                label = doc.get('label', '')
                category = doc.get('category', '')
                plate = doc.get('plate_number') or doc.get('properties', {}).get('plate_number', '')
                conf = doc.get('confidence', '')
                lines.append(f"{i}. {filename} | {label} | {category} | plate={plate} | conf={conf}")

            header = f'검색어: "{query}"  (총 {len(results)}건)\n'
            preview = '\n'.join(lines)
            text = header + preview
            # 결과가 길어도 메시지로 우선 제공
            QMessageBox.information(self, '검색 결과', text)
        except Exception as e:
            QMessageBox.critical(self, '검색 결과 표시 오류', f'결과 표시 중 오류가 발생했습니다:\n{str(e)}')
