# MongoDB 네트워크 공유 설정 스크립트 (.env 파일 지원)
# 현재 컴퓨터의 MongoDB를 네트워크에서 접근 가능하도록 설정

param(
    [string]$EnvFile = ".env",
    [switch]$ShowCurrentConfig,
    [switch]$EnableNetworkAccess,
    [switch]$DisableNetworkAccess,
    [switch]$SetupFirewall,
    [switch]$CreateUsers,
    [switch]$ResetUsers,
    [switch]$TestConnection,
    [switch]$Interactive,
    [switch]$CreateEnvTemplate
)

# .env 파일 로드
. "$PSScriptRoot\load-env.ps1"

# 관리자 권한 확인
function Test-Administrator {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# 현재 설정 표시
function Show-CurrentConfiguration {
    Write-Host "=== 현재 MongoDB 네트워크 설정 ===" -ForegroundColor Cyan
    
    # .env 파일 설정 표시
    if (Test-Path $EnvFile) {
        Write-Host "📄 .env 파일 설정:" -ForegroundColor Yellow
        Show-EnvSummary
        Write-Host ""
    } else {
        Write-Host "⚠️ .env 파일이 없습니다. 기본값을 사용합니다." -ForegroundColor Yellow
    }
    
    # 서비스 상태
    $mongoService = Get-Service -Name "MongoDB" -ErrorAction SilentlyContinue
    if ($mongoService) {
        Write-Host "MongoDB 서비스: $($mongoService.Status)" -ForegroundColor $(if ($mongoService.Status -eq "Running") {"Green"} else {"Red"})
    } else {
        Write-Host "MongoDB 서비스: 설치되지 않음" -ForegroundColor Red
        return
    }
    
    # 포트 바인딩 상태
    $netstat = netstat -an | findstr ":$(Get-EnvValue 'MONGODB_PORT' '27017')"
    Write-Host "포트 바인딩 상태:" -ForegroundColor Yellow
    foreach ($line in $netstat) {
        Write-Host "  $line" -ForegroundColor White
    }
    
    # 현재 컴퓨터 IP
    $ipAddresses = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.*"}).IPAddress
    Write-Host "현재 컴퓨터 IP 주소:" -ForegroundColor Yellow
    foreach ($ip in $ipAddresses) {
        $configuredIP = Get-EnvValue 'MONGODB_SERVER_IP' 'localhost'
        $color = if ($ip -eq $configuredIP) {"Green"} else {"White"}
        $marker = if ($ip -eq $configuredIP) {" ← .env 설정"} else {""}
        Write-Host "  $ip$marker" -ForegroundColor $color
    }
    
    # 설정 파일 확인
    $configPath = "C:\Program Files\MongoDB\Server\8.0\bin\mongod.cfg"
    if (Test-Path $configPath) {
        Write-Host "`n현재 bindIp 설정:" -ForegroundColor Yellow
        $bindIpLine = Get-Content $configPath | Where-Object {$_ -match "bindIp"}
        if ($bindIpLine) {
            $expectedBindIp = Get-EnvValue 'MONGODB_BIND_IP' '127.0.0.1'
            $actualBindIp = ($bindIpLine -split ':')[1].Trim()
            $color = if ($actualBindIp -eq $expectedBindIp) {"Green"} else {"Yellow"}
            Write-Host "  파일: $bindIpLine" -ForegroundColor $color
            Write-Host "  .env: bindIp: $expectedBindIp" -ForegroundColor White
        }
    }
    
    # 방화벽 규칙 확인
    $firewallRule = Get-NetFirewallRule -DisplayName "*MongoDB*" -ErrorAction SilentlyContinue
    if ($firewallRule) {
        Write-Host "방화벽 규칙: 설정됨" -ForegroundColor Green
    } else {
        Write-Host "방화벽 규칙: 설정되지 않음" -ForegroundColor Red
    }
    
    Write-Host ""
}
    
    # 방화벽 규칙 확인
    $firewallRule = Get-NetFirewallRule -DisplayName "*MongoDB*" -ErrorAction SilentlyContinue
    if ($firewallRule) {
        Write-Host "방화벽 규칙: 설정됨" -ForegroundColor Green
    } else {
        Write-Host "방화벽 규칙: 설정되지 않음" -ForegroundColor Red
    }
    
    Write-Host ""
}

