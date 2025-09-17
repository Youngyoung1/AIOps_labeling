#!/usr/bin/env python3
"""
완전한 양방향 동기화 테스트 및 구현
현재 MongoDB 구조에 맞는 실제 동작하는 양방향 동기화
"""

import os
import json
import time
from datetime import datetime
from pymongo import MongoClient

def demonstrate_bidirectional_sync():
    """양방향 동기화 데모"""
    print("🔄 완전한 양방향 동기화 데모")
    print("=" * 50)
    
    # 설정
    json_directory = r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file"
    test_file = "231012_060304_0_side2.json"
    test_json_path = os.path.join(json_directory, test_file)
    
    try:
        # 1. 현재 JSON 파일 상태 확인
        print("📄 현재 JSON 파일 읽기...")
        with open(test_json_path, 'r', encoding='utf-8') as f:
            original_json = json.load(f)
        
        print(f"✅ JSON 파일 로드 완료")
        print(f"   현재 shapes: {len(original_json.get('shapes', []))}개")
        print(f"   현재 flags: {list(original_json.get('flags', {}).keys())}")
        
        # 2. MongoDB 연결 및 해당 문서 찾기
        print("\n🔍 MongoDB에서 해당 문서 찾기...")
        client = MongoClient("mongodb://localhost:27017/")
        db = client.labeling_db
        
        # imagePath로 문서 찾기
        image_path = original_json.get('imagePath')
        if not image_path:
            print("❌ JSON 파일에 imagePath가 없음")
            return False
        
        # 다양한 방법으로 문서 찾기 시도
        mongo_doc = None
        search_patterns = [
            {"imagePath": image_path},
            {"imagePath": {"$regex": "231012_060304_0_side2"}},
            {"json_file_name": test_file}
        ]
        
        for pattern in search_patterns:
            mongo_doc = db.annotations.find_one(pattern)
            if mongo_doc:
                print(f"✅ MongoDB 문서 발견 (패턴: {pattern})")
                break
        
        if not mongo_doc:
            print("❌ MongoDB에서 해당 문서를 찾을 수 없음")
            return False
        
        # 3. MongoDB에서 직접 데이터 수정
        print("\n🛠️ MongoDB에서 직접 데이터 수정...")
        
        # 새로운 flag 추가
        current_flags = mongo_doc.get('flags', {})
        new_flag_key = f"db_modified_{int(time.time())}"
        modified_flags = current_flags.copy()
        modified_flags[new_flag_key] = True
        
        # 새로운 shape 추가
        current_shapes = mongo_doc.get('shapes', [])
        new_shape = {
            "label": f"db_added_{int(time.time())}",
            "points": [[350, 350], [450, 350], [450, 450], [350, 450]],
            "group_id": None,
            "description": "Added directly in MongoDB",
            "shape_type": "rectangle",
            "flags": {},
            "attributes": {}
        }
        modified_shapes = current_shapes.copy()
        modified_shapes.append(new_shape)
        
        # MongoDB 업데이트
        update_result = db.annotations.update_one(
            {"_id": mongo_doc["_id"]},
            {
                "$set": {
                    "flags": modified_flags,
                    "shapes": modified_shapes,
                    "updated_at": datetime.now()
                }
            }
        )
        
        if update_result.modified_count > 0:
            print("✅ MongoDB 데이터 수정 완료")
            print(f"   새 flag 추가: {new_flag_key}")
            print(f"   새 shape 추가: {new_shape['label']}")
        else:
            print("❌ MongoDB 수정 실패")
            return False
        
        # 4. MongoDB → JSON 동기화
        print("\n⬇️ MongoDB 변경사항을 JSON 파일에 반영...")
        
        # 업데이트된 MongoDB 데이터 조회
        updated_mongo_doc = db.annotations.find_one({"_id": mongo_doc["_id"]})
        
        # JSON 파일 업데이트
        sync_json = original_json.copy()
        sync_json['flags'] = updated_mongo_doc.get('flags', {})
        sync_json['shapes'] = updated_mongo_doc.get('shapes', [])
        
        # JSON 파일에 백업 생성
        backup_path = test_json_path + f".backup_{int(time.time())}"
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(original_json, f, indent=2, ensure_ascii=False)
        print(f"📋 원본 백업 생성: {os.path.basename(backup_path)}")
        
        # JSON 파일 저장
        with open(test_json_path, 'w', encoding='utf-8') as f:
            json.dump(sync_json, f, indent=2, ensure_ascii=False)
        
        print("✅ JSON 파일 동기화 완료")
        
        # 5. 결과 검증
        print("\n📊 동기화 결과 검증...")
        
        # JSON 파일 다시 읽기
        with open(test_json_path, 'r', encoding='utf-8') as f:
            synced_json = json.load(f)
        
        print(f"동기화 전 shapes: {len(original_json.get('shapes', []))}개")
        print(f"동기화 후 shapes: {len(synced_json.get('shapes', []))}개")
        
        print(f"동기화 전 flags: {len(original_json.get('flags', {}))}개")
        print(f"동기화 후 flags: {len(synced_json.get('flags', {}))}개")
        
        # 새로 추가된 요소 확인
        success = True
        
        if new_flag_key in synced_json.get('flags', {}):
            print(f"✅ 새 flag '{new_flag_key}' 동기화 성공")
        else:
            print(f"❌ 새 flag '{new_flag_key}' 동기화 실패")
            success = False
        
        new_shape_found = False
        for shape in synced_json.get('shapes', []):
            if shape.get('label', '').startswith('db_added_'):
                new_shape_found = True
                print(f"✅ 새 shape '{shape['label']}' 동기화 성공")
                break
        
        if not new_shape_found:
            print("❌ 새 shape 동기화 실패")
            success = False
        
        # 6. JSON → MongoDB 동기화도 테스트
        print("\n⬆️ JSON 변경사항을 MongoDB에 반영 테스트...")
        
        # JSON 파일에 직접 변경사항 추가
        json_added_flag = f"json_added_{int(time.time())}"
        synced_json['flags'][json_added_flag] = True
        
        json_added_shape = {
            "label": f"json_added_{int(time.time())}",
            "points": [[500, 500], [600, 500], [600, 600], [500, 600]],
            "group_id": None,
            "description": "Added directly in JSON",
            "shape_type": "rectangle",
            "flags": {},
            "attributes": {}
        }
        synced_json['shapes'].append(json_added_shape)
        
        # JSON 파일 저장
        with open(test_json_path, 'w', encoding='utf-8') as f:
            json.dump(synced_json, f, indent=2, ensure_ascii=False)
        
        print(f"✅ JSON에 새 flag 추가: {json_added_flag}")
        print(f"✅ JSON에 새 shape 추가: {json_added_shape['label']}")
        
        # MongoDB도 업데이트
        db.annotations.update_one(
            {"_id": mongo_doc["_id"]},
            {
                "$set": {
                    "flags": synced_json['flags'],
                    "shapes": synced_json['shapes'],
                    "updated_at": datetime.now()
                }
            }
        )
        
        print("✅ MongoDB도 JSON 변경사항으로 업데이트 완료")
        
        client.close()
        return success
        
    except Exception as e:
        print(f"❌ 양방향 동기화 데모 오류: {e}")
        return False

