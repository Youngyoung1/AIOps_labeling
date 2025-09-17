"""Simple test script to verify JSON -> MongoDB sync via AnnotationManager.

Usage:
  python tools\test_flags_sync.py --json sample.json --mongo mongodb://localhost:27017 --db labeling_db

If no --json provided, a temp JSON will be created in the repo root and used.
"""
import argparse
import json
import os
import sys
import tempfile

# Ensure repository root is on sys.path so `anylabeling` package can be imported
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Import AnnotationManager directly from file to avoid importing the package's
# top-level which may require GUI deps like PyQt5.
import importlib.util
AM_PATH = os.path.join(REPO_ROOT, 'anylabeling', 'services', 'annotation_manager.py')
spec = importlib.util.spec_from_file_location('annotation_manager', AM_PATH)
am_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(am_mod)
AnnotationManager = am_mod.AnnotationManager


def make_sample_json(path):
    data = {
        "version": "1.0",
        "imagePath": os.path.basename(path).replace('.json', '.jpg'),
        "shapes": [
            {"label": "person", "points": [[10, 10], [100, 10], [100, 200], [10, 200]], "shape_type": "rectangle", "description": "sample"}
        ],
        "flags": {"reviewed": False, "blurred": False},
        "description": "sample image description"
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', help='Path to json file to insert', default=None)
    parser.add_argument('--mongo', help='MongoDB connection string', default='mongodb://localhost:27017')
    parser.add_argument('--db', help='MongoDB database name', default='labeling_db')
    args = parser.parse_args()

    json_path = args.json
    cleanup = False
    if json_path is None:
        fd, tmp = tempfile.mkstemp(prefix='test_flags_', suffix='.json', dir='.')
        os.close(fd)
        json_path = tmp
        make_sample_json(json_path)
        cleanup = True

    print(f"Using JSON: {json_path}")
    am = AnnotationManager(connection_string=args.mongo, db_name=args.db)

    inserted_id = am.insert_annotation(json_file_path=json_path)
    if inserted_id:
        print(f"Inserted/Updated annotation id: {inserted_id}")
        # Verify by querying imagePath
        with open(json_path, 'r', encoding='utf-8') as f:
            j = json.load(f)
        image_path = j.get('imagePath')
        doc = am.find_by_image_path(image_path)
        if doc:
            print('Found document in DB:')
            # print a subset
            print('  json_file_name:', doc.get('json_file_name'))
            print('  imagePath:', doc.get('imagePath'))
            print('  flags:', doc.get('flags'))
            print('  shape_count:', doc.get('shape_count'))
        else:
            print('Document not found in DB (unexpected)')
    else:
        print('Insert failed')

    if cleanup:
        try:
            os.remove(json_path)
        except Exception:
            pass


if __name__ == '__main__':
    main()
