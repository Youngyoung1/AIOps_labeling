# 환경별 MongoDB 설정 관리 도구
# 개발, 테스트, 운영 환경을 쉽게 전환하고 관리할 수 있는 도구

param(
    [string]$Environment = "",
    [switch]$ListEnvironments,
    [switch]$CreateEnvironment,
    [switch]$SwitchEnvironment,
    [switch]$BackupCurrent,
    [switch]$ShowDifferences,
    [switch]$Interactive
)

# 환경별 설정 템플릿
$EnvironmentTemplates = @{
    "development" = @{
        "ENVIRONMENT" = "development"
        "DEBUG_MODE" = "true"
        "MONGODB_SERVER_IP" = "localhost"
        "MONGODB_PORT" = "27017"
        "MONGODB_DATABASE" = "labeling_db_dev"
        "MONGODB_ADMIN_USERNAME" = "admin"
        "MONGODB_ADMIN_PASSWORD" = "admin123!@#"
        "MONGODB_APP_USERNAME" = "labeling_user"
        "MONGODB_APP_PASSWORD" = "labeling_password"
        "MONGODB_ENABLE_NETWORK_ACCESS" = "false"
        "MONGODB_BIND_IP" = "127.0.0.1"
        "MONGODB_ENABLE_AUTH" = "false"
        "MONGODB_USE_SSL" = "false"
        "FIREWALL_AUTO_CONFIGURE" = "false"
        "FIREWALL_ALLOWED_NETWORKS" = "all"
        "DISABLE_VECTOR_SEARCH" = "false"
        "MONGODB_CONNECT_TIMEOUT" = "10000"
        "MONGODB_SERVER_SELECTION_TIMEOUT" = "5000"
        "LOG_LEVEL" = "DEBUG"
        "AUTO_BACKUP_ENABLED" = "false"
        "BACKUP_INTERVAL_HOURS" = "24"
        "BACKUP_RETENTION_DAYS" = "3"
        "BACKUP_PATH" = "./backups/dev"
    }
    "testing" = @{
        "ENVIRONMENT" = "testing"
        "DEBUG_MODE" = "true"
        "MONGODB_SERVER_IP" = "localhost"
        "MONGODB_PORT" = "27018"
        "MONGODB_DATABASE" = "labeling_db_test"
        "MONGODB_ADMIN_USERNAME" = "test_admin"
        "MONGODB_ADMIN_PASSWORD" = "test_admin_pass_2024!"
        "MONGODB_APP_USERNAME" = "test_user"
        "MONGODB_APP_PASSWORD" = "test_user_pass_2024!"
        "MONGODB_ENABLE_NETWORK_ACCESS" = "false"
        "MONGODB_BIND_IP" = "127.0.0.1"
        "MONGODB_ENABLE_AUTH" = "true"
        "MONGODB_USE_SSL" = "false"
        "FIREWALL_AUTO_CONFIGURE" = "false"
        "FIREWALL_ALLOWED_NETWORKS" = "127.0.0.1"
        "DISABLE_VECTOR_SEARCH" = "true"
        "MONGODB_CONNECT_TIMEOUT" = "5000"
        "MONGODB_SERVER_SELECTION_TIMEOUT" = "3000"
        "LOG_LEVEL" = "INFO"
        "AUTO_BACKUP_ENABLED" = "false"
        "BACKUP_INTERVAL_HOURS" = "12"
        "BACKUP_RETENTION_DAYS" = "1"
        "BACKUP_PATH" = "./backups/test"
    }
    "production" = @{
        "ENVIRONMENT" = "production"
        "DEBUG_MODE" = "false"
        "MONGODB_SERVER_IP" = "192.168.1.100"
        "MONGODB_PORT" = "27017"
        "MONGODB_DATABASE" = "labeling_db"
        "MONGODB_ADMIN_USERNAME" = "prod_admin"
        "MONGODB_ADMIN_PASSWORD" = "CHANGE_THIS_STRONG_ADMIN_PASSWORD!"
        "MONGODB_APP_USERNAME" = "labeling_app"
        "MONGODB_APP_PASSWORD" = "CHANGE_THIS_STRONG_APP_PASSWORD!"
        "MONGODB_ENABLE_NETWORK_ACCESS" = "true"
        "MONGODB_BIND_IP" = "0.0.0.0"
        "MONGODB_ENABLE_AUTH" = "true"
        "MONGODB_USE_SSL" = "true"
        "FIREWALL_AUTO_CONFIGURE" = "true"
        "FIREWALL_ALLOWED_NETWORKS" = "192.168.1.0/24"
        "DISABLE_VECTOR_SEARCH" = "false"
        "MONGODB_CONNECT_TIMEOUT" = "15000"
        "MONGODB_SERVER_SELECTION_TIMEOUT" = "10000"
        "LOG_LEVEL" = "WARNING"
        "AUTO_BACKUP_ENABLED" = "true"
        "BACKUP_INTERVAL_HOURS" = "6"
        "BACKUP_RETENTION_DAYS" = "30"
        "BACKUP_PATH" = "D:/backups/mongodb"
    }
}

