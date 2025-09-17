#!/usr/bin/env python3
"""여러 디렉토리의 JSON 파일들을 MongoDB에 저장하는 스크립트"""

import os
import json
import sys
from datetime import datetime
import glob

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.getcwd())

def extract_annotation_features(json_data):
    """JSON 데이터에서 검색 최적화용 필드들 추출"""
    shapes = json_data.get('shapes', [])
    
    # labels 배열 생성 (중복 제거)
    labels = list(set([shape.get('label', '') for shape in shapes if shape.get('label')]))
    
    # shape_types 추출
    shape_types = list(set([shape.get('shape_type', '') for shape in shapes if shape.get('shape_type')]))
    
    # descriptions 추출 (비어있지 않은 것만)
    descriptions = [shape.get('description', '') for shape in shapes 
                  if shape.get('description') and shape.get('description').strip()]
    has_descriptions = len(descriptions) > 0
    
    # difficult 플래그 체크
    has_difficult = any(shape.get('difficult', False) for shape in shapes)
    
    # tag 정보 추출
    all_tags = []
    for shape in shapes:
        tags = shape.get('tag', [])
        if tags and isinstance(tags, list):
            all_tags.extend(tags)
    unique_tags = list(set(all_tags))
    has_tags = len(unique_tags) > 0
    
    # attributes 정보 추출
    has_attributes = any(shape.get('attributes', {}) for shape in shapes 
                       if isinstance(shape.get('attributes'), dict) and shape.get('attributes'))
    
    # flags 정보 추출 (전역 + shape별)
    global_flags = json_data.get("flags", {})
    has_global_flags = bool(global_flags)
    
    shape_flags = []
    for shape in shapes:
        if shape.get('flags') and shape.get('flags') is not None:
            if isinstance(shape.get('flags'), dict) and shape.get('flags'):
                shape_flags.append(shape.get('flags'))
    has_shape_flags = len(shape_flags) > 0
    
    return {
        "labels": labels,
        "shape_types": shape_types,
        "tags": unique_tags,
        
        # 개수 정보
        "shape_count": len(shapes),
        "label_count": len(labels),
        "tag_count": len(unique_tags),
        "description_count": len(descriptions),
        
        # 플래그 정보
        "has_descriptions": has_descriptions,
        "has_difficult": has_difficult,
        "has_tags": has_tags,
        "has_attributes": has_attributes,
        "has_global_flags": has_global_flags,
        "has_shape_flags": has_shape_flags
    }