# 네트워크 접근 활성화
function Enable-NetworkAccess {
    if (-not (Test-Administrator)) {
        Write-Host "❌ 관리자 권한이 필요합니다. PowerShell을 관리자로 실행해주세요." -ForegroundColor Red
        return $false
    }
    
    Write-Host "=== MongoDB 네트워크 접근 활성화 (.env 기반) ===" -ForegroundColor Cyan
    
    # .env에서 설정 읽기
    $targetBindIP = Get-EnvValue 'MONGODB_BIND_IP' '0.0.0.0'
    $port = Get-EnvValue 'MONGODB_PORT' '27017'
    
    Write-Host "설정할 바인딩 IP: $targetBindIP" -ForegroundColor Yellow
    Write-Host "포트: $port" -ForegroundColor Yellow
    
    $configPath = "C:\Program Files\MongoDB\Server\8.0\bin\mongod.cfg"
    $backupPath = $configPath + ".backup." + (Get-Date -Format "yyyyMMdd_HHmmss")
    
    try {
        # 백업 생성
        Copy-Item $configPath $backupPath
        Write-Host "✅ 설정 파일 백업 완료: $backupPath" -ForegroundColor Green
        
        # 설정 파일 읽기
        $content = Get-Content $configPath
        
        # bindIp 설정 변경
        $newContent = @()
        $bindIpUpdated = $false
        $portUpdated = $false
        
        foreach ($line in $content) {
            if ($line -match "^\s*bindIp:\s*") {
                $newContent += "  bindIp: $targetBindIP  # .env에서 설정됨"
                Write-Host "✅ bindIp를 $targetBindIP으로 변경" -ForegroundColor Green
                $bindIpUpdated = $true
            } elseif ($line -match "^\s*port:\s*") {
                $newContent += "  port: $port  # .env에서 설정됨"
                Write-Host "✅ 포트를 $port으로 설정" -ForegroundColor Green
                $portUpdated = $true
            } else {
                $newContent += $line
            }
        }
        
        # 파일 쓰기
        $newContent | Set-Content $configPath -Encoding UTF8
        
        # MongoDB 서비스 재시작
        Write-Host "MongoDB 서비스 재시작 중..." -ForegroundColor Yellow
        Restart-Service -Name "MongoDB" -Force
        
        # 잠시 대기
        Start-Sleep -Seconds 3
        
        # 상태 확인
        $service = Get-Service -Name "MongoDB"
        if ($service.Status -eq "Running") {
            Write-Host "✅ MongoDB 서비스 재시작 완료" -ForegroundColor Green
            
            # 새 포트 바인딩 확인
            Start-Sleep -Seconds 2
            $netstat = netstat -an | findstr ":$port"
            Write-Host "새 포트 바인딩:" -ForegroundColor Yellow
            foreach ($line in $netstat) {
                Write-Host "  $line" -ForegroundColor White
            }
        } else {
            Write-Host "❌ MongoDB 서비스 재시작 실패" -ForegroundColor Red
            return $false
        }
        
        return $true
        
    } catch {
        Write-Host "❌ 설정 변경 중 오류: $_" -ForegroundColor Red
        # 백업에서 복원
        if (Test-Path $backupPath) {
            Copy-Item $backupPath $configPath
            Write-Host "설정을 백업에서 복원했습니다." -ForegroundColor Yellow
        }
        return $false
    }
}