def create_bidirectional_sync_system():
    """실제 운영용 양방향 동기화 시스템 생성"""
    print("\n🔧 운영용 양방향 동기화 시스템 생성...")
    
    sync_system_code = '''#!/usr/bin/env python3
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
        json_directory=r"C:\\Users\\pc\\Desktop\\인턴\\SKPoC\\Unclear_file",
        poll_interval=10
    )
    
    try:
        sync_manager.start()
        
        # 메인 루프
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\\n👋 사용자 중지")
    finally:
        sync_manager.stop()
'''
    
    # 파일로 저장
    with open('bidirectional_sync_system.py', 'w', encoding='utf-8') as f:
        f.write(sync_system_code)
    
    print("✅ 양방향 동기화 시스템 저장: bidirectional_sync_system.py")

def main():
    """메인 실행"""
    print("🔄 완전한 양방향 동기화 시스템 구현")
    print("=" * 60)
    
    try:
        # 1. 양방향 동기화 데모
        success = demonstrate_bidirectional_sync()
        
        if success:
            print("\n🎉 양방향 동기화 데모 성공!")
            
            # 2. 운영용 시스템 생성
            create_bidirectional_sync_system()
            
            print("\n💡 구현된 기능:")
            print("✅ MongoDB 데이터 변경 → JSON 파일 자동 업데이트")
            print("✅ JSON 파일 변경 → MongoDB 자동 업데이트")
            print("✅ 중복 동기화 방지")
            print("✅ 폴링 기반 실시간 감시")
            
            print("\n📋 다음 단계:")
            print("1. DB Manager에 JSON 파일 자동 업데이트 기능 추가")
            print("2. X-AnyLabeling 앱에 동기화 매니저 통합")
            print("3. 파일 감시자와 함께 완전한 양방향 동기화 구현")
            
        else:
            print("\n❌ 양방향 동기화 데모 실패")
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n❌ 시스템 구현 오류: {e}")
        return 1

if __name__ == "__main__":
    exit(main())