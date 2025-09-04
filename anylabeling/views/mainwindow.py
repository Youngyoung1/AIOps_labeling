"""This module defines the main application window"""

from PyQt5.QtWidgets import (
    QMainWindow,
    QStatusBar,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QLabel,
)

from ..app_info import __appdescription__, __appname__
from .labeling.label_wrapper import LabelingWrapper


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

        status_bar = QStatusBar()
        status_bar.showMessage(f"{__appname__} - {__appdescription__}")
        self.setStatusBar(status_bar)

    # LabelingWidget 이 상단 라벨을 갱신할 때 접근할 helper
    def set_top_file_index_text(self, text: str):
        if hasattr(self, 'file_index_label_top'):
            self.file_index_label_top.setText(text)

    def closeEvent(self, event):
        self.labeling_widget.closeEvent(event)
