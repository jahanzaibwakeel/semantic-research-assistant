$ErrorActionPreference = "Stop"

docker compose exec -T postgres psql -U research -d research -c "VACUUM ANALYZE;"
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/health/ready"
Write-Output "Maintenance checks completed"
