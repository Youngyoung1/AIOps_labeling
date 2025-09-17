"""This module defines labeling wrapper and related functions"""

from PyQt5.QtWidgets import QVBoxLayout, QWidget

from .label_widget import LabelingWidget


class LabelingWrapper(QWidget):
    """Wrapper widget for labeling module"""

    def __init__(
        self,
        parent,
        config=None,
        filename=None,
        output=None,
        output_file=None,
        output_dir=None,
    ):
        super().__init__()
        self.parent = parent

        # Create a labeling widget
        self.view = LabelingWidget(
            self,
            config=config,
            filename=filename,
            output=output,
            output_file=output_file,
            output_dir=output_dir,
        )

        # Compatibility aliases: some parts of the app expect `.widget` or `.labeling_widget`
        # to reference the inner LabelingWidget. Provide both to avoid AttributeError.
        self.widget = self.view
        self.labeling_widget = self.view

        # Create the main layout and put labeling into
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.view)
        self.setLayout(main_layout)

    def set_file_list(self, file_list, start_index=0):
        """내부 LabelingWidget(view)의 set_file_list를 호출하는 위임 메서드"""
        if hasattr(self.view, 'set_file_list'):
            self.view.set_file_list(file_list, start_index)

    def closeEvent(self, event):
        self.view.closeEvent(event)
