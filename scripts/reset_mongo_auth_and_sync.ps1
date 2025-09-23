param(
    [string]$EnvFile = ".env"
)

# Load .env helpers
. "$PSScriptRoot\load-env.ps1"

if (-not (Load-EnvFile -EnvFile $EnvFile)) {
    Write-Host "❌ .env 파일을 로드하지 못했습니다: $EnvFile" -ForegroundColor Red
    exit 1
}

function Set-AuthState {
    param(
        [ValidateSet('enabled','disabled')]
        [string]$State
    )
    if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Host "❌ 관리자 권한이 필요합니다. PowerShell을 관리자로 실행하세요." -ForegroundColor Red
        return $false
    }
    $cfg = "C:\\Program Files\\MongoDB\\Server\\8.0\\bin\\mongod.cfg"
    if (-not (Test-Path $cfg)) {
        Write-Host "❌ mongod.cfg를 찾을 수 없습니다: $cfg" -ForegroundColor Red
        return $false
    }
    $backup = "$cfg.bak.$((Get-Date).ToString('yyyyMMdd_HHmmss'))"
    Copy-Item $cfg $backup -Force
    try {
        $raw = Get-Content -Raw $cfg
        if ($raw -match 'authorization:\s*(enabled|disabled)') {
            $raw = [regex]::Replace($raw, 'authorization:\s*(enabled|disabled)', "authorization: $State")
        } elseif ($raw -match '(?m)^\s*security:') {
            # security 섹션은 있으나 authorization 없음
            $raw = $raw -replace '(?m)^(\s*security:\s*)$', "$1`r`n  authorization: $State"
        } else {
            # security 섹션 자체가 없음
            $raw = $raw + "`r`nsecurity:`r`n  authorization: $State`r`n"
        }
        Set-Content -Path $cfg -Value $raw -Encoding UTF8
        Restart-Service -Name MongoDB -Force
        Start-Sleep -Seconds 3
        Write-Host "✅ authorization: $State" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "❌ authorization 전환 중 오류: $_" -ForegroundColor Red
        Copy-Item $backup $cfg -Force
        return $false
    }
}

function Sync-Users {
        # Use Python helper to sync users when authorization is disabled
        $py = "python"
        & $py "${PSScriptRoot}\sync_users_noauth.py"
        if ($LASTEXITCODE -ne 0) {
                Write-Host "User sync Python script failed with code $LASTEXITCODE" -ForegroundColor Red
                return $false
        }
        return $true
}

# Run cycle: auth OFF -> sync users -> auth ON
if (-not (Set-AuthState -State 'disabled')) { exit 2 }
if (-not (Sync-Users)) { exit 3 }
if (-not (Set-AuthState -State 'enabled')) { exit 4 }

Write-Host "🎉 사용자/비밀번호가 .env 기준으로 동기화되었습니다." -ForegroundColor Green
exit 0
