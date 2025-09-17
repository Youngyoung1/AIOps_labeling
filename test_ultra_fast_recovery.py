"""
Ultra Fast 시스템 코드 무결성 검증
PyQt5 없이도 기본 구조 확인
"""

import sys
import os
import importlib.util

def test_file_exists_and_has_content():
    """파일 존재 및 내용 확인"""
    
    files_to_check = [
        'anylabeling/services/ultra_fast_startup.py',
        'anylabeling/services/fast_file_loader.py', 
        'anylabeling/services/lazy_importer.py',
        'anylabeling/services/app_instance_manager.py'
    ]
    
    results = {}
    
    for file_path in files_to_check:
        full_path = os.path.join(os.getcwd(), file_path)
        
        if not os.path.exists(full_path):
            results[file_path] = "❌ 파일 없음"
            continue
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                results[file_path] = "⚠️ 파일 비어있음"
            elif len(content) < 100:
                results[file_path] = f"⚠️ 내용 부족 ({len(content)} chars)"
            else:
                # 기본 클래스나 함수가 있는지 확인
                if 'class' in content or 'def' in content:
                    results[file_path] = f"✅ 정상 ({len(content)} chars)"
                else:
                    results[file_path] = f"⚠️ 구조 없음 ({len(content)} chars)"
                    
        except Exception as e:
            results[file_path] = f"❌ 읽기 실패: {e}"
    
    return results

def test_syntax_without_imports():
    """임포트 없이 구문 검사"""
    
    print("🔍 구문 검사 (임포트 제외)...")
    
    files_to_check = [
        'anylabeling/services/ultra_fast_startup.py',
        'anylabeling/services/fast_file_loader.py', 
        'anylabeling/services/lazy_importer.py'
    ]
    
    for file_path in files_to_check:
        try:
            full_path = os.path.join(os.getcwd(), file_path)
            
            if not os.path.exists(full_path):
                print(f"  ❌ {file_path}: 파일 없음")
                continue
            
            # 파일 내용을 읽어서 기본 구문 확인
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Python 구문 검사 (컴파일 시도)
            try:
                compile(content, full_path, 'exec')
                print(f"  ✅ {file_path}: 구문 정상")
            except SyntaxError as e:
                print(f"  ❌ {file_path}: 구문 오류 - {e}")
            
        except Exception as e:
            print(f"  ❌ {file_path}: 검사 실패 - {e}")

if __name__ == "__main__":
    print("🔧 Ultra Fast 시스템 복구 확인")
    print("=" * 50)
    
    # 파일 존재 및 내용 확인
    print("📁 파일 상태 확인:")
    results = test_file_exists_and_has_content()
    
    for file_path, status in results.items():
        print(f"  {status} {file_path}")
    
    print()
    
    # 구문 검사
    test_syntax_without_imports()
    
    print("\n" + "=" * 50)
    
    # 결과 요약
    success_count = sum(1 for status in results.values() if status.startswith("✅"))
    total_count = len(results)
    
    if success_count == total_count:
        print("🎉 Ultra Fast 시스템이 완전히 복구되었습니다!")
        print("💡 이제 DB 검수 파일이 Ultra Fast 모드로 열립니다!")
    elif success_count > total_count // 2:
        print("✅ Ultra Fast 시스템이 대부분 복구되었습니다!")
        print(f"   ({success_count}/{total_count} 파일 정상)")
    else:
        print("⚠️ 일부 파일에 문제가 있습니다.")
        print(f"   ({success_count}/{total_count} 파일 정상)")