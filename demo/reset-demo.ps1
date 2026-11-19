# Reset every document, chunk and embedding so the demo can be re-seeded.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File demo/reset-demo.ps1

$ErrorActionPreference = "Stop"

$sql = "TRUNCATE TABLE document_chunks, documents RESTART IDENTITY CASCADE;"

Write-Host "Truncating documents and document_chunks..." -ForegroundColor Yellow
docker exec ai-platform-postgres psql -U ai_platform -d ai_platform -c $sql

Write-Host "Removing uploaded files..." -ForegroundColor Yellow
Get-ChildItem -Path (Join-Path $PSScriptRoot "..\data\uploads") -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -ne ".gitkeep" } |
    Remove-Item -Force

Write-Host "Flushing the query embedding cache in Redis..." -ForegroundColor Yellow
docker exec ai-platform-redis redis-cli FLUSHDB | Out-Null

Write-Host "Clearing conversation checkpoints..." -ForegroundColor Yellow
$checkpointSql = "DO `$`$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'checkpoints') THEN TRUNCATE TABLE checkpoints CASCADE; END IF; END `$`$;"
docker exec ai-platform-postgres psql -U ai_platform -d ai_platform -c $checkpointSql | Out-Null

Write-Host ""
Write-Host "Reset done. Run demo/seed-demo.ps1 to load the demo corpus again." -ForegroundColor Green
