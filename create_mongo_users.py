from pymongo import MongoClient
import os
import sys
from urllib.parse import quote_plus


def load_env(env_path: str = ".env") -> dict:
    env = {}
    if not os.path.exists(env_path):
        print(f"[WARN] .env 파일을 찾을 수 없습니다: {env_path}")
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


def ensure_users(env: dict) -> int:
    """Create or update admin and app users to match .env values.
    Returns exit code (0 success, non-zero error)."""
    server_ip = env.get("MONGODB_SERVER_IP", "localhost")
    port = env.get("MONGODB_PORT", "27017")
    db_name = env.get("MONGODB_DATABASE", "labeling_db")

    admin_user = env.get("MONGODB_ADMIN_USERNAME", "admin")
    admin_pass_env = env.get("MONGODB_ADMIN_PASSWORD", "")
    app_user = env.get("MONGODB_APP_USERNAME", "labeling_user")
    app_pass_env = env.get("MONGODB_APP_PASSWORD", "")

    print("[INFO] MongoDB 사용자 동기화(.env) 수행 중...")

    # 후보 관리자 비밀번호: .env 값 우선, 과거 기본값 보조
    admin_pass_candidates = [p for p in [admin_pass_env, "admin123!@#"] if p]
    if not admin_pass_candidates:
        admin_pass_candidates = ["admin123!@#"]

    # 1) 인증 ON 상태에서 admin 계정으로 로그인 시도
    admin_client = None
    last_error = None
    for idx, pwd in enumerate(admin_pass_candidates, 1):
        # RFC 3986에 따라 사용자명/비밀번호 인코딩
        admin_user_enc = quote_plus(admin_user)
        admin_pwd_enc = quote_plus(pwd)
        admin_uri = f"mongodb://{admin_user_enc}:{admin_pwd_enc}@{server_ip}:{port}/admin"
        try:
            admin_client = MongoClient(admin_uri, serverSelectionTimeoutMS=5000)
            _ = admin_client.server_info()
            print(f"[OK] 관리자 인증 성공 (시도 {idx})")
            # .env 비밀번호와 다르면 admin 비밀번호를 .env 값으로 업데이트
            if admin_pass_env and pwd != admin_pass_env:
                try:
                    admin_client["admin"].command("updateUser", admin_user, pwd=admin_pass_env)
                    print("[OK] 관리자 비밀번호를 .env 값으로 업데이트 완료")
                except Exception as e:
                    print(f"[WARN] 관리자 비밀번호 업데이트 실패: {e}")
            break
        except Exception as e:
            last_error = e
            admin_client = None

    # 2) 만약 admin 인증이 모두 실패하면, 인증 OFF 상태에서만 실행 가능
    if admin_client is None:
        print("[ERROR] 관리자 인증 실패. 인증이 비활성화된 상태에서만 사용자 생성/수정이 가능합니다.")
        print("[HINT] 일시적으로 인증을 꺼서 다시 실행하거나, 정확한 관리자 비밀번호를 .env에 설정해주세요.")
        if last_error:
            print(f"   마지막 오류: {last_error}")
        return 2

    # 3) 애플리케이션 사용자 보장 (labeling_db)
    try:
        app_db = admin_client[db_name]
        # 먼저 updateUser 시도 (존재하지 않으면 createUser로 대체)
        try:
            if app_pass_env:
                app_db.command("updateUser", app_user, pwd=app_pass_env, roles=["readWrite"])
                print("[OK] 애플리케이션 사용자 비밀번호/권한 업데이트 완료")
            else:
                # 비밀번호가 비어있으면 권한만 보장
                app_db.command("updateUser", app_user, roles=["readWrite"])
                print("[OK] 애플리케이션 사용자 권한 업데이트 완료")
        except Exception as ue:
            # 존재하지 않으면 createUser
            if "not found" in str(ue) or "does not exist" in str(ue):
                app_db.command("createUser", app_user, pwd=(app_pass_env or "labeling_password"), roles=["readWrite"])
                print("[OK] 애플리케이션 사용자 생성 완료")
            else:
                raise
    except Exception as e:
        print(f"[ERROR] 애플리케이션 사용자 설정 오류: {e}")
        return 3

    # 4) 마무리
    try:
        admin_client.close()
    except Exception:
        pass
    print("\n[SUCCESS] 사용자 동기화가 완료되었습니다!")
    return 0


if __name__ == "__main__":
    env = load_env()
    code = ensure_users(env)
    sys.exit(code)