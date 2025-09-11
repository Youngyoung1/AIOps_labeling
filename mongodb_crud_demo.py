from pymongo import MongoClient
from datetime import datetime

# MongoDB 연결
client = MongoClient("mongodb://localhost:27017/")
db = client["labeling_db"]

print("=== MongoDB CRUD 작업 데모 ===\n")

# 1. CREATE (삽입)
print("1. 데이터 삽입 (CREATE)")
annotations_data = [
    {
        "image_id": "img_001.jpg",
        "label": "car",
        "bbox": [100, 200, 300, 400],
        "confidence": 0.95,
        "created_at": datetime.now()
    },
    {
        "image_id": "img_002.jpg",
        "label": "person",
        "bbox": [50, 100, 150, 300],
        "confidence": 0.88,
        "created_at": datetime.now()
    },
    {
        "image_id": "img_001.jpg",
        "label": "license_plate",
        "bbox": [120, 250, 180, 280],
        "confidence": 0.92,
        "created_at": datetime.now()
    }
]

# 여러 문서 삽입
result = db.annotations.insert_many(annotations_data)
print(f"삽입된 문서 ID들: {result.inserted_ids}")

# 이미지 메타데이터 삽입
images_data = [
    {
        "image_id": "img_001.jpg",
        "path": "/dataset/train/img_001.jpg",
        "width": 640,
        "height": 480,
        "uploaded_at": datetime.now()
    },
    {
        "image_id": "img_002.jpg",
        "path": "/dataset/train/img_002.jpg",
        "width": 640,
        "height": 480,
        "uploaded_at": datetime.now()
    }
]

db.images.insert_many(images_data)
print("이미지 메타데이터도 삽입됨\n")

# 2. READ (조회)
print("2. 데이터 조회 (READ)")
print("모든 어노테이션:")
for doc in db.annotations.find():
    image_id = doc.get('image_id', 'N/A')
    label = doc.get('label', 'N/A')
    bbox = doc.get('bbox', 'N/A')
    print(f"  - {image_id}: {label} (bbox: {bbox})")

print("\n특정 라벨 조회 (car):")
for doc in db.annotations.find({"label": "car"}):
    image_id = doc.get('image_id', 'N/A')
    label = doc.get('label', 'N/A')
    print(f"  - {image_id}: {label}")

print("\n특정 이미지의 모든 어노테이션:")
for doc in db.annotations.find({"image_id": "img_001.jpg"}):
    label = doc.get('label', 'N/A')
    bbox = doc.get('bbox', 'N/A')
    print(f"  - {label}: {bbox}")

# 3. UPDATE (수정)
print("\n3. 데이터 수정 (UPDATE)")
# confidence 값 업데이트
db.annotations.update_one(
    {"image_id": "img_001.jpg", "label": "car"},
    {"$set": {"confidence": 0.98, "updated_at": datetime.now()}}
)
print("img_001.jpg의 car 라벨 confidence를 0.98로 업데이트")

# 여러 문서 업데이트
db.annotations.update_many(
    {"image_id": "img_002.jpg"},
    {"$set": {"verified": True, "updated_at": datetime.now()}}
)
print("img_002.jpg의 모든 어노테이션에 verified 필드 추가\n")

# 4. DELETE (삭제)
print("4. 데이터 삭제 (DELETE)")
# 특정 조건의 문서 삭제
delete_result = db.annotations.delete_one({"label": "license_plate"})
print(f"삭제된 문서 수: {delete_result.deleted_count}")

# 여러 문서 삭제 (테스트용)
delete_result = db.annotations.delete_many({"confidence": {"$lt": 0.9}})
print(f"낮은 confidence 문서 삭제 수: {delete_result.deleted_count}\n")

# 최종 결과 확인
print("=== 최종 데이터 상태 ===")
print("남은 어노테이션:")
for doc in db.annotations.find():
    image_id = doc.get('image_id', 'N/A')
    label = doc.get('label', 'N/A')
    confidence = doc.get('confidence', 'N/A')
    print(f"  - {image_id}: {label} (confidence: {confidence})")

print("\n이미지 메타데이터:")
for doc in db.images.find():
    image_id = doc.get('image_id', 'N/A')
    path = doc.get('path', 'N/A')
    print(f"  - {image_id}: {path}")

# 데이터베이스 통계
print(f"\n컬렉션 통계:")
print(f"  - annotations: {db.annotations.count_documents({})} 개")
print(f"  - images: {db.images.count_documents({})} 개")
