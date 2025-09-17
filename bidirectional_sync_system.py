#!/usr/bin/env python3
"""
운영용 양방향 동기화 시스템
MongoDB ↔ JSON 파일 간의 실시간 동기화
"""

import os
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Set, Optional
from pymongo import MongoClient

class BidirectionalSyncManager:
    """양방향 동기화 관리자"""
    
    def __init__(self, json_directory: str, poll_interval: int = 10):
        self.json_directory = json_directory
        self.poll_interval = poll_interval
        self.client = MongoClient("mongodb://localhost:27017/")
        self.db = self.client.labeling_db
        
        # 동기화 상태 추적
        self._last_check = datetime.now()
        self._syncing_files: Set[str] = set()
        self._file_timestamps: Dict[str, datetime] = {}
        
        # 폴링 스레드
        self._polling_thread = None
        self._is_running = False
    
    def start(self):
        """동기화 시작"""
        print(f"🔄 양방향 동기화 시작 (간격: {self.poll_interval}초)")
        self._is_running = True
        self._polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self._polling_thread.start()
    
    def stop(self):
        """동기화 중지"""
        print("🛑 양방향 동기화 중지...")
        self._is_running = False
        if self._polling_thread:
            self._polling_thread.join(timeout=5)
        self.client.close()
    
    def _polling_loop(self):
        """폴링 메인 루프"""
        while self._is_running:
            try:
                self._sync_mongodb_to_json()
                time.sleep(self.poll_interval)
            except Exception as e:
                print(f"⚠️ 폴링 오류: {e}")
                time.sleep(self.poll_interval)
    
    def _sync_mongodb_to_json(self):
        """MongoDB 변경사항을 JSON 파일에 동기화"""
        try:
            # 최근 업데이트된 MongoDB 문서들 찾기
            recent_docs = list(self.db.annotations.find({
                "updated_at": {"$gte": self._last_check}
            }))
            
            if recent_docs:
                print(f"🔄 {len(recent_docs)}개 문서의 MongoDB 변경사항 감지")
                
                for doc in recent_docs:
                    json_file_name = doc.get('json_file_name')
                    if json_file_name:
                        self._update_json_from_mongodb(json_file_name, doc)
            
            self._last_check = datetime.now()
            
        except Exception as e:
            print(f"❌ MongoDB → JSON 동기화 오류: {e}")
    
    def _update_json_from_mongodb(self, json_filename: str, mongo_doc: dict):
        """MongoDB 문서를 기반으로 JSON 파일 업데이트"""
        json_path = os.path.join(self.json_directory, json_filename)
        
        if not os.path.exists(json_path):
            return
        
        if json_filename in self._syncing_files:
            return
        
        try:
            self._syncing_files.add(json_filename)
            
            # 현재 JSON 파일 읽기
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # MongoDB 데이터로 업데이트
            json_data['flags'] = mongo_doc.get('flags', {})
            json_data['shapes'] = mongo_doc.get('shapes', [])
            
            # JSON 파일 저장
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ JSON 파일 업데이트: {json_filename}")
            
        except Exception as e:
            print(f"❌ JSON 파일 업데이트 오류 ({json_filename}): {e}")
        finally:
            self._syncing_files.discard(json_filename)
    
    def sync_json_to_mongodb(self, json_filename: str):
        """JSON 파일 변경사항을 MongoDB에 동기화"""
        json_path = os.path.join(self.json_directory, json_filename)
        
        if not os.path.exists(json_path):
            return False
        
        try:
            # JSON 파일 읽기
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # MongoDB 문서 찾기 및 업데이트
            image_path = json_data.get('imagePath')
            if image_path:
                result = self.db.annotations.update_one(
                    {"imagePath": {"$regex": os.path.splitext(os.path.basename(image_path))[0]}},
                    {
                        "$set": {
                            "flags": json_data.get('flags', {}),
                            "shapes": json_data.get('shapes', []),
                            "updated_at": datetime.now()
                        }
                    }
                )
                
                if result.modified_count > 0:
                    print(f"✅ MongoDB 업데이트: {json_filename}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"❌ JSON → MongoDB 동기화 오류 ({json_filename}): {e}")
            return False

# 사용 예시
if __name__ == "__main__":
    sync_manager = BidirectionalSyncManager(
        json_directory=r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file",
        poll_interval=10
    )
    
    try:
        sync_manager.start()
        
        # 메인 루프
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n👋 사용자 중지")
    finally:
        sync_manager.stop()
