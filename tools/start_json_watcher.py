"""
JSON 파일 변경 감시 및 MongoDB 자동 동기화 시작 스크립트
"""
import os
import sys
import time

# Add repo root to path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, REPO_ROOT)

def start_json_watcher(directory):
    """JSON 파일 감시 시작"""
    try:
        from annotation_watcher import AnnotationWatcher
        
        print(f"🔍 JSON 파일 감시 시작...")
        print(f"📁 감시 디렉토리: {directory}")
        print(f"🔄 외부에서 JSON 파일을 수정하면 자동으로 MongoDB에 반영됩니다")
        print("🛑 중지하려면 Ctrl+C를 누르세요\n")
        
        # 파일 감시 시작
        watcher = AnnotationWatcher(watch_directory=directory)
        watcher.start()
        
        try:
            while watcher.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 사용자에 의해 중지됨")
            watcher.stop()
            
    except Exception as e:
        print(f"❌ 파일 감시 시작 실패: {e}")
        return 1
    
    return 0

def main():
    # SKPoC 디렉토리 감시
    watch_dir = r"C:\Users\pc\Desktop\인턴\SKPoC\Unclear_file"
    
    if not os.path.exists(watch_dir):
        print(f"❌ 디렉토리가 존재하지 않습니다: {watch_dir}")
        return 1
    
    return start_json_watcher(watch_dir)

if __name__ == '__main__':
    sys.exit(main())