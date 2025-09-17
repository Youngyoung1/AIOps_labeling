#!/usr/bin/env python3
"""간단한 불필요한 파일 정리 스크립트"""

import sys
import os

# 현재 디렉토리를 path에 추가
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join('anylabeling', 'services'))

from annotation_manager import AnnotationManager

def cleanup_db():
    """DB에서 불필요한 파일들 정리"""
    try:
        print("🧹 MongoDB 불필요한 파일 정리 시작...")
        
        # AnnotationManager 초기화
        am = AnnotationManager()
        collection = am.collection
        
        # 1. 전체 문서 수 확인
        total_count = collection.count_documents({})
        print(f"📊 전체 문서 수: {total_count}개")
        
        # 2. 알 수 없는 파일들 찾기 (imagePath가 없거나 null인 경우)
        print("\n🔍 알 수 없는 파일 검색 중...")
        unknown_query = {
            "$or": [
                {"imagePath": {"$exists": False}},
                {"imagePath": None},
                {"imagePath": ""},
                {"imagePath": "None"}
            ]
        }
        
        unknown_docs = list(collection.find(unknown_query))
        unknown_count = len(unknown_docs)
        
        print(f"❓ 알 수 없는 파일: {unknown_count}개")
        if unknown_count > 0:
            print("   샘플:")
            for i, doc in enumerate(unknown_docs[:3]):
                image_path = doc.get('imagePath', 'N/A')
                json_name = doc.get('json_file_name', 'N/A')
                print(f"   - JSON: {json_name}, imagePath: {image_path}")
        
        # 3. 모든 imagePath 가져오기 (null이 아닌 것만)
        print("\n🔍 파일 확장자 분석 중...")
        docs_with_paths = list(collection.find({
            "imagePath": {
                "$exists": True,
                "$ne": None,
                "$ne": "",
                "$ne": "None"
            }
        }, {"imagePath": 1, "json_file_name": 1}))
        
        # 4. Python으로 확장자 분석
        extension_stats = {}
        non_image_files = []
        
        allowed_extensions = ['.png', '.jpg', '.jpeg']
        
        for doc in docs_with_paths:
            image_path = doc.get('imagePath', '')
            if isinstance(image_path, str) and image_path:
                # 확장자 추출
                path_lower = image_path.lower()
                extension = None
                for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff', '.svg']:
                    if path_lower.endswith(ext):
                        extension = ext
                        break
                
                if not extension:
                    extension = 'unknown'
                
                # 통계 수집
                if extension not in extension_stats:
                    extension_stats[extension] = []
                extension_stats[extension].append(doc)
                
                # PNG, JPG가 아닌 파일 수집
                if not any(path_lower.endswith(ext) for ext in allowed_extensions):
                    non_image_files.append(doc)
        
        # 5. 확장자별 통계 출력
        print("\n📂 확장자별 분석:")
        for ext, docs in sorted(extension_stats.items(), key=lambda x: len(x[1]), reverse=True):
            count = len(docs)
            if ext in allowed_extensions:
                print(f"   ✅ {ext}: {count}개 (유지)")
            else:
                print(f"   ❌ {ext}: {count}개 (삭제 대상)")
                # 샘플 표시
                for doc in docs[:2]:
                    json_name = doc.get('json_file_name', 'N/A')
                    image_path = doc.get('imagePath', 'N/A')
                    print(f"      - {json_name} → {image_path}")
        
        non_image_count = len(non_image_files)
        total_to_delete = unknown_count + non_image_count
        
        print(f"\n📊 삭제 예정:")
        print(f"   ❓ 알 수 없는 파일: {unknown_count}개")
        print(f"   ❌ PNG/JPG가 아닌 파일: {non_image_count}개")
        print(f"   🗑️ 총 삭제 예정: {total_to_delete}개")
        print(f"   ✅ 유지될 파일: {total_count - total_to_delete}개")
        
        if total_to_delete == 0:
            print("\n✅ 삭제할 파일이 없습니다!")
            am.close()
            return
        
        # 6. 사용자 확인
        print(f"\n⚠️  정말로 {total_to_delete}개의 파일을 삭제하시겠습니까?")
        response = input("삭제하려면 'DELETE'를 입력하세요: ")
        
        if response != 'DELETE':
            print("❌ 삭제가 취소되었습니다.")
            am.close()
            return
        
        # 7. 실제 삭제 수행
        print("\n🗑️ 삭제 시작...")
        total_deleted = 0
        
        # 알 수 없는 파일들 삭제
        if unknown_count > 0:
            result1 = collection.delete_many(unknown_query)
            total_deleted += result1.deleted_count
            print(f"   ✅ 알 수 없는 파일 {result1.deleted_count}개 삭제")
        
        # PNG, JPG가 아닌 파일들 삭제
        if non_image_count > 0:
            # ID 기반으로 삭제 (더 안전함)
            non_image_ids = [doc['_id'] for doc in non_image_files]
            result2 = collection.delete_many({"_id": {"$in": non_image_ids}})
            total_deleted += result2.deleted_count
            print(f"   ✅ PNG/JPG가 아닌 파일 {result2.deleted_count}개 삭제")
        
        # 8. 결과 확인
        remaining_count = collection.count_documents({})
        print(f"\n📊 정리 완료:")
        print(f"   🗑️ 삭제된 파일: {total_deleted}개")
        print(f"   ✅ 남은 파일: {remaining_count}개")
        
        # 9. 남은 파일들의 확장자 확인
        print(f"\n📂 남은 파일들 확인:")
        remaining_docs = list(collection.find({
            "imagePath": {
                "$exists": True,
                "$ne": None,
                "$ne": ""
            }
        }, {"imagePath": 1}).limit(10))
        
        remaining_extensions = {}
        for doc in remaining_docs:
            image_path = doc.get('imagePath', '')
            if isinstance(image_path, str) and image_path:
                path_lower = image_path.lower()
                for ext in ['.png', '.jpg', '.jpeg']:
                    if path_lower.endswith(ext):
                        if ext not in remaining_extensions:
                            remaining_extensions[ext] = 0
                        remaining_extensions[ext] += 1
                        break
        
        for ext, count in remaining_extensions.items():
            print(f"   📄 {ext}: {count}개")
        
        am.close()
        print(f"\n🎉 정리 완료! 이제 PNG, JPG 파일만 남았습니다.")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    cleanup_db()
