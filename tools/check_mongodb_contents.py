"""Simple script to query MongoDB and show what's actually in the database"""
import os
import sys

# Ensure repo root on path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Import AnnotationManager
import importlib.util
AM_PATH = os.path.join(REPO_ROOT, 'anylabeling', 'services', 'annotation_manager.py')
spec = importlib.util.spec_from_file_location('annotation_manager', AM_PATH)
am_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(am_mod)
AnnotationManager = am_mod.AnnotationManager

def main():
    try:
        am = AnnotationManager(connection_string='mongodb://localhost:27017', db_name='labeling_db')
        
        # Get basic stats
        stats = am.get_statistics()
        print("=== MongoDB Database Statistics ===")
        print(f"Total images: {stats.get('total_images', 0)}")
        print(f"Total shapes: {stats.get('total_shapes', 0)}")
        print(f"Average shapes per image: {stats.get('avg_shapes_per_image', 0):.2f}")
        print(f"Images with descriptions: {stats.get('images_with_descriptions', 0)}")
        print(f"Images with difficult shapes: {stats.get('images_with_difficult', 0)}")
        
        # Show recent documents
        print("\n=== Recent Documents (last 10) ===")
        pipeline = [
            {"$sort": {"updated_at": -1}},
            {"$limit": 10},
            {"$project": {
                "imagePath": 1,
                "json_file_name": 1,
                "shape_count": 1,
                "flags": 1,
                "updated_at": 1
            }}
        ]
        
        recent_docs = list(am.collection.aggregate(pipeline))
        for i, doc in enumerate(recent_docs, 1):
            print(f"{i:2d}. {doc.get('json_file_name', 'N/A')}")
            print(f"    imagePath: {doc.get('imagePath', 'N/A')}")
            print(f"    shapes: {doc.get('shape_count', 0)}, flags: {doc.get('flags', {})}")
            print(f"    updated: {doc.get('updated_at', 'N/A')}")
        
        # Check for documents from the SKPoC directory specifically
        print("\n=== Documents from SKPoC/Unclear_file ===")
        skpoc_docs = list(am.collection.find(
            {"imagePath": {"$regex": "SKPoC.*Unclear_file"}},
            {"imagePath": 1, "json_file_name": 1, "shape_count": 1, "flags": 1}
        ))
        
        if skpoc_docs:
            print(f"Found {len(skpoc_docs)} documents from SKPoC/Unclear_file:")
            for doc in skpoc_docs:
                print(f"  - {doc.get('json_file_name', 'N/A')} ({doc.get('shape_count', 0)} shapes)")
        else:
            print("No documents found from SKPoC/Unclear_file directory")
            
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())