def save_json_to_mongodb(json_file_path):
    """JSON 파일을 MongoDB에 저장"""
    try:
        import pymongo
        
        # MongoDB 연결
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client.labeling_db
        collection = db.annotations
        
        # JSON 파일 읽기
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        print(f"📋 파일 읽기: {os.path.basename(json_file_path)}")
        print(f"📊 이미지 경로: {json_data.get('imagePath')}")
        print(f"🔸 Shape 개수: {len(json_data.get('shapes', []))}")
        
        # 파일 경로 정보 추출
        abs_path = os.path.abspath(json_file_path)
        path_info = {
            "json_file_path": abs_path,  # JSON 파일의 전체 경로
            "json_file_name": os.path.basename(abs_path),  # JSON 파일명
            "json_directory": os.path.dirname(abs_path),  # JSON 파일이 있는 디렉토리
            "json_relative_path": os.path.relpath(abs_path),  # 상대 경로
        }
        
        # 이미지 파일 경로 정보도 추가
        image_path = json_data.get("imagePath")
        if image_path:
            # 이미지 경로가 상대 경로인 경우 JSON 파일 기준으로 절대 경로 생성
            if not os.path.isabs(image_path):
                image_abs_path = os.path.join(os.path.dirname(abs_path), image_path)
                image_abs_path = os.path.abspath(image_abs_path)
            else:
                image_abs_path = image_path
            
            # 이미지 파일이 실제로 존재하는지 확인
            image_exists = os.path.exists(image_abs_path)
            
            # 이미지와 JSON이 같은 디렉토리에 있는지 확인
            same_directory = os.path.dirname(image_abs_path) == os.path.dirname(abs_path)
            
            path_info.update({
                "image_file_path": image_abs_path,  # 이미지 파일의 전체 경로
                "image_file_name": os.path.basename(image_abs_path),  # 이미지 파일명
                "image_directory": os.path.dirname(image_abs_path),  # 이미지 파일이 있는 디렉토리
                "image_relative_path": os.path.relpath(image_abs_path),  # 이미지 상대 경로
                "image_exists": image_exists,  # 이미지 파일 존재 여부
                "same_directory": same_directory,  # JSON과 이미지가 같은 디렉토리인지
                "image_extension": os.path.splitext(image_abs_path)[1].lower(),  # 이미지 확장자
            })
        
        print(f"📁 JSON 전체 경로: {path_info['json_file_path']}")
        print(f"📁 JSON 디렉토리: {path_info['json_directory']}")
        if image_path:
            print(f"🖼️ 이미지 전체 경로: {path_info.get('image_file_path', 'N/A')}")
            print(f"📁 이미지 디렉토리: {path_info.get('image_directory', 'N/A')}")
        
        # 검색 최적화용 필드들 추출
        features = extract_annotation_features(json_data)
        
        # MongoDB에 저장할 문서 구성
        document = {
            # 원본 데이터 필드들
            "version": json_data.get("version"),
            "flags": json_data.get("flags", {}),
            "shapes": json_data.get("shapes", []),
            "imagePath": json_data.get("imagePath"),  # 원본 경로 유지
            "imageData": json_data.get("imageData"),
            "imageHeight": json_data.get("imageHeight"),
            "imageWidth": json_data.get("imageWidth"),
            "description": json_data.get("description", ""),
            
            # 파일 경로 정보 추가
            **path_info,
            
            # 원본 JSON 전체 보존
            "annotation": json_data,
            
            # 검색 최적화용 필드들
            **features,
            
            # 시간 정보
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        print(f"🏷️ 라벨: {features['labels']}")
        print(f"🔸 Shape 타입: {features['shape_types']}")
        print(f"📝 설명 있음: {features['has_descriptions']}")
        
        # 기존 데이터 확인 및 upsert (JSON 파일 경로로 확인)
        existing = collection.find_one({"json_file_path": abs_path})
        if existing:
            # 업데이트
            document["created_at"] = existing.get("created_at", datetime.now())
            result = collection.replace_one(
                {"json_file_path": abs_path}, 
                document
            )
            print(f"🔄 업데이트 완료: matched={result.matched_count}, modified={result.modified_count}")
        else:
            # 새로 삽입
            result = collection.insert_one(document)
            print(f"➕ 삽입 완료: ID={str(result.inserted_id)}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ MongoDB 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def find_json_files_recursively(base_paths):
    """여러 기본 경로에서 재귀적으로 JSON 파일 찾기"""
    json_files = []
    
    for base_path in base_paths:
        if not os.path.exists(base_path):
            print(f"⚠️ 경로가 존재하지 않음: {base_path}")
            continue
            
        print(f"🔍 검색 중: {base_path}")
        
        # 재귀적으로 JSON 파일 찾기
        pattern = os.path.join(base_path, "**", "*.json")
        found_files = glob.glob(pattern, recursive=True)
        
        # 어노테이션 JSON 파일만 필터링 (shapes 필드가 있는 것)
        annotation_files = []
        for file_path in found_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'shapes' in data or 'imagePath' in data:  # 어노테이션 파일 판별
                        annotation_files.append(file_path)
            except:
                pass  # JSON 파싱 실패한 파일은 무시
        
        json_files.extend(annotation_files)
        print(f"📁 {base_path}에서 발견: {len(annotation_files)}개 어노테이션 파일")
    
    return json_files

def main():
    """메인 함수"""
    print("🔍 여러 디렉토리 JSON 파일 MongoDB 저장 테스트\n")
    
    # 검색할 기본 경로들
    base_paths = [
        # 현재 디렉토리
        os.getcwd(),
        # 사용자가 지정한 다른 경로들 (필요에 따라 추가)
        r"C:\Users\pc\Desktop",
        r"C:\Users\pc\Documents",
        # 더 많은 경로 추가 가능...
    ]
    
    print("🗂️ 검색 대상 디렉토리:")
    for path in base_paths:
        print(f"  📁 {path}")
    print()
    
    # JSON 파일 찾기
    json_files = find_json_files_recursively(base_paths)
    
    if not json_files:
        print("❌ 어노테이션 JSON 파일을 찾을 수 없습니다.")
        return
    
    print(f"🎯 총 발견된 어노테이션 파일: {len(json_files)}개")
    print()
    
    # 디렉토리별 통계
    dir_stats = {}
    for file_path in json_files:
        dir_path = os.path.dirname(file_path)
        dir_stats[dir_path] = dir_stats.get(dir_path, 0) + 1
    
    print("📊 디렉토리별 파일 개수:")
    for dir_path, count in sorted(dir_stats.items()):
        print(f"  📁 {dir_path}: {count}개")
    print()
    
    print(f"🚀 MongoDB 저장 시작...")
    
    success_count = 0
    for i, json_file in enumerate(json_files, 1):
        print(f"\n[{i}/{len(json_files)}] 처리 중: {json_file}")
        print("-" * 80)
        
        if save_json_to_mongodb(json_file):
            success_count += 1
            print(f"✅ 성공")
        else:
            print(f"❌ 실패")
    
    print(f"\n📊 처리 결과:")
    print(f"✅ 성공: {success_count}개")
    print(f"❌ 실패: {len(json_files) - success_count}개")
    print(f"📈 성공률: {success_count/len(json_files)*100:.1f}%")
    
    # 최종 MongoDB 통계 확인
    try:
        import pymongo
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client.labeling_db
        collection = db.annotations
        
        total_count = collection.count_documents({})
        unique_dirs = collection.distinct("json_directory")
        
        print(f"\n🗄️ MongoDB 최종 상태:")
        print(f"📊 총 저장된 문서: {total_count}개")
        print(f"📁 저장된 디렉토리 수: {len(unique_dirs)}개")
        
        client.close()
    except Exception as e:
        print(f"⚠️ MongoDB 상태 확인 실패: {e}")

if __name__ == "__main__":
    main()
