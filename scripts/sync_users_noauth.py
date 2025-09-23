#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sync MongoDB admin/app users to .env values when authorization is DISABLED.
This script connects WITHOUT credentials and upserts users accordingly.
"""
from pymongo import MongoClient
import os
import sys


def load_env(env_path: str = ".env") -> dict:
    env = {}
    if not os.path.exists(env_path):
        return env
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def upsert_user(db, user: str, pwd: str, roles):
    try:
        # Try updateUser first (works if user exists)
        db.command("updateUser", user, pwd=pwd, roles=roles)
        print(f"[OK] updateUser: {db.name}.{user}")
    except Exception as e:
        msg = str(e)
        if "not found" in msg or "does not exist" in msg or "UserNotFound" in msg:
            # Create if not exists
            db.command("createUser", user, pwd=pwd, roles=roles)
            print(f"[OK] createUser: {db.name}.{user}")
        else:
            raise


def main() -> int:
    env = load_env()
    server_ip = env.get("MONGODB_SERVER_IP", "localhost")
    port = env.get("MONGODB_PORT", "27017")
    db_name = env.get("MONGODB_DATABASE", "labeling_db")
    admin_user = env.get("MONGODB_ADMIN_USERNAME", "admin")
    admin_pass = env.get("MONGODB_ADMIN_PASSWORD", "admin123!@#")
    app_user = env.get("MONGODB_APP_USERNAME", "labeling_user")
    app_pass = env.get("MONGODB_APP_PASSWORD", "labeling_password")

    uri = f"mongodb://{server_ip}:{port}/admin"
    print(f"[INFO] Connecting without auth to {server_ip}:{port} (authorization must be disabled)")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        _ = client.server_info()
    except Exception as e:
        print("[ERROR] Cannot connect to MongoDB:", e)
        return 2

    try:
        # Admin user in admin DB
        upsert_user(client["admin"], admin_user, admin_pass, roles=[
            "userAdminAnyDatabase", "dbAdminAnyDatabase", "readWriteAnyDatabase"
        ])
        # App user in application DB
        upsert_user(client[db_name], app_user, app_pass, roles=["readWrite"])
    except Exception as e:
        print("[ERROR] Upsert users failed:", e)
        return 3
    finally:
        try:
            client.close()
        except Exception:
            pass

    print("[SUCCESS] Users synced to .env values (admin/app).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
