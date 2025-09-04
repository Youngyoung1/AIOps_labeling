#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Mock Qt classes for testing
class MockStatusBar:
    def showMessage(self, message, timeout=0):
        print(f"STATUS BAR: {message} (timeout: {timeout})")

class MockFileListWidget:
    def __init__(self):
        self.items = []
    
    def count(self):
        return len(self.items)
    
    def item(self, index):
        return self.items[index] if 0 <= index < len(self.items) else None
    
    def addItem(self, filename):
        self.items.append(MockItem(filename))

class MockItem:
    def __init__(self, text):
        self._text = text
    
    def text(self):
        return self._text

class MockLabelWidget:
    def __init__(self):
        self.file_list_widget = MockFileListWidget()
        self.fn_to_index = {}
        self.filename = None
        self._status_bar = MockStatusBar()
    
    def statusBar(self):
        return self._status_bar
    
    @property
    def image_list(self):
        lst = []
        for i in range(self.file_list_widget.count()):
            item = self.file_list_widget.item(i)
            lst.append(item.text())
        return lst
    
    def update_file_status_info(self):
        """현재 파일 번호와 전체 파일 개수 정보를 상태바에 업데이트"""
        print(f"[DEBUG] update_file_status_info called - image_list: {hasattr(self, 'image_list')}, count: {len(self.image_list) if hasattr(self, 'image_list') else 0}, filename: {self.filename}")
        
        if not hasattr(self, 'image_list') or not self.image_list:
            # image_list가 없거나 비어있으면 상태바 메시지 지우지 않음
            print("[DEBUG] No image_list or empty, returning")
            return
        
        if not self.filename:
            print("[DEBUG] No filename, showing '파일 없음'")
            self.statusBar().showMessage("파일 없음", 0)
            return
        
        try:
            current_index = self.fn_to_index.get(str(self.filename), -1)
            if current_index >= 0:
                import os.path as osp
                filename = osp.basename(str(self.filename))
                file_info = f"[{current_index + 1}/{len(self.image_list)}] {filename}"
                print(f"[DEBUG] Showing file info: {file_info}")
                # 기존 메시지와 함께 표시하기 위해 영구 표시
                self.statusBar().showMessage(file_info, 0)
            else:
                print(f"[DEBUG] File index error - current_index: {current_index}")
                self.statusBar().showMessage("파일 인덱스 오류", 0)
        except Exception as e:
            print(f"[DEBUG] Exception in update_file_status_info: {e}")
            self.statusBar().showMessage("파일 상태 정보 오류", 0)

# Test the function
def test_file_status():
    print("=== Testing file status display ===")
    
    widget = MockLabelWidget()
    
    # Test 1: Empty state
    print("\n1. Testing empty state:")
    widget.update_file_status_info()
    
    # Test 2: Add some files
    print("\n2. Testing with files but no current filename:")
    files = ["image001.jpg", "image002.jpg", "image003.jpg"]
    for i, filename in enumerate(files):
        widget.file_list_widget.addItem(filename)
        widget.fn_to_index[filename] = i
    
    widget.update_file_status_info()
    
    # Test 3: Set current filename
    print("\n3. Testing with current filename set:")
    widget.filename = "image002.jpg"
    widget.update_file_status_info()
    
    # Test 4: Test different file
    print("\n4. Testing with different current file:")
    widget.filename = "image001.jpg"
    widget.update_file_status_info()
    
    # Test 5: Test file not in index
    print("\n5. Testing with file not in index:")
    widget.filename = "unknown.jpg"
    widget.update_file_status_info()

if __name__ == "__main__":
    test_file_status()
