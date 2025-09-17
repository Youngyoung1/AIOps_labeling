"""Debug script to test JSON file insertion into MongoDB

This script takes a directory path containing JSON files and attempts to insert
them into MongoDB using AnnotationManager, providing detailed diagnostics about
what succeeds and what fails.

Usage:
  python tools\debug_json_insertion.py --dir "C:\path\to\json\files" --mongo mongodb://localhost:27017 --db labeling_db
"""
import os
import sys
import json
import glob
import argparse
from pathlib import Path

# Ensure repo root on path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Import AnnotationManager directly from file to avoid GUI dependencies
import importlib.util
AM_PATH = os.path.join(REPO_ROOT, 'anylabeling', 'services', 'annotation_manager.py')
spec = importlib.util.spec_from_file_location('annotation_manager', AM_PATH)
am_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(am_mod)
AnnotationManager = am_mod.AnnotationManager


def analyze_json_file(json_path):
    """Analyze a JSON file and return diagnostic info"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        analysis = {
            'valid_json': True,
            'file_size': os.path.getsize(json_path),
            'has_imagePath': 'imagePath' in data,
            'imagePath': data.get('imagePath', 'N/A'),
            'has_shapes': 'shapes' in data and len(data.get('shapes', [])) > 0,
            'shape_count': len(data.get('shapes', [])),
            'has_flags': 'flags' in data and bool(data.get('flags', {})),
            'flags': data.get('flags', {}),
            'has_description': bool(data.get('description', '').strip()),
            'version': data.get('version', 'N/A')
        }
        
        # Check if imagePath points to existing file
        image_path = data.get('imagePath', '')
        if image_path:
            if not os.path.isabs(image_path):
                # Try relative to JSON file directory
                json_dir = os.path.dirname(json_path)
                full_image_path = os.path.join(json_dir, image_path)
                analysis['image_exists'] = os.path.exists(full_image_path)
                analysis['full_image_path'] = full_image_path
            else:
                analysis['image_exists'] = os.path.exists(image_path)
                analysis['full_image_path'] = image_path
        else:
            analysis['image_exists'] = False
            analysis['full_image_path'] = 'N/A'
            
        return analysis
        
    except json.JSONDecodeError as e:
        return {
            'valid_json': False,
            'error': f'JSON decode error: {e}',
            'file_size': os.path.getsize(json_path)
        }
    except Exception as e:
        return {
            'valid_json': False,
            'error': f'File error: {e}',
            'file_size': 0
        }


def test_insertion(json_path, annotation_manager):
    """Test inserting a single JSON file and return results"""
    try:
        result_id = annotation_manager.insert_annotation(json_file_path=json_path)
        if result_id:
            # Try to find the inserted document
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            image_path = data.get('imagePath', '')
            doc = None
            
            # Try multiple search strategies
            if image_path:
                doc = annotation_manager.find_by_image_path(image_path)
                if not doc:
                    doc = annotation_manager.find_by_image_path(os.path.basename(image_path))
            
            return {
                'success': True,
                'inserted_id': result_id,
                'found_in_db': doc is not None,
                'db_doc_summary': {
                    'json_file_name': doc.get('json_file_name') if doc else None,
                    'imagePath': doc.get('imagePath') if doc else None,
                    'flags': doc.get('flags') if doc else None,
                    'shape_count': doc.get('shape_count') if doc else None
                } if doc else None
            }
        else:
            return {
                'success': False,
                'error': 'AnnotationManager.insert_annotation returned None/False'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Exception during insertion: {e}'
        }


def main():
    parser = argparse.ArgumentParser(description='Debug JSON file insertion into MongoDB')
    parser.add_argument('--dir', required=True, help='Directory containing JSON files')
    parser.add_argument('--mongo', default='mongodb://localhost:27017', help='MongoDB connection string')
    parser.add_argument('--db', default='labeling_db', help='MongoDB database name')
    parser.add_argument('--pattern', default='*.json', help='File pattern to match')
    parser.add_argument('--max-files', type=int, help='Maximum number of files to process')
    args = parser.parse_args()
    
    # Check if directory exists
    if not os.path.exists(args.dir):
        print(f"ERROR: Directory does not exist: {args.dir}")
        return 1
    
    # Find JSON files
    json_pattern = os.path.join(args.dir, args.pattern)
    json_files = glob.glob(json_pattern)
    
    if not json_files:
        print(f"No JSON files found matching pattern: {json_pattern}")
        return 1
    
    if args.max_files:
        json_files = json_files[:args.max_files]
    
    print(f"Found {len(json_files)} JSON files to process")
    print(f"MongoDB: {args.mongo}")
    print(f"Database: {args.db}")
    print("-" * 60)
    
    # Initialize AnnotationManager
    try:
        am = AnnotationManager(connection_string=args.mongo, db_name=args.db)
        print("✓ AnnotationManager initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize AnnotationManager: {e}")
        return 1
    
    # Process each file
    successful_insertions = 0
    failed_insertions = 0
    
    for i, json_path in enumerate(json_files, 1):
        print(f"\n[{i}/{len(json_files)}] Processing: {os.path.basename(json_path)}")
        
        # Analyze file
        analysis = analyze_json_file(json_path)
        
        if not analysis['valid_json']:
            print(f"  ✗ Invalid JSON: {analysis['error']}")
            failed_insertions += 1
            continue
        
        print(f"  File size: {analysis['file_size']} bytes")
        print(f"  Has imagePath: {analysis['has_imagePath']} ({analysis['imagePath']})")
        print(f"  Image exists: {analysis.get('image_exists', 'N/A')}")
        print(f"  Shapes: {analysis['shape_count']}")
        print(f"  Flags: {analysis['flags']}")
        print(f"  Description: {analysis['has_description']}")
        
        # Test insertion
        insertion_result = test_insertion(json_path, am)
        
        if insertion_result['success']:
            print(f"  ✓ Insertion successful (ID: {insertion_result['inserted_id']})")
            if insertion_result['found_in_db']:
                print(f"  ✓ Document found in DB")
                db_summary = insertion_result['db_doc_summary']
                print(f"    - DB imagePath: {db_summary['imagePath']}")
                print(f"    - DB flags: {db_summary['flags']}")
                print(f"    - DB shapes: {db_summary['shape_count']}")
            else:
                print(f"  ⚠ Document inserted but not found in search")
            successful_insertions += 1
        else:
            print(f"  ✗ Insertion failed: {insertion_result['error']}")
            failed_insertions += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"Total files: {len(json_files)}")
    print(f"Successful insertions: {successful_insertions}")
    print(f"Failed insertions: {failed_insertions}")
    
    if failed_insertions > 0:
        print(f"\n⚠ {failed_insertions} files failed to insert. Check the detailed output above.")
        return 1
    else:
        print(f"\n✓ All files processed successfully!")
        return 0


if __name__ == '__main__':
    sys.exit(main())