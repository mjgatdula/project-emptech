param(
    [Parameter(Mandatory=$true)][string]$EnvFile,
    [Parameter(Mandatory=$true)][string]$Destination,
    [Parameter(Mandatory=$true)][switch]$WritesPaused
)
$ErrorActionPreference = 'Stop'
if (-not $WritesPaused) { throw 'Pause all app writers before taking the database/media checkpoint.' }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker is required for the PostgreSQL 18 backup client.' }
$backupPath = [IO.Path]::GetFullPath($Destination)
if (Test-Path -LiteralPath $backupPath) { throw 'Use a new backup directory; backups are never overwritten.' }
$projectPath = Split-Path -Parent $PSScriptRoot
$secretPath = (Resolve-Path -LiteralPath $EnvFile).Path
$prior = @{}
$changed = [Collections.Generic.List[string]]::new()
function Set-PrivateEnvironment([string]$Name,[string]$Value) {
    if (-not $prior.ContainsKey($Name)) { $prior[$Name] = [Environment]::GetEnvironmentVariable($Name,'Process'); $changed.Add($Name) }
    [Environment]::SetEnvironmentVariable($Name,$Value,'Process')
}
function Run-Docker([string[]]$Arguments) {
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'Docker backup operation failed; backup is incomplete.' }
}
try {
    foreach ($line in Get-Content -LiteralPath $secretPath) {
        if ($line -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') { Set-PrivateEnvironment $Matches[1] $Matches[2] }
    }
    foreach ($mapping in @(@('PGHOST','DB_HOST'),@('PGPORT','DB_PORT'),@('PGDATABASE','DB_NAME'),@('PGUSER','DB_USER'),@('PGPASSWORD','DB_PASSWORD'),@('PGSSLMODE','DB_SSLMODE'))) {
        $value = [Environment]::GetEnvironmentVariable($mapping[1],'Process')
        if ([string]::IsNullOrWhiteSpace($value)) { throw ('Missing environment key: '+$mapping[1]) }
        Set-PrivateEnvironment $mapping[0] $value
    }
    New-Item -ItemType Directory -Path $backupPath | Out-Null
    if ($env:OS -eq 'Windows_NT') {
        $acl = Get-Acl -LiteralPath $backupPath
        $acl.SetAccessRuleProtection($true,$false)
        $identity = [Security.Principal.WindowsIdentity]::GetCurrent().User
        $rule = [Security.AccessControl.FileSystemAccessRule]::new($identity,'FullControl','ContainerInherit,ObjectInherit','None','Allow')
        $acl.SetAccessRule($rule)
        Set-Acl -LiteralPath $backupPath -AclObject $acl
    }
    $common = @('run','--rm','--env','PGHOST','--env','PGPORT','--env','PGDATABASE','--env','PGUSER','--env','PGPASSWORD','--env','PGSSLMODE','--mount',"type=bind,source=$backupPath,target=/backup",'postgres:18')
    Run-Docker ($common + @('pg_dump','--format=custom','--no-owner','--no-privileges','--file=/backup/database.dump'))
    $countSql = "SELECT json_build_object('auth_user',(SELECT count(*) FROM auth_user),'base_item_report',(SELECT count(*) FROM base_item_report),'base_ownership_claim',(SELECT count(*) FROM base_ownership_claim),'base_google_identity',(SELECT count(*) FROM base_google_identity),'base_claim_evidence',(SELECT count(*) FROM base_claim_evidence),'base_release_record',(SELECT count(*) FROM base_release_record));"
    $counts = & docker @common psql --tuples-only --no-align --command $countSql
    if ($LASTEXITCODE -ne 0) { throw 'Could not record database verification counts.' }
    $counts | Set-Content -LiteralPath (Join-Path $backupPath 'database-counts.json') -Encoding utf8
    Set-PrivateEnvironment 'DJANGO_SETTINGS_MODULE' 'backend.production_settings'
    & (Join-Path $projectPath 'venv/Scripts/python.exe') (Join-Path $projectPath 'backend/manage.py') export_private_media --directory (Join-Path $backupPath 'media')
    if ($LASTEXITCODE -ne 0) { throw 'Media export failed; checkpoint is incomplete.' }
    $digest = (Get-FileHash -LiteralPath (Join-Path $backupPath 'database.dump') -Algorithm SHA256).Hash
    $digest | Set-Content -LiteralPath (Join-Path $backupPath 'database.sha256') -Encoding ascii
    'Complete checkpoint created. Keep it private and encrypted at rest; run verify-restore.ps1 before treating it as recoverable.'
} finally {
    foreach ($name in $changed) { [Environment]::SetEnvironmentVariable($name,$prior[$name],'Process') }
}
