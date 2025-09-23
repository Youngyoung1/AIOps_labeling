@echo off
echo === 현재 NAS MongoDB 연결 상태 확인 ===
echo.

REM 현재 환경변수 확인
echo [현재 설정된 환경변수]
echo MONGODB_URI: %MONGODB_URI%
echo NAS_MONGODB_SERVER: %NAS_MONGODB_SERVER%
echo.

REM 환경변수에서 NAS IP 추출
if defined MONGODB_URI (
    echo [연결 정보 분석]
    for /f "tokens=3 delims=/@" %%a in ("%MONGODB_URI%") do (
        for /f "tokens=1 delims=:" %%b in ("%%a") do (
            set CURRENT_NAS_IP=%%b
        )
    )
    
    if defined CURRENT_NAS_IP (
        echo 현재 연결된 NAS IP: %CURRENT_NAS_IP%
    ) else (
        echo NAS IP를 추출할 수 없습니다.
    )
) else (
    echo MongoDB URI가 설정되지 않았습니다.
)

echo.
echo [연결 테스트]
if defined MONGODB_URI (
    python -c "from pymongo import MongoClient; import sys; client = MongoClient('%MONGODB_URI%', serverSelectionTimeoutMS=3000); print('✅ 연결 성공:', client.server_info()['version']); client.close()" 2>nul
    if %errorlevel% equ 0 (
        echo 상태: 정상 연결됨
    ) else (
        echo 상태: 연결 실패
    )
) else (
    echo 상태: 설정되지 않음
)

echo.
echo [옵션]
echo 1. NAS IP 변경
echo 2. 연결 테스트 재실행
echo 3. 설정 초기화
echo 4. 종료
echo.
set /p choice="선택 (1-4): "

if "%choice%"=="1" goto change_ip
if "%choice%"=="2" goto test_connection
if "%choice%"=="3" goto reset_config
if "%choice%"=="4" goto end

:change_ip
echo.
echo === NAS IP 변경 ===
set /p new_ip="새로운 NAS IP 주소: "
if "%new_ip%"=="" (
    echo IP가 입력되지 않았습니다.
    goto end
)

REM 새 URI 생성
set USERNAME=labeling_user
set PASSWORD=labeling_password
set DATABASE=labeling_db
set PORT=27017
set NEW_URI=mongodb://%USERNAME%:%PASSWORD%@%new_ip%:%PORT%/%DATABASE%

echo.
echo 새 연결 정보: %NEW_URI%
echo.
set /p confirm="변경하시겠습니까? (y/N): "
if /i "%confirm%"=="y" (
    setx MONGODB_URI "%NEW_URI%"
    setx NAS_MONGODB_SERVER "%new_ip%"
    echo ✅ 설정이 변경되었습니다. 애플리케이션을 재시작하세요.
) else (
    echo 변경이 취소되었습니다.
)
goto end

:test_connection
echo.
echo === 연결 테스트 재실행 ===
if defined MONGODB_URI (
    python -c "from pymongo import MongoClient; client = MongoClient('%MONGODB_URI%', serverSelectionTimeoutMS=5000); print('서버 정보:', client.server_info()); print('데이터베이스:', client.list_database_names()); client.close()"
) else (
    echo MongoDB URI가 설정되지 않았습니다.
)
pause
goto end

:reset_config
echo.
echo === 설정 초기화 ===
set /p confirm="모든 MongoDB 설정을 삭제하시겠습니까? (y/N): "
if /i "%confirm%"=="y" (
    setx MONGODB_URI ""
    setx NAS_MONGODB_SERVER ""
    echo ✅ 설정이 초기화되었습니다.
) else (
    echo 초기화가 취소되었습니다.
)
goto end

:end
echo.
pause