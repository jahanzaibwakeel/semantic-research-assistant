param(
    [string]$BackupDir = "backups"
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$target = Join-Path $BackupDir $timestamp
New-Item -ItemType Directory -Force $target | Out-Null

docker compose exec -T postgres pg_dump -U research -d research | Out-File -Encoding utf8 (Join-Path $target "postgres.sql")

$qdrantSnapshot = Invoke-RestMethod -Method Post -Uri "http://localhost:6333/collections/research_chunks/snapshots"
if ($qdrantSnapshot.name) {
    Invoke-WebRequest -Uri "http://localhost:6333/collections/research_chunks/snapshots/$($qdrantSnapshot.name)" -OutFile (Join-Path $target $qdrantSnapshot.name)
}

Write-Output "Backup written to $target"
