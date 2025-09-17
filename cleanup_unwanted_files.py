#!/usr/bin/env python3
"""불필요한 파일 정리 스크립트"""

import sys
import os
import json
from datetime import datetime

# 현재 디렉토리를 path에 추가
sys.path.insert(0, os.getcwd())

def analyze_files_to_delete():
    """삭제할 파일들 분석"""
    try:
        # AnnotationManager import
        sys.path.insert(0, os.path.join('anylabeling', 'services'))
        from annotation_manager import AnnotationManager
        
        print("🗑️ 삭제 대상 파일 분석")
        print("=" * 60)
        
        # MongoDB 연결
        am = AnnotationManager()
        
        # 전체 문서 수
        total_count = am.collection.count_documents({})
        print(f"📊 전체 문서 수: {total_count}개")
        
        # 1. 알 수 없는 파일 (imagePath가 None이거나 빈값)
        unknown_files_query = {
            "$or": [
                {"imagePath": None},
                {"imagePath": ""},
                {"imagePath": {"$exists": False}},
                {"imagePath": "None"},  # 문자열 'None'
                {"json_file_name": None},
                {"json_file_name": ""},
                {"json_file_name": {"$exists": False}},
                {"json_file_name": "N/A"}
            ]
        }
        
        unknown_count = am.collection.count_documents(unknown_files_query)
        print(f"❓ 알 수 없는 파일: {unknown_count}개")
        
        if unknown_count > 0:
            print("   샘플:")
            unknown_samples = list(am.collection.find(unknown_files_query).limit(5))
            for sample in unknown_samples:
                print(f"   - JSON: {sample.get('json_file_name', 'N/A')}, imagePath: {sample.get('imagePath', 'N/A')}")
        
        # 2. PNG, JPG가 아닌 확장자
        # 허용할 확장자들
        allowed_extensions = ['.png', '.jpg', '.jpeg']
        
        # 확장자별 통계
        print(f"\n📂 확장자별 분석:")
        
        pipeline = [
            {"$match": {
                "imagePath": {
                    "$exists": True, 
                    "$ne": None, 
                    "$ne": "", 
                    "$type": "string"
                }
            }},
            {"$addFields": {
                "extension": {
                    "$toLower": {
                        "$cond": {
                            "if": {"$gte": [{"$strLenCP": "$imagePath"}, 4]},
                            "then": {
                                "$substr": [
                                    "$imagePath", 
                                    {"$subtract": [{"$strLenCP": "$imagePath"}, 4]}, 
                                    4
                                ]
                            },
                            "else": "$imagePath"
                        }
                    }
                }
            }},
            {"$group": {
                "_id": "$extension",
                "count": {"$sum": 1},
                "samples": {"$push": {"imagePath": "$imagePath", "json_file_name": "$json_file_name"}}
            }},
            {"$sort": {"count": -1}}
        ]
        
        extension_stats = list(am.collection.aggregate(pipeline))
        
        delete_count = 0
        keep_count = 0
        
        for stat in extension_stats:
            ext = stat['_id']
            count = stat['count']
            
            if any(allowed_ext in ext for allowed_ext in allowed_extensions):
                print(f"   ✅ {ext}: {count}개 (유지)")
                keep_count += count
            else:
                print(f"   ❌ {ext}: {count}개 (삭제 대상)")
                delete_count += count
                
                # 샘플 표시 (최대 3개)
                samples = stat.get('samples', [])[:3]
                for sample in samples:
                    print(f"      - {sample.get('json_file_name', 'N/A')} → {sample.get('imagePath', 'N/A')}")
        
        # 3. 특별한 경우: webp 파일 확인
        webp_count = am.collection.count_documents({"imagePath": {"$regex": "\.webp$", "$options": "i"}})
        if webp_count > 0:
            print(f"\n🔍 WEBP 파일 발견: {webp_count}개")
            webp_samples = list(am.collection.find({"imagePath": {"$regex": "\.webp$", "$options": "i"}}).limit(3))
            for sample in webp_samples:
                print(f"   - {sample.get('json_file_name', 'N/A')} → {sample.get('imagePath', 'N/A')}")
            
            user_input = input("\nWEBP 파일도 삭제하시겠습니까? (y/N): ").strip().lower()
            if user_input == 'y':
                delete_count += webp_count
            else:
                keep_count += webp_count
                allowed_extensions.append('.webp')
        
        # 4. 총 삭제 예정 개수
        total_delete = unknown_count + delete_count
        
        print(f"\n📊 삭제 예정 통계:")
        print(f"   ❓ 알 수 없는 파일: {unknown_count}개")
        print(f"   ❌ 허용되지 않은 확장자: {delete_count}개")
        print(f"   🗑️ 총 삭제 예정: {total_delete}개")
        print(f"   ✅ 유지될 파일: {total_count - total_delete}개")
        print(f"   📈 삭제율: {(total_delete/total_count*100):.1f}%")
        
        am.close()
        return total_delete, unknown_files_query, allowed_extensions
        
    except Exception as e:
        print(f"❌ 분석 실패: {e}")
        import traceback
        traceback.print_exc()
        return 0, {}, []

