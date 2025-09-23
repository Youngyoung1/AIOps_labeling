# .env 파일을 읽어서 환경변수로 로드하는 공통 함수
# 다른 스크립트에서 dot sourcing으로 사용: . .\scripts\load-env.ps1

function Load-EnvFile {
    param(
        [string]$EnvFile = ".env",
        [switch]$ShowLoaded
    )
    
    if (-not (Test-Path $EnvFile)) {
        Write-Warning ".env 파일을 찾을 수 없습니다: $EnvFile"
        Write-Host "템플릿 파일(.env.template)을 복사해서 .env로 만들어주세요." -ForegroundColor Yellow
        return $false
    }
    
    try {
        Write-Host "환경변수 로드 중: $EnvFile" -ForegroundColor Cyan
        
        $loadedVars = @()
        $content = Get-Content $EnvFile -ErrorAction Stop
        
        foreach ($line in $content) {
            # 주석과 빈 줄 건너뛰기
            if ($line -match '^\s*#' -or $line -match '^\s*$') {
                continue
            }
            
            # KEY=VALUE 형식 파싱
            if ($line -match '^([^=]+)=(.*)$') {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim()
                
                # 따옴표 제거
                $value = $value -replace '^["'']|["'']$', ''
                
                # 환경변수 설정
                [Environment]::SetEnvironmentVariable($key, $value, "Process")
                $loadedVars += $key
                
                if ($ShowLoaded) {
                    Write-Host "  $key = $value" -ForegroundColor Green
                }
            }
        }
        
    Write-Host "Loaded $($loadedVars.Count) environment variables." -ForegroundColor Green
        return $true
        
    } catch {
        Write-Error "환경변수 로드 중 오류: $_"
        return $false
    }
}

function Get-EnvValue {
    param(
        [string]$Key,
        [string]$DefaultValue = ""
    )
    
    $value = [Environment]::GetEnvironmentVariable($Key)
    if ([string]::IsNullOrEmpty($value)) {
        return $DefaultValue
    }
    return $value
}

function Get-EnvBool {
    param(
        [string]$Key,
        [bool]$DefaultValue = $false
    )
    
    $value = Get-EnvValue -Key $Key
    if ([string]::IsNullOrEmpty($value)) {
        return $DefaultValue
    }
    
    return $value -in @("true", "True", "TRUE", "1", "yes", "Yes", "YES", "on", "On", "ON")
}

function Get-EnvInt {
    param(
        [string]$Key,
        [int]$DefaultValue = 0
    )
    
    $value = Get-EnvValue -Key $Key
    if ([string]::IsNullOrEmpty($value)) {
        return $DefaultValue
    }
    
    try {
        return [int]$value
    } catch {
    Write-Warning "Env var $Key value '$value' is not an integer. Using default $DefaultValue."
        return $DefaultValue
    }
}

function Show-EnvSummary {
    Write-Host "`n=== MongoDB Environment Summary ===" -ForegroundColor Cyan
    
    Write-Host "Server:" -ForegroundColor Yellow
    Write-Host "  IP: $(Get-EnvValue 'MONGODB_SERVER_IP' 'localhost')" -ForegroundColor White
    Write-Host "  Port: $(Get-EnvValue 'MONGODB_PORT' '27017')" -ForegroundColor White
    Write-Host "  Database: $(Get-EnvValue 'MONGODB_DATABASE' 'labeling_db')" -ForegroundColor White
    
    Write-Host "Auth:" -ForegroundColor Yellow
    Write-Host "  Username: $(Get-EnvValue 'MONGODB_APP_USERNAME' 'labeling_user')" -ForegroundColor White
    Write-Host "  Password: $('*' * (Get-EnvValue 'MONGODB_APP_PASSWORD' 'password').Length)" -ForegroundColor White
    
    Write-Host "Network:" -ForegroundColor Yellow
    Write-Host "  External Access: $(if (Get-EnvBool 'MONGODB_ENABLE_NETWORK_ACCESS') {'enabled'} else {'disabled'})" -ForegroundColor White
    Write-Host "  Bind IP: $(Get-EnvValue 'MONGODB_BIND_IP' '127.0.0.1')" -ForegroundColor White
    Write-Host "  Authorization: $(if (Get-EnvBool 'MONGODB_ENABLE_AUTH') {'enabled'} else {'disabled'})" -ForegroundColor White
    
    Write-Host "Security:" -ForegroundColor Yellow
    Write-Host "  SSL/TLS: $(if (Get-EnvBool 'MONGODB_USE_SSL') {'enabled'} else {'disabled'})" -ForegroundColor White
    Write-Host "  Firewall Auto-Configure: $(if (Get-EnvBool 'FIREWALL_AUTO_CONFIGURE') {'enabled'} else {'disabled'})" -ForegroundColor White
    Write-Host "  Allowed Networks: $(Get-EnvValue 'FIREWALL_ALLOWED_NETWORKS' 'all')" -ForegroundColor White
    
    Write-Host "App Env:" -ForegroundColor Yellow
    Write-Host "  Environment: $(Get-EnvValue 'ENVIRONMENT' 'development')" -ForegroundColor White
    Write-Host "  Debug Mode: $(if (Get-EnvBool 'DEBUG_MODE') {'enabled'} else {'disabled'})" -ForegroundColor White
    Write-Host "  Log Level: $(Get-EnvValue 'LOG_LEVEL' 'INFO')" -ForegroundColor White
}