# 방화벽 설정
function Setup-Firewall {
    if (-not (Test-Administrator)) {
        Write-Host "❌ 관리자 권한이 필요합니다." -ForegroundColor Red
        return $false
    }
    
    Write-Host "=== Windows 방화벽 설정 (.env 기반) ===" -ForegroundColor Cyan
    
    # .env에서 설정 읽기
    $port = Get-EnvValue 'MONGODB_PORT' '27017'
    $allowedNetworks = Get-EnvValue 'FIREWALL_ALLOWED_NETWORKS' 'all'
    $autoConfig = Get-EnvBool 'FIREWALL_AUTO_CONFIGURE' $true
    
    if (-not $autoConfig) {
        Write-Host "⚠️ .env에서 FIREWALL_AUTO_CONFIGURE=false로 설정되어 있습니다." -ForegroundColor Yellow
        $proceed = Read-Host "방화벽을 설정하시겠습니까? (y/N)"
        if ($proceed -ne 'y' -and $proceed -ne 'Y') {
            return $false
        }
    }
    
    Write-Host "포트: $port" -ForegroundColor Yellow
    Write-Host "허용 네트워크: $allowedNetworks" -ForegroundColor Yellow
    
    try {
        # 기존 규칙 확인 및 삭제
        $existingRule = Get-NetFirewallRule -DisplayName "MongoDB Server*" -ErrorAction SilentlyContinue
        if ($existingRule) {
            Remove-NetFirewallRule -DisplayName "MongoDB Server*"
            Write-Host "기존 방화벽 규칙 삭제됨" -ForegroundColor Yellow
        }
        
        # 새 규칙 생성
        if ($allowedNetworks -eq 'all') {
            New-NetFirewallRule -DisplayName "MongoDB Server" -Direction Inbound -Protocol TCP -LocalPort $port -Action Allow -Profile Any
            Write-Host "✅ MongoDB 포트($port) 방화벽 규칙 생성 완료 (모든 IP 허용)" -ForegroundColor Green
        } else {
            New-NetFirewallRule -DisplayName "MongoDB Server (Restricted)" -Direction Inbound -Protocol TCP -LocalPort $port -Action Allow -RemoteAddress $allowedNetworks -Profile Any
            Write-Host "✅ MongoDB 포트($port) 제한된 방화벽 규칙 생성: $allowedNetworks" -ForegroundColor Green
        }
        
        return $true
        
    } catch {
        Write-Host "❌ 방화벽 설정 중 오류: $_" -ForegroundColor Red
        return $false
    }
}

