"""
NAS MongoDB 관리 도구
모든 클라이언트에서 NAS의 MongoDB를 쉽게 관리할 수 있는 유틸리티
"""

import os
import sys
import json
from typing import Dict, List, Any
from datetime import datetime

# 현재 스크립트의 상위 디렉토리를 path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from anylabeling.services.storage.mongodb_client import NASMongoConfig, MongoStorage

class NASMongoManager:
    """NAS MongoDB 관리 클래스"""
    
    def __init__(self):
        self.nas_ip = os.getenv('NAS_MONGODB_SERVER', '')
        self.uri = os.getenv('MONGODB_URI', '')
        self.storage = None
        
    def detect_nas_servers(self) -> List[str]:
        """NAS MongoDB 서버 자동 감지"""
        print("네트워크에서 MongoDB 서버를 찾는 중...")
        servers = NASMongoConfig.detect_nas_mongodb_servers()
        
        if not servers:
            print("❌ MongoDB 서버를 찾을 수 없습니다.")
            return []
        
        print(f"✅ {len(servers)}개의 MongoDB 서버를 발견했습니다:")
        for i, server in enumerate(servers, 1):
            print(f"  {i}. {server}")
        
        return servers
    
    def setup_connection(self, server_ip: str, username: str = "labeling_user", 
                        password: str = "labeling_password") -> bool:
        """NAS 연결 설정"""
        uri = NASMongoConfig.create_nas_uri(server_ip, username, password)
        
        print(f"연결 테스트: {server_ip}")
        result = NASMongoConfig.test_nas_connection(uri)
        
        if result['success']:
            print("✅ 연결 성공!")
            print(f"  서버 버전: {result['server_version']}")
            print(f"  데이터베이스: {result['databases']}")
            
            # 환경변수 설정
            os.environ['MONGODB_URI'] = uri
            os.environ['NAS_MONGODB_SERVER'] = server_ip
            
            # 시스템 환경변수로도 설정 (Windows)
            if sys.platform == 'win32':
                os.system(f'setx MONGODB_URI "{uri}"')
                os.system(f'setx NAS_MONGODB_SERVER "{server_ip}"')
            
            self.uri = uri
            self.nas_ip = server_ip
            self.storage = MongoStorage(uri=uri)
            
            return True
        else:
            print("❌ 연결 실패!")
            print(f"  오류: {result['error']}")
            return False
    
    def get_database_status(self) -> Dict[str, Any]:
        """데이터베이스 상태 조회"""
        if not self.storage:
            return {"error": "연결되지 않음"}
        
        try:
            stats = self.storage.get_database_stats()
            connection_test = self.storage.test_connection()
            
            return {
                "connected": connection_test,
                "server": self.nas_ip,
                "uri": self.uri,
                "stats": stats,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}
    
    def backup_database(self, backup_path: str) -> bool:
        """데이터베이스 백업"""
        if not self.storage:
            print("❌ 데이터베이스에 연결되지 않았습니다.")
            return False
        
        try:
            print("데이터베이스 백업 중...")
            
            # 어노테이션 데이터 백업
            annotations = self.storage.find_annotations()
            images = list(self.storage.images.find())
            flags = self.storage.find_flags()
            
            backup_data = {
                "backup_date": datetime.now().isoformat(),
                "server": self.nas_ip,
                "annotations": annotations,
                "images": images,
                "flags": flags
            }
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, default=str, indent=2, ensure_ascii=False)
            
            print(f"✅ 백업 완료: {backup_path}")
            return True
            
        except Exception as e:
            print(f"❌ 백업 실패: {e}")
            return False
    
    def sync_check(self) -> Dict[str, Any]:
        """다른 클라이언트와 동기화 상태 확인"""
        if not self.storage:
            return {"error": "연결되지 않음"}
        
        try:
            # 최근 활동 조회
            recent_annotations = list(self.storage.annotations.find().sort("created_at", -1).limit(10))
            recent_images = list(self.storage.images.find().sort("uploaded_at", -1).limit(10))
            
            return {
                "recent_annotations": len(recent_annotations),
                "recent_images": len(recent_images),
                "last_annotation": recent_annotations[0].get('created_at') if recent_annotations else None,
                "last_image": recent_images[0].get('uploaded_at') if recent_images else None
            }
        except Exception as e:
            return {"error": str(e)}

def main():
    """메인 함수"""
    manager = NASMongoManager()
    
    print("=== NAS MongoDB 관리 도구 ===")
    print()
    
    while True:
        print("1. NAS 서버 자동 감지")
        print("2. 연결 설정")
        print("3. 데이터베이스 상태 확인")
        print("4. 데이터베이스 백업")
        print("5. 동기화 상태 확인")
        print("0. 종료")
        print()
        
        choice = input("선택: ").strip()
        
        if choice == '1':
            servers = manager.detect_nas_servers()
            if servers:
                print("\n자동 연결을 시도하려면 2번을 선택하세요.")
        
        elif choice == '2':
            server_ip = input("NAS 서버 IP: ").strip()
            if server_ip:
                username = input("사용자명 (기본: labeling_user): ").strip() or "labeling_user"
                password = input("비밀번호 (기본: labeling_password): ").strip() or "labeling_password"
                manager.setup_connection(server_ip, username, password)
        
        elif choice == '3':
            status = manager.get_database_status()
            print(json.dumps(status, indent=2, ensure_ascii=False, default=str))
        
        elif choice == '4':
            backup_path = input("백업 파일 경로: ").strip()
            if backup_path:
                manager.backup_database(backup_path)
        
        elif choice == '5':
            sync_status = manager.sync_check()
            print(json.dumps(sync_status, indent=2, ensure_ascii=False, default=str))
        
        elif choice == '0':
            break
        
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()