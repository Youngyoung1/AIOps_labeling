"""번호판 인식 서비스 - 네트워크 스토리지 지원"""

import requests
import time
import os
from datetime import datetime

def confirm_dangerous_operation(operation_type, target="", count=0):
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
        msg_box.setWindowTitle("⚠️ 번호판 인식 작업 확인")
        msg_box.setIcon(QMessageBox.Question)
        
        # 메시지 내용 구성
        message = f"<b>작업 유형:</b> {operation_type}<br>"
        if target:
            message += f"<b>대상:</b> {target}<br>"
        if count > 0:
            message += f"<b>처리할 이미지 수:</b> {count}개<br>"
        message += "<br><b>이 작업은 시간이 오래 걸릴 수 있으며<br>MongoDB에 대량의 데이터가 저장됩니다.</b><br>"
        message += "계속 진행하시겠습니까?"
        
        msg_box.setText(message)
        
        # 버튼 설정
        msg_box.addButton("진행", QMessageBox.YesRole)
        cancel_button = msg_box.addButton("취소", QMessageBox.NoRole)
        msg_box.setDefaultButton(cancel_button)
        
        # 스타일 설정
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #f8f9fa;
                font-size: 12px;
            }
            QMessageBox QPushButton {
                min-width: 80px;
                min-height: 30px;
                padding: 5px 15px;
                font-weight: bold;
            }
            QMessageBox QPushButton[text="진행"] {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QMessageBox QPushButton[text="취소"] {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
            }
        """)
        
        # 다이얼로그 실행
        result = msg_box.exec_()
        
        if result == 0:  # "진행" 선택
            print("✅ 사용자가 번호판 인식 작업 진행을 승인했습니다.")
            return True
        else:  # "취소" 선택
            print("❌ 사용자가 번호판 인식 작업을 취소했습니다.")
            return False
            
    except ImportError:
        # PyQt5가 없으면 터미널 입력으로 폴백
        print("\n" + "="*60)
        print("⚠️  번호판 인식 작업 확인")
        print("="*60)
        print(f"작업 유형: {operation_type}")
        if target:
            print(f"대상: {target}")
        if count > 0:
            print(f"처리할 이미지 수: {count}개")
        print("\n이 작업은 시간이 오래 걸릴 수 있으며 MongoDB에 대량의 데이터가 저장됩니다.")
        print("계속 진행하시겠습니까?")
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

class PlateRecognitionService:
    """번호판 인식 서비스 (로컬 파일 시스템 지원)"""
    
    def __init__(self, server_url='http://192.168.0.43:8081/lpr'):
        self.server_url = server_url
        
        # MongoDB 및 로컬 설정 로드
        try:
            from .storage.mongodb_client import MongoStorage
            from .network_storage import network_config, image_manager
            
            self.mongo_storage = MongoStorage()
            self.network_config = network_config
            self.image_manager = image_manager
            print("✅ MongoDB 및 로컬 설정 로드 완료")
            
        except ImportError as e:
            print(f"❌ 모듈 로드 실패: {e}")
            self.mongo_storage = None
            self.network_config = None
            self.image_manager = None
    
    def recognize_plate_local_batch(self, local_directory, project_id=None):
        """로컬 디렉토리에서 배치로 번호판 인식 - 안전 확인"""
        if not self.image_manager:
            print("❌ 네트워크 이미지 매니저를 사용할 수 없습니다")
            return {
                'plate_7': [],
                'plate_0to6': [],
                'plate_8to9': [],
                'plate_trash': []
            }
        
        # 🚨 위험한 작업 확인
        if not confirm_dangerous_operation("로컬 배치 번호판 인식", local_directory):
            return {
                'plate_7': [],
                'plate_0to6': [],
                'plate_8to9': [],
                'plate_trash': []
            }
            
        results = {
            'plate_7': [],      # 7로 시작
            'plate_0to6': [],   # 0-6으로 시작  
            'plate_8to9': [],   # 8-9로 시작
            'plate_trash': []   # 기타
        }
        
        try:
            # 로컬 디렉토리에서 이미지 스캔
            print(f"📁 로컬 디렉토리 스캔: {local_directory}")
            images = self.image_manager.scan_directory(local_directory)
            
            if not images:
                print("❌ 이미지를 찾을 수 없습니다")
                return results
                
            print(f"🔍 {len(images)}개 이미지 발견")
            
            # 🚨 대량 처리 확인
            if len(images) > 10:
                if not confirm_dangerous_operation(f"대량 이미지 처리", f"{len(images)}개 이미지 MongoDB 저장"):
                    print("❌ 대량 처리가 취소되었습니다.")
                    return results
            
            for i, img_path in enumerate(images):
                try:
                    filename = os.path.basename(img_path)
                    print(f'처리 중: {i+1}/{len(images)} - {filename}')
                    
                    # 로컬 경로는 그대로 사용
                    local_path = img_path
                    
                    if not local_path or not os.path.exists(local_path):
                        print(f"❌ 접근 불가: {img_path}")
                        results['plate_trash'].append({
                            'filename': filename,
                            'error': 'Network path not accessible',
                            'confidence': 0.0,
                            'local_path': img_path
                        })
                        continue
                        
                    # 번호판 인식 수행
                    plate_result = self.recognize_single_plate(local_path)
                    
                    if plate_result['success']:
                        plate_number = plate_result['plate_number']
                        confidence = plate_result['confidence']
                        
                        # 분류
                        category = self.classify_plate(plate_number)
                        
                        plate_data = {
                            'filename': filename,
                            'plate_number': plate_number,
                            'confidence': confidence,
                            'local_path': img_path,
                            'local_location': local_directory
                        }
                        
                        results[category].append(plate_data)
                        
                        # MongoDB에 저장 (로컬 경로 포함)
                        if self.mongo_storage:
                            self.save_to_mongodb(
                                filename, img_path, plate_number, 
                                confidence, category, project_id, 
                                nas_path=img_path
                            )
                            
                        print(f"  → 인식 성공: {plate_number} (신뢰도: {confidence:.3f}, 카테고리: {category})")
                    else:
                        print(f"  → 인식 실패: {plate_result.get('error', 'Unknown error')}")
                        results['plate_trash'].append({
                            'filename': filename,
                            'error': plate_result.get('error', 'Recognition failed'),
                            'confidence': 0.0,
                            'local_path': img_path
                        })
                        
                except Exception as e:
                    print(f"❌ 처리 중 오류 ({img_path}): {e}")
                    results['plate_trash'].append({
                        'filename': os.path.basename(img_path) if img_path else 'Unknown',
                        'error': str(e),
                        'confidence': 0.0,
                        'local_path': img_path
                    })
                    continue
                    
        except Exception as e:
            print(f"❌ 로컬 배치 처리 오류: {e}")
            
        print(f"✅ 배치 처리 완료:")
        print(f"  - 7로 시작: {len(results['plate_7'])}개")
        print(f"  - 0-6으로 시작: {len(results['plate_0to6'])}개") 
        print(f"  - 8-9로 시작: {len(results['plate_8to9'])}개")
        print(f"  - 기타/실패: {len(results['plate_trash'])}개")
        
        return results

    def recognize_plate_batch(self, image_folder, project_id=None):
        """기존 로컬 배치 번호판 인식 (호환성 유지)"""
        results = {
            'plate_7': [],      # 7로 시작
            'plate_0to6': [],   # 0-6으로 시작  
            'plate_8to9': [],   # 8-9로 시작
            'plate_trash': []   # 기타
        }
        
        if not os.path.exists(image_folder):
            print(f"폴더가 존재하지 않습니다: {image_folder}")
            return results
        
        image_files = [f for f in os.listdir(image_folder) 
                      if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
        
        print(f"처리할 이미지 파일: {len(image_files)}개")
        
        for i, filename in enumerate(image_files):
            print(f'처리 중: {i+1}/{len(image_files)} - {filename}')
            
            # 번호판 인식
            file_path = os.path.join(image_folder, filename)
            plate_result = self.recognize_single_plate(file_path)
            
            if plate_result['success']:
                plate_number = plate_result['plate_number']
                confidence = plate_result['confidence']
                
                # 분류
                category = self.classify_plate(plate_number)
                results[category].append({
                    'filename': filename,
                    'plate_number': plate_number,
                    'confidence': confidence
                })
                
                # MongoDB에 저장
                self.save_to_mongodb(
                    filename, file_path, plate_number, 
                    confidence, category, project_id
                )
                
                print(f"  → 인식 성공: {plate_number} (신뢰도: {confidence:.3f}, 카테고리: {category})")
            else:
                print(f"  → 인식 실패: {plate_result.get('error', 'Unknown error')}")
                results['plate_trash'].append({
                    'filename': filename,
                    'error': plate_result.get('error', 'Recognition failed'),
                    'confidence': 0.0
                })
            
            # 서버 부하 방지
            if i % 10 == 0 and i > 0:
                print(f"  → 잠시 대기 (서버 부하 방지)...")
                time.sleep(0.8)
        
        self.print_batch_summary(results)
        return results
    
    def recognize_single_plate(self, file_path):
        """단일 이미지 번호판 인식"""
        try:
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'error': 'File not found'
                }
            
            with open(file_path, 'rb') as file:
                upload = {
                    'name': 'anylabeling',
                    'imgBuffer': file,
                }
                
                # 재시도 로직
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = requests.post(
                            self.server_url, 
                            data=upload, 
                            timeout=30
                        )
                        response.raise_for_status()
                        break
                    except requests.exceptions.RequestException as e:
                        if attempt < max_retries - 1:
                            print(f'  → 서버 연결 실패 (재시도 {attempt + 1}/{max_retries}): {e}')
                            time.sleep(2)
                            continue
                        else:
                            return {
                                'success': False,
                                'error': f'Server connection failed after {max_retries} attempts: {str(e)}'
                            }
                
                plate_number = response.text.strip()
                
                if not plate_number or plate_number.lower() in ['error', 'fail', 'none']:
                    return {
                        'success': False,
                        'error': 'No plate detected'
                    }
                
                return {
                    'success': True,
                    'plate_number': plate_number,
                    'confidence': self.estimate_confidence(plate_number)
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def classify_plate(self, plate_number):
        """번호판 분류"""
        if not plate_number:
            return 'plate_trash'
        
        # 첫 번째 문자로 분류
        first_char = plate_number[0] if len(plate_number) > 0 else ''
        
        if first_char == '7':
            return 'plate_7'
        elif first_char in ['8', '9']:
            return 'plate_8to9'
        elif first_char in ['0', '1', '2', '3', '4', '5', '6']:
            return 'plate_0to6'
        else:
            return 'plate_trash'
    
    def estimate_confidence(self, plate_number):
        """신뢰도 추정 (간단한 휴리스틱)"""
        if not plate_number:
            return 0.0
        
        # 한국 번호판 패턴 확인
        if len(plate_number) >= 7 and len(plate_number) <= 8:
            # 숫자만 있는 경우
            if plate_number.isdigit():
                return 0.9
            # 숫자와 한글이 적절히 섞인 경우 (한국 번호판)
            elif any(c.isdigit() for c in plate_number):
                return 0.8
        
        # 길이가 적절하지 않거나 패턴이 맞지 않는 경우
        if len(plate_number) >= 6:
            return 0.6
        else:
            return 0.3
    
    def save_to_mongodb(self, filename, file_path, plate_number, 
                       confidence, category, project_id=None, nas_path=None):
        """MongoDB에 결과 저장 (로컬 및 네트워크 경로 지원)"""
        if not self.mongo_storage:
            print("❌ MongoDB 연결을 사용할 수 없습니다")
            return None
            
        try:
            # 이미지 정보 저장
            image_doc = {
                'image_id': filename,
                'filename': filename,
                'file_path': file_path,
                'nas_path': nas_path,  # 네트워크 경로 추가 (선택사항)
                'uploaded_at': datetime.now(),
                'status': 'completed',
                'metadata': {
                    'source': 'nas_network' if nas_path else 'local_storage',
                    'plate_recognition': True
                }
            }
            
            if project_id:
                image_doc['project_id'] = project_id
            
            self.mongo_storage.upsert_image(image_doc)
            
            # 어노테이션 저장
            annotation_doc = {
                'image_id': filename,
                'label': 'license_plate',
                'category': 'license_plate', 
                'confidence': confidence,
                'bbox': [],  # 바운딩 박스 정보가 있다면 추가
                'properties': {
                    'plate_number': plate_number,
                    'plate_category': category,
                    'recognition_method': 'api_server',
                    'server_url': self.server_url,
                    'nas_processed': bool(nas_path)  # 네트워크 처리 여부
                },
                'created_by': 'plate_recognition_service',
                'created_at': datetime.now()
            }
            
            if project_id:
                annotation_doc['project_id'] = project_id
            
            annotation_id = self.mongo_storage.insert_annotation(annotation_doc)
            return annotation_id
            
        except Exception as e:
            print(f'MongoDB 저장 오류 ({filename}): {e}')
            return None
    
    def print_batch_summary(self, results):
        """배치 처리 결과 요약 출력"""
        total_processed = sum(len(results[key]) for key in results)
        
        print("\n" + "="*50)
        print("배치 처리 결과 요약")
        print("="*50)
        print(f"총 처리된 이미지: {total_processed}개")
        print(f"• 7번대 번호판: {len(results['plate_7'])}개")
        print(f"• 0-6번대 번호판: {len(results['plate_0to6'])}개")
        print(f"• 8-9번대 번호판: {len(results['plate_8to9'])}개")
        print(f"• 인식 실패/기타: {len(results['plate_trash'])}개")
        
        # 성공률 계산
        success_count = total_processed - len(results['plate_trash'])
        if total_processed > 0:
            success_rate = (success_count / total_processed) * 100
            print(f"• 인식 성공률: {success_rate:.1f}%")
        
        print("="*50)
    
    def recognize_folder_and_save(self, image_folder, project_name=None):
        """폴더의 모든 이미지를 인식하고 저장"""
        print(f"번호판 인식 시작: {image_folder}")
        
        # 프로젝트 생성 (옵션)
        project_id = None
        if project_name:
            try:
                project_id = self.mongo_storage.create_project(
                    name=project_name,
                    description=f"번호판 인식 배치 작업 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
                print(f"프로젝트 생성됨: {project_name} (ID: {project_id})")
            except Exception as e:
                print(f"프로젝트 생성 실패: {e}")
        
        # 배치 인식 실행
        results = self.recognize_plate_batch(image_folder, project_id)
        
        # 프로젝트 통계 업데이트
        if project_id:
            try:
                self.mongo_storage.update_project_stats(project_id)
                print(f"프로젝트 통계 업데이트 완료")
            except Exception as e:
                print(f"프로젝트 통계 업데이트 실패: {e}")
        
        return results
    
    def get_recognition_stats(self):
        """인식 통계 조회"""
        try:
            stats = self.mongo_storage.get_plate_statistics()
            return stats
        except Exception as e:
            print(f"통계 조회 오류: {e}")
            return {}
    
    def test_server_connection(self):
        """서버 연결 테스트"""
        try:
            # 간단한 GET 요청으로 서버 상태 확인
            response = requests.get(self.server_url.replace('/lpr', '/'), timeout=5)
            return True
        except:
            try:
                # POST 요청으로 재시도 (더미 데이터)
                response = requests.post(self.server_url, data={'test': 'connection'}, timeout=5)
                return True
            except:
                return False


def demo_plate_recognition():
    """번호판 인식 데모"""
    service = PlateRecognitionService()
    
    # 서버 연결 테스트
    print("서버 연결 테스트...")
    if service.test_server_connection():
        print("✅ 서버 연결 성공")
    else:
        print("❌ 서버 연결 실패")
        return
    
    # 테스트 폴더 (사용자가 실제 경로로 변경해야 함)
    test_folder = input("이미지 폴더 경로를 입력하세요: ").strip()
    
    if not test_folder or not os.path.exists(test_folder):
        print("올바른 폴더 경로를 입력해주세요.")
        return
    
    project_name = input("프로젝트명을 입력하세요 (선택사항): ").strip()
    if not project_name:
        project_name = None
    
    # 인식 실행
    results = service.recognize_folder_and_save(test_folder, project_name)
    
    print("\n처리 완료!")


if __name__ == "__main__":
    demo_plate_recognition()
