param(
    [Parameter(Mandatory = $true)]
    [string]$SqlFile
)

$ErrorActionPreference = "Stop"
if (!(Test-Path $SqlFile)) {
    throw "SQL file not found: $SqlFile"
}

Get-Content $SqlFile | docker compose exec -T postgres psql -U research -d research
Write-Output "Postgres restore completed from $SqlFile"
