# 다른 컴퓨터에서 MongoDB 서버에 연결하는 클라이언트 설정 스크립트

param(
    [string]$ServerIP = "",
    [string]$Username = "labeling_user",
    [string]$Password = "labeling_password",
    [string]$Database = "labeling_db",
    [int]$Port = 27017,
    [switch]$TestConnection,
    [switch]$SetEnvironment,
    [switch]$Interactive
)

function Test-ServerConnection {
    param(
        [string]$ServerIP,
        [string]$Username,
        [string]$Password,
        [string]$Database,
        [int]$Port
    )
    
    Write-Host "=== MongoDB 서버 연결 테스트 ===" -ForegroundColor Cyan
    Write-Host "서버: $ServerIP`:$Port" -ForegroundColor Yellow
    Write-Host "사용자: $Username" -ForegroundColor Yellow
    Write-Host "데이터베이스: $Database" -ForegroundColor Yellow
    
    # 기본 네트워크 연결 테스트
    Write-Host "`n1. 네트워크 연결 테스트..." -ForegroundColor Yellow
    $tcpTest = Test-NetConnection -ComputerName $ServerIP -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($tcpTest) {
        Write-Host "✅ 네트워크 연결 성공" -ForegroundColor Green
    } else {
        Write-Host "❌ 네트워크 연결 실패" -ForegroundColor Red
        Write-Host "가능한 원인:" -ForegroundColor Yellow
        Write-Host "- 서버 IP 주소가 잘못됨" -ForegroundColor White
        Write-Host "- MongoDB 서버가 실행되지 않음" -ForegroundColor White
        Write-Host "- 방화벽이 포트를 차단함" -ForegroundColor White
        Write-Host "- 네트워크 문제" -ForegroundColor White
        return $false
    }
    
    # MongoDB 연결 테스트
    Write-Host "2. MongoDB 인증 테스트..." -ForegroundColor Yellow
    
    $uri = "mongodb://$Username`:$Password@$ServerIP`:$Port/$Database"
    
    $testScript = @"
from pymongo import MongoClient
import sys
import json
from datetime import datetime

try:
    uri = '$uri'
    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    
    # 서버 정보 조회
    server_info = client.server_info()
    
    # 데이터베이스 접근 테스트
    db = client.get_database('$Database')
    collections = db.list_collection_names()
    
    # 간단한 읽기/쓰기 테스트
    test_collection = db.connection_test
    test_doc = {'test': True, 'timestamp': datetime.now().isoformat(), 'client_ip': 'test'}
    
    # 쓰기 테스트
    result = test_collection.insert_one(test_doc)
    
    # 읽기 테스트
    found_doc = test_collection.find_one({'_id': result.inserted_id})
    
    # 테스트 데이터 삭제
    test_collection.delete_one({'_id': result.inserted_id})
    
    # 통계 정보
    stats = {}
    if 'annotations' in collections:
        stats['annotations'] = db.annotations.count_documents({})
    if 'images' in collections:
        stats['images'] = db.images.count_documents({})
    
    result = {
        'success': True,
        'server_version': server_info.get('version'),
        'collections': collections,
        'stats': stats,
        'read_write_test': 'passed'
    }
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
    client.close()
    
except Exception as e:
    result = {
        'success': False,
        'error': str(e),
        'error_type': type(e).__name__
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(1)
"@
    
    try {
        $result = python -c $testScript | ConvertFrom-Json
        
        if ($result.success) {
            Write-Host "✅ MongoDB 연결 및 인증 성공!" -ForegroundColor Green
            Write-Host "서버 버전: $($result.server_version)" -ForegroundColor White
            Write-Host "컬렉션: $($result.collections -join ', ')" -ForegroundColor White
            Write-Host "읽기/쓰기 테스트: $($result.read_write_test)" -ForegroundColor White
            
            if ($result.stats) {
                Write-Host "데이터 통계:" -ForegroundColor White
                $result.stats.PSObject.Properties | ForEach-Object {
                    Write-Host "  $($_.Name): $($_.Value)개" -ForegroundColor Gray
                }
            }
            return $true
        } else {
            Write-Host "❌ MongoDB 연결 실패!" -ForegroundColor Red
            Write-Host "오류: $($result.error)" -ForegroundColor Red
            
            # 일반적인 오류 해결 방법 제안
            if ($result.error -like "*authentication failed*") {
                Write-Host "`n🔧 인증 오류 해결 방법:" -ForegroundColor Yellow
                Write-Host "- 사용자명/비밀번호 확인" -ForegroundColor White
                Write-Host "- 서버에서 사용자가 생성되었는지 확인" -ForegroundColor White
            } elseif ($result.error -like "*connection*") {
                Write-Host "`n🔧 연결 오류 해결 방법:" -ForegroundColor Yellow
                Write-Host "- 서버 IP 주소 확인" -ForegroundColor White
                Write-Host "- MongoDB 서비스 상태 확인" -ForegroundColor White
                Write-Host "- 방화벽 설정 확인" -ForegroundColor White
            }
            return $false
        }
    } catch {
        Write-Host "❌ 연결 테스트 중 오류: $_" -ForegroundColor Red
        return $false
    }
}

function Set-ClientEnvironment {
    param(
        [string]$ServerIP,
        [string]$Username,
        [string]$Password,
        [string]$Database,
        [int]$Port
    )
    
    Write-Host "=== 클라이언트 환경 설정 ===" -ForegroundColor Cyan
    
    $uri = "mongodb://$Username`:$Password@$ServerIP`:$Port/$Database"
    
    Write-Host "설정할 환경변수:" -ForegroundColor Yellow
    Write-Host "MONGODB_URI = $uri" -ForegroundColor White
    Write-Host "NAS_MONGODB_SERVER = $ServerIP" -ForegroundColor White
    
    $confirm = Read-Host "`n환경변수를 설정하시겠습니까? (y/N)"
    if ($confirm -eq 'y' -or $confirm -eq 'Y') {
        try {
            # 사용자 환경변수 설정
            [Environment]::SetEnvironmentVariable("MONGODB_URI", $uri, "User")
            [Environment]::SetEnvironmentVariable("NAS_MONGODB_SERVER", $ServerIP, "User")
            
            # 현재 세션에도 적용
            $env:MONGODB_URI = $uri
            $env:NAS_MONGODB_SERVER = $ServerIP
            
            Write-Host "✅ 환경변수가 설정되었습니다." -ForegroundColor Green
            Write-Host "다음에 애플리케이션을 시작하면 자동으로 이 서버에 연결됩니다." -ForegroundColor Yellow
            
            return $true
        } catch {
            Write-Host "❌ 환경변수 설정 중 오류: $_" -ForegroundColor Red
            return $false
        }
    } else {
        Write-Host "환경변수 설정이 취소되었습니다." -ForegroundColor Yellow
        return $false
    }
}

function Find-MongoServers {
    Write-Host "=== 네트워크에서 MongoDB 서버 찾기 ===" -ForegroundColor Cyan
    
    # 현재 네트워크 대역 확인
    $defaultGateway = Get-NetRoute -DestinationPrefix "0.0.0.0/0" | Select-Object -First 1 -ExpandProperty NextHop
    if ($defaultGateway -and $defaultGateway -ne "0.0.0.0") {
        $networkBase = $defaultGateway.Substring(0, $defaultGateway.LastIndexOf('.')) + "."
        Write-Host "검색 대역: $networkBase*" -ForegroundColor Yellow
        
        $found = @()
        Write-Host "MongoDB 서버 검색 중... (시간이 걸릴 수 있습니다)" -ForegroundColor Yellow
        
        # 병렬 검색
        $jobs = 1..254 | ForEach-Object {
            $ip = $networkBase + $_
            Start-Job -ScriptBlock {
                param($targetIP)
                if (Test-NetConnection -ComputerName $targetIP -Port 27017 -InformationLevel Quiet -WarningAction SilentlyContinue) {
                    return $targetIP
                }
            } -ArgumentList $ip
        }
        
        # 결과 수집 (최대 30초 대기)
        $timeout = 30
        $elapsed = 0
        while ($elapsed -lt $timeout -and ($jobs | Where-Object {$_.State -eq "Running"}).Count -gt 0) {
            Start-Sleep -Seconds 1
            $elapsed++
            
            # 완료된 작업에서 결과 수집
            $completed = $jobs | Where-Object {$_.State -eq "Completed"}
            foreach ($job in $completed) {
                $result = Receive-Job $job
                if ($result) {
                    $found += $result
                    Write-Host "MongoDB 서버 발견: $result" -ForegroundColor Green
                }
                Remove-Job $job
            }
        }
        
        # 남은 작업 정리
        $jobs | Remove-Job -Force
        
        if ($found.Count -eq 0) {
            Write-Host "❌ MongoDB 서버를 찾을 수 없습니다." -ForegroundColor Red
        } else {
            Write-Host "`n발견된 서버:" -ForegroundColor Green
            for ($i = 0; $i -lt $found.Count; $i++) {
                Write-Host "$($i + 1). $($found[$i])" -ForegroundColor White
            }
            
            return $found
        }
    } else {
        Write-Host "❌ 네트워크 게이트웨이를 찾을 수 없습니다." -ForegroundColor Red
    }
    
    return @()
}

function Show-InteractiveMenu {
    Write-Host "=== MongoDB 클라이언트 연결 설정 ===" -ForegroundColor Cyan
    
    while ($true) {
        Write-Host "`n옵션을 선택하세요:" -ForegroundColor Yellow
        Write-Host "1. 서버 IP 직접 입력" -ForegroundColor White
        Write-Host "2. 네트워크에서 서버 자동 검색" -ForegroundColor White
        Write-Host "3. 연결 테스트만 수행" -ForegroundColor White
        Write-Host "4. 현재 환경변수 확인" -ForegroundColor White
        Write-Host "0. 종료" -ForegroundColor White
        
        $choice = Read-Host "`n선택"
        
        switch ($choice) {
            "1" {
                $serverIP = Read-Host "MongoDB 서버 IP 주소를 입력하세요"
                if ($serverIP) {
                    $username = Read-Host "사용자명 (기본값: labeling_user)" 
                    if (-not $username) { $username = "labeling_user" }
                    
                    $password = Read-Host "비밀번호 (기본값: labeling_password)"
                    if (-not $password) { $password = "labeling_password" }
                    
                    if (Test-ServerConnection -ServerIP $serverIP -Username $username -Password $password -Database "labeling_db" -Port 27017) {
                        $setEnv = Read-Host "`n환경변수를 설정하시겠습니까? (y/N)"
                        if ($setEnv -eq 'y' -or $setEnv -eq 'Y') {
                            Set-ClientEnvironment -ServerIP $serverIP -Username $username -Password $password -Database "labeling_db" -Port 27017
                        }
                    }
                }
            }
            "2" {
                $servers = Find-MongoServers
                if ($servers.Count -gt 0) {
                    $selection = Read-Host "서버를 선택하세요 (1-$($servers.Count))"
                    $selectedIndex = [int]$selection - 1
                    if ($selectedIndex -ge 0 -and $selectedIndex -lt $servers.Count) {
                        $serverIP = $servers[$selectedIndex]
                        if (Test-ServerConnection -ServerIP $serverIP -Username "labeling_user" -Password "labeling_password" -Database "labeling_db" -Port 27017) {
                            $setEnv = Read-Host "`n환경변수를 설정하시겠습니까? (y/N)"
                            if ($setEnv -eq 'y' -or $setEnv -eq 'Y') {
                                Set-ClientEnvironment -ServerIP $serverIP -Username "labeling_user" -Password "labeling_password" -Database "labeling_db" -Port 27017
                            }
                        }
                    }
                }
            }
            "3" {
                $serverIP = Read-Host "테스트할 서버 IP"
                if ($serverIP) {
                    Test-ServerConnection -ServerIP $serverIP -Username "labeling_user" -Password "labeling_password" -Database "labeling_db" -Port 27017
                }
            }
            "4" {
                Write-Host "`n=== 현재 환경변수 ===" -ForegroundColor Cyan
                $mongoUri = $env:MONGODB_URI
                $nasServer = $env:NAS_MONGODB_SERVER
                
                if ($mongoUri) {
                    Write-Host "MONGODB_URI: $mongoUri" -ForegroundColor Green
                } else {
                    Write-Host "MONGODB_URI: 설정되지 않음" -ForegroundColor Red
                }
                
                if ($nasServer) {
                    Write-Host "NAS_MONGODB_SERVER: $nasServer" -ForegroundColor Green
                } else {
                    Write-Host "NAS_MONGODB_SERVER: 설정되지 않음" -ForegroundColor Red
                }
            }
            "0" { return }
            default { Write-Host "올바른 번호를 선택하세요." -ForegroundColor Red }
        }
    }
}

# 메인 실행
if ($TestConnection -and $ServerIP) {
    Test-ServerConnection -ServerIP $ServerIP -Username $Username -Password $Password -Database $Database -Port $Port
} elseif ($SetEnvironment -and $ServerIP) {
    if (Test-ServerConnection -ServerIP $ServerIP -Username $Username -Password $Password -Database $Database -Port $Port) {
        Set-ClientEnvironment -ServerIP $ServerIP -Username $Username -Password $Password -Database $Database -Port $Port
    }
} elseif ($Interactive) {
    Show-InteractiveMenu
} elseif ($ServerIP) {
    if (Test-ServerConnection -ServerIP $ServerIP -Username $Username -Password $Password -Database $Database -Port $Port) {
        Set-ClientEnvironment -ServerIP $ServerIP -Username $Username -Password $Password -Database $Database -Port $Port
    }
} else {
    Write-Host "=== MongoDB 클라이언트 연결 도구 ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "사용법:" -ForegroundColor Yellow
    Write-Host "  대화형 모드: -Interactive" -ForegroundColor White
    Write-Host "  직접 연결: -ServerIP '192.168.1.100'" -ForegroundColor White
    Write-Host "  연결 테스트: -ServerIP '192.168.1.100' -TestConnection" -ForegroundColor White
    Write-Host ""
    Write-Host "대화형 모드를 시작하려면 -Interactive 옵션을 사용하세요." -ForegroundColor Cyan
}