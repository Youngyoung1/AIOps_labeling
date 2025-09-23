import os
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any, List
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
# Allow forcing vector-search to be disabled via environment variable (useful for CI / dev machines
# where sentence-transformers is not installed or should be avoided).
if os.getenv("DISABLE_VECTOR_SEARCH", "0") in ("1", "true", "True", "TRUE"):
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("sentence-transformers 사용이 환경변수로 비활성화되었습니다 (DISABLE_VECTOR_SEARCH=1). 벡터 검색 비활성화")

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
        msg_box.setWindowTitle("⚠️ 위험한 작업 감지")
        msg_box.setIcon(QMessageBox.Warning)
        
        # 메시지 내용 구성
        message = f"<b>작업 유형:</b> {operation_type}<br>"
        if target:
            message += f"<b>대상:</b> {target}<br>"
        if count > 0:
            message += f"<b>영향받는 항목 수:</b> {count}개<br>"
        message += "<br><b>이 작업은 중요한 데이터에 영향을 줄 수 있습니다.</b><br>"
        message += "정말로 계속하시겠습니까?"
        
        msg_box.setText(message)
        
        # 버튼 설정
        msg_box.addButton("계속 진행", QMessageBox.YesRole)
        cancel_button = msg_box.addButton("취소", QMessageBox.NoRole)
        msg_box.setDefaultButton(cancel_button)
        
        # 아이콘 설정 시도
        try:
            # QRC prefix is "/images", and files live under images/* inside it.
            # So the full resource path is ":/images/images/<file>".
            msg_box.setWindowIcon(QIcon(":/images/images/warning.svg"))
        except Exception:
            pass
        
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
        if target:
            print(f"대상: {target}")
        if count > 0:
            print(f"영향받는 항목 수: {count}개")
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


class NASMongoConfig:
    """NAS 환경에서의 MongoDB 연결 관리 클래스"""
    
    @staticmethod
    def detect_nas_mongodb_servers() -> List[str]:
        """네트워크에서 MongoDB 서버 자동 감지"""
        import socket
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def check_port(ip: str, port: int = 27017, timeout: float = 1.0) -> bool:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((ip, port))
                sock.close()
                return result == 0
            except:
                return False
        
        # 현재 네트워크 대역 감지
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            network_base = '.'.join(local_ip.split('.')[:-1]) + '.'
        except:
            network_base = "192.168.1."
        
        found_servers = []
        print(f"네트워크 {network_base}*에서 MongoDB 서버 검색 중...")
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = {executor.submit(check_port, f"{network_base}{i}"): f"{network_base}{i}" 
                      for i in range(1, 255)}
            
            for future in as_completed(futures):
                ip = futures[future]
                if future.result():
                    found_servers.append(ip)
                    print(f"MongoDB 서버 발견: {ip}")
        
        return found_servers
    
    @staticmethod
    def create_nas_uri(server_ip: str, username: str = "", password: str = "", 
                      database: str = "labeling_db", port: int = 27017) -> str:
        """NAS MongoDB URI 생성"""
        if username and password:
            return f"mongodb://{username}:{password}@{server_ip}:{port}/{database}"
        else:
            return f"mongodb://{server_ip}:{port}/{database}"
    
    @staticmethod
    def test_nas_connection(uri: str) -> Dict[str, Any]:
        """NAS MongoDB 연결 테스트"""
        try:
            from pymongo import MongoClient
            client = MongoClient(uri, serverSelectionTimeoutMS=3000)
            
            # 기본 정보 수집
            databases = client.list_database_names()
            server_info = client.server_info()
            
            result = {
                'success': True,
                'server_version': server_info.get('version', 'Unknown'),
                'databases': databases,
                'connection_time': 'OK'
            }
            
            client.close()
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }


