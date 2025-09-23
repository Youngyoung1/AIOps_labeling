# MongoDB 원격 연결 설정 PowerShell 스크립트

param(
    [Parameter(Mandatory=$true)]
    [string]$ServerIP,
    
    [int]$Port = 27017,
    [string]$Username = "",
    [string]$Password = "",
    [string]$Database = "labeling_db",
    [switch]$TestConnection
)

# URI 구성
if ($Username -eq "") {
    $mongoUri = "mongodb://$ServerIP`:$Port/$Database"
} else {
    $mongoUri = "mongodb://$Username`:$Password@$ServerIP`:$Port/$Database"
}

Write-Host "MongoDB URI 설정: $mongoUri" -ForegroundColor Green

# 환경변수 설정
[Environment]::SetEnvironmentVariable("MONGODB_URI", $mongoUri, "User")
$env:MONGODB_URI = $mongoUri

Write-Host "환경변수가 설정되었습니다." -ForegroundColor Green

if ($TestConnection) {
    Write-Host "연결 테스트 중..." -ForegroundColor Yellow
    
    try {
        # Python으로 연결 테스트
        $testScript = @"
from pymongo import MongoClient
import sys
try:
    client = MongoClient('$mongoUri', serverSelectionTimeoutMS=3000)
    databases = client.list_database_names()
    print('✅ 연결 성공!')
    print('사용 가능한 데이터베이스:', databases)
    client.close()
except Exception as e:
    print('❌ 연결 실패:', str(e))
    sys.exit(1)
"@
        
        python -c $testScript
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "MongoDB 연결이 성공했습니다!" -ForegroundColor Green
        } else {
            Write-Host "MongoDB 연결에 실패했습니다." -ForegroundColor Red
        }
    }
    catch {
        Write-Host "연결 테스트 중 오류 발생: $_" -ForegroundColor Red
    }
}

Write-Host "`n사용법 예시:" -ForegroundColor Cyan
Write-Host ".\set_remote_mongodb.ps1 -ServerIP 192.168.1.100 -TestConnection" -ForegroundColor White
Write-Host ".\set_remote_mongodb.ps1 -ServerIP 192.168.1.100 -Username admin -Password mypass -TestConnection" -ForegroundColor White