function Build-MongoUri {
    param(
        [switch]$ForAdmin
    )
    
    $serverIP = Get-EnvValue 'MONGODB_SERVER_IP' 'localhost'
    $port = Get-EnvValue 'MONGODB_PORT' '27017'
    $database = Get-EnvValue 'MONGODB_DATABASE' 'labeling_db'
    
    if ($ForAdmin) {
        $username = Get-EnvValue 'MONGODB_ADMIN_USERNAME' 'admin'
        $password = Get-EnvValue 'MONGODB_ADMIN_PASSWORD' 'admin123'
        $database = 'admin'
    } else {
        $username = Get-EnvValue 'MONGODB_APP_USERNAME' 'labeling_user'
        $password = Get-EnvValue 'MONGODB_APP_PASSWORD' 'labeling_password'
    }
    
    $useSSL = Get-EnvBool 'MONGODB_USE_SSL'
    $sslParam = if ($useSSL) { '?ssl=true' } else { '' }
    
    if (Get-EnvBool 'MONGODB_ENABLE_AUTH') {
        return "mongodb://$username`:$password@$serverIP`:$port/$database$sslParam"
    } else {
        return "mongodb://$serverIP`:$port/$database$sslParam"
    }
}

function Test-EnvConfiguration {
    Write-Host "=== Env validation ===" -ForegroundColor Cyan
    
    $errors = @()
    $warnings = @()
    
    # Required settings
    $requiredVars = @('MONGODB_SERVER_IP', 'MONGODB_PORT', 'MONGODB_DATABASE')
    foreach ($var in $requiredVars) {
        if ([string]::IsNullOrEmpty((Get-EnvValue $var))) {
            $errors += "Missing required env var: $var"
        }
    }
    
    # IP format
    $serverIP = Get-EnvValue 'MONGODB_SERVER_IP'
    if ($serverIP -and $serverIP -notmatch '^(\d{1,3}\.){3}\d{1,3}$' -and $serverIP -ne 'localhost') {
        $errors += "Invalid IP address format: $serverIP"
    }
    
    # Port number
    $port = Get-EnvInt 'MONGODB_PORT'
    if ($port -lt 1 -or $port -gt 65535) {
        $errors += "Invalid port: $port"
    }
    
    # Auth check
    if (Get-EnvBool 'MONGODB_ENABLE_AUTH') {
        $username = Get-EnvValue 'MONGODB_APP_USERNAME'
        $password = Get-EnvValue 'MONGODB_APP_PASSWORD'
        if ([string]::IsNullOrEmpty($username)) { $errors += "Auth enabled but username is empty" }
        if ([string]::IsNullOrEmpty($password)) { $warnings += "Auth enabled but password is empty" }
        elseif ($password.Length -lt 8) { $warnings += "Password too short (< 8 chars)" }
    }
    
    # Network check
    if (Get-EnvBool 'MONGODB_ENABLE_NETWORK_ACCESS') {
        $bindIP = Get-EnvValue 'MONGODB_BIND_IP'
        if ($bindIP -eq '127.0.0.1') { $warnings += "External access on, but bind IP is localhost" }
    }
    
    # Output
    if ($errors.Count -gt 0) {
        Write-Host "Errors:" -ForegroundColor Red
        foreach ($error in $errors) { Write-Host "  - $error" -ForegroundColor Red }
    }
    if ($warnings.Count -gt 0) {
        Write-Host "Warnings:" -ForegroundColor Yellow
        foreach ($warning in $warnings) { Write-Host "  - $warning" -ForegroundColor Yellow }
    }
    if ($errors.Count -eq 0 -and $warnings.Count -eq 0) { Write-Host "Environment looks good." -ForegroundColor Green }
    return $errors.Count -eq 0
}

# 스크립트가 직접 실행될 때
if ($MyInvocation.InvocationName -eq $MyInvocation.MyCommand.Name) {
    param(
        [string]$EnvFile = ".env",
        [switch]$ShowSummary,
        [switch]$TestConfig,
        [switch]$CreateTemplate
    )
    
    if ($CreateTemplate) {
        if (Test-Path ".env.template") {
            Copy-Item ".env.template" ".env"
            Write-Host ".env created from template." -ForegroundColor Green
            Write-Host "Edit .env and set real values." -ForegroundColor Yellow
        } else {
            Write-Host ".env.template file not found." -ForegroundColor Red
        }
        return
    }
    
    if (Load-EnvFile -EnvFile $EnvFile -ShowLoaded) {
        if ($ShowSummary) { Show-EnvSummary }
        if ($TestConfig) { Test-EnvConfiguration }
    }
}