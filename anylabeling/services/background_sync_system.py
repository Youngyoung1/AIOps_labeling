#!/usr/bin/env python3
"""
통합 백그라운드 동기화 시스템
- 지능형 + 플래그 기반 동기화
- 사용자 설정 가능한 모드
- 통계 및 모니터링
"""

import os
import json
from typing import Dict, Any, Optional
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QSpinBox, QGroupBox

from .smart_sync import SmartSyncService
from .flag_sync_manager import FlagBasedSyncManager
from anylabeling.services.annotation_manager import AnnotationManager

import logging
logger = logging.getLogger(__name__)


class BackgroundSyncSystem(QObject):
    """통합 백그라운드 동기화 시스템"""
    
    # Qt 시그널
    sync_event = pyqtSignal(str, str, bool)  # file_path, mode, success
    status_changed = pyqtSignal(str)
    stats_updated = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 동기화 서비스들
        self.smart_sync = SmartSyncService(self)
        self.flag_sync = FlagBasedSyncManager(self)
        
        # 설정
        self.sync_mode = 'smart'  # 'smart', 'flag', 'hybrid'
        self.is_running = False
        #!/usr/bin/env python3
        """
        Deprecated module: anylabeling.services.background_sync_system

        This UI/service combo was removed during repository cleanup to keep the
        application lean. A stub remains to provide a clear error if imported.
        """


        class BackgroundSyncSystem:  # pragma: no cover - deprecated stub
            def __init__(self, *args, **kwargs):
                raise ImportError(
                    "BackgroundSyncSystem has been removed from this build (deprecated)."
                )


        class BackgroundSyncWidget:  # pragma: no cover - deprecated stub
            def __init__(self, *args, **kwargs):
                raise ImportError(
                    "BackgroundSyncWidget has been removed from this build (deprecated)."
                )