function Get-EnvironmentList {
    Write-Host "=== 사용 가능한 환경 ===" -ForegroundColor Cyan
    
    # 템플릿 환경
    Write-Host "`n📋 기본 템플릿:" -ForegroundColor Yellow
    foreach ($env in $EnvironmentTemplates.Keys) {
        Write-Host "  • $env" -ForegroundColor Green
    }
    
    # 기존 .env 파일들
    Write-Host "`n📄 기존 환경 파일:" -ForegroundColor Yellow
    $envFiles = Get-ChildItem ".env*" -ErrorAction SilentlyContinue | Where-Object {$_.Name -match "\.env\.(dev|development|test|testing|prod|production)$"}
    if ($envFiles) {
        foreach ($file in $envFiles) {
            $envName = $file.Name -replace "\.env\.", ""
            Write-Host "  • $envName ($($file.Name))" -ForegroundColor White
        }
    } else {
        Write-Host "  (없음)" -ForegroundColor Gray
    }
    
    # 현재 활성 환경
    Write-Host "`n🔄 현재 환경:" -ForegroundColor Yellow
    if (Test-Path ".env") {
        . "$PSScriptRoot\load-env.ps1"
        if (Load-EnvFile -EnvFile ".env") {
            $currentEnv = [Environment]::GetEnvironmentVariable("ENVIRONMENT")
            if ($currentEnv) {
                Write-Host "  $currentEnv" -ForegroundColor Green
            } else {
                Write-Host "  (환경 정보 없음)" -ForegroundColor Gray
            }
        }
    } else {
        Write-Host "  (설정되지 않음)" -ForegroundColor Red
    }
}

function New-EnvironmentFile {
    param([string]$EnvName)
    
    if (-not $EnvironmentTemplates.ContainsKey($EnvName)) {
        Write-Host "❌ 알 수 없는 환경: $EnvName" -ForegroundColor Red
        Write-Host "사용 가능한 환경: $($EnvironmentTemplates.Keys -join ', ')" -ForegroundColor Yellow
        return $false
    }
    
    $fileName = ".env.$EnvName"
    
    if (Test-Path $fileName) {
        $overwrite = Read-Host "$fileName 파일이 이미 존재합니다. 덮어쓰시겠습니까? (y/N)"
        if ($overwrite -ne 'y' -and $overwrite -ne 'Y') {
            Write-Host "취소되었습니다." -ForegroundColor Yellow
            return $false
        }
    }
    
    Write-Host "=== $EnvName 환경 파일 생성 ===" -ForegroundColor Cyan
    
    $template = $EnvironmentTemplates[$EnvName]
    $content = @()
    
    $content += "# MongoDB $EnvName 환경 설정"
    $content += "# 자동 생성됨: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    $content += ""
    
    # 카테고리별로 정리
    $categories = @{
        "MongoDB 서버 설정" = @("MONGODB_SERVER_IP", "MONGODB_PORT", "MONGODB_DATABASE")
        "MongoDB 인증 정보" = @("MONGODB_ADMIN_USERNAME", "MONGODB_ADMIN_PASSWORD", "MONGODB_APP_USERNAME", "MONGODB_APP_PASSWORD")
        "네트워크 및 보안 설정" = @("MONGODB_ENABLE_NETWORK_ACCESS", "MONGODB_BIND_IP", "MONGODB_ENABLE_AUTH", "MONGODB_USE_SSL")
        "방화벽 설정" = @("FIREWALL_AUTO_CONFIGURE", "FIREWALL_ALLOWED_NETWORKS")
        "애플리케이션 설정" = @("DISABLE_VECTOR_SEARCH", "MONGODB_CONNECT_TIMEOUT", "MONGODB_SERVER_SELECTION_TIMEOUT")
        "환경 및 로깅" = @("ENVIRONMENT", "DEBUG_MODE", "LOG_LEVEL")
        "백업 설정" = @("AUTO_BACKUP_ENABLED", "BACKUP_INTERVAL_HOURS", "BACKUP_RETENTION_DAYS", "BACKUP_PATH")
    }
    
    foreach ($category in $categories.Keys) {
        $content += "# ================================="
        $content += "# $category"
        $content += "# ================================="
        $content += ""
        
        foreach ($key in $categories[$category]) {
            if ($template.ContainsKey($key)) {
                $content += "$key=$($template[$key])"
            }
        }
        $content += ""
    }
    
    try {
        $content | Set-Content $fileName -Encoding UTF8
        Write-Host "✅ $fileName 파일이 생성되었습니다." -ForegroundColor Green
        
        if ($EnvName -eq "production") {
            Write-Host "⚠️ 운영 환경 설정에서는 비밀번호를 반드시 변경하세요!" -ForegroundColor Yellow
        }
        
        return $true
    } catch {
        Write-Host "❌ 파일 생성 중 오류: $_" -ForegroundColor Red
        return $false
    }
}

