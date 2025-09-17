#!/usr/bin/env python3
"""이미지 경로 분석 스크립트"""

import sys
import os
import json
from datetime import datetime

# 현재 디렉토리를 path에 추가
sys.path.insert(0, os.getcwd())

def analyze_image_paths():
    """MongoDB의 이미지 경로 패턴 분석"""
    try:
        # AnnotationManager import
        sys.path.insert(0, os.path.join('anylabeling', 'services'))
        from annotation_manager import AnnotationManager
        
        print("🔍 MongoDB 이미지 경로 패턴 분석")
        print("=" * 60)
        
        # MongoDB 연결
        am = AnnotationManager()
        
        # 샘플 데이터 조회
        sample_docs = list(am.collection.find({}).limit(10))
        
        print(f"📊 분석 대상: {len(sample_docs)}개 문서")
        print("-" * 60)
        
        path_patterns = {
            "절대경로_존재": 0,
            "상대경로_만": 0, 
            "경로_없음": 0,
            "파일_존재": 0,
            "파일_없음": 0,
            "JSON_이미지_동일디렉토리": 0,
            "JSON_이미지_다른디렉토리": 0
        }
        
        for i, doc in enumerate(sample_docs, 1):
            print(f"\n[{i}] 문서 분석:")
            
            # 기본 정보
            json_file_name = doc.get('json_file_name', 'N/A')
            image_path = doc.get('imagePath', 'N/A')
            json_file_path = doc.get('json_file_path', '')
            image_file_path = doc.get('image_file_path', '')
            
            print(f"  📄 JSON 파일: {json_file_name}")
            print(f"  🖼️ imagePath: {image_path}")
            print(f"  📁 JSON 전체경로: {json_file_path}")
            print(f"  🖼️ 이미지 전체경로: {image_file_path}")
            
            # 1. 절대경로 vs 상대경로
            if image_file_path and os.path.isabs(image_file_path):
                path_patterns["절대경로_존재"] += 1
                print(f"  ✅ 절대경로 존재")
            elif image_path:
                path_patterns["상대경로_만"] += 1
                print(f"  ⚠️ 상대경로만 존재")
            else:
                path_patterns["경로_없음"] += 1
                print(f"  ❌ 경로 정보 없음")
            
            # 2. 파일 존재 여부
            actual_path = image_file_path or ""
            if not actual_path and json_file_path and image_path:
                # JSON 경로 기준으로 이미지 경로 추정
                json_dir = os.path.dirname(json_file_path)
                actual_path = os.path.join(json_dir, image_path)
            
            if actual_path and os.path.exists(actual_path):
                path_patterns["파일_존재"] += 1
                print(f"  ✅ 파일 존재: {actual_path}")
            else:
                path_patterns["파일_없음"] += 1
                print(f"  ❌ 파일 없음: {actual_path}")
            
            # 3. JSON과 이미지 디렉토리 관계
            if json_file_path and image_file_path:
                json_dir = os.path.dirname(json_file_path)
                image_dir = os.path.dirname(image_file_path)
                
                if json_dir == image_dir:
                    path_patterns["JSON_이미지_동일디렉토리"] += 1
                    print(f"  📂 같은 디렉토리")
                else:
                    path_patterns["JSON_이미지_다른디렉토리"] += 1
                    print(f"  📂 다른 디렉토리")
                    print(f"     JSON: {json_dir}")
                    print(f"     이미지: {image_dir}")
            
            # 4. 실행 가능성 판단
            can_execute = False
            execution_method = ""
            
            if image_file_path and os.path.exists(image_file_path):
                can_execute = True
                execution_method = "절대경로로 실행 가능"
            elif json_file_path and image_path:
                estimated_path = os.path.join(os.path.dirname(json_file_path), image_path)
                if os.path.exists(estimated_path):
                    can_execute = True
                    execution_method = "추정경로로 실행 가능"
            
            if can_execute:
                print(f"  🚀 {execution_method}")
            else:
                print(f"  🚫 실행 불가")
        
        # 요약 통계
        print(f"\n📈 경로 패턴 분석 결과:")
        print("=" * 60)
        for pattern, count in path_patterns.items():
            percentage = (count / len(sample_docs)) * 100 if sample_docs else 0
            print(f"{pattern:25}: {count:2d}개 ({percentage:5.1f}%)")
        
        # 실행 성공률 계산
        success_rate = (path_patterns["파일_존재"] / len(sample_docs)) * 100 if sample_docs else 0
        print(f"\n🎯 실행 성공률: {success_rate:.1f}%")
        
        # 권장사항
        print(f"\n💡 권장사항:")
        if path_patterns["절대경로_존재"] < len(sample_docs) * 0.8:
            print("  • 모든 문서에 절대경로 정보 추가 필요")
        if path_patterns["파일_없음"] > 0:
            print("  • 존재하지 않는 파일 경로 정리 필요")
        if path_patterns["JSON_이미지_다른디렉토리"] > 0:
            print("  • 다른 디렉토리의 이미지 파일 경로 확인 필요")
        
        am.close()
        
    except Exception as e:
        print(f"❌ 분석 실패: {e}")
        import traceback
        traceback.print_exc()

def analyze_execution_logic():
    """현재 실행 로직 분석"""
    print(f"\n🔧 현재 실행 로직 분석:")
    print("=" * 60)
    
    print("1️⃣ 캐시된 절대경로 사용 (image_file_path + image_exists=True)")
    print("   → 가장 빠름, 파일 존재 확인 생략")
    
    print("\n2️⃣ MongoDB 인덱스 조회 (imagePath 또는 json_file_name 기준)")
    print("   → 빠름, DB에서 경로 정보 조회")
    
    print("\n3️⃣ JSON 경로 기준 추정 (json_file_path + imagePath)")
    print("   → 보통, 파일 시스템에서 상대경로 결합")
    
    print("\n4️⃣ 파일 시스템 검색 (디렉토리 스캔)")
    print("   → 느림, 전체 디렉토리 검색")
    
    print(f"\n💡 실행되는 이유:")
    print("• 일부 파일: 절대경로가 DB에 저장되어 있음 (빠른 실행)")
    print("• 일부 파일: JSON과 이미지가 같은 디렉토리에 있어 추정 가능")
    print("• 일부 파일: 경로가 없거나 파일이 없어서 실행 실패")

def main():
    """메인 함수"""
    print("🔍 이미지 경로 실행 패턴 분석 시작\n")
    
    analyze_image_paths()
    analyze_execution_logic()
    
    print(f"\n✅ 분석 완료!")

if __name__ == "__main__":
    main()
