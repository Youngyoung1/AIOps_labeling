#!/usr/bin/env python3
"""이미지 경로 정리 및 최적화 스크립트"""

import sys
import os
import json
from datetime import datetime

# 현재 디렉토리를 path에 추가
sys.path.insert(0, os.getcwd())

def fix_missing_paths():
    """누락된 이미지 경로 정보 보완"""
    try:
        # AnnotationManager import
        sys.path.insert(0, os.path.join('anylabeling', 'services'))
        from annotation_manager import AnnotationManager
        
        print("🔧 이미지 경로 정보 보완 시작")
        print("=" * 60)
        
        # MongoDB 연결
        am = AnnotationManager()
        
        # 문제가 있는 문서들 조회
        problematic_docs = list(am.collection.find({
            "$or": [
                {"image_file_path": {"$exists": False}},
                {"image_file_path": ""},
                {"image_file_path": None},
                {"image_exists": {"$exists": False}}
            ]
        }))
        
        print(f"📊 보완 대상: {len(problematic_docs)}개 문서")
        
        fixed_count = 0
        not_found_count = 0
        
        for doc in problematic_docs:
            try:
                doc_id = doc.get('_id')
                json_file_path = doc.get('json_file_path', '')
                image_path = doc.get('imagePath', '')
                
                print(f"\n🔍 처리 중: {doc.get('json_file_name', 'N/A')}")
                
                # 이미지 파일 경로 추정
                estimated_image_path = ""
                image_exists = False
                
                if json_file_path and image_path:
                    # JSON 파일과 같은 디렉토리에서 이미지 찾기
                    json_dir = os.path.dirname(json_file_path)
                    estimated_image_path = os.path.join(json_dir, image_path)
                    estimated_image_path = os.path.abspath(estimated_image_path)
                    
                    if os.path.exists(estimated_image_path):
                        image_exists = True
                        print(f"  ✅ 이미지 발견: {estimated_image_path}")
                    else:
                        print(f"  ❌ 이미지 없음: {estimated_image_path}")
                
                # 다른 확장자도 시도
                if not image_exists and json_file_path and image_path:
                    json_dir = os.path.dirname(json_file_path)
                    image_name_without_ext = os.path.splitext(image_path)[0]
                    
                    # 일반적인 이미지 확장자들
                    extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
                    
                    for ext in extensions:
                        test_path = os.path.join(json_dir, image_name_without_ext + ext)
                        if os.path.exists(test_path):
                            estimated_image_path = os.path.abspath(test_path)
                            image_exists = True
                            print(f"  ✅ 다른 확장자로 발견: {estimated_image_path}")
                            break
                
                # MongoDB 업데이트
                update_data = {
                    "image_file_path": estimated_image_path,
                    "image_file_name": os.path.basename(estimated_image_path) if estimated_image_path else "",
                    "image_directory": os.path.dirname(estimated_image_path) if estimated_image_path else "",
                    "image_relative_path": os.path.relpath(estimated_image_path) if estimated_image_path else "",
                    "image_exists": image_exists,
                    "same_directory": True if json_file_path and estimated_image_path and os.path.dirname(json_file_path) == os.path.dirname(estimated_image_path) else False,
                    "image_extension": os.path.splitext(estimated_image_path)[1].lower() if estimated_image_path else "",
                    "updated_at": datetime.now()
                }
                
                result = am.collection.update_one(
                    {"_id": doc_id},
                    {"$set": update_data}
                )
                
                if result.modified_count > 0:
                    fixed_count += 1
                    print(f"  🔧 DB 업데이트 완료")
                else:
                    print(f"  ⚠️ DB 업데이트 실패")
                
                if not image_exists:
                    not_found_count += 1
                
            except Exception as e:
                print(f"  ❌ 문서 처리 실패: {e}")
        
        print(f"\n📊 처리 결과:")
        print(f"  ✅ 수정된 문서: {fixed_count}개")
        print(f"  ❌ 파일 없는 문서: {not_found_count}개")
        print(f"  📈 수정률: {(fixed_count/len(problematic_docs)*100):.1f}%" if problematic_docs else "0%")
        
        am.close()
        
    except Exception as e:
        print(f"❌ 경로 정리 실패: {e}")
        import traceback
        traceback.print_exc()

