# 현재 NAS MongoDB 설정 관리 스크립트

param(
    [string]$NewIP = "",
    [switch]$ShowConfig,
    [switch]$TestConnection,
    [switch]$ResetConfig,
    [switch]$Interactive
)

function Show-CurrentConfig {
    Write-Host "=== 현재 NAS MongoDB 설정 ===" -ForegroundColor Cyan
    
    $mongoUri = $env:MONGODB_URI
    $nasServer = $env:NAS_MONGODB_SERVER
    
    if ($mongoUri) {
        Write-Host "MongoDB URI: $mongoUri" -ForegroundColor Green
        
        # URI에서 정보 추출
        if ($mongoUri -match "mongodb://(.+?)@(.+?):(\d+)/(.+)") {
            $credentials = $matches[1]
            $server = $matches[2]
            $port = $matches[3]
            $database = $matches[4]
            
            Write-Host "서버: $server" -ForegroundColor Yellow
            Write-Host "포트: $port" -ForegroundColor Yellow
            Write-Host "데이터베이스: $database" -ForegroundColor Yellow
            Write-Host "인증: $credentials" -ForegroundColor Yellow
        }
    } else {
        Write-Host "MongoDB URI가 설정되지 않았습니다." -ForegroundColor Red
    }
    
    if ($nasServer) {
        Write-Host "NAS 서버: $nasServer" -ForegroundColor Green
    } else {
        Write-Host "NAS 서버가 설정되지 않았습니다." -ForegroundColor Red
    }
    
    Write-Host ""
}

