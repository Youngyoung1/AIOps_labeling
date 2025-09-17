from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QLineEdit, QPushButton, QComboBox, QListWidget, QListWidgetItem,
    QTabWidget, QWidget, QTextEdit, QCheckBox, QSpinBox, QMessageBox,
    QSplitter, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox
)
import json
from datetime import datetime
from ..logger import logger

class AnnotationSearchDialog(QDialog):
    annotation_selected = pyqtSignal(str)  # imagePath를 emit
    
    def __init__(self, annotation_manager, parent=None):
        super().__init__(parent)
        self.annotation_manager = annotation_manager
        self.current_results = []
        self.init_ui()
        self.load_search_options()
    
    def init_ui(self):
        self.setWindowTitle("어노테이션 검색 및 통계")
        self.setGeometry(200, 200, 1000, 700)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout()
        
        # 탭 위젯 생성
        tab_widget = QTabWidget()
        
        # 검색 탭
        search_tab = self.create_search_tab()
        tab_widget.addTab(search_tab, "검색")
        
        # 통계 탭
        stats_tab = self.create_stats_tab()
        tab_widget.addTab(stats_tab, "통계")
        
        # 관리 탭
        manage_tab = self.create_manage_tab()
        tab_widget.addTab(manage_tab, "관리")
        
        main_layout.addWidget(tab_widget)
        
        # 닫기 버튼
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.close)
        close_layout.addWidget(close_btn)
        main_layout.addLayout(close_layout)
        
        self.setLayout(main_layout)
    
    def create_search_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 검색 조건 영역
        search_group = QGroupBox("검색 조건")
        search_layout = QGridLayout()
        
        # 라벨 검색
        search_layout.addWidget(QLabel("라벨:"), 0, 0)
        self.label_combo = QComboBox()
        self.label_combo.setEditable(True)
        search_layout.addWidget(self.label_combo, 0, 1)
        
        # Shape 타입 검색
        search_layout.addWidget(QLabel("Shape 타입:"), 0, 2)
        self.shape_type_combo = QComboBox()
        search_layout.addWidget(self.shape_type_combo, 0, 3)
        
        # 태그 검색
        search_layout.addWidget(QLabel("태그:"), 1, 0)
        self.tag_combo = QComboBox()
        self.tag_combo.setEditable(True)
        search_layout.addWidget(self.tag_combo, 1, 1)
        
        # 이미지 경로 검색
        search_layout.addWidget(QLabel("이미지 경로:"), 1, 2)
        self.image_path_edit = QLineEdit()
        search_layout.addWidget(self.image_path_edit, 1, 3)
        
        # 플래그 옵션들
        flags_layout = QHBoxLayout()
        self.has_descriptions_cb = QCheckBox("설명 있음")
        self.has_difficult_cb = QCheckBox("Difficult 있음")
        self.has_attributes_cb = QCheckBox("Attributes 있음")
        self.has_tags_cb = QCheckBox("태그 있음")
        
        flags_layout.addWidget(self.has_descriptions_cb)
        flags_layout.addWidget(self.has_difficult_cb)
        flags_layout.addWidget(self.has_attributes_cb)
        flags_layout.addWidget(self.has_tags_cb)
        flags_layout.addStretch()
        
        search_layout.addLayout(flags_layout, 2, 0, 1, 4)
        
        # 검색 버튼들
        button_layout = QHBoxLayout()
        self.search_btn = QPushButton("검색")
        self.search_btn.clicked.connect(self.perform_search)
        self.clear_btn = QPushButton("초기화")
        self.clear_btn.clicked.connect(self.clear_search)
        
        button_layout.addWidget(self.search_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        
        search_layout.addLayout(button_layout, 3, 0, 1, 4)
        
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # 결과 영역
        results_group = QGroupBox("검색 결과")
        results_layout = QVBoxLayout()
        
        # 결과 수 표시
        self.result_count_label = QLabel("검색 결과: 0개")
        results_layout.addWidget(self.result_count_label)
        
        # 결과 테이블
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "이미지 경로", "라벨 수", "Shape 수", "설명", "생성일", "수정일"
        ])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.results_table.doubleClicked.connect(self.on_result_double_click)
        
        results_layout.addWidget(self.results_table)
        
        # 상세 정보 영역
        detail_layout = QHBoxLayout()
        
        # 선택된 어노테이션 상세 정보
        self.detail_text = QTextEdit()
        self.detail_text.setMaximumHeight(150)
        self.detail_text.setPlaceholderText("검색 결과를 선택하면 상세 정보가 표시됩니다.")
        
        # 액션 버튼들
        action_layout = QVBoxLayout()
        self.open_annotation_btn = QPushButton("어노테이션 열기")
        self.open_annotation_btn.clicked.connect(self.open_selected_annotation)
        self.open_annotation_btn.setEnabled(False)
        
        self.delete_annotation_btn = QPushButton("어노테이션 삭제")
        self.delete_annotation_btn.clicked.connect(self.delete_selected_annotation)
        self.delete_annotation_btn.setEnabled(False)
        self.delete_annotation_btn.setStyleSheet("color: red;")
        
        action_layout.addWidget(self.open_annotation_btn)
        action_layout.addWidget(self.delete_annotation_btn)
        action_layout.addStretch()
        
        detail_layout.addWidget(self.detail_text, 3)
        detail_layout.addLayout(action_layout, 1)
        
        results_layout.addLayout(detail_layout)
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # 결과 테이블 선택 변경 이벤트
        self.results_table.itemSelectionChanged.connect(self.on_selection_changed)
        
        widget.setLayout(layout)
        return widget
    
    def create_stats_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 통계 새로고침 버튼
        refresh_layout = QHBoxLayout()
        refresh_btn = QPushButton("통계 새로고침")
        refresh_btn.clicked.connect(self.load_statistics)
        refresh_layout.addWidget(refresh_btn)
        refresh_layout.addStretch()
        layout.addLayout(refresh_layout)
        
        # 통계 정보 표시 영역
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        layout.addWidget(self.stats_text)
        
        widget.setLayout(layout)
        return widget
    
    def create_manage_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 일괄 처리 영역
        batch_group = QGroupBox("일괄 처리")
        batch_layout = QGridLayout()
        
        # JSON 파일 일괄 가져오기
        batch_layout.addWidget(QLabel("JSON 파일 패턴:"), 0, 0)
        self.file_pattern_edit = QLineEdit()
        self.file_pattern_edit.setPlaceholderText("예: /path/to/annotations/*.json")
        batch_layout.addWidget(self.file_pattern_edit, 0, 1)
        
        import_btn = QPushButton("일괄 가져오기")
        import_btn.clicked.connect(self.import_json_files)
        batch_layout.addWidget(import_btn, 0, 2)
        
        # 진행 상황 표시
        self.progress_text = QTextEdit()
        self.progress_text.setMaximumHeight(200)
        self.progress_text.setReadOnly(True)
        batch_layout.addWidget(self.progress_text, 1, 0, 1, 3)
        
        batch_group.setLayout(batch_layout)
        layout.addWidget(batch_group)
        
        # 데이터베이스 관리
        db_group = QGroupBox("데이터베이스 관리")
        db_layout = QHBoxLayout()
        
        clear_all_btn = QPushButton("모든 어노테이션 삭제")
        clear_all_btn.clicked.connect(self.clear_all_annotations)
        clear_all_btn.setStyleSheet("color: red; font-weight: bold;")
        
        db_layout.addWidget(clear_all_btn)
        db_layout.addStretch()
        
        db_group.setLayout(db_layout)
        layout.addWidget(db_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def load_search_options(self):
        """검색 옵션들 로드"""
        try:
            # 라벨 목록 로드
            labels = self.annotation_manager.get_all_labels()
            self.label_combo.addItem("-- 전체 --")
            self.label_combo.addItems(labels)
            
            # Shape 타입 목록 로드
            shape_types = self.annotation_manager.get_all_shape_types()
            self.shape_type_combo.addItem("-- 전체 --")
            self.shape_type_combo.addItems(shape_types)
            
            # 태그 목록 로드
            tags = self.annotation_manager.get_all_tags()
            self.tag_combo.addItem("-- 전체 --")
            self.tag_combo.addItems(tags)
            
        except Exception as e:
            logger.error(f"검색 옵션 로드 실패: {e}")
    
    def perform_search(self):
        """검색 수행"""
        try:
            results = []
            
            # 각 조건에 따라 검색
            label = self.label_combo.currentText()
            if label and label != "-- 전체 --":
                results = self.annotation_manager.find_by_label(label)
            
            shape_type = self.shape_type_combo.currentText()
            if shape_type and shape_type != "-- 전체 --":
                if results:
                    # 기존 결과를 필터링
                    results = [r for r in results if shape_type in r.get('shape_types', [])]
                else:
                    results = self.annotation_manager.find_by_shape_type(shape_type)
            
            tag = self.tag_combo.currentText()
            if tag and tag != "-- 전체 --":
                if results:
                    results = [r for r in results if tag in r.get('tags', [])]
                else:
                    results = self.annotation_manager.find_by_tag(tag)
            
            image_path = self.image_path_edit.text().strip()
            if image_path:
                if results:
                    results = [r for r in results if image_path.lower() in r.get('imagePath', '').lower()]
                else:
                    # 전체에서 이미지 경로로 검색
                    from pymongo import MongoClient
                    results = list(self.annotation_manager.collection.find({
                        "imagePath": {"$regex": image_path, "$options": "i"}
                    }))
            
            # 플래그 조건들 적용
            if self.has_descriptions_cb.isChecked():
                if results:
                    results = [r for r in results if r.get('has_descriptions', False)]
                else:
                    results = self.annotation_manager.find_with_descriptions()
            
            if self.has_difficult_cb.isChecked():
                if results:
                    results = [r for r in results if r.get('has_difficult', False)]
                else:
                    results = self.annotation_manager.find_difficult_annotations()
            
            if self.has_attributes_cb.isChecked():
                if results:
                    results = [r for r in results if r.get('has_attributes', False)]
                else:
                    results = self.annotation_manager.find_with_attributes()
            
            if self.has_tags_cb.isChecked():
                if results:
                    results = [r for r in results if r.get('has_tags', False)]
                else:
                    results = [r for r in list(self.annotation_manager.collection.find({"has_tags": True}))]
            
            # 아무 조건도 없으면 전체 검색
            if not any([label and label != "-- 전체 --", 
                       shape_type and shape_type != "-- 전체 --",
                       tag and tag != "-- 전체 --",
                       image_path,
                       self.has_descriptions_cb.isChecked(),
                       self.has_difficult_cb.isChecked(),
                       self.has_attributes_cb.isChecked(),
                       self.has_tags_cb.isChecked()]):
                results = list(self.annotation_manager.collection.find().limit(100))  # 최대 100개
            
            self.display_results(results)
            
        except Exception as e:
            logger.error(f"검색 수행 중 오류: {e}")
            QMessageBox.warning(self, "검색 오류", f"검색 중 오류가 발생했습니다:\n{str(e)}")
    
    def display_results(self, results):
        """검색 결과 표시"""
        self.current_results = results
        self.result_count_label.setText(f"검색 결과: {len(results)}개")
        
        # 테이블 초기화
        self.results_table.setRowCount(len(results))
        
        for i, result in enumerate(results):
            # 이미지 경로
            self.results_table.setItem(i, 0, QTableWidgetItem(result.get('imagePath', '')))
            
            # 라벨 수
            label_count = result.get('label_count', 0)
            self.results_table.setItem(i, 1, QTableWidgetItem(str(label_count)))
            
            # Shape 수
            shape_count = result.get('shape_count', 0)
            self.results_table.setItem(i, 2, QTableWidgetItem(str(shape_count)))
            
            # 설명
            description = result.get('description', '')[:50]
            if len(result.get('description', '')) > 50:
                description += "..."
            self.results_table.setItem(i, 3, QTableWidgetItem(description))
            
            # 생성일
            created_at = result.get('created_at', '')
            if isinstance(created_at, datetime):
                created_at = created_at.strftime('%Y-%m-%d %H:%M')
            self.results_table.setItem(i, 4, QTableWidgetItem(str(created_at)))
            
            # 수정일
            updated_at = result.get('updated_at', '')
            if isinstance(updated_at, datetime):
                updated_at = updated_at.strftime('%Y-%m-%d %H:%M')
            self.results_table.setItem(i, 5, QTableWidgetItem(str(updated_at)))
        
        # 컬럼 크기 조정
        self.results_table.resizeColumnsToContents()
    
    def clear_search(self):
        """검색 조건 초기화"""
        self.label_combo.setCurrentIndex(0)
        self.shape_type_combo.setCurrentIndex(0)
        self.tag_combo.setCurrentIndex(0)
        self.image_path_edit.clear()
        self.has_descriptions_cb.setChecked(False)
        self.has_difficult_cb.setChecked(False)
        self.has_attributes_cb.setChecked(False)
        self.has_tags_cb.setChecked(False)
        
        # 결과 초기화
        self.results_table.setRowCount(0)
        self.result_count_label.setText("검색 결과: 0개")
        self.detail_text.clear()
        self.current_results = []
    
    def on_selection_changed(self):
        """선택 변경 이벤트"""
        selected_rows = self.results_table.selectionModel().selectedRows()
        if selected_rows:
            self.open_annotation_btn.setEnabled(True)
            self.delete_annotation_btn.setEnabled(True)
            
            # 상세 정보 표시
            row = selected_rows[0].row()
            if row < len(self.current_results):
                result = self.current_results[row]
                detail_info = self.format_detail_info(result)
                self.detail_text.setPlainText(detail_info)
        else:
            self.open_annotation_btn.setEnabled(False)
            self.delete_annotation_btn.setEnabled(False)
            self.detail_text.clear()
    
    def format_detail_info(self, result):
        """상세 정보 포맷"""
        info = []
        info.append(f"이미지 경로: {result.get('imagePath', '')}")
        info.append(f"라벨들: {', '.join(result.get('labels', []))}")
        info.append(f"Shape 타입들: {', '.join(result.get('shape_types', []))}")
        info.append(f"태그들: {', '.join(result.get('tags', []))}")
        info.append(f"Shape 개수: {result.get('shape_count', 0)}")
        info.append(f"설명 여부: {'있음' if result.get('has_descriptions') else '없음'}")
        info.append(f"Difficult 여부: {'있음' if result.get('has_difficult') else '없음'}")
        info.append(f"Attributes 여부: {'있음' if result.get('has_attributes') else '없음'}")
        
        if result.get('description'):
            info.append(f"\n이미지 설명:\n{result.get('description')}")
        
        return "\n".join(info)
    
    def on_result_double_click(self):
        """결과 더블클릭 - 어노테이션 열기"""
        self.open_selected_annotation()
    
    def open_selected_annotation(self):
        """선택된 어노테이션 열기"""
        selected_rows = self.results_table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            if row < len(self.current_results):
                result = self.current_results[row]
                image_path = result.get('imagePath', '')
                if image_path:
                    self.annotation_selected.emit(image_path)
                    self.close()
    
    def delete_selected_annotation(self):
        """선택된 어노테이션 삭제"""
        selected_rows = self.results_table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            if row < len(self.current_results):
                result = self.current_results[row]
                image_path = result.get('imagePath', '')
                
                # 확인 다이얼로그
                reply = QMessageBox.question(
                    self, "어노테이션 삭제", 
                    f"다음 어노테이션을 삭제하시겠습니까?\n\n{image_path}",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    try:
                        success = self.annotation_manager.delete_annotation(image_path)
                        if success:
                            QMessageBox.information(self, "삭제 완료", "어노테이션이 삭제되었습니다.")
                            # 검색 결과에서 제거
                            self.current_results.pop(row)
                            self.display_results(self.current_results)
                        else:
                            QMessageBox.warning(self, "삭제 실패", "어노테이션 삭제에 실패했습니다.")
                    except Exception as e:
                        QMessageBox.critical(self, "삭제 오류", f"삭제 중 오류가 발생했습니다:\n{str(e)}")
    
    def load_statistics(self):
        """통계 정보 로드"""
        try:
            stats = self.annotation_manager.get_statistics()
            
            stats_text = []
            stats_text.append("=== 어노테이션 통계 ===\n")
            stats_text.append(f"전체 이미지 수: {stats.get('total_images', 0):,}")
            stats_text.append(f"전체 Shape 수: {stats.get('total_shapes', 0):,}")
            stats_text.append(f"이미지당 평균 Shape 수: {stats.get('avg_shapes_per_image', 0):.2f}")
            stats_text.append(f"설명이 있는 이미지 수: {stats.get('images_with_descriptions', 0):,}")
            stats_text.append(f"Difficult가 있는 이미지 수: {stats.get('images_with_difficult', 0):,}")
            stats_text.append(f"태그가 있는 이미지 수: {stats.get('images_with_tags', 0):,}")
            stats_text.append(f"Attributes가 있는 이미지 수: {stats.get('images_with_attributes', 0):,}")
            
            # 라벨 통계
            labels = self.annotation_manager.get_all_labels()
            stats_text.append(f"\n=== 라벨 정보 ===")
            stats_text.append(f"유니크한 라벨 수: {len(labels)}")
            if labels:
                stats_text.append("라벨 목록:")
                for label in labels[:20]:  # 최대 20개만 표시
                    stats_text.append(f"  - {label}")
                if len(labels) > 20:
                    stats_text.append(f"  ... 및 {len(labels) - 20}개 더")
            
            # Shape 타입 통계
            shape_types = self.annotation_manager.get_all_shape_types()
            stats_text.append(f"\n=== Shape 타입 정보 ===")
            stats_text.append(f"유니크한 Shape 타입 수: {len(shape_types)}")
            if shape_types:
                stats_text.append("Shape 타입 목록:")
                for shape_type in shape_types:
                    stats_text.append(f"  - {shape_type}")
            
            # 태그 통계
            tags = self.annotation_manager.get_all_tags()
            stats_text.append(f"\n=== 태그 정보 ===")
            stats_text.append(f"유니크한 태그 수: {len(tags)}")
            if tags:
                stats_text.append("태그 목록:")
                for tag in tags[:20]:  # 최대 20개만 표시
                    stats_text.append(f"  - {tag}")
                if len(tags) > 20:
                    stats_text.append(f"  ... 및 {len(tags) - 20}개 더")
            
            self.stats_text.setPlainText("\n".join(stats_text))
            
        except Exception as e:
            logger.error(f"통계 로드 실패: {e}")
            self.stats_text.setPlainText(f"통계 로드 중 오류가 발생했습니다:\n{str(e)}")
    
    def import_json_files(self):
        """JSON 파일들 일괄 가져오기"""
        file_pattern = self.file_pattern_edit.text().strip()
        if not file_pattern:
            QMessageBox.warning(self, "입력 오류", "파일 패턴을 입력해주세요.")
            return
        
        try:
            self.progress_text.append(f"파일 패턴으로 검색 중: {file_pattern}")
            inserted_ids = self.annotation_manager.insert_multiple_files(file_pattern)
            
            self.progress_text.append(f"처리 완료: {len(inserted_ids)}개 파일")
            
            # 검색 옵션 새로고침
            self.load_search_options()
            
        except Exception as e:
            logger.error(f"일괄 가져오기 실패: {e}")
            self.progress_text.append(f"오류: {str(e)}")
    
    def clear_all_annotations(self):
        """모든 어노테이션 삭제"""
        reply = QMessageBox.question(
            self, "전체 삭제", 
            "정말로 모든 어노테이션을 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                result = self.annotation_manager.collection.delete_many({})
                QMessageBox.information(
                    self, "삭제 완료", 
                    f"{result.deleted_count}개의 어노테이션이 삭제되었습니다."
                )
                # 검색 결과 초기화
                self.clear_search()
                # 검색 옵션 새로고침
                self.load_search_options()
            except Exception as e:
                QMessageBox.critical(self, "삭제 오류", f"삭제 중 오류가 발생했습니다:\n{str(e)}")
    
    def showEvent(self, event):
        """다이얼로그가 표시될 때 통계 로드"""
        super().showEvent(event)
        self.load_statistics()