# MongoDB 사용자 생성
function Create-MongoUsers {
    Write-Host "=== MongoDB 사용자 인증 설정 (.env 기반) ===" -ForegroundColor Cyan
    # 비밀번호는 반드시 .env로 관리합니다. 이 스크립트는 .env 값을 사용하며 화면 출력 시 마스킹합니다.
    
    # .env에서 인증 정보 읽기
    $adminUser = Get-EnvValue 'MONGODB_ADMIN_USERNAME' 'admin'
    $adminPass = Get-EnvValue 'MONGODB_ADMIN_PASSWORD' 'admin123!@#'
    $appUser = Get-EnvValue 'MONGODB_APP_USERNAME' 'labeling_user'
    $appPass = Get-EnvValue 'MONGODB_APP_PASSWORD' 'labeling_password'
    $database = Get-EnvValue 'MONGODB_DATABASE' 'labeling_db'
    $enableAuth = Get-EnvBool 'MONGODB_ENABLE_AUTH' $true
    
    Write-Host "관리자 사용자: $adminUser" -ForegroundColor Yellow
    Write-Host "앱 사용자: $appUser" -ForegroundColor Yellow
    Write-Host "데이터베이스: $database" -ForegroundColor Yellow
    Write-Host "인증 활성화: $enableAuth" -ForegroundColor Yellow
    
        $createScript = @"
// 사용자 동기화: 존재 시 updateUser, 없으면 createUser
use admin
const adminUser = "$adminUser";
const adminPass = "$adminPass";
if (db.getUser(adminUser)) {
    db.updateUser(adminUser, { pwd: adminPass, roles: ["userAdminAnyDatabase", "dbAdminAnyDatabase", "readWriteAnyDatabase"] });
    print("[OK] admin 사용자 업데이트 완료");
} else {
    db.createUser({ user: adminUser, pwd: adminPass, roles: ["userAdminAnyDatabase", "dbAdminAnyDatabase", "readWriteAnyDatabase"] });
    print("[OK] admin 사용자 생성 완료");
}

use $database
const appUser = "$appUser";
const appPass = "$appPass";
if (db.getUser(appUser)) {
    db.updateUser(appUser, { pwd: appPass, roles: ["readWrite"] });
    print("[OK] 앱 사용자 업데이트 완료");
} else {
    db.createUser({ user: appUser, pwd: appPass, roles: ["readWrite"] });
    print("[OK] 앱 사용자 생성 완료");
}

print("[SUCCESS] 사용자 동기화 완료");
"@
    
    try {
        # MongoDB shell에서 사용자 생성
        $scriptPath = "$env:TEMP\create_mongo_users.js"
        $createScript | Set-Content $scriptPath
        
        $mongoShell = "C:\Program Files\MongoDB\Server\8.0\bin\mongosh.exe"
        if (-not (Test-Path $mongoShell)) {
            $mongoShell = "C:\Program Files\MongoDB\Server\8.0\bin\mongo.exe"
        }
        
        if (Test-Path $mongoShell) {
            & $mongoShell $scriptPath
            Remove-Item $scriptPath
        } else {
            Write-Host "❌ MongoDB shell을 찾을 수 없습니다." -ForegroundColor Red
            return $false
        }
        
        if ($enableAuth) {
            Write-Host "`n인증을 활성화하겠습니다..." -ForegroundColor Yellow
            Enable-Authentication
        } else {
            Write-Host "⚠️ .env에서 MONGODB_ENABLE_AUTH=false로 설정되어 있습니다." -ForegroundColor Yellow
            Write-Host "보안을 위해 인증 활성화를 권장합니다." -ForegroundColor Yellow
        }
        
        return $true
        
    } catch {
        Write-Host "❌ 사용자 생성 중 오류: $_" -ForegroundColor Red
        return $false
    }
}

# 인증 활성화
function Enable-Authentication {
    if (-not (Test-Administrator)) {
        Write-Host "❌ 관리자 권한이 필요합니다." -ForegroundColor Red
        return $false
    }
    
    $configPath = "C:\Program Files\MongoDB\Server\8.0\bin\mongod.cfg"
    
    try {
        $content = Get-Content $configPath
        $newContent = @()
        $securitySectionFound = $false
        
        foreach ($line in $content) {
            if ($line -match "^#security:") {
                $newContent += "security:"
                $newContent += "  authorization: enabled"
                $securitySectionFound = $true
                Write-Host "✅ 인증 설정 활성화" -ForegroundColor Green
            } elseif ($line -match "^security:" -and -not $securitySectionFound) {
                $newContent += $line
                $newContent += "  authorization: enabled"
                $securitySectionFound = $true
            } else {
                $newContent += $line
            }
        }
        
        # security 섹션이 없으면 추가
        if (-not $securitySectionFound) {
            $newContent += ""
            $newContent += "security:"
            $newContent += "  authorization: enabled"
        }
        
        $newContent | Set-Content $configPath -Encoding UTF8
        
        # 서비스 재시작
        Restart-Service -Name "MongoDB" -Force
        Start-Sleep -Seconds 3
        
        Write-Host "✅ 인증이 활성화되었습니다. 이제 사용자명/비밀번호가 필요합니다." -ForegroundColor Green
        
    } catch {
        Write-Host "❌ 인증 설정 중 오류: $_" -ForegroundColor Red
        return $false
    }
}