class MongoStorage:
    """Lightweight MongoDB storage helper for labeling data with vector search support."""

    def __init__(
        self,
        uri: Optional[str] = None,
        db_name: str = "labeling_db",
        annotations_collection: str = "annotations",
        images_collection: str = "images",
        flags_collection: str = "flags",
        embedding_model: str = "all-MiniLM-L6-v2",
    ) -> None:
        # 네트워크 스토리지 설정
        try:
            from ..network_storage import network_config
            self.network_config = network_config
        except ImportError:
            self.network_config = None
            print("네트워크 스토리지 설정을 로드할 수 없습니다.")
        
        self.uri = uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        self.client = MongoClient(self.uri)
        self.db = self.client[db_name]
        self.annotations: Collection = self.db[annotations_collection]
        self.images: Collection = self.db[images_collection]
        self.flags: Collection = self.db[flags_collection]
        
        # 벡터 검색을 위한 임베딩 모델 초기화
        self.embedding_model_name = embedding_model
        self.embedding_model = None
        self._init_embedding_model()
        
        self._ensure_indexes()

    def _init_embedding_model(self):
        """임베딩 모델 초기화"""
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(self.embedding_model_name)
                print(f"임베딩 모델 '{self.embedding_model_name}' 로드 완료")
            except Exception as e:
                print(f"임베딩 모델 로드 실패: {e}")
                self.embedding_model = None
        else:
            print("sentence-transformers 패키지가 설치되지 않음. 벡터 검색 비활성화")

    def _ensure_indexes(self):
        try:
            self.annotations.create_index([("image_id", ASCENDING)])
            self.flags.create_index([("annotation_id", ASCENDING)])
            self.images.create_index([("image_id", ASCENDING)], unique=True)
            # 파일 경로/이름 기반 조회를 위한 인덱스 추가 (DB에 필드가 존재할 경우 활용됨)
            try:
                self.images.create_index([("file_path", ASCENDING)], name="file_path_1")
            except Exception:
                pass
            try:
                self.images.create_index([("filename", ASCENDING)], name="filename_1")
            except Exception:
                pass
            # 사용자 환경에서 사용될 수 있는 다양한 필드명에 대한 인덱스도 시도
            for field, idx_name in [("imagePath", "imagePath_1"), ("image_file_path", "image_file_path_1"), ("path", "path_1")]:
                try:
                    self.images.create_index([(field, ASCENDING)], name=idx_name)
                except Exception:
                    pass
            # 벡터 검색을 위한 텍스트 인덱스 추가
            self.annotations.create_index([("label", "text"), ("description", "text")])
        except Exception:
            pass

    # Images ---------------------------------------------------------------------------------
    def upsert_image(self, image_doc: Dict[str, Any]) -> str:
        image_id = image_doc.get("image_id")
        if not image_id:
            raise ValueError("image_doc must contain 'image_id'")
        
        # 네트워크 경로 정규화
        if self.network_config and 'file_path' in image_doc:
            image_doc['file_path'] = self.network_config.normalize_path(image_doc['file_path'])
            image_doc['is_network_file'] = self.network_config.is_network_path(image_doc['file_path'])
        
        self.images.update_one({"image_id": image_id}, {"$set": image_doc}, upsert=True)
        return image_id
    
    def delete_image(self, image_id: str) -> bool:
        """이미지 삭제 - 안전 확인"""
        # 🚨 이미지 존재 확인
        existing = self.images.find_one({"image_id": image_id})
        if not existing:
            print(f"❌ 삭제할 이미지가 없습니다: {image_id}")
            return False
            
        # 위험한 작업 확인
        if not confirm_dangerous_operation("이미지 삭제", f"image_id: {image_id}"):
            return False
            
        # 관련된 어노테이션도 확인
        annotation_count = self.annotations.count_documents({"image_id": image_id})
        if annotation_count > 0:
            print(f"⚠️  이 이미지에는 {annotation_count}개의 어노테이션이 있습니다.")
            if not confirm_dangerous_operation("관련 어노테이션도 삭제", f"{annotation_count}개 어노테이션"):
                return False
            # 어노테이션도 삭제
            self.annotations.delete_many({"image_id": image_id})
            print(f"✅ 관련 어노테이션 삭제 완료: {annotation_count}개")
            
        # 이미지 삭제
        result = self.images.delete_one({"image_id": image_id})
        if result.deleted_count > 0:
            print(f"✅ 이미지 삭제 완료: {image_id}")
            return True
        else:
            print(f"❌ 이미지 삭제 실패: {image_id}")
            return False
    
    def delete_multiple_images(self, query: Dict[str, Any]) -> int:
        """다중 이미지 삭제 - 안전 확인"""
        # 🚨 삭제할 항목 수 확인
        count = self.images.count_documents(query)
        if count == 0:
            print("❌ 삭제할 이미지가 없습니다.")
            return 0
            
        # 위험한 작업 확인
        if not confirm_dangerous_operation("다중 이미지 삭제", f"쿼리: {query}", count):
            return 0
            
        # 관련 어노테이션 수 확인
        image_ids = [img["image_id"] for img in self.images.find(query, {"image_id": 1})]
        annotation_count = self.annotations.count_documents({"image_id": {"$in": image_ids}})
        
        if annotation_count > 0:
            print(f"⚠️  이 이미지들에는 총 {annotation_count}개의 어노테이션이 있습니다.")
            if not confirm_dangerous_operation("관련 어노테이션도 삭제", f"{annotation_count}개 어노테이션"):
                return 0
            # 어노테이션도 삭제
            self.annotations.delete_many({"image_id": {"$in": image_ids}})
            print(f"✅ 관련 어노테이션 삭제 완료: {annotation_count}개")
            
        # 이미지 삭제
        result = self.images.delete_many(query)
        deleted_count = result.deleted_count
        if deleted_count > 0:
            print(f"✅ 이미지 삭제 완료: {deleted_count}개")
        return deleted_count

    def get_network_images(self, accessible_only: bool = True) -> List[Dict[str, Any]]:
        """네트워크 이미지 목록 조회"""
        query = {"is_network_file": True}
        
        if accessible_only:
            query["status"] = {"$ne": "inaccessible"}
        
        return list(self.images.find(query))

    def scan_and_register_directory(self, directory_path: str, project_id: str = None) -> Dict[str, Any]:
        """디렉토리 스캔 및 이미지 등록 (로컬/네트워크 지원)"""
        if not self.network_config:
            return {"error": "네트워크 설정이 없습니다"}
        
        try:
            from ..network_storage import image_manager
            
            # 진행 상황 콜백
            def progress_callback(current, total, filename):
                print(f"스캔 진행: {current}/{total} - {filename}")
            
            # 디렉토리 스캔
            scan_results = image_manager.batch_scan_directory(directory_path, progress_callback)
            
            # MongoDB에 저장
            saved_count = image_manager.create_image_database_entries(
                scan_results, self, project_id
            )
            
            return {
                "success": True,
                "scanned_files": scan_results['total_files'],
                "accessible_files": scan_results['accessible_files'],
                "saved_to_db": saved_count,
                "total_size_mb": scan_results['total_size_mb']
            }
            
        except Exception as e:
            return {"error": str(e)}

    def validate_network_images(self, batch_size: int = 50) -> Dict[str, Any]:
        """네트워크 이미지들의 접근 가능성 검증"""
        network_images = self.get_network_images(accessible_only=False)
        total = len(network_images)
        
        if total == 0:
            return {"message": "네트워크 이미지가 없습니다"}
        
        accessible_count = 0
        inaccessible_count = 0
        
        print(f"네트워크 이미지 {total}개 검증 시작...")
        
        for i, image in enumerate(network_images):
            if i % batch_size == 0:
                print(f"진행: {i}/{total}")
            
            file_path = image.get('file_path', '')
            exists = False
            
            try:
                if self.network_config:
                    exists = self.network_config.path_exists(file_path)
                else:
                    exists = os.path.exists(file_path)
                
                if exists:
                    accessible_count += 1
                    # 상태 업데이트
                    self.images.update_one(
                        {"image_id": image['image_id']},
                        {"$set": {"status": "accessible", "last_checked": datetime.now()}}
                    )
                else:
                    inaccessible_count += 1
                    self.images.update_one(
                        {"image_id": image['image_id']},
                        {"$set": {"status": "inaccessible", "last_checked": datetime.now()}}
                    )
                    
            except Exception as e:
                inaccessible_count += 1
                self.images.update_one(
                    {"image_id": image['image_id']},
                    {"$set": {"status": "error", "error_message": str(e), "last_checked": datetime.now()}}
                )
        
        return {
            "total_checked": total,
            "accessible": accessible_count,
            "inaccessible": inaccessible_count,
            "success_rate": (accessible_count / total * 100) if total > 0 else 0
        }

    # Annotations ----------------------------------------------------------------------------
    def insert_annotation(self, doc: Dict[str, Any]) -> str:
        # 벡터 임베딩 추가
        if self.embedding_model and 'label' in doc:
            doc['label_embedding'] = self._get_embedding(doc['label'])
        if self.embedding_model and 'description' in doc:
            doc['description_embedding'] = self._get_embedding(doc['description'])
        
        res = self.annotations.insert_one(doc)
        return str(res.inserted_id)

    def find_annotations(self, query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return list(self.annotations.find(query or {}))

    def vector_search_annotations(
        self, 
        query_text: str, 
        field: str = 'label', 
        limit: int = 10, 
        similarity_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        벡터 유사도 기반 검색
        Args:
            query_text: 검색할 텍스트
            field: 검색할 필드 ('label' 또는 'description')
            limit: 결과 개수 제한
            similarity_threshold: 유사도 임계값 (0.0 ~ 1.0)
        Returns:
            유사도가 높은 순으로 정렬된 결과 리스트
        """
        if not self.embedding_model:
            # 임베딩 모델이 없으면 일반 텍스트 검색으로 대체
            return self._fallback_text_search(query_text, field, limit)
        
        try:
            # 쿼리 임베딩 생성
            query_embedding = self._get_embedding(query_text)
            embedding_field = f"{field}_embedding"
            
            # 모든 annotation 가져오기 (임베딩이 있는 것만)
            cursor = self.annotations.find({embedding_field: {"$exists": True}})
            
            results = []
            for doc in cursor:
                if embedding_field in doc:
                    # 코사인 유사도 계산
                    similarity = self._cosine_similarity(query_embedding, doc[embedding_field])
                    if similarity >= similarity_threshold:
                        doc['similarity_score'] = similarity
                        results.append(doc)
            
            # 유사도 기준으로 정렬
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            return results[:limit]
            
        except Exception as e:
            print(f"벡터 검색 실패: {e}")
            return self._fallback_text_search(query_text, field, limit)

    def _get_embedding(self, text: str) -> List[float]:
        """텍스트를 벡터로 변환"""
        if not self.embedding_model:
            return []
        try:
            embedding = self.embedding_model.encode(text)
            return embedding.tolist()
        except Exception as e:
            print(f"임베딩 생성 실패: {e}")
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """코사인 유사도 계산"""
        try:
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            
            dot_product = np.dot(vec1, vec2)
            norm_vec1 = np.linalg.norm(vec1)
            norm_vec2 = np.linalg.norm(vec2)
            
            if norm_vec1 == 0 or norm_vec2 == 0:
                return 0.0
            
            return dot_product / (norm_vec1 * norm_vec2)
        except Exception:
            return 0.0

    def _fallback_text_search(self, query_text: str, field: str, limit: int) -> List[Dict[str, Any]]:
        """임베딩 모델이 없을 때 사용하는 일반 텍스트 검색"""
        try:
            # MongoDB 텍스트 검색 사용
            results = list(self.annotations.find(
                {"$text": {"$search": query_text}},
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit))
            
            if not results:
                # 텍스트 검색 실패시 부분 매칭 검색
                regex_query = {"$regex": query_text, "$options": "i"}
                results = list(self.annotations.find({field: regex_query}).limit(limit))
            
            return results
        except Exception as e:
            print(f"텍스트 검색 실패: {e}")
            # 마지막 대안: 부분 매칭
            regex_query = {"$regex": query_text, "$options": "i"}
            return list(self.annotations.find({field: regex_query}).limit(limit))

    def update_annotation(self, query: Dict[str, Any], update_fields: Dict[str, Any]) -> int:
        res = self.annotations.update_one(query, {"$set": update_fields})
        return res.modified_count

    def delete_annotation(self, query: Dict[str, Any]) -> int:
        """어노테이션 삭제 - 안전 확인"""
        # 🚨 삭제할 항목 수 확인
        count = self.annotations.count_documents(query)
        if count == 0:
            print("❌ 삭제할 어노테이션이 없습니다.")
            return 0
            
        # 위험한 작업 확인
        if not confirm_dangerous_operation("어노테이션 삭제", f"쿼리: {query}", count):
            return 0
            
        res = self.annotations.delete_one(query)
        deleted_count = res.deleted_count
        if deleted_count > 0:
            print(f"✅ 어노테이션 삭제 완료: {deleted_count}개")
        return deleted_count
    
    def delete_multiple_annotations(self, query: Dict[str, Any]) -> int:
        """다중 어노테이션 삭제 - 안전 확인"""
        # 🚨 삭제할 항목 수 확인
        count = self.annotations.count_documents(query)
        if count == 0:
            print("❌ 삭제할 어노테이션이 없습니다.")
            return 0
            
        # 위험한 작업 확인
        if not confirm_dangerous_operation("다중 어노테이션 삭제", f"쿼리: {query}", count):
            return 0
            
        res = self.annotations.delete_many(query)
        deleted_count = res.deleted_count
        if deleted_count > 0:
            print(f"✅ 어노테이션 삭제 완료: {deleted_count}개")
        return deleted_count

    # Flags ----------------------------------------------------------------------------------
    def insert_flag(self, doc: Dict[str, Any]) -> str:
        res = self.flags.insert_one(doc)
        return str(res.inserted_id)

    def find_flags(self, query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return list(self.flags.find(query or {}))

    # 프로젝트 관리 -------------------------------------------------------------------------
    def create_project(self, name: str, description: str = "", settings: Dict = None) -> str:
        """프로젝트 생성"""
        try:
            from datetime import datetime
            project_doc = {
                "name": name,
                "description": description,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "owner": "user",
                "status": "active",
                "settings": settings or {
                    "label_types": ["classification", "detection"],
                    "categories": ["license_plate"],
                    "auto_save": True
                },
                "stats": {
                    "total_images": 0,
                    "labeled_images": 0,
                    "progress_percent": 0.0
                }
            }
            
            # 프로젝트 컬렉션이 없으면 생성
            if 'projects' not in self.db.list_collection_names():
                self.db.create_collection('projects')
            
            result = self.db.projects.insert_one(project_doc)
            return str(result.inserted_id)
            
        except Exception as e:
            print(f"프로젝트 생성 오류: {e}")
            return ""

    def get_projects(self, status: str = None) -> List[Dict[str, Any]]:
        """프로젝트 목록 조회"""
        try:
            query = {}
            if status:
                query["status"] = status
            
            if 'projects' not in self.db.list_collection_names():
                return []
                
            projects = list(self.db.projects.find(query).sort("created_at", -1))
            return projects
            
        except Exception as e:
            print(f"프로젝트 조회 오류: {e}")
            return []

    def update_project_stats(self, project_id: str):
        """프로젝트 통계 업데이트"""
        try:
            from bson import ObjectId
            from datetime import datetime
            
            if isinstance(project_id, str):
                project_id = ObjectId(project_id)
            
            # 이미지 통계 계산
            total_images = self.images.count_documents({"project_id": project_id})
            labeled_images = self.images.count_documents({
                "project_id": project_id,
                "status": "completed"
            })
            
            progress = (labeled_images / total_images * 100) if total_images > 0 else 0
            
            # 프로젝트 업데이트
            self.db.projects.update_one(
                {"_id": project_id},
                {
                    "$set": {
                        "stats.total_images": total_images,
                        "stats.labeled_images": labeled_images,
                        "stats.progress_percent": progress,
                        "updated_at": datetime.now()
                    }
                }
            )
            
            return True
            
        except Exception as e:
            print(f"프로젝트 통계 업데이트 오류: {e}")
            return False

    # 고급 검색 기능 -------------------------------------------------------------------------
    def multi_field_search(self, query_text: str) -> List[Dict[str, Any]]:
        """다중 필드 검색"""
        try:
            # 여러 필드에서 검색
            search_conditions = [
                {"label": {"$regex": query_text, "$options": "i"}},
                {"category": {"$regex": query_text, "$options": "i"}},
                {"description": {"$regex": query_text, "$options": "i"}},
                {"properties.plate_number": {"$regex": query_text, "$options": "i"}},
            ]
            
            # 이미지 정보와 조인
            results = list(self.annotations.aggregate([
                {
                    "$match": {
                        "$or": search_conditions
                    }
                },
                {
                    "$lookup": {
                        "from": "images",
                        "localField": "image_id", 
                        "foreignField": "image_id",
                        "as": "image_info"
                    }
                },
                {
                    "$unwind": {"path": "$image_info", "preserveNullAndEmptyArrays": True}
                },
                {
                    "$project": {
                        "filename": "$image_info.filename",
                        "label": 1,
                        "category": 1,
                        "plate_number": "$properties.plate_number",
                        "confidence": 1,
                        "created_at": 1,
                        "bbox": 1
                    }
                },
                {
                    "$limit": 50
                }
            ]))
            
            return results
            
        except Exception as e:
            print(f"다중 필드 검색 오류: {e}")
            return []

    def search_by_category(self, category: str) -> List[Dict[str, Any]]:
        """카테고리별 검색"""
        try:
            return self.find_annotations({"category": category})
        except Exception as e:
            print(f"카테고리 검색 오류: {e}")
            return []

    def search_by_confidence(self, min_confidence: float, max_confidence: float = 1.0) -> List[Dict[str, Any]]:
        """신뢰도 범위 검색"""
        try:
            query = {
                "confidence": {
                    "$gte": min_confidence,
                    "$lte": max_confidence
                }
            }
            return self.find_annotations(query)
        except Exception as e:
            print(f"신뢰도 검색 오류: {e}")
            return []

    # 통계 기능 -----------------------------------------------------------------------------
    def get_database_stats(self) -> Dict[str, Any]:
        """데이터베이스 통계 조회"""
        try:
            stats = {}
            
            # Annotations 컬렉션에서 고유한 이미지 경로(imagePath)의 개수를 세어 총 이미지 수 계산
            try:
                # imagePath 필드가 존재하고 비어있지 않은 문서만 대상으로 함
                distinct_images = self.annotations.distinct("imagePath", {"imagePath": {"$exists": True, "$ne": ""}})
                stats['total_images'] = len(distinct_images)
            except Exception:
                stats['total_images'] = 0

            # labeled_images는 기존 로직을 유지하거나, 별도 정의가 필요하면 수정 가능
            # 여기서는 annotations이 있는 이미지는 모두 labeled 되었다고 가정
            stats['labeled_images'] = stats['total_images']
            
            # 어노테이션의 shapes 개수를 합산하여 총 어노테이션 수 계산
            try:
                pipeline = [
                    {"$match": {"shapes": {"$exists": True, "$ne": []}}},
                    {
                        "$group": {
                            "_id": None,
                            "total_shapes": {"$sum": {"$size": "$shapes"}}
                        }
                    }
                ]
                result = list(self.annotations.aggregate(pipeline))
                stats['total_annotations'] = result[0]['total_shapes'] if result else 0
            except Exception:
                stats['total_annotations'] = 0
            
            # 진행률 계산
            if stats['total_images'] > 0:
                stats['progress'] = (stats['labeled_images'] / stats['total_images']) * 100
            else:
                stats['progress'] = 0
            
            # 카테고리별 통계
            try:
                category_stats = list(self.annotations.aggregate([
                    {
                        "$group": {
                            "_id": "$category",
                            "count": {"$sum": 1},
                            "avg_confidence": {"$avg": "$confidence"}
                        }
                    }
                ]))
                stats['categories'] = category_stats
            except:
                stats['categories'] = []
            
            # 번호판 카테고리별 통계
            try:
                plate_stats = list(self.annotations.aggregate([
                    {
                        "$match": {"properties.plate_category": {"$exists": True}}
                    },
                    {
                        "$group": {
                            "_id": "$properties.plate_category",
                            "count": {"$sum": 1}
                        }
                    }
                ]))
                stats['plate_categories'] = plate_stats
            except:
                stats['plate_categories'] = []
            
            return stats
            
        except Exception as e:
            print(f"통계 조회 오류: {e}")
            return {}

    # 배치 작업 기능 -------------------------------------------------------------------------
    def batch_update_status(self, image_ids: List[str], new_status: str) -> int:
        """배치 상태 업데이트"""
        try:
            result = self.images.update_many(
                {"image_id": {"$in": image_ids}},
                {"$set": {"status": new_status, "updated_at": datetime.now()}}
            )
            return result.modified_count
            
        except Exception as e:
            print(f"배치 상태 업데이트 오류: {e}")
            return 0

    def batch_delete_annotations(self, annotation_ids: List[str]) -> int:
        """배치 어노테이션 삭제"""
        try:
            from bson import ObjectId
            object_ids = [ObjectId(id) if isinstance(id, str) else id for id in annotation_ids]
            result = self.annotations.delete_many(
                {"_id": {"$in": object_ids}}
            )
            return result.deleted_count
            
        except Exception as e:
            print(f"배치 삭제 오류: {e}")
            return 0

    def batch_update_category(self, annotation_ids: List[str], new_category: str) -> int:
        """배치 카테고리 업데이트"""
        try:
            from bson import ObjectId
            from datetime import datetime
            
            object_ids = [ObjectId(id) if isinstance(id, str) else id for id in annotation_ids]
            result = self.annotations.update_many(
                {"_id": {"$in": object_ids}},
                {"$set": {"category": new_category, "updated_at": datetime.now()}}
            )
            return result.modified_count
            
        except Exception as e:
            print(f"배치 카테고리 업데이트 오류: {e}")
            return 0

    # 데이터 내보내기 -----------------------------------------------------------------------
    def export_annotations(self, filters: Dict = None, format: str = 'json') -> str:
        """어노테이션 내보내기"""
        try:
            import json
            query = filters or {}
            
            # 이미지 정보와 조인하여 데이터 조회
            results = list(self.annotations.aggregate([
                {"$match": query},
                {
                    "$lookup": {
                        "from": "images",
                        "localField": "image_id",
                        "foreignField": "image_id", 
                        "as": "image_info"
                    }
                },
                {
                    "$unwind": {"path": "$image_info", "preserveNullAndEmptyArrays": True}
                }
            ]))
            
            if format == 'json':
                return json.dumps(results, default=str, indent=2, ensure_ascii=False)
            
            elif format == 'csv':
                import csv
                import io
                
                output = io.StringIO()
                if results:
                    fieldnames = ['filename', 'label', 'category', 'plate_number', 'confidence', 'bbox', 'created_at']
                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for result in results:
                        writer.writerow({
                            'filename': result.get('image_info', {}).get('filename', ''),
                            'label': result.get('label', ''),
                            'category': result.get('category', ''),
                            'plate_number': result.get('properties', {}).get('plate_number', ''),
                            'confidence': result.get('confidence', ''),
                            'bbox': str(result.get('bbox', '')),
                            'created_at': str(result.get('created_at', ''))
                        })
                
                return output.getvalue()
            
            return ""
            
        except Exception as e:
            print(f"내보내기 오류: {e}")
            return ""

    # 번호판 인식 관련 기능 ------------------------------------------------------------------
    def save_plate_recognition_result(self, filename: str, file_path: str, plate_number: str, 
                                    confidence: float, category: str, project_id: str = None):
        """번호판 인식 결과 저장"""
        try:
            from datetime import datetime
            
            # 이미지 정보 저장
            image_doc = {
                'image_id': filename,
                'filename': filename,
                'file_path': file_path,
                'uploaded_at': datetime.now(),
                'status': 'completed'
            }
            
            if project_id:
                image_doc['project_id'] = project_id
            
            self.upsert_image(image_doc)
            
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
                    'recognition_method': 'api_server'
                },
                'created_by': 'plate_recognition_service',
                'created_at': datetime.now()
            }
            
            if project_id:
                annotation_doc['project_id'] = project_id
            
            return self.insert_annotation(annotation_doc)
            
        except Exception as e:
            print(f'번호판 결과 저장 오류: {e}')
            return None

    def get_plate_statistics(self) -> Dict[str, Any]:
        """번호판 통계 조회"""
        try:
            # 번호판 카테고리별 통계
            plate_stats = list(self.annotations.aggregate([
                {
                    "$match": {
                        "properties.plate_category": {"$exists": True}
                    }
                },
                {
                    "$group": {
                        "_id": "$properties.plate_category",
                        "count": {"$sum": 1},
                        "avg_confidence": {"$avg": "$confidence"}
                    }
                }
            ]))
            
            # 신뢰도별 분포
            confidence_stats = list(self.annotations.aggregate([
                {
                    "$match": {
                        "label": "license_plate"
                    }
                },
                {
                    "$bucket": {
                        "groupBy": "$confidence",
                        "boundaries": [0.0, 0.5, 0.7, 0.8, 0.9, 1.0],
                        "default": "other",
                        "output": {
                            "count": {"$sum": 1}
                        }
                    }
                }
            ]))
            
            return {
                'plate_categories': plate_stats,
                'confidence_distribution': confidence_stats
            }
            
        except Exception as e:
            print(f"번호판 통계 조회 오류: {e}")
            return {}

    # Utility --------------------------------------------------------------------------------
    def test_connection(self) -> bool:
        """연결 테스트"""
        try:
            # 간단한 쿼리로 연결 테스트
            self.db.list_collection_names()
            return True
        except Exception as e:
            print(f"연결 테스트 실패: {e}")
            return False

    def close(self):
        self.client.close()


if __name__ == "__main__":  # Simple smoke test
    storage = MongoStorage()
    storage.upsert_image({"image_id": "img_001.jpg", "path": "./img_001.jpg"})
    ann_id = storage.insert_annotation({"image_id": "img_001.jpg", "label": "car", "bbox": [1,2,3,4]})
    storage.insert_flag({"annotation_id": ann_id, "type": "occlusion", "comment": "plate hidden"})
    print("Annotations:", storage.find_annotations({"image_id": "img_001.jpg"}))
    print("Flags:", storage.find_flags())
    storage.close()
