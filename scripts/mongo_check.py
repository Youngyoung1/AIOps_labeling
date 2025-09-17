import os, json, sys, traceback
from pathlib import Path

out_path = Path(__file__).with_name('mongo_check_out.json')
uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
result = { 'uri': uri, 'ok': False, 'error': '' }
try:
    from pymongo import MongoClient
    client = MongoClient(uri, serverSelectionTimeoutMS=1500)
    # This will trigger a server selection and fail quickly if unreachable
    _ = client.list_database_names()
    result['ok'] = True
except Exception as e:
    result['ok'] = False
    result['error'] = f"{type(e).__name__}: {e}"
    result['traceback'] = traceback.format_exc()

try:
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
except Exception as e:
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)