# 연결 테스트
function Test-NetworkConnection {
    Write-Host "=== 네트워크 연결 테스트 ===" -ForegroundColor Cyan
    
    # 현재 컴퓨터 IP
    $currentIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.*"}).IPAddress | Select-Object -First 1
    
    if (-not $currentIP) {
        Write-Host "❌ IP 주소를 확인할 수 없습니다." -ForegroundColor Red
        return
    }
    
    Write-Host "테스트할 IP: $currentIP" -ForegroundColor Yellow
    
    # Python 연결 테스트 스크립트
    $testScript = @"
from pymongo import MongoClient
import sys

def test_connection(uri):
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        server_info = client.server_info()
        databases = client.list_database_names()
        
        print(f"✅ 연결 성공!")
        print(f"서버 버전: {server_info.get('version')}")
        print(f"데이터베이스: {', '.join(databases)}")
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ 연결 실패: {e}")
        return False

# 테스트할 URI들
test_uris = [
    "mongodb://$currentIP:27017/",
    "mongodb://labeling_user:labeling_password@$currentIP:27017/labeling_db"
]

for i, uri in enumerate(test_uris, 1):
    print(f"\\n테스트 {i}: {uri}")
    test_connection(uri)
"@
    
    try {
        python -c $testScript
    } catch {
        Write-Host "❌ Python 테스트 실행 중 오류: $_" -ForegroundColor Red
    }
}

# 네트워크 접근 비활성화
function Disable-NetworkAccess {
    if (-not (Test-Administrator)) {
        Write-Host "❌ 관리자 권한이 필요합니다." -ForegroundColor Red
        return $false
    }
    
    Write-Host "=== MongoDB 네트워크 접근 비활성화 ===" -ForegroundColor Cyan
    
    $configPath = "C:\Program Files\MongoDB\Server\8.0\bin\mongod.cfg"
    
    try {
        $content = Get-Content $configPath
        $newContent = @()
        
        foreach ($line in $content) {
            if ($line -match "bindIp.*0\.0\.0\.0") {
                $newContent += "  bindIp: 127.0.0.1"
                Write-Host "✅ bindIp를 localhost로 변경" -ForegroundColor Green
            } else {
                $newContent += $line
            }
        }
        
        $newContent | Set-Content $configPath -Encoding UTF8
        Restart-Service -Name "MongoDB" -Force
        
        # 방화벽 규칙 삭제
        Remove-NetFirewallRule -DisplayName "*MongoDB*" -ErrorAction SilentlyContinue
        Write-Host "✅ 방화벽 규칙 삭제됨" -ForegroundColor Green
        
        Write-Host "✅ 네트워크 접근이 비활성화되었습니다." -ForegroundColor Green
        
    } catch {
        Write-Host "❌ 설정 변경 중 오류: $_" -ForegroundColor Red
        return $false
    }
}