def delete_unwanted_files(unknown_files_query, allowed_extensions):
    """불필요한 파일들 삭제"""
    try:
        # AnnotationManager import
        sys.path.insert(0, os.path.join('anylabeling', 'services'))
        from annotation_manager import AnnotationManager
        
        print(f"\n🗑️ 불필요한 파일 삭제 시작")
        print("=" * 60)
        
        # MongoDB 연결
        am = AnnotationManager()
        
        total_deleted = 0
        
        # 1. 알 수 없는 파일 삭제
        print("1️⃣ 알 수 없는 파일 삭제...")
        unknown_result = am.collection.delete_many(unknown_files_query)
        print(f"   🗑️ 삭제된 알 수 없는 파일: {unknown_result.deleted_count}개")
        total_deleted += unknown_result.deleted_count
        
        # 2. 허용되지 않은 확장자 파일 삭제
        print("2️⃣ 허용되지 않은 확장자 파일 삭제...")
        
        # 허용된 확장자 패턴 생성
        allowed_pattern = "|".join([f"\\{ext}$" for ext in allowed_extensions])
        
        disallowed_query = {
            "imagePath": {
                "$ne": None,
                "$ne": "",
                "$exists": True,
                "$not": {"$regex": f"({allowed_pattern})", "$options": "i"}
            }
        }
        
        # 삭제 전 확인
        disallowed_count = am.collection.count_documents(disallowed_query)
        print(f"   📊 삭제 예정 확장자 파일: {disallowed_count}개")
        
        if disallowed_count > 0:
            # 샘플 표시
            samples = list(am.collection.find(disallowed_query, {"imagePath": 1, "json_file_name": 1}).limit(5))
            print(f"   📋 삭제 예정 샘플:")
            for sample in samples:
                print(f"      - {sample.get('json_file_name', 'N/A')} → {sample.get('imagePath', 'N/A')}")
            
            # 실제 삭제
            disallowed_result = am.collection.delete_many(disallowed_query)
            print(f"   🗑️ 삭제된 확장자 파일: {disallowed_result.deleted_count}개")
            total_deleted += disallowed_result.deleted_count
        
        # 3. 결과 요약
        remaining_count = am.collection.count_documents({})
        
        print(f"\n📊 삭제 결과:")
        print(f"   🗑️ 총 삭제된 파일: {total_deleted}개")
        print(f"   ✅ 남은 파일: {remaining_count}개")
        
        # 4. 남은 파일들의 확장자 분포
        print(f"\n📂 남은 파일들의 확장자 분포:")
        remaining_extensions = list(am.collection.aggregate([
            {"$match": {
                "imagePath": {
                    "$exists": True, 
                    "$ne": None, 
                    "$ne": "", 
                    "$type": "string"
                }
            }},
            {"$addFields": {
                "extension": {
                    "$toLower": {
                        "$cond": {
                            "if": {"$gte": [{"$strLenCP": "$imagePath"}, 4]},
                            "then": {
                                "$substr": [
                                    "$imagePath", 
                                    {"$subtract": [{"$strLenCP": "$imagePath"}, 4]}, 
                                    4
                                ]
                            },
                            "else": "$imagePath"
                        }
                    }
                }
            }},
            {"$group": {
                "_id": "$extension",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]))
        
        for ext_stat in remaining_extensions:
            print(f"   📄 {ext_stat['_id']}: {ext_stat['count']}개")
        
        am.close()
        
        print(f"\n✅ 정리 완료! 이제 PNG, JPG 파일만 남았습니다.")
        
    except Exception as e:
        print(f"❌ 삭제 실패: {e}")
        import traceback
        traceback.print_exc()

def main():
    """메인 함수"""
    print("🗑️ 불필요한 파일 정리 시작\n")
    
    # 1. 삭제 대상 분석
    total_delete, unknown_query, allowed_extensions = analyze_files_to_delete()
    
    if total_delete == 0:
        print("\n✅ 삭제할 파일이 없습니다!")
        return
    
    # 2. 사용자 확인
    print(f"\n⚠️ 주의: 총 {total_delete}개의 파일이 삭제됩니다!")
    print(f"허용된 확장자: {', '.join(allowed_extensions)}")
    
    user_confirm = input("\n계속 진행하시겠습니까? (y/N): ").strip().lower()
    
    if user_confirm != 'y':
        print("❌ 작업이 취소되었습니다.")
        return
    
    # 3. 실제 삭제 수행
    delete_unwanted_files(unknown_query, allowed_extensions)
    
    print(f"\n🎉 모든 정리 작업이 완료되었습니다!")

if __name__ == "__main__":
    main()
