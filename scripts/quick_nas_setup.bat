@echo off
echo === NAS MongoDB 빠른 설정 ===
echo.

REM 기본 설정값
set /p NAS_IP="NAS 서버 IP 주소 입력: "
if "%NAS_IP%"=="" (
    echo IP 주소가 입력되지 않았습니다.
    pause
    exit /b 1
)

set USERNAME=labeling_user
set PASSWORD=labeling_password
set DATABASE=labeling_db
set PORT=27017

REM MongoDB URI 생성
set MONGODB_URI=mongodb://%USERNAME%:%PASSWORD%@%NAS_IP%:%PORT%/%DATABASE%

echo.
echo 설정할 MongoDB URI: %MONGODB_URI%
echo.

REM 환경변수 설정
setx MONGODB_URI "%MONGODB_URI%"
setx NAS_MONGODB_SERVER "%NAS_IP%"

echo.
echo 환경변수가 설정되었습니다.
echo.

REM 연결 테스트
echo 연결 테스트 중...
python -c "from pymongo import MongoClient; client = MongoClient('%MONGODB_URI%', serverSelectionTimeoutMS=3000); print('연결 성공:', client.list_database_names()); client.close()" 2>nul

if %errorlevel% equ 0 (
    echo ✅ MongoDB 연결 성공!
) else (
    echo ❌ MongoDB 연결 실패
    echo 다음을 확인하세요:
    echo 1. NAS에서 MongoDB가 실행 중인지
    echo 2. 방화벽에서 포트 27017이 열려있는지
    echo 3. 사용자 인증 정보가 올바른지
)

echo.
echo 설정 완료! 애플리케이션을 재시작하세요.
echo 다른 컴퓨터에서도 동일하게 설정하세요.
pause