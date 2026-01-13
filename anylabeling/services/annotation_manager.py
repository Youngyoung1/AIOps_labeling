import json
import glob
import os
import os.path as osp
from datetime import datetime
from pymongo import MongoClient
from typing import List, Dict, Any, Optional

# Logger import 처리 (상대 import 문제 해결)
try:
    from ..logger import logger
except ImportError:
    # 직접 실행시 또는 상대 import 실패시 기본 로거 사용
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)


class AnnotationManager:
    def __init__(self, connection_string: str = None, db_name: str = None, config_path: str = "mongo_config.json"):
        # .env 파일에서 MongoDB 설정 읽기
        if connection_string is None or db_name is None:
            try:
                # .env 파일 경로 찾기 (현재 디렉토리부터 상위로 탐색)
                env_path = self._find_env_file()
                if env_path:
                    env_vars = self._load_env_file(env_path)
                    
                    # .env 파일에서 MongoDB 인증 정보 구성 (IP는 로컬호스트로 강제)
                    mongodb_ip = "127.0.0.1"  # MongoDB가 0.0.0.0에서 리스닝하므로 로컬호스트로 연결
                    mongodb_port = env_vars.get("MONGODB_PORT", "27017")
                    mongodb_username = env_vars.get("MONGODB_ADMIN_USERNAME", "admin")
                    mongodb_password = env_vars.get("MONGODB_ADMIN_PASSWORD", "")
                    mongodb_database = env_vars.get("MONGODB_DATABASE", "labeling_db")
                    
                    if mongodb_password:
                        connection_string = connection_string or f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_ip}:{mongodb_port}/?authSource=admin"
                    else:
                        connection_string = connection_string or f"mongodb://{mongodb_ip}:{mongodb_port}/"
                    
                    db_name = db_name or mongodb_database
                    logger.info(f"MongoDB 연결 설정: {mongodb_ip}:{mongodb_port}, DB: {db_name}, User: {mongodb_username}")
                else:
                    logger.warning(".env 파일을 찾을 수 없습니다. 기본 설정을 사용합니다.")
                    
            except Exception as e:
                logger.error(f".env 파일 읽기 실패: {e}")
            
            # mongo_config.json 백업 설정 (기존 호환성)
            if connection_string is None or db_name is None:
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    connection_string = connection_string or config.get("connection_string", "mongodb://localhost:27017")
                    db_name = db_name or config.get("db_name", "labeling_db")
                except Exception as e:
                    logger.error(f"mongo_config.json 읽기 실패: {e}")
                    # 기본값 사용
                    connection_string = connection_string or "mongodb://localhost:27017"
                    db_name = db_name or "labeling_db"

        try:
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            # 연결 테스트
            self.client.admin.command('ismaster')
            self.db = self.client[db_name]
            self.collection = self.db['annotations']  # 실제 컬렉션 이름: annotations
            self._create_indexes()
            logger.info(f"AnnotationManager 초기화 완료: {db_name}")
        except Exception as e:
            logger.error(f"인증된 MongoDB 연결 실패: {e}")
            # 인증 오류 시 인증 없는 연결로 재시도
            try:
                logger.info("인증 없는 MongoDB 연결을 시도합니다...")
                # .env에서 기본 정보 가져오기 (IP는 로컬호스트로 강제)
                env_path = self._find_env_file()
                if env_path:
                    env_vars = self._load_env_file(env_path)
                    # MongoDB가 0.0.0.0에서 리스닝하므로 로컬호스트로 연결
                    mongodb_ip = "127.0.0.1"  # env_vars.get("MONGODB_SERVER_IP", "127.0.0.1")
                    mongodb_port = env_vars.get("MONGODB_PORT", "27017")
                    db_name = env_vars.get("MONGODB_DATABASE", "labeling_db")
                    # .env에서 관리자 계정 정보 읽기
                    admin_username = env_vars.get("MONGODB_ADMIN_USERNAME", "admin")
                    admin_password = env_vars.get("MONGODB_ADMIN_PASSWORD", "Admin$ecure2024!")
                else:
                    mongodb_ip = "127.0.0.1"
                    mongodb_port = "27017"
                    admin_username = "admin"
                    admin_password = "Admin$ecure2024!"
                
                # 관리자 계정으로 fallback 연결 시도 (.env 정보 사용)
                fallback_connection = f"mongodb://{admin_username}:{admin_password}@{mongodb_ip}:{mongodb_port}/?authSource=admin"
                logger.info(f"Fallback 연결 시도 (관리자 계정): mongodb://{admin_username}:***@{mongodb_ip}:{mongodb_port}/?authSource=admin")
                
                self.client = MongoClient(fallback_connection, serverSelectionTimeoutMS=5000)
                self.client.admin.command('ismaster')
                self.db = self.client[db_name]
                self.collection = self.db['annotations']
                self._create_indexes()
                logger.info(f"AnnotationManager 초기화 완료 (인증 없음): {db_name}")
                
            except Exception as fallback_error:
                logger.error(f"Fallback MongoDB 연결도 실패: {fallback_error}")
                logger.error("MongoDB가 실행 중이 아니거나 접근할 수 없습니다.")
                raise

    def _find_env_file(self):
        """현재 디렉토리부터 상위로 .env 파일 찾기"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        while current_dir != os.path.dirname(current_dir):  # 루트까지
            env_path = os.path.join(current_dir, '.env')
            if os.path.exists(env_path):
                return env_path
            current_dir = os.path.dirname(current_dir)
        return None
    
    def _load_env_file(self, env_path):
        """간단한 .env 파일 파서"""
        env_vars = {}
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        except Exception as e:
            logger.error(f".env 파일 파싱 오류: {e}")
        return env_vars

    def _create_indexes(self):
        """필요한 인덱스 생성"""
        try:
            # 🚀 이미지/JSON 관련 인덱스
            self.collection.create_index("imagePath")         # JSON 내부 imagePath
            self.collection.create_index("json_file_path")    # JSON 파일 경로
            self.collection.create_index("image_file_path")   # 이미지 파일 경로
            self.collection.create_index("json_file_name")    # JSON 파일명
            self.collection.create_index("image_file_name")   # 이미지 파일명

            # 🔍 검색 최적화 인덱스
            self.collection.create_index("labels")
            self.collection.create_index("shapes.label")
            self.collection.create_index([("imagePath", 1), ("labels", 1)])

            # 설명 검색용 text 인덱스 (컬렉션당 하나만 허용)
            try:
                existing_text = None
                for idx in self.collection.list_indexes():
                    key_spec = idx.get('key') or idx.get('keyPattern') or {}
                    if 'text' in str(key_spec):
                        existing_text = idx
                        break
                if existing_text:
                    logger.info(f"텍스트 인덱스 이미 존재: {existing_text.get('name', '<unnamed>')}, 건너뜀")
                else:
                    # shapes.description만 사용하여 일관성 유지
                    self.collection.create_index([("shapes.description", "text")])
            except Exception as te:
                logger.warning(f"텍스트 인덱스 생성/확인 중 에러: {te}")

            # 📊 어노테이션 최적화 인덱스
            self.collection.create_index("shape_types")
            self.collection.create_index("tags")
            self.collection.create_index("shape_count")
            self.collection.create_index("label_count")

            # 🏷️ 플래그 검색 인덱스
            self.collection.create_index("has_descriptions")
            self.collection.create_index("has_difficult")
            self.collection.create_index("has_tags")
            self.collection.create_index("has_attributes")
            self.collection.create_index("has_shape_flags")
            self.collection.create_index("has_global_flags")

            # ⏰ 시간 기반 인덱스
            self.collection.create_index("created_at")
            self.collection.create_index("updated_at")
            self.collection.create_index("review_status")

            # 🔗 복합 인덱스
            self.collection.create_index([("review_status", 1), ("updated_at", -1)])
            self.collection.create_index([("labels", 1), ("shape_count", -1)])
            self.collection.create_index([("json_directory", 1), ("json_file_name", 1)])

            logger.info("MongoDB 인덱스 생성 완료 (텍스트 인덱스는 최대 1개)")
        except Exception as e:
            logger.warning(f"인덱스 생성 중 에러: {e}")

    def _safe_relpath(self, target_path: str, start: str = None) -> str:
        """
        다른 드라이브에 있는 경로를 relpath로 변환할 때 발생하는 ValueError를 방지.
        드라이브가 다르면 절대 경로를 그대로 반환한다.
        """
        try:
            return os.path.relpath(target_path, start or os.getcwd())
        except ValueError:
            return os.path.abspath(target_path)

    def _extract_annotation_features(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """JSON 데이터에서 검색 최적화용 필드들 추출"""
        shapes = json_data.get('shapes', [])

        # labels 배열 생성 (중복 제거)
        labels = list(set([shape.get('label', '') for shape in shapes if shape.get('label')]))

        # shape_types 추출
        shape_types = list(set([shape.get('shape_type', '') for shape in shapes if shape.get('shape_type')]))

        # descriptions 추출
        descriptions = [shape.get('description', '') for shape in shapes
                        if shape.get('description') and shape.get('description').strip()]
        has_descriptions = len(descriptions) > 0

        # difficult 플래그
        has_difficult = any(shape.get('difficult', False) for shape in shapes)

        # tag 정보
        all_tags = []
        for shape in shapes:
            tags = shape.get('tag', [])
            if tags and isinstance(tags, list):
                all_tags.extend(tags)
        unique_tags = list(set(all_tags))
        has_tags = len(unique_tags) > 0

        # attributes 정보
        has_attributes = any(shape.get('attributes', {}) for shape in shapes
                             if isinstance(shape.get('attributes'), dict) and shape.get('attributes'))

        # flags 정보
        global_flags = json_data.get("flags", {})
        has_global_flags = bool(global_flags)

        shape_flags = []
        for shape in shapes:
            if shape.get('flags') and isinstance(shape.get('flags'), dict) and shape.get('flags'):
                shape_flags.append(shape.get('flags'))
        has_shape_flags = len(shape_flags) > 0

        return {
            "labels": labels,
            "shape_types": shape_types,
            "tags": unique_tags,

            # 개수 정보
            "shape_count": len(shapes),
            "label_count": len(labels),
            "tag_count": len(unique_tags),
            "description_count": len(descriptions),

            # 플래그 정보
            "has_descriptions": has_descriptions,
            "has_difficult": has_difficult,
            "has_tags": has_tags,
            "has_attributes": has_attributes,
            "has_global_flags": has_global_flags,
            "has_shape_flags": has_shape_flags
        }

    def insert_annotation(self, json_file_path: str = None, json_data: Dict[str, Any] = None) -> Optional[str]:
        """JSON 파일 또는 JSON 데이터를 MongoDB에 삽입"""
        try:
            # JSON 데이터 준비
            if json_data is None and json_file_path:
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
            elif json_data is None:
                raise ValueError("json_file_path 또는 json_data 중 하나는 제공되어야 합니다")

            # 파일 경로 정보
            path_info = {}
            if json_file_path:
                abs_path = os.path.abspath(json_file_path)
                path_info = {
                    "json_file_path": abs_path,
                    "json_file_name": os.path.basename(abs_path),
                    "json_directory": os.path.dirname(abs_path),
                    "json_relative_path": self._safe_relpath(abs_path),
                }

                # 이미지 파일 경로 정보
                image_path = json_data.get("imagePath")
                if image_path:
                    if not os.path.isabs(image_path):
                        image_abs_path = os.path.join(os.path.dirname(abs_path), image_path)
                        image_abs_path = os.path.abspath(image_abs_path)
                    else:
                        image_abs_path = image_path

                    image_exists = os.path.exists(image_abs_path)
                    same_directory = os.path.dirname(image_abs_path) == os.path.dirname(abs_path)

                    path_info.update({
                        "image_file_path": image_abs_path,
                        "image_file_name": os.path.basename(image_abs_path),
                        "image_directory": os.path.dirname(image_abs_path),
                        "image_relative_path": self._safe_relpath(image_abs_path),
                        "image_exists": image_exists,
                        "same_directory": same_directory,
                        "image_extension": os.path.splitext(image_abs_path)[1].lower(),
                    })

            # 검색 최적화용 필드
            features = self._extract_annotation_features(json_data)

            # MongoDB 문서 (annotation.description 제외하여 일관성 유지)
            document = {
                "version": json_data.get("version"),
                "flags": json_data.get("flags", {}),
                "shapes": json_data.get("shapes", []),
                "imagePath": json_data.get("imagePath"),
                "imageData": json_data.get("imageData"),
                # description 필드 제거 - shapes.description만 사용

                **path_info,
                "annotation": json_data,
                **features,

                "created_at": datetime.now(),
                "last_modified": datetime.now(),
                "updated_at": datetime.now()
            }

            # upsert 처리
            query = {"json_file_path": os.path.abspath(json_file_path)} if json_file_path else {"imagePath": json_data.get("imagePath")}
            existing = self.collection.find_one(query)
            if existing:
                document["created_at"] = existing.get("created_at", datetime.now())
                self.collection.replace_one(query, document)
                logger.info(f"데이터 업데이트 완료 - {json_data.get('imagePath')}")
                return str(existing["_id"])
            else:
                result = self.collection.insert_one(document)
                logger.info(f"데이터 삽입 완료 - {json_data.get('imagePath')}")
                return str(result.inserted_id)

        except Exception as e:
            logger.error(f"데이터 처리 중 에러: {e}")
            return None
   
    def insert_multiple_files(self, file_pattern: str = "*.json") -> List[str]:
        """여러 JSON 파일을 한 번에 처리"""
        files = glob.glob(file_pattern)
        inserted_ids = []
        
        logger.info(f"AnnotationManager: {len(files)}개 파일 처리 시작...")
        
        for file_path in files:
            inserted_id = self.insert_annotation(json_file_path=file_path)
            if inserted_id:
                inserted_ids.append(inserted_id)
        
        logger.info(f"AnnotationManager: 총 {len(inserted_ids)}개 파일 처리 완료")
        return inserted_ids
    
    def find_by_image_path(self, image_path: str) -> Optional[Dict[str, Any]]:
        """이미지 경로로 annotation 조회"""
        try:
            return self.collection.find_one({"imagePath": image_path})
        except Exception as e:
            logger.error(f"이미지 경로 조회 실패: {e}")
            return None
    
    def find_by_label(self, label: str) -> List[Dict[str, Any]]:
        """특정 라벨을 포함한 모든 annotation 조회"""
        try:
            return list(self.collection.find({"labels": label}))
        except Exception as e:
            logger.error(f"라벨 조회 실패: {e}")
            return []
    
    def find_by_shape_type(self, shape_type: str) -> List[Dict[str, Any]]:
        """특정 shape type을 포함한 모든 annotation 조회"""
        try:
            return list(self.collection.find({"shape_types": shape_type}))
        except Exception as e:
            logger.error(f"Shape type 조회 실패: {e}")
            return []
    
    def find_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """특정 태그를 포함한 모든 annotation 조회"""
        try:
            return list(self.collection.find({"tags": tag}))
        except Exception as e:
            logger.error(f"태그 조회 실패: {e}")
            return []
    
    def find_with_descriptions(self) -> List[Dict[str, Any]]:
        """설명이 있는 annotation들 조회"""
        try:
            return list(self.collection.find({"has_descriptions": True}))
        except Exception as e:
            logger.error(f"설명 있는 annotation 조회 실패: {e}")
            return []
    
    def find_difficult_annotations(self) -> List[Dict[str, Any]]:
        """difficult 플래그가 있는 annotation들 조회"""
        try:
            return list(self.collection.find({"has_difficult": True}))
        except Exception as e:
            logger.error(f"Difficult annotation 조회 실패: {e}")
            return []
    
    def find_with_flags(self, global_flags: bool = None, shape_flags: bool = None) -> List[Dict[str, Any]]:
        """플래그가 있는 annotation들 조회"""
        try:
            query = {}
            if global_flags is not None:
                query["has_global_flags"] = global_flags
            if shape_flags is not None:
                query["has_shape_flags"] = shape_flags
            return list(self.collection.find(query))
        except Exception as e:
            logger.error(f"플래그 annotation 조회 실패: {e}")
            return []
    
    def find_with_attributes(self) -> List[Dict[str, Any]]:
        """attributes가 있는 annotation들 조회"""
        try:
            return list(self.collection.find({"has_attributes": True}))
        except Exception as e:
            logger.error(f"Attributes annotation 조회 실패: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """전체 통계 정보 조회"""
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "total_images": {"$sum": 1},
                        "total_shapes": {"$sum": "$shape_count"},
                        "avg_shapes_per_image": {"$avg": "$shape_count"},
                        "images_with_descriptions": {"$sum": {"$cond": ["$has_descriptions", 1, 0]}},
                        "images_with_difficult": {"$sum": {"$cond": ["$has_difficult", 1, 0]}},
                        "images_with_tags": {"$sum": {"$cond": ["$has_tags", 1, 0]}},
                        "images_with_attributes": {"$sum": {"$cond": ["$has_attributes", 1, 0]}}
                    }
                }
            ]
            
            result = list(self.collection.aggregate(pipeline))
            return result[0] if result else {}
        except Exception as e:
            logger.error(f"통계 조회 실패: {e}")
            return {}
    
    def get_annotation_statistics(self) -> Dict[str, Any]:
        """어노테이션 통계 정보 조회 (improved_review_widgets.py에서 사용)"""
        return self.get_statistics()
    
    def get_all_labels(self) -> List[str]:
        """모든 유니크한 라벨 목록 조회"""
        try:
            pipeline = [
                {"$unwind": "$labels"},
                {"$group": {"_id": "$labels"}},
                {"$sort": {"_id": 1}}
            ]
            result = self.collection.aggregate(pipeline)
            return [doc["_id"] for doc in result]
        except Exception as e:
            logger.error(f"라벨 목록 조회 실패: {e}")
            return []
    
    def get_all_tags(self) -> List[str]:
        """모든 유니크한 태그 목록 조회"""
        try:
            pipeline = [
                {"$unwind": "$tags"},
                {"$group": {"_id": "$tags"}},
                {"$sort": {"_id": 1}}
            ]
            result = self.collection.aggregate(pipeline)
            return [doc["_id"] for doc in result]
        except Exception as e:
            logger.error(f"태그 목록 조회 실패: {e}")
            return []
    
    def get_all_shape_types(self) -> List[str]:
        """모든 유니크한 shape type 목록 조회"""
        try:
            pipeline = [
                {"$unwind": "$shape_types"},
                {"$group": {"_id": "$shape_types"}},
                {"$sort": {"_id": 1}}
            ]
            result = self.collection.aggregate(pipeline)
            return [doc["_id"] for doc in result]
        except Exception as e:
            logger.error(f"Shape type 목록 조회 실패: {e}")
            return []
    
    def update_annotation(self, image_path: str, updated_data: Dict[str, Any]) -> bool:
        """기존 annotation 업데이트"""
        try:
            # 새로운 특성들 추출
            features = self._extract_annotation_features(updated_data)
            
            # 업데이트할 필드들 (description 제외하여 일관성 유지)
            update_fields = {
                # 원본 데이터 필드들
                "version": updated_data.get("version"),
                "flags": updated_data.get("flags", {}),
                "shapes": updated_data.get("shapes", []),
                "imageData": updated_data.get("imageData"),
                # description 필드 제거 - shapes.description만 사용
                
                # 원본 JSON 전체 보존
                "annotation": updated_data,
                
                # 검색 최적화용 필드들
                **features,
                
                # 업데이트 시간
                "updated_at": datetime.now()
            }
            
            result = self.collection.update_one(
                {"imagePath": image_path},
                {"$set": update_fields}
            )
            
            if result.modified_count > 0:
                logger.info(f"AnnotationManager: annotation 업데이트 완료 - {image_path}")
                return True
            else:
                logger.warning(f"AnnotationManager: 업데이트할 annotation을 찾을 수 없음 - {image_path}")
                return False
                
        except Exception as e:
            logger.error(f"AnnotationManager: annotation 업데이트 중 에러 - {e}")
            return False
    
    def delete_annotation(self, image_path: str) -> bool:
        """annotation 삭제"""
        try:
            result = self.collection.delete_one({"imagePath": image_path})
            if result.deleted_count > 0:
                logger.info(f"AnnotationManager: annotation 삭제 완료 - {image_path}")
                return True
            else:
                logger.warning(f"AnnotationManager: 삭제할 annotation을 찾을 수 없음 - {image_path}")
                return False
        except Exception as e:
            logger.error(f"AnnotationManager: annotation 삭제 중 에러 - {e}")
            return False
    
    def search_annotations(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """다양한 조건으로 어노테이션 검색"""
        try:
            import re
            query = {}
            
            # 라벨 검색
            if criteria.get("label"):
                # 특수 문자 이스케이프 처리
                escaped_label = re.escape(criteria["label"])
                query["labels"] = {"$regex": escaped_label, "$options": "i"}
            
            # 파일명 검색
            if criteria.get("filename"):
                # 파일명은 일반적으로 안전하지만 이스케이프 처리
                escaped_filename = re.escape(criteria["filename"])
                query["json_file_name"] = {"$regex": escaped_filename, "$options": "i"}
            
            # JSON 파일 경로 검색 (새로 추가)
            if criteria.get("json_file_path"):
                # Windows 경로의 백슬래시 문제 해결을 위해 정확한 매칭 사용
                json_path = criteria["json_file_path"]
                if "\\" in json_path:
                    # 정확한 매칭 사용 (정규식 대신)
                    query["json_file_path"] = json_path
                else:
                    # 백슬래시가 없으면 부분 매칭 가능
                    escaped_path = re.escape(json_path)
                    query["json_file_path"] = {"$regex": escaped_path, "$options": "i"}
            
            # 이미지 경로 검색 (새로 추가)
            if criteria.get("image_path"):
                image_path = criteria["image_path"]
                if "\\" in image_path:
                    # 정확한 매칭 사용
                    query["imagePath"] = image_path
                else:
                    # 부분 매칭
                    escaped_path = re.escape(image_path)
                    query["imagePath"] = {"$regex": escaped_path, "$options": "i"}
            
            # Shape 타입 검색
            if criteria.get("shape_type"):
                query["shape_types"] = criteria["shape_type"]
            
            # 설명 유무
            if criteria.get("has_descriptions"):
                query["has_descriptions"] = True
            
            # 태그 유무
            if criteria.get("has_tags"):
                query["has_tags"] = True
            
            # 빈 조건인 경우 모든 데이터 조회
            if not query:
                results = list(self.collection.find().sort("updated_at", -1).limit(1000))
            else:
                # 결과 조회 (최신순 정렬)
                results = list(self.collection.find(query).sort("updated_at", -1).limit(100))
            
            # ObjectId를 문자열로 변환
            for result in results:
                if "_id" in result:
                    result["_id"] = str(result["_id"])
            
            return results
            
        except Exception as e:
            logger.error(f"검색 실패: {e}")
            return []
    
    def get_image_path_fast(self, identifier, identifier_type="imagePath"):
        """
        🚀 이미지 경로 빠른 조회 (인덱스 활용)
        
        Args:
            identifier: 식별자 (imagePath, json_file_name 등)
            identifier_type: 식별자 타입 ("imagePath", "json_file_name", "image_file_name")
        
        Returns:
            dict: 이미지 관련 경로 정보 또는 None
        """
        try:
            # 필요한 필드만 선택하여 네트워크 트래픽 최소화
            projection = {
                "imagePath": 1,
                "image_file_path": 1,
                "image_file_name": 1,
                "json_file_path": 1,
                "json_file_name": 1,
                "json_directory": 1,
                "image_directory": 1,
                "image_exists": 1,
                "same_directory": 1
            }
            
            # 인덱스를 활용한 빠른 검색
            query = {identifier_type: identifier}
            result = self.collection.find_one(query, projection)
            
            if result:
                # ObjectId 제거
                result.pop("_id", None)
                return result
            else:
                logger.warning(f"이미지 정보를 찾을 수 없음: {identifier_type}={identifier}")
                return None
                
        except Exception as e:
            logger.error(f"이미지 경로 조회 실패: {e}")
            return None
    
    def batch_get_image_paths(self, identifiers, identifier_type="imagePath"):
        """
        🚀 여러 이미지 경로 배치 조회 (대량 처리 최적화)
        
        Args:
            identifiers: 식별자 리스트
            identifier_type: 식별자 타입
        
        Returns:
            dict: {identifier: path_info} 형태의 딕셔너리
        """
        try:
            projection = {
                identifier_type: 1,
                "image_file_path": 1,
                "image_exists": 1,
                "json_file_path": 1
            }
            
            # $in 연산자로 배치 조회
            query = {identifier_type: {"$in": identifiers}}
            results = self.collection.find(query, projection)
            
            # 결과를 딕셔너리로 변환
            path_map = {}
            for result in results:
                key = result.get(identifier_type)
                if key:
                    path_map[key] = {
                        "image_file_path": result.get("image_file_path"),
                        "image_exists": result.get("image_exists", False),
                        "json_file_path": result.get("json_file_path")
                    }
            
            return path_map
            
        except Exception as e:
            logger.error(f"배치 이미지 경로 조회 실패: {e}")
            return {}
    
    def update_image_existence_cache(self):
        """
        📁 이미지 파일 존재 여부 캐시 업데이트
        (주기적으로 실행하여 파일 존재 여부를 미리 확인)
        """
        try:
            import os
            
            # 모든 이미지 경로 조회
            projection = {"image_file_path": 1, "image_exists": 1}
            documents = self.collection.find({"image_file_path": {"$exists": True}}, projection)
            
            update_count = 0
            for doc in documents:
                image_path = doc.get("image_file_path")
                if image_path:
                    current_exists = doc.get("image_exists", False)
                    actual_exists = os.path.exists(image_path)
                    
                    # 상태가 변경된 경우만 업데이트
                    if current_exists != actual_exists:
                        self.collection.update_one(
                            {"_id": doc["_id"]},
                            {"$set": {"image_exists": actual_exists}}
                        )
                        update_count += 1
            
            logger.info(f"이미지 존재 여부 캐시 업데이트 완료: {update_count}개 변경")
            return update_count
            
        except Exception as e:
            logger.error(f"이미지 존재 여부 캐시 업데이트 실패: {e}")
            return 0
    
    def search_by_exact_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        """정확한 파일명으로 검색 (정규식 없이)"""
        try:
            return self.collection.find_one({"json_file_name": filename})
        except Exception as e:
            logger.error(f"정확한 파일명 검색 실패: {e}")
            return None
    
    def search_by_exact_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """정확한 파일 경로로 검색 (정규식 없이)"""
        try:
            return self.collection.find_one({"json_file_path": file_path})
        except Exception as e:
            logger.error(f"정확한 경로 검색 실패: {e}")
            return None
    
    def search_by_partial_path(self, partial_path: str) -> List[Dict[str, Any]]:
        """부분 경로로 검색 (안전한 정규식 사용)"""
        try:
            import re
            # 특수 문자 이스케이프 처리
            escaped_path = re.escape(partial_path)
            
            # json_file_path와 imagePath 모두에서 검색
            query = {
                "$or": [
                    {"json_file_path": {"$regex": escaped_path, "$options": "i"}},
                    {"imagePath": {"$regex": escaped_path, "$options": "i"}}
                ]
            }
            
            results = list(self.collection.find(query).sort("updated_at", -1).limit(100))
            
            # ObjectId를 문자열로 변환
            for result in results:
                if "_id" in result:
                    result["_id"] = str(result["_id"])
            
            return results
            
        except Exception as e:
            logger.error(f"부분 경로 검색 실패: {e}")
            return []
    
    def find_file_safely(self, identifier: str) -> Optional[Dict[str, Any]]:
        """안전한 파일 검색 (여러 방법 시도)"""
        try:
            # 1. 정확한 파일명으로 검색
            result = self.search_by_exact_filename(identifier)
            if result:
                logger.info(f"파일명으로 찾음: {identifier}")
                return result
            
            # 2. 정확한 경로로 검색
            result = self.search_by_exact_path(identifier)
            if result:
                logger.info(f"정확한 경로로 찾음: {identifier}")
                return result
            
            # 3. 부분 경로로 검색 (첫 번째 결과 반환)
            results = self.search_by_partial_path(identifier)
            if results:
                logger.info(f"부분 경로로 찾음: {identifier} ({len(results)}개 발견)")
                return results[0]
            
            logger.warning(f"파일을 찾을 수 없음: {identifier}")
            return None
            
        except Exception as e:
            logger.error(f"안전한 파일 검색 실패: {e}")
            return None
    
    def close(self):
        """연결 종료"""
        try:
            self.client.close()
            logger.info("AnnotationManager: MongoDB 연결 종료")
        except Exception as e:
            logger.error(f"AnnotationManager: 연결 종료 중 에러 - {e}")
