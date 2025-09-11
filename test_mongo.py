from pymongo import MongoClient
try:
    c = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
    print("Databases:", c.list_database_names())
except Exception as e:
    print("Connection failed:", e)