function Switch-Environment {
    param([string]$EnvName)
    
    $sourceFile = ".env.$EnvName"
    
    if (-not (Test-Path $sourceFile)) {
        Write-Host "❌ $sourceFile 파일을 찾을 수 없습니다." -ForegroundColor Red
        
        if ($EnvironmentTemplates.ContainsKey($EnvName)) {
            $create = Read-Host "템플릿에서 생성하시겠습니까? (y/N)"
            if ($create -eq 'y' -or $create -eq 'Y') {
                if (New-EnvironmentFile -EnvName $EnvName) {
                    # 재귀 호출
                    Switch-Environment -EnvName $EnvName
                }
            }
        }
        return $false
    }
    
    Write-Host "=== $EnvName 환경으로 전환 ===" -ForegroundColor Cyan
    
    # 현재 설정 백업
    if (Test-Path ".env") {
        $backupName = ".env.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Copy-Item ".env" $backupName
        Write-Host "✅ 현재 설정을 $backupName으로 백업했습니다." -ForegroundColor Green
    }
    
    # 환경 전환
    try {
        Copy-Item $sourceFile ".env"
        Write-Host "✅ $EnvName 환경으로 전환되었습니다." -ForegroundColor Green
        
        # 설정 검증
        . "$PSScriptRoot\load-env.ps1"
        if (Load-EnvFile -EnvFile ".env") {
            Show-EnvSummary
            
            $verify = Read-Host "`n설정을 검증하시겠습니까? (y/N)"
            if ($verify -eq 'y' -or $verify -eq 'Y') {
                Test-EnvConfiguration
            }
        }
        
        return $true
    } catch {
        Write-Host "❌ 환경 전환 중 오류: $_" -ForegroundColor Red
        return $false
    }
}

function Backup-CurrentEnvironment {
    if (-not (Test-Path ".env")) {
        Write-Host "❌ .env 파일이 없습니다." -ForegroundColor Red
        return $false
    }
    
    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $backupName = ".env.backup.$timestamp"
    
    try {
        Copy-Item ".env" $backupName
        Write-Host "✅ 현재 환경을 $backupName으로 백업했습니다." -ForegroundColor Green
        
        # 환경 정보 추가
        . "$PSScriptRoot\load-env.ps1"
        if (Load-EnvFile -EnvFile ".env") {
            $envType = [Environment]::GetEnvironmentVariable("ENVIRONMENT")
            if ($envType) {
                Write-Host "환경 유형: $envType" -ForegroundColor Yellow
            }
        }
        
        return $true
    } catch {
        Write-Host "❌ 백업 중 오류: $_" -ForegroundColor Red
        return $false
    }
}

