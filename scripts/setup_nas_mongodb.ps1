# NAS MongoDB 연결 자동 설정 스크립트
# 모든 클라이언트 컴퓨터에서 실행

param(
    [Parameter(Mandatory=$false)]
    [string]$NasIP = "",
    
    [Parameter(Mandatory=$false)]
    [string]$Username = "labeling_user",
    
    [Parameter(Mandatory=$false)]
    [string]$Password = "labeling_password",
    
    [Parameter(Mandatory=$false)]
    [string]$Database = "labeling_db",
    
    [Parameter(Mandatory=$false)]
    [int]$Port = 27017,
    
    [switch]$AutoDetectNAS,
    [switch]$TestConnection,
    [switch]$CreateDesktopShortcut
)

Write-Host "=== NAS MongoDB 연결 설정 ===" -ForegroundColor Cyan

# NAS IP 자동 감지
if ($AutoDetectNAS -or $NasIP -eq "") {
    Write-Host "NAS 서버를 자동으로 찾는 중..." -ForegroundColor Yellow
    
    # 네트워크 스캔으로 NAS 찾기
    $networkBase = (Get-NetRoute -DestinationPrefix "0.0.0.0/0").NextHop | Where-Object {$_ -ne "0.0.0.0"} | Select-Object -First 1
    $networkPrefix = $networkBase.Substring(0, $networkBase.LastIndexOf('.')) + "."
    
    $foundServers = @()
    for ($i = 1; $i -le 254; $i++) {
        $ip = $networkPrefix + $i
        $result = Test-NetConnection -ComputerName $ip -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue
        if ($result) {
            $foundServers += $ip
            Write-Host "MongoDB 서버 발견: $ip" -ForegroundColor Green
        }
    }
    
    if ($foundServers.Count -eq 0) {
        Write-Host "자동으로 MongoDB 서버를 찾을 수 없습니다." -ForegroundColor Red
        $NasIP = Read-Host "NAS 서버 IP를 직접 입력하세요"
    } elseif ($foundServers.Count -eq 1) {
        $NasIP = $foundServers[0]
        Write-Host "NAS 서버로 $NasIP 를 사용합니다." -ForegroundColor Green
    } else {
        Write-Host "여러 MongoDB 서버가 발견되었습니다:" -ForegroundColor Yellow
        for ($i = 0; $i -lt $foundServers.Count; $i++) {
            Write-Host "$($i+1). $($foundServers[$i])"
        }
        $choice = Read-Host "사용할 서버 번호를 선택하세요 (1-$($foundServers.Count))"
        $NasIP = $foundServers[$choice - 1]
    }
}

if ($NasIP -eq "") {
    Write-Host "NAS IP가 지정되지 않았습니다." -ForegroundColor Red
    exit 1
}

# MongoDB URI 구성
$mongoUri = "mongodb://$Username`:$Password@$NasIP`:$Port/$Database"

Write-Host "MongoDB URI: $mongoUri" -ForegroundColor Green

# 환경변수 설정
[Environment]::SetEnvironmentVariable("MONGODB_URI", $mongoUri, "User")
[Environment]::SetEnvironmentVariable("NAS_MONGODB_SERVER", $NasIP, "User")
$env:MONGODB_URI = $mongoUri

Write-Host "환경변수가 설정되었습니다." -ForegroundColor Green

# 연결 테스트
if ($TestConnection) {
    Write-Host "연결 테스트 중..." -ForegroundColor Yellow
    
    $testScript = @"
from pymongo import MongoClient
import sys
try:
    client = MongoClient('$mongoUri', serverSelectionTimeoutMS=5000)
    databases = client.list_database_names()
    print('✅ NAS MongoDB 연결 성공!')
    print('서버:', '$NasIP`:$Port')
    print('데이터베이스:', databases)
    
    # 기본 컬렉션 확인
    db = client['$Database']
    collections = db.list_collection_names()
    print('컬렉션:', collections)
    
    client.close()
except Exception as e:
    print('❌ 연결 실패:', str(e))
    print('다음을 확인해주세요:')
    print('1. NAS 서버의 MongoDB가 실행 중인지')
    print('2. 방화벽에서 포트 $Port가 열려있는지') 
    print('3. 사용자 인증 정보가 올바른지')
    sys.exit(1)
"@
    
    try {
        python -c $testScript
        if ($LASTEXITCODE -eq 0) {
            Write-Host "NAS MongoDB 연결이 성공했습니다!" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "연결 테스트 중 오류: $_" -ForegroundColor Red
    }
}

# 바탕화면 바로가기 생성
if ($CreateDesktopShortcut) {
    $desktopPath = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = "$desktopPath\X-AnyLabeling (NAS DB).lnk"
    
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = "D:\anaconda3\envs\labelme2\python.exe"
    $shortcut.Arguments = "`"c:\Users\pc\Desktop\202412이전\바탕화면\X-AnyLabeling-main\X-AnyLabeling-main\anylabeling\app.py`""
    $shortcut.WorkingDirectory = "c:\Users\pc\Desktop\202412이전\바탕화면\X-AnyLabeling-main\X-AnyLabeling-main"
    $shortcut.Description = "X-AnyLabeling with NAS MongoDB"
    $shortcut.Save()
    
    Write-Host "바탕화면 바로가기가 생성되었습니다: $shortcutPath" -ForegroundColor Green
}

Write-Host "`n=== 설정 완료 ===" -ForegroundColor Cyan
Write-Host "이제 X-AnyLabeling을 실행하면 NAS의 MongoDB에 연결됩니다." -ForegroundColor Green
Write-Host "다른 컴퓨터에서도 동일한 스크립트를 실행하세요." -ForegroundColor Yellow