# 대화형 메뉴
function Show-InteractiveMenu {
    while ($true) {
        Write-Host "`n=== MongoDB 네트워크 공유 설정 ===" -ForegroundColor Cyan
        Write-Host "현재 컴퓨터 IP: $((Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.*'}).IPAddress -join ', ')" -ForegroundColor Green
        Write-Host ""
        Write-Host "1. 현재 설정 확인" -ForegroundColor White
        Write-Host "2. 네트워크 접근 활성화" -ForegroundColor White
        Write-Host "3. 방화벽 설정" -ForegroundColor White
        Write-Host "4. 사용자 인증 설정" -ForegroundColor White
        Write-Host "5. 연결 테스트" -ForegroundColor White
        Write-Host "6. 네트워크 접근 비활성화" -ForegroundColor White
        Write-Host "7. 전체 설정 (권장)" -ForegroundColor Yellow
        Write-Host "0. 종료" -ForegroundColor White
        
        $choice = Read-Host "`n선택"
        
        switch ($choice) {
            "1" { Show-CurrentConfiguration }
            "2" { Enable-NetworkAccess }
            "3" { Setup-Firewall }
            "4" { Create-MongoUsers }
            "5" { Test-NetworkConnection }
            "6" { Disable-NetworkAccess }
            "7" { 
                Write-Host "전체 설정을 시작합니다..." -ForegroundColor Yellow
                if (Enable-NetworkAccess) {
                    Setup-Firewall
                    Create-MongoUsers
                    Test-NetworkConnection
                    
                    Write-Host "`n=== 설정 완료 ===" -ForegroundColor Green
                    Write-Host "다른 컴퓨터에서 연결할 때 사용할 정보:" -ForegroundColor Yellow
                    $currentIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.*"}).IPAddress | Select-Object -First 1
                    $port = Get-EnvValue 'MONGODB_PORT' '27017'
                    $dbName = Get-EnvValue 'MONGODB_DATABASE' 'labeling_db'
                    $appUser = Get-EnvValue 'MONGODB_APP_USERNAME' 'labeling_user'
                    $appPass = Get-EnvValue 'MONGODB_APP_PASSWORD' 'labeling_password'
                    $masked = ('*' * ($appPass.Length))
                    Write-Host "서버 IP: $currentIP" -ForegroundColor White
                    Write-Host "포트: $port" -ForegroundColor White
                    Write-Host "사용자: $appUser" -ForegroundColor White
                    Write-Host "비밀번호: $masked" -ForegroundColor White
                    Write-Host "URI: mongodb://$appUser:<redacted>@$currentIP:$port/$dbName?authSource=$dbName" -ForegroundColor White
                }
            }
            "0" { return }
            default { Write-Host "올바른 번호를 선택하세요." -ForegroundColor Red }
        }
    }
}

# 메인 실행
if ($CreateEnvTemplate) {
    if (Test-Path ".env.template") {
        if (-not (Test-Path ".env")) {
            Copy-Item ".env.template" ".env"
            Write-Host "✅ .env 파일이 템플릿에서 생성되었습니다." -ForegroundColor Green
            Write-Host "실제 값을 입력하기 위해 .env 파일을 편집하세요." -ForegroundColor Yellow
        } else {
            Write-Host "⚠️ .env 파일이 이미 존재합니다." -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ .env.template 파일을 찾을 수 없습니다." -ForegroundColor Red
    }
    return
}

# .env 파일 로드
if (Test-Path $EnvFile) {
    if (-not (Load-EnvFile -EnvFile $EnvFile)) {
        Write-Host "❌ .env 파일 로드에 실패했습니다." -ForegroundColor Red
        return
    }
} else {
    Write-Host "⚠️ .env 파일이 없습니다. 기본값을 사용합니다." -ForegroundColor Yellow
    Write-Host "템플릿을 생성하려면: -CreateEnvTemplate 옵션을 사용하세요." -ForegroundColor Cyan
}

if ($ShowCurrentConfig) {
    Show-CurrentConfiguration
} elseif ($EnableNetworkAccess) {
    Enable-NetworkAccess
} elseif ($DisableNetworkAccess) {
    Disable-NetworkAccess
} elseif ($SetupFirewall) {
    Setup-Firewall
} elseif ($CreateUsers) {
    Create-MongoUsers
} elseif ($TestConnection) {
    Test-NetworkConnection
} elseif ($Interactive) {
    Show-InteractiveMenu
} else {
    Show-CurrentConfiguration
    Write-Host "`n사용법:" -ForegroundColor Cyan
    Write-Host "  대화형 모드: -Interactive" -ForegroundColor White
    Write-Host "  .env 템플릿 생성: -CreateEnvTemplate" -ForegroundColor White
    Write-Host "  관리자 권한으로 실행하면 모든 기능을 사용할 수 있습니다." -ForegroundColor Yellow
}