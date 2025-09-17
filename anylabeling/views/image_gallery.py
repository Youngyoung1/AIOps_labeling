import os
from PyQt5.QtWidgets import (
    QDialog,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QApplication,
    QDialogButtonBox,
    QAbstractItemView,
)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QSize, Qt, pyqtSignal

class ImageGallery(QDialog):
    """
    A dialog to display a gallery of images from the database.
    Images are shown as thumbnails in a list. Clicking an image
    emits a signal with the image path, all paths, and selected index.
    """

    # (selected_path, all_paths, selected_index)
    imageSelected = pyqtSignal(str, list, int)

    def __init__(self, image_paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle("사진 보기 (DB)")
        self.setMinimumSize(800, 600)

        self.image_paths = image_paths
        self.thumbnails = []  # (icon, basename, fullpath) 튜플 리스트

        # Layout
        layout = QVBoxLayout(self)

        # Image List Widget
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(128, 128))
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setMovement(QListWidget.Static)
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.list_widget)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self.preload_thumbnails()
        self.populate_gallery()
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
    
    def update_image_paths(self, new_image_paths):
        """새로운 이미지 경로 목록으로 갤러리 업데이트"""
        self.image_paths = new_image_paths
        self.preload_thumbnails()
        self.populate_gallery()
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def preload_thumbnails(self):
        """모든 이미지를 한 번에 미리 썸네일 생성 (빠른 이동용)"""
        self.thumbnails = []
        for path in self.image_paths:
            if not path:
                # 경로가 None이거나 빈 문자열인 경우
                icon = QIcon()
                basename = "Invalid Path"
            elif not os.path.exists(path):
                # 경로가 존재하지 않는 경우
                icon = QIcon()
                basename = os.path.basename(path) + " (파일 없음)"
            else:
                try:
                    pixmap = QPixmap(path)
                    if pixmap.isNull():
                        # 이미지 로드 실패
                        icon = QIcon()
                        basename = os.path.basename(path) + " (로드 실패)"
                    else:
                        # 정상 썸네일 생성
                        icon = QIcon(pixmap.scaled(
                            self.list_widget.iconSize(),
                            Qt.KeepAspectRatio,
                            Qt.SmoothTransformation
                        ))
                        basename = os.path.basename(path)
                except Exception as e:
                    # 예외 발생 시
                    icon = QIcon()
                    basename = os.path.basename(path) + f" (오류: {str(e)[:20]})"
            
            self.thumbnails.append((icon, basename, path))

    def on_item_double_clicked(self, item):
        """Emit signal with the path, all paths, and index, then close."""
        path = item.data(Qt.UserRole)
        if path:
            idx = self.list_widget.row(item)
            self.imageSelected.emit(path, self.image_paths, idx)
            self.accept()

    def populate_gallery(self):
        """미리 생성한 썸네일을 리스트에 채워 넣습니다."""
        self.list_widget.clear()
        # 썸네일이 없다면 즉시 생성
        if not self.thumbnails:
            self.preload_thumbnails()
        for icon, name, fullpath in self.thumbnails:
            item = QListWidgetItem(icon, name)
            item.setData(Qt.UserRole, fullpath)
            item.setToolTip(fullpath)
            self.list_widget.addItem(item)

    def accept(self):
        """Handle dialog acceptance."""
        # If an item is selected, emit its path, all paths, and index on OK click as well
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            path = selected_items[0].data(Qt.UserRole)
            idx = self.list_widget.row(selected_items[0])
            if path:
                self.imageSelected.emit(path, self.image_paths, idx)
        super().accept()

    
