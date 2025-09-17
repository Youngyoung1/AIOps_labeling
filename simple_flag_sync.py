#!/usr/bin/env python3
"""
간단한 플래그 기반 동기화 도구
- MongoDB 변경사항에 플래그를 설정하고
- 백그라운드에서 자동으로 JSON 파일로 동기화
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime

# X-AnyLabeling 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
anylabeling_dir = os.path.join(current_dir, 'anylabeling')
sys.path.insert(0, current_dir)

from anylabeling.services.annotation_manager import AnnotationManager


class SimpleFlagSync:
    """간단한 플래그 기반 동기화"""
    
    def __init__(self):
        self.annotation_manager = AnnotationManager()
        self.sync_flag = 'sync_needed'
        
    def mark_all_for_sync(self, directory_filter: str = None):
        """모든 파일을 동기화 대상으로 표시"""
        try:
            query = {}
            if directory_filter:
                query['json_file_path'] = {'$regex': directory_filter.replace('\\', '/')}
                
            result = self.annotation_manager.collection.update_many(
                query,
                {
                    '$set': {
                        self.sync_flag: True,
                        'sync_marked_time': datetime.now()
                    }
                }
            )
            
            print(f"🚩 {result.modified_count}개 파일에 동기화 플래그 설정됨")
            return result.modified_count
            
        except Exception as e:
            print(f"❌ 플래그 설정 실패: {e}")
            return 0
            
    def mark_specific_files(self, file_patterns: list):
        """특정 파일들을 동기화 대상으로 표시"""
        marked_count = 0
        
        for pattern in file_patterns:
            try:
                query = {'json_file_path': {'$regex': pattern}}
                
                result = self.annotation_manager.collection.update_many(
                    query,
                    {
                        '$set': {
                            self.sync_flag: True,
                            'sync_marked_time': datetime.now()
                        }
                    }
                )
                
                print(f"🚩 패턴 '{pattern}': {result.modified_count}개 파일 플래그 설정")
                marked_count += result.modified_count
                
            except Exception as e:
                print(f"❌ 패턴 '{pattern}' 플래그 설정 실패: {e}")
                
        return marked_count
        
    def sync_flagged_to_json(self, batch_size: int = 10):
        """플래그된 파일들을 JSON으로 동기화"""
        try:
            # 플래그된 문서들 조회
            flagged_docs = list(self.annotation_manager.collection.find({
                self.sync_flag: True
            }).limit(batch_size))
            
            if not flagged_docs:
                print("📊 동기화할 플래그된 파일이 없습니다")
                return 0
                
            print(f"🔄 {len(flagged_docs)}개 플래그된 파일 동기화 시작...")
            
            success_count = 0
            
            for doc in flagged_docs:
                json_file_path = doc.get('json_file_path', '')
                
                if not json_file_path or not os.path.exists(json_file_path):
                    print(f"⚠️ JSON 파일이 존재하지 않음: {json_file_path}")
                    continue
                    
                # MongoDB → JSON 동기화
                if self._sync_single_mongodb_to_json(doc, json_file_path):
                    success_count += 1
                    
                    # 플래그 제거
                    self.annotation_manager.collection.update_one(
                        {'_id': doc['_id']},
                        {
                            '$unset': {self.sync_flag: ""},
                            '$set': {'last_synced': datetime.now()}
                        }
                    )
                    
                    print(f"✅ 동기화 완료: {os.path.basename(json_file_path)}")
                else:
                    print(f"❌ 동기화 실패: {os.path.basename(json_file_path)}")
                    
            print(f"🎯 동기화 결과: {success_count}/{len(flagged_docs)}개 성공")
            return success_count
            
        except Exception as e:
            print(f"❌ 플래그된 파일 동기화 실패: {e}")
            return 0
            
    def _sync_single_mongodb_to_json(self, mongodb_doc: dict, json_file_path: str) -> bool:
        """단일 파일 MongoDB → JSON 동기화"""
        try:
            # 백업 생성
            backup_path = f"{json_file_path}.backup_{int(time.time())}"
            import shutil
            shutil.copy2(json_file_path, backup_path)
            
            # JSON 파일 읽기
            with open(json_file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                
            # MongoDB 데이터로 업데이트
            json_data['flags'] = mongodb_doc.get('flags', {})
            json_data['shapes'] = mongodb_doc.get('shapes', [])
            json_data['description'] = mongodb_doc.get('description', '')
            
            # 동기화 메타데이터 추가
            if 'flags' not in json_data:
                json_data['flags'] = {}
            json_data['flags']['last_synced_from_mongodb'] = datetime.now().isoformat()
            
            # JSON 파일 쓰기
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
                
            # 오래된 백업 정리 (최근 3개만 유지)
            self._cleanup_old_backups(json_file_path)
            
            return True
            
        except Exception as e:
            print(f"❌ 파일 동기화 실패: {e}")
            return False
            
    def _cleanup_old_backups(self, json_file_path: str):
        """오래된 백업 파일 정리"""
        try:
            directory = os.path.dirname(json_file_path)
            filename = os.path.basename(json_file_path)
            
            # 백업 파일들 찾기
            backup_files = []
            for file in os.listdir(directory):
                if file.startswith(f"{filename}.backup_"):
                    backup_path = os.path.join(directory, file)
                    backup_files.append((backup_path, os.path.getmtime(backup_path)))
                    
            # 시간순 정렬 (최신 순)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # 3개 초과 시 오래된 것 삭제
            for backup_path, _ in backup_files[3:]:
                os.remove(backup_path)
                
        except Exception as e:
            print(f"⚠️ 백업 정리 실패: {e}")
            
    def get_flagged_count(self) -> int:
        """플래그된 파일 개수 반환"""
        try:
            return self.annotation_manager.collection.count_documents({
                self.sync_flag: True
            })
        except Exception:
            return 0
            
    def clear_all_flags(self):
        """모든 동기화 플래그 제거"""
        try:
            result = self.annotation_manager.collection.update_many(
                {self.sync_flag: {'$exists': True}},
                {'$unset': {self.sync_flag: ""}}
            )
            
            print(f"🧹 {result.modified_count}개 동기화 플래그 제거됨")
            return result.modified_count
            
        except Exception as e:
            print(f"❌ 플래그 제거 실패: {e}")
            return 0
            
    def update_mongodb_field(self, file_pattern: str, field_updates: dict):
        """MongoDB 필드 직접 업데이트 (테스트용)"""
        try:
            query = {'json_file_path': {'$regex': file_pattern}}
            
            # 업데이트에 동기화 플래그도 추가
            update_data = {**field_updates}
            update_data[self.sync_flag] = True
            update_data['sync_marked_time'] = datetime.now()
            
            result = self.annotation_manager.collection.update_many(
                query,
                {'$set': update_data}
            )
            
            print(f"🔄 패턴 '{file_pattern}': {result.modified_count}개 문서 업데이트됨")
            return result.modified_count
            
        except Exception as e:
            print(f"❌ MongoDB 업데이트 실패: {e}")
            return 0


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="간단한 플래그 기반 동기화 도구")
    parser.add_argument('action', choices=[
        'mark-all', 'mark-files', 'sync', 'clear', 'status', 'update-test'
    ], help="실행할 동작")
    
    parser.add_argument('--directory', '-d', type=str, 
                       help="대상 디렉토리 (mark-all용)")
    parser.add_argument('--patterns', '-p', nargs='+', 
                       help="파일 패턴들 (mark-files용)")
    parser.add_argument('--batch-size', '-b', type=int, default=10,
                       help="배치 크기 (sync용)")
    
    args = parser.parse_args()
    
    sync_tool = SimpleFlagSync()
    
    if args.action == 'mark-all':
        print("🚩 모든 파일에 동기화 플래그 설정...")
        count = sync_tool.mark_all_for_sync(args.directory)
        print(f"✅ 완료: {count}개 파일")
        
    elif args.action == 'mark-files':
        if not args.patterns:
            print("❌ --patterns 옵션이 필요합니다")
            return
            
        print(f"🚩 특정 파일들에 동기화 플래그 설정...")
        count = sync_tool.mark_specific_files(args.patterns)
        print(f"✅ 완료: {count}개 파일")
        
    elif args.action == 'sync':
        print(f"🔄 플래그된 파일들 동기화 시작 (배치 크기: {args.batch_size})...")
        count = sync_tool.sync_flagged_to_json(args.batch_size)
        print(f"✅ 완료: {count}개 파일 동기화됨")
        
    elif args.action == 'clear':
        print("🧹 모든 동기화 플래그 제거...")
        count = sync_tool.clear_all_flags()
        print(f"✅ 완료: {count}개 플래그 제거됨")
        
    elif args.action == 'status':
        flagged_count = sync_tool.get_flagged_count()
        print(f"📊 현재 상태:")
        print(f"   플래그된 파일: {flagged_count}개")
        
    elif args.action == 'update-test':
        # 테스트용 MongoDB 업데이트
        test_pattern = r"C:/Users/pc/Desktop/인턴/SKPoC/Unclear_file"
        test_updates = {
            'flags.test_update': True,
            'flags.update_time': datetime.now().isoformat(),
            'description': f"플래그 동기화 테스트 - {datetime.now().strftime('%H:%M:%S')}"
        }
        
        print("🧪 테스트용 MongoDB 업데이트...")
        count = sync_tool.update_mongodb_field(test_pattern, test_updates)
        print(f"✅ 완료: {count}개 문서 업데이트됨")


if __name__ == '__main__':
    print("🔄 간단한 플래그 기반 동기화 도구")
    print("=" * 50)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 사용자에 의해 중단됨")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        
    print("=" * 50)