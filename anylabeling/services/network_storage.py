"""네트워크 스토리지 설정 및 경로 관리"""

import os
import json
from pathlib import Path
from datetime import datetime

def confirm_dangerous_operation(operation_type, target_path=""):
    """위험한 작업에 대한 GUI 확인 다이얼로그"""
    try:
        from PyQt5.QtWidgets import QMessageBox, QApplication
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QIcon
        
        # QApplication이 없으면 생성
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # 메시지 박스 생성
        msg_box = QMessageBox()
        msg_box.setWindowTitle("⚠️ 위험한 작업 감지")
        msg_box.setIcon(QMessageBox.Warning)
        
        # 메시지 내용 구성
        message = f"<b>작업 유형:</b> {operation_type}<br>"
        if target_path:
            message += f"<b>대상 경로:</b> {target_path}<br>"
        message += "<br><b>이 작업은 중요한 데이터에 영향을 줄 수 있습니다.</b><br>"
        message += "정말로 계속하시겠습니까?"
        
        msg_box.setText(message)
        
        # 버튼 설정
        msg_box.addButton("계속 진행", QMessageBox.YesRole)
        cancel_button = msg_box.addButton("취소", QMessageBox.NoRole)
        msg_box.setDefaultButton(cancel_button)
        
        # 스타일 설정
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #f0f0f0;
                font-size: 12px;
            }
            QMessageBox QPushButton {
                min-width: 80px;
                min-height: 25px;
                padding: 5px;
            }
        """)
        
        # 다이얼로그 실행
        result = msg_box.exec_()
        
        if result == 0:  # "계속 진행" 선택
            print("✅ 사용자가 작업 진행을 승인했습니다.")
            return True
        else:  # "취소" 선택
            print("❌ 사용자가 작업을 취소했습니다.")
            return False
            
    except ImportError:
        # PyQt5가 없으면 터미널 입력으로 폴백
        print("\n" + "="*60)
        print("⚠️  위험한 작업 감지!")
        print("="*60)
        print(f"작업 유형: {operation_type}")
        if target_path:
            print(f"대상 경로: {target_path}")
        print("\n이 작업은 중요한 데이터에 영향을 줄 수 있습니다.")
        print("정말로 계속하시겠습니까?")
        print("="*60)
        
        while True:
            response = input("계속하려면 'YES'를 입력하세요 (취소: 'NO' 또는 Enter): ").strip()
            if response.upper() == 'YES':
                print("✅ 작업을 계속합니다...")
                return True
            elif response.upper() == 'NO' or response == '':
                print("❌ 작업이 취소되었습니다.")
                return False
            else:
                print("'YES' 또는 'NO'를 입력해주세요.")
    except Exception as e:
        print(f"❌ 확인 다이얼로그 오류: {e}")
        # 오류 시 안전하게 False 반환 (작업 취소)
        return False

class NetworkStorageConfig:
    """네트워크 스토리지 설정 관리"""
    
    def __init__(self, config_file="network_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self):
        """설정 파일 로드 (중요 경로 보호)"""
        # 🔒 절대 변경되면 안 되는 중요 경로들 (READ-ONLY) - 현재 주석처리
        PROTECTED_PATHS = {
            # "busnas": "\\\\busnas\\HOV-work",  # 주석처리
            # "schoolnas": "\\\\schoolnas-work\\schoolnas-work",  # 주석처리
            # "images_base": "\\\\busnas\\HOV-work\\02._HOVlane\\번호판검지",  # 주석처리
            # "labels_base": "\\\\schoolnas-work\\schoolnas-work\\seatbelt\\01_WORKSPACE_2025\\500.Research_Other\\102.pillar\\3rd\\testset_sampled"  # 주석처리
            "local_test": "C:\\Users\\pc\\Desktop\\인턴\\SKPoC\\Unclear_file",  # 로컬 테스트 경로
            "images_base": "C:\\Users\\pc\\Desktop\\인턴\\SKPoC\\Unclear_file",
            "labels_base": "C:\\Users\\pc\\Desktop\\인턴\\SKPoC\\Unclear_file"
        }
        
        default_config = {
            "nas_paths": {
                # "busnas": "\\\\busnas\\HOV-work",  # 주석처리
                # "schoolnas": "\\\\schoolnas-work\\schoolnas-work",  # 주석처리
                # "images_base": "\\\\busnas\\HOV-work\\02._HOVlane\\번호판검지",  # 주석처리
                # "labels_base": "\\\\schoolnas-work\\schoolnas-work\\seatbelt\\01_WORKSPACE_2025\\500.Research_Other\\102.pillar\\3rd\\testset_sampled",  # 주석처리
                "local_test": "C:\\Users\\pc\\Desktop\\인턴\\SKPoC\\Unclear_file",
                "images_base": "C:\\Users\\pc\\Desktop\\인턴\\SKPoC\\Unclear_file",
                "labels_base": "C:\\Users\\pc\\Desktop\\인턴\\SKPoC\\Unclear_file"
            },
            "local_cache": {
                "enabled": True,
                "cache_dir": "./cache/images",
                "max_cache_size_gb": 5
            },
            "mongodb": {
                "local_uri": "mongodb://localhost:27017/",
                "database": "local_test_labeling_db"
            },
            "image_extensions": [".jpg", ".jpeg", ".png", ".bmp", ".tiff"],
            "batch_size": 100
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    
                    # 🛡️ 안전한 병합: 보호된 경로는 절대 덮어쓰지 않음
                    for key, value in loaded_config.items():
                        if key == "nas_paths":
                            # NAS 경로는 보호된 경로만 허용, 새로운 경로 추가는 가능
                            if isinstance(value, dict):
                                for path_key, path_value in value.items():
                                    if path_key not in PROTECTED_PATHS:
                                        # 보호되지 않은 새로운 경로만 추가 허용
                                        default_config["nas_paths"][path_key] = path_value
                                        print(f"✅ 새로운 NAS 경로 추가: {path_key} -> {path_value}")
                                    else:
                                        print(f"🔒 보호된 경로는 변경할 수 없습니다: {path_key}")
                        else:
                            # 다른 설정들은 정상적으로 업데이트
                            default_config[key] = value
                            
            except Exception as e:
                print(f"설정 파일 로드 오류: {e}, 기본 설정 사용")
        
        return default_config
    
    def save_config(self):
        """설정 파일 저장 (보호된 경로 제외) - 안전 확인"""
        
        # 🚨 위험한 작업 확인
        if not confirm_dangerous_operation("설정 파일 저장", self.config_file):
            return False
            
        try:
            # 🔒 보호된 경로들은 설정 파일에 저장하지 않음
            # PROTECTED_KEYS = ["busnas", "schoolnas", "images_base", "labels_base"]  # 주석처리
            PROTECTED_KEYS = ["local_test", "images_base", "labels_base"]  # 로컬 테스트용
            
            # 저장할 설정 준비 (보호된 경로 제외)
            save_config = self.config.copy()
            
            if "nas_paths" in save_config:
                filtered_nas_paths = {}
                for key, value in save_config["nas_paths"].items():
                    if key not in PROTECTED_KEYS:
                        filtered_nas_paths[key] = value
                        print(f"💾 사용자 정의 경로 저장: {key} -> {value}")
                    else:
                        print(f"🔒 보호된 경로는 저장하지 않음: {key}")
                
                save_config["nas_paths"] = filtered_nas_paths
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(save_config, f, indent=2, ensure_ascii=False)
                
            print(f"✅ 설정 파일 저장 완료: {self.config_file}")
            return True
            
        except Exception as e:
            print(f"❌ 설정 파일 저장 오류: {e}")
            return False
    
    def get_nas_path(self, path_key):
        """NAS 경로 반환"""
        return self.config["nas_paths"].get(path_key, "")
    
    def is_protected_path(self, path_key):
        """보호된 경로인지 확인"""
        # PROTECTED_KEYS = ["busnas", "schoolnas", "images_base", "labels_base"]  # 주석처리
        PROTECTED_KEYS = ["local_test", "images_base", "labels_base"]  # 로컬 테스트용
        return path_key in PROTECTED_KEYS
    
    def get_protected_paths(self):
        """모든 보호된 경로 반환"""
        # PROTECTED_KEYS = ["busnas", "schoolnas", "images_base", "labels_base"]  # 주석처리
        PROTECTED_KEYS = ["local_test", "images_base", "labels_base"]  # 로컬 테스트용
        return {key: self.config["nas_paths"].get(key, "") for key in PROTECTED_KEYS}
    
    def validate_path_integrity(self):
        """중요 경로들의 무결성 검증"""
        # NAS 경로들 주석처리
        EXPECTED_PATHS = {
            # "busnas": "\\\\busnas\\HOV-work",  # 주석처리
            # "schoolnas": "\\\\schoolnas-work\\schoolnas-work",  # 주석처리
            # "images_base": "\\\\busnas\\HOV-work\\02._HOVlane\\번호판검지",  # 주석처리
            # "labels_base": "\\\\schoolnas-work\\schoolnas-work\\seatbelt\\01_WORKSPACE_2025\\500.Research_Other\\102.pillar\\3rd\\testset_sampled"  # 주석처리
            "local_test": "C:\\Users\\pc\\Desktop\\인턴\\SKPoC\\Unclear_file",  # 로컬 테스트
            "images_base": "C:\\Users\\pc\\Desktop\\인턴\\SKPoC\\Unclear_file",
            "labels_base": "C:\\Users\\pc\\Desktop\\인턴\\SKPoC\\Unclear_file"
        }
        
        integrity_ok = True
        for key, expected_path in EXPECTED_PATHS.items():
            actual_path = self.config["nas_paths"].get(key, "")
            if actual_path != expected_path:
                print(f"❌ 경로 무결성 오류: {key}")
                print(f"   예상: {expected_path}")
                print(f"   실제: {actual_path}")
                integrity_ok = False
            else:
                print(f"✅ 경로 검증 통과: {key}")
        
        return integrity_ok
    
    def normalize_path(self, file_path):
        """경로 정규화 (네트워크 경로 처리)"""
        if not file_path:
            return ""
        
        # Windows 네트워크 경로 정규화
        normalized = str(file_path).replace('/', '\\')
        
        # UNC 경로인지 확인
        if normalized.startswith('\\\\'):
            return normalized
        
        # 절대 경로가 아니면 NAS 기본 경로와 결합
        if not os.path.isabs(normalized):
            base_path = self.get_nas_path("images_base") or "C:\\Users\\pc\\Desktop\\인턴\\SKPoC\\Unclear_file"
            normalized = os.path.join(base_path, normalized)
        
        return normalized
    
    def is_network_path(self, file_path):
        """네트워크 경로인지 확인"""
        normalized = self.normalize_path(file_path)
        return normalized.startswith('\\\\')
    
    def path_exists(self, file_path):
        """경로 존재 여부 확인 (네트워크 경로 포함)"""
        try:
            normalized = self.normalize_path(file_path)
            return os.path.exists(normalized)
        except Exception:
            return False
    
    def get_file_size(self, file_path):
        """파일 크기 조회 (네트워크 경로 포함)"""
        try:
            normalized = self.normalize_path(file_path)
            if os.path.exists(normalized):
                return os.path.getsize(normalized)
        except Exception:
            pass
        return 0
    
    def list_images_in_directory(self, directory_path, recursive=True):
        """디렉토리의 이미지 파일 목록 조회"""
        normalized_dir = self.normalize_path(directory_path)
        image_files = []
        
        if not os.path.exists(normalized_dir):
            print(f"디렉토리가 존재하지 않습니다: {normalized_dir}")
            return image_files
        
        try:
            extensions = self.config["image_extensions"]
            
            if recursive:
                for root, dirs, files in os.walk(normalized_dir):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in extensions):
                            full_path = os.path.join(root, file)
                            image_files.append({
                                'filename': file,
                                'full_path': full_path,
                                'relative_path': os.path.relpath(full_path, normalized_dir),
                                'size': self.get_file_size(full_path)
                            })
            else:
                for file in os.listdir(normalized_dir):
                    if any(file.lower().endswith(ext) for ext in extensions):
                        full_path = os.path.join(normalized_dir, file)
                        if os.path.isfile(full_path):
                            image_files.append({
                                'filename': file,
                                'full_path': full_path,
                                'relative_path': file,
                                'size': self.get_file_size(full_path)
                            })
                            
        except Exception as e:
            print(f"이미지 파일 목록 조회 오류: {e}")
        
        return image_files


class NetworkImageManager:
    """네트워크 이미지 관리"""
    
    def __init__(self, config=None):
        self.config = config or NetworkStorageConfig()
        self.cache_enabled = self.config.config["local_cache"]["enabled"]
        self.cache_dir = self.config.config["local_cache"]["cache_dir"]
        
        if self.cache_enabled:
            os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_image_info(self, file_path):
        """이미지 정보 조회"""
        normalized_path = self.config.normalize_path(file_path)
        
        info = {
            'filename': os.path.basename(normalized_path),
            'full_path': normalized_path,
            'exists': self.config.path_exists(normalized_path),
            'size': self.config.get_file_size(normalized_path),
            'is_network': self.config.is_network_path(normalized_path),
            'accessible': False
        }
        
        # 접근 가능성 테스트
        try:
            if info['exists']:
                with open(normalized_path, 'rb') as f:
                    f.read(1024)  # 첫 1KB 읽기 테스트
                info['accessible'] = True
        except Exception as e:
            info['access_error'] = str(e)
        
        return info
    
    def batch_scan_directory(self, directory_path, progress_callback=None):
        """디렉토리 배치 스캔"""
        print(f"디렉토리 스캔 시작: {directory_path}")
        
        images = self.config.list_images_in_directory(directory_path)
        total = len(images)
        
        print(f"발견된 이미지 파일: {total}개")
        
        results = {
            'total_files': total,
            'accessible_files': 0,
            'inaccessible_files': 0,
            'total_size_mb': 0,
            'files': []
        }
        
        for i, image_data in enumerate(images):
            if progress_callback:
                progress_callback(i + 1, total, image_data['filename'])
            
            info = self.get_image_info(image_data['full_path'])
            results['files'].append(info)
            
            if info['accessible']:
                results['accessible_files'] += 1
                results['total_size_mb'] += info['size'] / (1024 * 1024)
            else:
                results['inaccessible_files'] += 1
        
        print(f"스캔 완료: {results['accessible_files']}/{total}개 접근 가능")
        return results
    
    def create_image_database_entries(self, scan_results, mongo_storage, project_id=None):
        """스캔 결과를 MongoDB에 저장 - 안전 확인"""
        
        # 🚨 위험한 작업 확인
        file_count = len([f for f in scan_results['files'] if f['accessible']])
        if not confirm_dangerous_operation(f"MongoDB에 {file_count}개 이미지 정보 저장", "데이터베이스"):
            return 0
            
        saved_count = 0
        
        for file_info in scan_results['files']:
            if not file_info['accessible']:
                continue
            
            try:
                image_doc = {
                    'image_id': file_info['filename'],
                    'filename': file_info['filename'],
                    'file_path': file_info['full_path'],
                    'file_size': file_info['size'],
                    'is_network_file': file_info['is_network'],
                    'status': 'pending',
                    'uploaded_at': datetime.now()
                }
                
                if project_id:
                    image_doc['project_id'] = project_id
                
                mongo_storage.upsert_image(image_doc)
                saved_count += 1
                
            except Exception as e:
                print(f"이미지 저장 오류 ({file_info['filename']}): {e}")
        
        print(f"데이터베이스에 저장된 이미지: {saved_count}개")
        return saved_count
    
    def delete_image_from_database(self, mongo_storage, image_id):
        """데이터베이스에서 이미지 삭제 - 안전 확인"""
        
        # 🚨 위험한 작업 확인
        if not confirm_dangerous_operation("이미지 데이터베이스 삭제", f"image_id: {image_id}"):
            return False
            
        try:
            result = mongo_storage.delete_image(image_id)
            if result:
                print(f"✅ 이미지 삭제 완료: {image_id}")
            else:
                print(f"❌ 이미지 삭제 실패: {image_id}")
            return result
        except Exception as e:
            print(f"❌ 이미지 삭제 오류: {e}")
            return False
    
    def batch_delete_images(self, mongo_storage, image_ids):
        """배치 이미지 삭제 - 안전 확인"""
        
        # 🚨 위험한 작업 확인
        if not confirm_dangerous_operation(f"배치 이미지 삭제 ({len(image_ids)}개)", "데이터베이스"):
            return 0
            
        deleted_count = 0
        for image_id in image_ids:
            try:
                if mongo_storage.delete_image(image_id):
                    deleted_count += 1
                    print(f"✅ 삭제 완료: {image_id}")
                else:
                    print(f"❌ 삭제 실패: {image_id}")
            except Exception as e:
                print(f"❌ 삭제 오류 ({image_id}): {e}")
        
        print(f"총 {deleted_count}/{len(image_ids)}개 이미지 삭제 완료")
        return deleted_count


# 전역 설정 인스턴스
network_config = NetworkStorageConfig()
image_manager = NetworkImageManager(network_config)
