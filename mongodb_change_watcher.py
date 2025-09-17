#!/usr/bin/env python3
"""
MongoDB Change Streams Watcher
MongoDB 데이터 변경을 감지하고 해당 JSON 파일을 자동 업데이트하여 양방향 동기화 구현
"""

import os
import json
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

import pymongo
from pymongo import MongoClient
from pymongo.errors import OperationFailure


class MongoDBChangeWatcher:
    """MongoDB Change Streams를 사용한 양방향 동기화"""
    
    def __init__(self, 
                 json_directory: str = None,
                 mongo_uri: str = "mongodb://localhost:27017/",
                 db_name: str = "labeling_db"):
        """
        Args:
            json_directory: JSON 파일들이 저장된 디렉토리
            mongo_uri: MongoDB 연결 URI
            db_name: 데이터베이스 이름
        """
        self.json_directory = json_directory or r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file"
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        
        # MongoDB 연결
        self.client = None
        self.db = None
        self.annotations_collection = None
        
        # Change Stream 관련
        self.change_stream = None
        self.watcher_thread = None
        self.is_running = False
        
        # 무한 루프 방지
        self._syncing_files = set()  # 현재 동기화 중인 파일들
        
        print(f"📁 JSON 디렉토리: {self.json_directory}")
        print(f"🔗 MongoDB URI: {self.mongo_uri}")
        print(f"💾 데이터베이스: {self.db_name}")
    
    def connect_mongodb(self) -> bool:
        """MongoDB 연결"""
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.db_name]
            self.annotations_collection = self.db.annotations
            
            # 연결 테스트
            self.client.admin.command('ping')
            print("✅ MongoDB 연결 성공")
            return True
            
        except Exception as e:
            print(f"❌ MongoDB 연결 실패: {e}")
            return False
    
    def start_watching(self):
        """Change Streams 감시 시작"""
        if not self.connect_mongodb():
            return False
        
        try:
            # Change Stream 시작 (insert, update, delete 모니터링)
            pipeline = [
                {
                    '$match': {
                        'operationType': {'$in': ['update', 'replace', 'delete']},
                        'ns.coll': 'annotations'
                    }
                }
            ]
            
            # Change Stream은 MongoDB 3.6+ 에서만 지원
            self.change_stream = self.annotations_collection.watch(pipeline)
            
            self.is_running = True
            self.watcher_thread = threading.Thread(target=self._watch_changes, daemon=True)
            self.watcher_thread.start()
            
            print("🔄 MongoDB Change Streams 감시 시작")
            print("📝 어노테이션 업데이트/삭제 시 자동으로 JSON 파일 동기화")
            print("⏹️ 중지하려면 Ctrl+C를 누르세요")
            return True
            
        except OperationFailure as e:
            print(f"❌ Change Streams 지원되지 않음 (MongoDB 3.6+ 필요): {e}")
            return False
        except Exception as e:
            print(f"❌ Change Streams 시작 실패: {e}")
            return False
    
    def _watch_changes(self):
        """Change Stream 이벤트 처리"""
        try:
            for change in self.change_stream:
                if not self.is_running:
                    break
                
                try:
                    self._handle_change_event(change)
                except Exception as e:
                    print(f"⚠️ 변경 이벤트 처리 오류: {e}")
                    
        except Exception as e:
            print(f"❌ Change Stream 감시 오류: {e}")
        finally:
            self.is_running = False
    
    def _handle_change_event(self, change: Dict[str, Any]):
        """개별 변경 이벤트 처리"""
        operation_type = change.get('operationType')
        
        if operation_type == 'update':
            self._handle_update(change)
        elif operation_type == 'replace':
            self._handle_replace(change)
        elif operation_type == 'delete':
            self._handle_delete(change)
    
    def _handle_update(self, change: Dict[str, Any]):
        """어노테이션 업데이트 처리"""
        try:
            # 업데이트된 document ID 가져오기
            doc_id = change['documentKey']['_id']
            
            # 최신 어노테이션 데이터 조회
            annotation = self.annotations_collection.find_one({'_id': doc_id})
            if not annotation:
                print(f"⚠️ 어노테이션을 찾을 수 없음: {doc_id}")
                return
            
            image_id = annotation.get('image_id')
            if not image_id:
                print(f"⚠️ image_id가 없는 어노테이션: {doc_id}")
                return
            
            # JSON 파일 업데이트
            self._update_json_file(image_id)
            print(f"🔄 MongoDB 변경 감지 → JSON 업데이트: {image_id}")
            
        except Exception as e:
            print(f"❌ 업데이트 처리 오류: {e}")
    
    def _handle_replace(self, change: Dict[str, Any]):
        """어노테이션 교체 처리 (update와 유사)"""
        self._handle_update(change)
    
    def _handle_delete(self, change: Dict[str, Any]):
        """어노테이션 삭제 처리"""
        try:
            # 삭제된 document의 image_id를 가져오기 위해 
            # fullDocument를 확인 (pre-image 설정 필요)
            full_document = change.get('fullDocument')
            if full_document and 'image_id' in full_document:
                image_id = full_document['image_id']
                self._update_json_file(image_id)
                print(f"🗑️ MongoDB 삭제 감지 → JSON 업데이트: {image_id}")
            else:
                print("⚠️ 삭제된 어노테이션의 image_id를 확인할 수 없음")
                
        except Exception as e:
            print(f"❌ 삭제 처리 오류: {e}")
    
    def _update_json_file(self, image_id: str):
        """특정 이미지의 JSON 파일을 MongoDB 데이터로 업데이트"""
        try:
            # 무한 루프 방지
            if image_id in self._syncing_files:
                print(f"⏭️ 이미 동기화 중인 파일: {image_id}")
                return
            
            self._syncing_files.add(image_id)
            
            try:
                # JSON 파일 경로 찾기
                json_path = self._find_json_file(image_id)
                if not json_path:
                    print(f"⚠️ JSON 파일을 찾을 수 없음: {image_id}")
                    return
                
                # MongoDB에서 해당 이미지의 모든 어노테이션 조회
                annotations = list(self.annotations_collection.find({
                    'image_id': image_id
                }))
                
                # 기존 JSON 파일 읽기
                if os.path.exists(json_path):
                    with open(json_path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                else:
                    # 기본 JSON 구조 생성
                    json_data = {
                        "version": "1.0.0",
                        "flags": {},
                        "shapes": [],
                        "imagePath": image_id,
                        "imageData": None,
                        "imageHeight": 0,
                        "imageWidth": 0
                    }
                
                # MongoDB 어노테이션을 JSON shapes 형식으로 변환
                shapes = []
                for ann in annotations:
                    shape = self._annotation_to_shape(ann)
                    if shape:
                        shapes.append(shape)
                
                # JSON 데이터 업데이트
                json_data['shapes'] = shapes
                json_data['imageData'] = None  # 이미지 데이터는 유지하지 않음
                
                # JSON 파일 저장
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
                
                print(f"✅ JSON 파일 업데이트 완료: {json_path}")
                
            finally:
                self._syncing_files.discard(image_id)
                
        except Exception as e:
            print(f"❌ JSON 파일 업데이트 오류: {e}")
            self._syncing_files.discard(image_id)
    
    def _find_json_file(self, image_id: str) -> Optional[str]:
        """이미지 ID에 해당하는 JSON 파일 찾기"""
        # 이미지 확장자를 json으로 변경
        base_name = os.path.splitext(image_id)[0]
        json_filename = f"{base_name}.json"
        json_path = os.path.join(self.json_directory, json_filename)
        
        if os.path.exists(json_path):
            return json_path
        
        # 대안: 디렉토리에서 유사한 이름의 JSON 파일 찾기
        for filename in os.listdir(self.json_directory):
            if filename.endswith('.json'):
                if os.path.splitext(filename)[0] == base_name:
                    return os.path.join(self.json_directory, filename)
        
        return None
    
    def _annotation_to_shape(self, annotation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """MongoDB 어노테이션을 JSON shape 형식으로 변환"""
        try:
            shape = {
                "label": annotation.get('label', ''),
                "points": annotation.get('points', []),
                "group_id": annotation.get('group_id'),
                "description": annotation.get('description', ''),
                "shape_type": annotation.get('shape_type', 'polygon'),
                "flags": annotation.get('flags', {}),
                "attributes": annotation.get('attributes', {})
            }
            
            # bbox가 있으면 points로 변환
            if 'bbox' in annotation and annotation['bbox']:
                bbox = annotation['bbox']
                if len(bbox) == 4:  # [x, y, width, height]
                    x, y, w, h = bbox
                    shape['points'] = [
                        [x, y],
                        [x + w, y],
                        [x + w, y + h],
                        [x, y + h]
                    ]
                    shape['shape_type'] = 'rectangle'
            
            return shape
            
        except Exception as e:
            print(f"❌ 어노테이션 변환 오류: {e}")
            return None
    
    def stop(self):
        """Change Stream 감시 중지"""
        print("\n🛑 MongoDB Change Streams 감시 중지...")
        self.is_running = False
        
        if self.change_stream:
            try:
                self.change_stream.close()
            except:
                pass
        
        if self.watcher_thread and self.watcher_thread.is_alive():
            self.watcher_thread.join(timeout=5)
        
        if self.client:
            self.client.close()
        
        print("✅ 감시 중지 완료")


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MongoDB Change Streams 양방향 동기화")
    parser.add_argument(
        "--directory", 
        default=r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file",
        help="JSON 파일 디렉토리"
    )
    parser.add_argument(
        "--mongo-uri",
        default="mongodb://localhost:27017/",
        help="MongoDB 연결 URI"
    )
    parser.add_argument(
        "--db-name",
        default="labeling_db",
        help="데이터베이스 이름"
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.directory):
        print(f"❌ 디렉토리가 존재하지 않습니다: {args.directory}")
        return 1
    
    watcher = MongoDBChangeWatcher(
        json_directory=args.directory,
        mongo_uri=args.mongo_uri,
        db_name=args.db_name
    )
    
    try:
        if not watcher.start_watching():
            return 1
        
        # 메인 스레드에서 대기
        while watcher.is_running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n👋 사용자가 중지 요청")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
    finally:
        watcher.stop()
    
    return 0


if __name__ == "__main__":
    exit(main())