function Compare-Environments {
    param(
        [string]$Env1 = ".env",
        [string]$Env2 = ""
    )
    
    if (-not $Env2) {
        $Env2 = Read-Host "비교할 환경 파일을 입력하세요 (예: .env.production)"
    }
    
    if (-not (Test-Path $Env1) -or -not (Test-Path $Env2)) {
        Write-Host "❌ 파일을 찾을 수 없습니다." -ForegroundColor Red
        return
    }
    
    Write-Host "=== 환경 설정 비교 ===" -ForegroundColor Cyan
    Write-Host "파일 1: $Env1" -ForegroundColor Yellow
    Write-Host "파일 2: $Env2" -ForegroundColor Yellow
    Write-Host ""
    
    # 파일 내용 읽기
    $content1 = @{}
    $content2 = @{}
    
    foreach ($line in (Get-Content $Env1)) {
        if ($line -match '^([^=]+)=(.*)$') {
            $content1[$matches[1].Trim()] = $matches[2].Trim()
        }
    }
    
    foreach ($line in (Get-Content $Env2)) {
        if ($line -match '^([^=]+)=(.*)$') {
            $content2[$matches[1].Trim()] = $matches[2].Trim()
        }
    }
    
    # 모든 키 수집
    $allKeys = ($content1.Keys + $content2.Keys) | Sort-Object -Unique
    
    foreach ($key in $allKeys) {
        $val1 = $content1[$key]
        $val2 = $content2[$key]
        
        if (-not $val1) {
            Write-Host "  $key" -ForegroundColor Red -NoNewline
            Write-Host " : (없음) → $val2" -ForegroundColor White
        } elseif (-not $val2) {
            Write-Host "  $key" -ForegroundColor Red -NoNewline
            Write-Host " : $val1 → (없음)" -ForegroundColor White
        } elseif ($val1 -ne $val2) {
            Write-Host "  $key" -ForegroundColor Yellow -NoNewline
            Write-Host " : $val1 → $val2" -ForegroundColor White
        } else {
            Write-Host "  $key" -ForegroundColor Green -NoNewline
            Write-Host " : $val1" -ForegroundColor Gray
        }
    }
}

function Show-InteractiveMenu {
    while ($true) {
        Write-Host "`n=== 환경 관리 도구 ===" -ForegroundColor Cyan
        Write-Host "1. 환경 목록 보기" -ForegroundColor White
        Write-Host "2. 새 환경 생성" -ForegroundColor White
        Write-Host "3. 환경 전환" -ForegroundColor White
        Write-Host "4. 현재 환경 백업" -ForegroundColor White
        Write-Host "5. 환경 설정 비교" -ForegroundColor White
        Write-Host "6. 현재 설정 확인" -ForegroundColor White
        Write-Host "0. 종료" -ForegroundColor White
        
        $choice = Read-Host "`n선택"
        
        switch ($choice) {
            "1" { Get-EnvironmentList }
            "2" { 
                Get-EnvironmentList
                $envName = Read-Host "`n생성할 환경 이름을 입력하세요"
                if ($envName) {
                    New-EnvironmentFile -EnvName $envName
                }
            }
            "3" { 
                Get-EnvironmentList
                $envName = Read-Host "`n전환할 환경 이름을 입력하세요"
                if ($envName) {
                    Switch-Environment -EnvName $envName
                }
            }
            "4" { Backup-CurrentEnvironment }
            "5" { 
                Write-Host "`n사용 가능한 파일:"
                Get-ChildItem ".env*" | ForEach-Object { Write-Host "  $($_.Name)" -ForegroundColor White }
                Compare-Environments
            }
            "6" { 
                if (Test-Path ".env") {
                    . "$PSScriptRoot\load-env.ps1"
                    Load-EnvFile -EnvFile ".env" -ShowLoaded
                    Show-EnvSummary
                } else {
                    Write-Host "❌ .env 파일이 없습니다." -ForegroundColor Red
                }
            }
            "0" { return }
            default { Write-Host "올바른 번호를 선택하세요." -ForegroundColor Red }
        }
    }
}

# 메인 실행
if ($ListEnvironments) {
    Get-EnvironmentList
} elseif ($CreateEnvironment -and $Environment) {
    New-EnvironmentFile -EnvName $Environment
} elseif ($SwitchEnvironment -and $Environment) {
    Switch-Environment -EnvName $Environment
} elseif ($BackupCurrent) {
    Backup-CurrentEnvironment
} elseif ($ShowDifferences) {
    Compare-Environments
} elseif ($Interactive) {
    Show-InteractiveMenu
} elseif ($Environment) {
    # 환경 이름만 제공된 경우 전환 시도
    Switch-Environment -EnvName $Environment
} else {
    Write-Host "=== 환경 관리 도구 ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "사용법:" -ForegroundColor Yellow
    Write-Host "  환경 목록: -ListEnvironments" -ForegroundColor White
    Write-Host "  환경 생성: -CreateEnvironment -Environment 'development'" -ForegroundColor White
    Write-Host "  환경 전환: -SwitchEnvironment -Environment 'production'" -ForegroundColor White
    Write-Host "  환경 전환: -Environment 'development'" -ForegroundColor White
    Write-Host "  현재 백업: -BackupCurrent" -ForegroundColor White
    Write-Host "  설정 비교: -ShowDifferences" -ForegroundColor White
    Write-Host "  대화형 모드: -Interactive" -ForegroundColor White
    Write-Host ""
    Get-EnvironmentList
}