function Test-MongoConnection {
    Write-Host "=== 연결 테스트 ===" -ForegroundColor Cyan
    
    $mongoUri = $env:MONGODB_URI
    if (-not $mongoUri) {
        Write-Host "MongoDB URI가 설정되지 않았습니다." -ForegroundColor Red
        return $false
    }
    
    $testScript = @"
from pymongo import MongoClient
import sys
import json
from datetime import datetime

try:
    client = MongoClient('$mongoUri', serverSelectionTimeoutMS=5000)
    
    # 서버 정보
    server_info = client.server_info()
    databases = client.list_database_names()
    
    # 데이터베이스 상태
    db = client.get_database('labeling_db')
    collections = db.list_collection_names()
    
    # 통계 정보
    stats = {}
    if 'annotations' in collections:
        stats['annotations'] = db.annotations.count_documents({})
    if 'images' in collections:
        stats['images'] = db.images.count_documents({})
    
    result = {
        'success': True,
        'server_version': server_info.get('version'),
        'databases': databases,
        'collections': collections,
        'stats': stats,
        'connection_time': datetime.now().isoformat()
    }
    
    print(json.dumps(result, indent=2))
    client.close()
    
except Exception as e:
    result = {
        'success': False,
        'error': str(e),
        'error_type': type(e).__name__
    }
    print(json.dumps(result, indent=2))
    sys.exit(1)
"@
    
    try {
        $result = python -c $testScript | ConvertFrom-Json
        
        if ($result.success) {
            Write-Host "✅ 연결 성공!" -ForegroundColor Green
            Write-Host "서버 버전: $($result.server_version)" -ForegroundColor Yellow
            Write-Host "데이터베이스: $($result.databases -join ', ')" -ForegroundColor Yellow
            Write-Host "컬렉션: $($result.collections -join ', ')" -ForegroundColor Yellow
            
            if ($result.stats) {
                Write-Host "데이터 통계:" -ForegroundColor Yellow
                $result.stats.PSObject.Properties | ForEach-Object {
                    Write-Host "  $($_.Name): $($_.Value)개" -ForegroundColor White
                }
            }
            return $true
        } else {
            Write-Host "❌ 연결 실패!" -ForegroundColor Red
            Write-Host "오류: $($result.error)" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "❌ 연결 테스트 중 오류: $_" -ForegroundColor Red
        return $false
    }
}

function Set-NASConfig {
    param([string]$IPAddress)
    
    Write-Host "=== NAS 설정 변경 ===" -ForegroundColor Cyan
    
    if (-not $IPAddress) {
        $IPAddress = Read-Host "새로운 NAS IP 주소를 입력하세요"
    }
    
    # IP 주소 유효성 검사
    if (-not ($IPAddress -match '^(\d{1,3}\.){3}\d{1,3}$')) {
        Write-Host "올바른 IP 주소 형식이 아닙니다." -ForegroundColor Red
        return $false
    }
    
    # 기본 설정값
    $username = "labeling_user"
    $password = "labeling_password"
    $database = "labeling_db"
    $port = 27017
    
    # 새 URI 생성
    $newUri = "mongodb://$username`:$password@$IPAddress`:$port/$database"
    
    Write-Host "새 연결 정보:" -ForegroundColor Yellow
    Write-Host "  서버: $IPAddress" -ForegroundColor White
    Write-Host "  URI: $newUri" -ForegroundColor White
    
    $confirm = Read-Host "설정을 변경하시겠습니까? (y/N)"
    if ($confirm -eq 'y' -or $confirm -eq 'Y') {
        # 환경변수 설정
        [Environment]::SetEnvironmentVariable("MONGODB_URI", $newUri, "User")
        [Environment]::SetEnvironmentVariable("NAS_MONGODB_SERVER", $IPAddress, "User")
        
        # 현재 세션에도 적용
        $env:MONGODB_URI = $newUri
        $env:NAS_MONGODB_SERVER = $IPAddress
        
        Write-Host "✅ 설정이 변경되었습니다." -ForegroundColor Green
        
        # 연결 테스트
        Write-Host "새 설정으로 연결 테스트 중..." -ForegroundColor Yellow
        Test-MongoConnection
        
        return $true
    } else {
        Write-Host "설정 변경이 취소되었습니다." -ForegroundColor Yellow
        return $false
    }
}

function Reset-NASConfig {
    Write-Host "=== 설정 초기화 ===" -ForegroundColor Cyan
    
    $confirm = Read-Host "모든 MongoDB 설정을 삭제하시겠습니까? (y/N)"
    if ($confirm -eq 'y' -or $confirm -eq 'Y') {
        [Environment]::SetEnvironmentVariable("MONGODB_URI", "", "User")
        [Environment]::SetEnvironmentVariable("NAS_MONGODB_SERVER", "", "User")
        
        $env:MONGODB_URI = ""
        $env:NAS_MONGODB_SERVER = ""
        
        Write-Host "✅ 설정이 초기화되었습니다." -ForegroundColor Green
        return $true
    } else {
        Write-Host "초기화가 취소되었습니다." -ForegroundColor Yellow
        return $false
    }
}

function Show-InteractiveMenu {
    while ($true) {
        Write-Host "`n=== NAS MongoDB 설정 관리 ===" -ForegroundColor Cyan
        Write-Host "1. 현재 설정 확인" -ForegroundColor White
        Write-Host "2. 연결 테스트" -ForegroundColor White
        Write-Host "3. NAS IP 변경" -ForegroundColor White
        Write-Host "4. 설정 초기화" -ForegroundColor White
        Write-Host "5. NAS 서버 자동 검색" -ForegroundColor White
        Write-Host "0. 종료" -ForegroundColor White
        
        $choice = Read-Host "`n선택"
        
        switch ($choice) {
            "1" { Show-CurrentConfig }
            "2" { Test-MongoConnection }
            "3" { Set-NASConfig }
            "4" { Reset-NASConfig }
            "5" { 
                Write-Host "네트워크에서 MongoDB 서버 검색 중..." -ForegroundColor Yellow
                # 간단한 네트워크 스캔
                $found = @()
                $network = (Get-NetRoute -DestinationPrefix "0.0.0.0/0").NextHop | Where-Object {$_ -ne "0.0.0.0"} | Select-Object -First 1
                if ($network) {
                    $networkBase = $network.Substring(0, $network.LastIndexOf('.')) + "."
                    Write-Host "스캔 범위: $networkBase*" -ForegroundColor Yellow
                    
                    1..254 | ForEach-Object -Parallel {
                        $ip = $using:networkBase + $_
                        if (Test-NetConnection -ComputerName $ip -Port 27017 -InformationLevel Quiet -WarningAction SilentlyContinue) {
                            return $ip
                        }
                    } -ThrottleLimit 50 | ForEach-Object {
                        $found += $_
                        Write-Host "MongoDB 서버 발견: $_" -ForegroundColor Green
                    }
                }
                
                if ($found.Count -eq 0) {
                    Write-Host "MongoDB 서버를 찾을 수 없습니다." -ForegroundColor Red
                } else {
                    Write-Host "`n발견된 서버 중 하나를 선택하여 설정하시겠습니까?" -ForegroundColor Yellow
                    for ($i = 0; $i -lt $found.Count; $i++) {
                        Write-Host "$($i+1). $($found[$i])" -ForegroundColor White
                    }
                    $serverChoice = Read-Host "서버 번호 선택 (Enter로 건너뛰기)"
                    if ($serverChoice -and $serverChoice -le $found.Count) {
                        Set-NASConfig -IPAddress $found[$serverChoice-1]
                    }
                }
            }
            "0" { return }
            default { Write-Host "올바른 번호를 선택하세요." -ForegroundColor Red }
        }
    }
}

# 메인 실행 로직
if ($ShowConfig) {
    Show-CurrentConfig
} elseif ($TestConnection) {
    Test-MongoConnection
} elseif ($ResetConfig) {
    Reset-NASConfig
} elseif ($NewIP) {
    Set-NASConfig -IPAddress $NewIP
} elseif ($Interactive) {
    Show-InteractiveMenu
} else {
    # 기본 동작: 현재 설정 표시
    Show-CurrentConfig
    Write-Host "`n대화형 모드를 실행하려면: -Interactive 옵션을 사용하세요" -ForegroundColor Cyan
}