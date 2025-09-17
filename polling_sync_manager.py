#!/usr/bin/env python3
"""
폴링 기반 MongoDB-JSON 양방향 동기화
Change Streams가 지원되지 않는 환경에서 주기적으로 MongoDB를 확인하여 JSON 파일 동기화
"""

import os
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Set
from pathlib import Path

import pymongo
from pymongo import MongoClient
from bson import ObjectId


class PollingBasedSyncManager:
    """폴링 기반 양방향 동기화 매니저"""
    
    def __init__(self, 
                 json_directory: str = None,
                 mongo_uri: str = "mongodb://localhost:27017/",
                 db_name: str = "labeling_db",
                 poll_interval: int = 5):
        """
        Args:
            json_directory: JSON 파일들이 저장된 디렉토리
            mongo_uri: MongoDB 연결 URI
            db_name: 데이터베이스 이름
            poll_interval: 폴링 간격 (초)
        """
        self.json_directory = json_directory or r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file"
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.poll_interval = poll_interval
        
        # MongoDB 연결
        self.client = None
        self.db = None
        self.annotations_collection = None
        self.images_collection = None
        
        # 폴링 관련
        self.polling_thread = None
        self.is_running = False
        
        # 동기화 상태 추적
        self._last_check_time = datetime.now()
        self._syncing_files: Set[str] = set()  # 현재 동기화 중인 파일들
        
        print(f"📁 JSON 디렉토리: {self.json_directory}")
        print(f"🔗 MongoDB URI: {self.mongo_uri}")
        print(f"💾 데이터베이스: {self.db_name}")
        print(f"⏰ 폴링 간격: {self.poll_interval}초")
    
    def connect_mongodb(self) -> bool:
        """MongoDB 연결"""
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.db_name]
            self.annotations_collection = self.db.annotations
            self.images_collection = self.db.images
            
            # 연결 테스트
            self.client.admin.command('ping')
            print("✅ MongoDB 연결 성공")
            return True
            
        except Exception as e:
            print(f"❌ MongoDB 연결 실패: {e}")
            return False
    
    def start_polling(self):
        """폴링 기반 동기화 시작"""
        if not self.connect_mongodb():
            return False
        
        self.is_running = True
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()
        
        print("🔄 폴링 기반 양방향 동기화 시작")
        print("📝 MongoDB 변경사항을 주기적으로 확인하여 JSON 파일 동기화")
        print("⏹️ 중지하려면 Ctrl+C를 누르세요")
        return True
    
    def _polling_loop(self):
        """폴링 메인 루프"""
        print(f"🔍 폴링 시작 (간격: {self.poll_interval}초)")
        
        while self.is_running:
            try:
                self._check_mongodb_changes()
                time.sleep(self.poll_interval)
            except Exception as e:
                print(f"⚠️ 폴링 오류: {e}")
                time.sleep(self.poll_interval)
    
    def _check_mongodb_changes(self):
        """MongoDB 변경사항 확인"""
        try:
            current_time = datetime.now()
            
            # 최근 업데이트된 어노테이션 조회
            # updated_at 필드가 있는 경우를 고려
            query = {
                "$or": [
                    {"updated_at": {"$gte": self._last_check_time}},
                    {"created_at": {"$gte": self._last_check_time}},
                    # updated_at이 없는 경우 ObjectId의 타임스탬프 사용
                    {"_id": {"$gte": ObjectId.from_datetime(self._last_check_time)}}
                ]
            }
            
            recent_annotations = list(self.annotations_collection.find(query))
            
            if recent_annotations:
                print(f"🔄 {len(recent_annotations)}개의 최근 변경사항 발견")
                
                # 영향받은 이미지들의 집합
                affected_images = set()
                for annotation in recent_annotations:
                    image_id = annotation.get('image_id')
                    if image_id:
                        affected_images.add(image_id)
                
                # 각 이미지의 JSON 파일 업데이트
                for image_id in affected_images:
                    self._sync_json_file(image_id)
            
            self._last_check_time = current_time
            
        except Exception as e:
            print(f"❌ MongoDB 변경사항 확인 오류: {e}")
    
    def _sync_json_file(self, image_id: str):
        """특정 이미지의 JSON 파일을 MongoDB 데이터와 동기화"""
        try:
            # 중복 동기화 방지
            if image_id in self._syncing_files:
                return
            
            self._syncing_files.add(image_id)
            
            try:
                # JSON 파일 경로 찾기
                json_path = self._find_json_file(image_id)
                if not json_path:
                    print(f"⚠️ JSON 파일을 찾을 수 없음: {image_id}")
                    return
                
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
                
                # MongoDB에서 최신 어노테이션 조회
                annotations = list(self.annotations_collection.find({
                    'image_id': image_id
                }).sort('created_at', 1))
                
                # MongoDB 어노테이션을 JSON shapes로 변환
                shapes = []
                for ann in annotations:
                    shape = self._annotation_to_shape(ann)
                    if shape:
                        shapes.append(shape)
                
                # JSON 파일이 실제로 변경되었는지 확인
                if json_data.get('shapes') != shapes:
                    # JSON 데이터 업데이트
                    json_data['shapes'] = shapes
                    
                    # JSON 파일 저장
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, indent=2, ensure_ascii=False)
                    
                    print(f"✅ JSON 파일 동기화: {os.path.basename(json_path)} ({len(shapes)}개 어노테이션)")
                
            finally:
                self._syncing_files.discard(image_id)
                
        except Exception as e:
            print(f"❌ JSON 파일 동기화 오류 ({image_id}): {e}")
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
        try:
            for filename in os.listdir(self.json_directory):
                if filename.endswith('.json'):
                    if os.path.splitext(filename)[0] == base_name:
                        return os.path.join(self.json_directory, filename)
        except Exception:
            pass
        
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
    
    def force_full_sync(self):
        """전체 동기화 강제 실행"""
        print("🔄 전체 JSON 파일 동기화 시작...")
        
        try:
            # 모든 이미지 ID 조회
            image_ids = self.annotations_collection.distinct('image_id')
            print(f"📊 총 {len(image_ids)}개 이미지 발견")
            
            success_count = 0
            for image_id in image_ids:
                try:
                    self._sync_json_file(image_id)
                    success_count += 1
                except Exception as e:
                    print(f"⚠️ {image_id} 동기화 실패: {e}")
            
            print(f"✅ 전체 동기화 완료: {success_count}/{len(image_ids)}개 성공")
            
        except Exception as e:
            print(f"❌ 전체 동기화 오류: {e}")
    
    def manual_sync_test(self, image_id: str):
        """특정 이미지의 수동 동기화 테스트"""
        print(f"🧪 수동 동기화 테스트: {image_id}")
        
        try:
            # 1. MongoDB에서 라벨 수정
            result = self.annotations_collection.update_one(
                {"image_id": image_id},
                {
                    "$set": {
                        "label": f"test_modified_{int(time.time())}",
                        "updated_at": datetime.now()
                    }
                }
            )
            
            if result.modified_count > 0:
                print("✅ MongoDB 데이터 수정 완료")
                
                # 2. JSON 파일 동기화
                self._sync_json_file(image_id)
                
                print("✅ 수동 동기화 테스트 완료")
                return True
            else:
                print("❌ MongoDB 수정 실패 - 해당 어노테이션이 없음")
                return False
                
        except Exception as e:
            print(f"❌ 수동 동기화 테스트 오류: {e}")
            return False
    
    def stop(self):
        """폴링 중지"""
        print("\n🛑 폴링 기반 동기화 중지...")
        self.is_running = False
        
        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=5)
        
        if self.client:
            self.client.close()
        
        print("✅ 동기화 중지 완료")


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="폴링 기반 MongoDB-JSON 양방향 동기화")
    parser.add_argument(
        "--directory", 
        default=r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file",
        help="JSON 파일 디렉토리"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="폴링 간격 (초)"
    )
    parser.add_argument(
        "--full-sync",
        action="store_true",
        help="시작 시 전체 동기화 실행"
    )
    parser.add_argument(
        "--test-sync",
        help="특정 이미지 ID의 동기화 테스트"
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.directory):
        print(f"❌ 디렉토리가 존재하지 않습니다: {args.directory}")
        return 1
    
    sync_manager = PollingBasedSyncManager(
        json_directory=args.directory,
        poll_interval=args.interval
    )
    
    try:
        if not sync_manager.connect_mongodb():
            return 1
        
        # 테스트 모드
        if args.test_sync:
            return 0 if sync_manager.manual_sync_test(args.test_sync) else 1
        
        # 전체 동기화
        if args.full_sync:
            sync_manager.force_full_sync()
        
        # 폴링 시작
        if not sync_manager.start_polling():
            return 1
        
        # 메인 스레드에서 대기
        while sync_manager.is_running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n👋 사용자가 중지 요청")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
    finally:
        sync_manager.stop()
    
    return 0


if __name__ == "__main__":
    exit(main())