def create_fast_image_access():
    """빠른 이미지 접근을 위한 최적화"""
    try:
        # AnnotationManager import
        sys.path.insert(0, os.path.join('anylabeling', 'services'))
        from annotation_manager import AnnotationManager
        
        print(f"\n🚀 빠른 이미지 접근 최적화")
        print("=" * 60)
        
        # MongoDB 연결
        am = AnnotationManager()
        
        # 1. 이미지 경로 인덱스 확인 및 생성
        print("1️⃣ 이미지 경로 인덱스 생성...")
        
        # 기존 인덱스에 추가
        additional_indexes = [
            "image_file_path",
            "image_exists", 
            "json_file_name",
            [("imagePath", 1), ("image_exists", 1)],
            [("json_file_name", 1), ("image_exists", 1)]
        ]
        
        for index in additional_indexes:
            try:
                am.collection.create_index(index)
                print(f"  ✅ 인덱스 생성: {index}")
            except Exception as e:
                print(f"  ⚠️ 인덱스 생성 실패: {index} - {e}")
        
        # 2. 실행 가능한 파일 통계
        print(f"\n2️⃣ 실행 가능성 통계...")
        
        total_docs = am.collection.count_documents({})
        executable_docs = am.collection.count_documents({"image_exists": True})
        missing_path_docs = am.collection.count_documents({
            "$or": [
                {"image_file_path": {"$exists": False}},
                {"image_file_path": ""},
                {"image_file_path": None}
            ]
        })
        
        print(f"  📊 전체 문서: {total_docs}개")
        print(f"  🚀 실행 가능: {executable_docs}개 ({executable_docs/total_docs*100:.1f}%)")
        print(f"  ❌ 경로 없음: {missing_path_docs}개 ({missing_path_docs/total_docs*100:.1f}%)")
        
        # 3. 샘플 빠른 조회 테스트
        print(f"\n3️⃣ 빠른 조회 성능 테스트...")
        
        import time
        
        # 랜덤 샘플 조회
        sample_doc = am.collection.find_one({"image_exists": True})
        if sample_doc:
            image_path_key = sample_doc.get('imagePath', '')
            
            # 인덱스 활용 조회 시간 측정
            start_time = time.time()
            result = am.collection.find_one({
                "imagePath": image_path_key,
                "image_exists": True
            }, {"image_file_path": 1, "image_exists": 1})
            end_time = time.time()
            
            query_time = (end_time - start_time) * 1000
            print(f"  ⚡ 인덱스 조회 시간: {query_time:.2f}ms")
            print(f"  📁 조회 결과: {result.get('image_file_path', 'N/A') if result else 'None'}")
        
        am.close()
        
    except Exception as e:
        print(f"❌ 최적화 실패: {e}")
        import traceback
        traceback.print_exc()

def main():
    """메인 함수"""
    print("🔧 이미지 경로 정리 및 최적화 시작\n")
    
    # 1. 누락된 경로 정보 보완
    fix_missing_paths()
    
    # 2. 빠른 접근 최적화
    create_fast_image_access()
    
    print(f"\n✅ 모든 정리 작업 완료!")
    print(f"\n💡 이제 이미지 실행 성공률이 크게 향상됩니다:")
    print(f"  • 절대경로 정보 보완으로 빠른 실행")
    print(f"  • 인덱스 최적화로 조회 속도 향상")
    print(f"  • 파일 존재 여부 캐시로 불필요한 파일 시스템 접근 감소")

if __name__ == "__main__":
    main()
