@echo off
REM MongoDB 원격 연결 설정 스크립트
REM 사용법: set_remote_mongodb.bat [서버IP] [포트] [사용자명] [비밀번호] [데이터베이스명]

SET SERVER_IP=%1
SET PORT=%2
SET USERNAME=%3
SET PASSWORD=%4
SET DATABASE=%5

REM 기본값 설정
IF "%SERVER_IP%"=="" SET SERVER_IP=192.168.1.100
IF "%PORT%"=="" SET PORT=27017
IF "%DATABASE%"=="" SET DATABASE=labeling_db

REM URI 구성
IF "%USERNAME%"=="" (
    SET MONGODB_URI=mongodb://%SERVER_IP%:%PORT%/%DATABASE%
) ELSE (
    SET MONGODB_URI=mongodb://%USERNAME%:%PASSWORD%@%SERVER_IP%:%PORT%/%DATABASE%
)

echo MongoDB URI 설정: %MONGODB_URI%
echo.
echo 환경변수를 설정합니다...
setx MONGODB_URI "%MONGODB_URI%"

echo.
echo 설정 완료! 애플리케이션을 재시작하세요.
echo.
echo 연결 테스트를 하려면 아무 키나 누르세요...
pause > nul

REM 연결 테스트
python -c "from pymongo import MongoClient; client = MongoClient('%MONGODB_URI%'); print('연결 성공:', client.list_database_names()); client.close()"