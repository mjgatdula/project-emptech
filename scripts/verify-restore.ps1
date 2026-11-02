param([Parameter(Mandatory=$true)][string]$BackupDirectory)
$ErrorActionPreference = 'Stop'
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker is required for isolated restore verification.' }
$backupPath = (Resolve-Path -LiteralPath $BackupDirectory).Path
$expected = (Get-Content -LiteralPath (Join-Path $backupPath 'database-counts.json') -Raw) | ConvertFrom-Json
$hash = (Get-Content -LiteralPath (Join-Path $backupPath 'database.sha256') -Raw).Trim()
if ((Get-FileHash -LiteralPath (Join-Path $backupPath 'database.dump') -Algorithm SHA256).Hash -ne $hash) { throw 'Database dump hash mismatch.' }
$manifest = (Get-Content -LiteralPath (Join-Path $backupPath 'media/manifest.json') -Raw) | ConvertFrom-Json
$mediaRoot = [IO.Path]::GetFullPath((Join-Path $backupPath 'media'))
foreach ($entry in $manifest) {
    $target = [IO.Path]::GetFullPath((Join-Path $mediaRoot $entry.name))
    if (-not $target.StartsWith($mediaRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe backup file path.' }
    if ((Get-Item -LiteralPath $target).Length -ne $entry.bytes -or (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw 'Private media integrity check failed.' }
}
$containerName = 'tipped-restore-'+[Guid]::NewGuid().ToString('N')
try {
    # Disposable database only: no published ports, no network and no production secrets.
    & docker run --rm --detach --name $containerName --network none --env POSTGRES_HOST_AUTH_METHOD=trust --env POSTGRES_DB=tipped_restore --mount "type=bind,source=$backupPath,target=/backup,readonly" postgres:18 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not create isolated restore container.' }
    $ready = $false
    for ($attempt=0;$attempt -lt 30;$attempt++) {
        & docker exec $containerName pg_isready --username=postgres --dbname=tipped_restore *> $null
        if ($LASTEXITCODE -eq 0) { $ready=$true;break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { throw 'Isolated restore database did not start.' }
    & docker exec $containerName pg_restore --username=postgres --dbname=tipped_restore --no-owner --no-privileges --exit-on-error /backup/database.dump
    if ($LASTEXITCODE -ne 0) { throw 'Database restore failed.' }
    $allowedTables = @('auth_user','base_item_report','base_ownership_claim','base_google_identity','base_claim_evidence','base_release_record')
    foreach ($table in $allowedTables) {
        if ($null -eq $expected.$table) { throw 'Missing expected database count.' }
        $actual = & docker exec $containerName psql --username=postgres --dbname=tipped_restore --tuples-only --no-align --command "SELECT count(*) FROM $table;"
        if ($LASTEXITCODE -ne 0 -or [long]$actual -ne [long]$expected.$table) { throw ('Restored row count mismatch: '+$table) }
    }
    'PASS isolated PostgreSQL restore, critical-table counts and private-media hashes. Production was not modified.'
} finally {
    & docker rm --force --volumes $containerName *> $null
}
