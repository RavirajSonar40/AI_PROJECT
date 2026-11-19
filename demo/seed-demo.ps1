# Seed demo data into the running AI Knowledge & Action Platform.
#
# Usage:
#   pwsh demo/seed-demo.ps1              # upload only new files
#   pwsh demo/seed-demo.ps1 -Force       # re-upload every file (creates duplicates)
#   pwsh demo/seed-demo.ps1 -ApiBase http://localhost:8000

param(
    [string]$ApiBase = "http://localhost:8000",
    [string]$DocumentsDir = (Join-Path $PSScriptRoot "documents"),
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Wait-Api {
    for ($i = 1; $i -le 30; $i++) {
        try {
            $null = Invoke-RestMethod -Uri "$ApiBase/health/ready" -TimeoutSec 5
            return
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    throw "API is not ready at $ApiBase"
}

Wait-Api

$existing = @{}
try {
    $current = Invoke-RestMethod -Uri "$ApiBase/documents" -TimeoutSec 15
    foreach ($doc in $current) { $existing[$doc.filename] = $doc.id }
} catch {
    Write-Warning "Could not list existing documents: $($_.Exception.Message)"
}

$files = Get-ChildItem -Path $DocumentsDir -Filter *.md | Sort-Object Name

if ($files.Count -eq 0) {
    throw "No .md files found in $DocumentsDir"
}

Write-Host ""
Write-Host "Seeding $($files.Count) documents into $ApiBase" -ForegroundColor Cyan
Write-Host ""

$rows = @()
$index = 0

foreach ($file in $files) {
    $index++

    if ($existing.ContainsKey($file.Name) -and -not $Force) {
        $rows += [pscustomobject]@{
            File    = $file.Name
            DocId   = $existing[$file.Name]
            Chunks  = "skipped"
            Vector  = "skipped"
            Status  = "already uploaded"
        }
        Write-Host ("[{0:D2}/{1:D2}] {2} - already uploaded (id {3})" -f $index, $files.Count, $file.Name, $existing[$file.Name]) -ForegroundColor DarkGray
        continue
    }

    # 1. Upload
    $raw = curl.exe -s -X POST "$ApiBase/documents/upload" -F "file=@$($file.FullName)"
    $doc = $raw | ConvertFrom-Json
    if (-not $doc.id) {
        throw "Upload failed for $($file.Name): $raw"
    }

    # 2. Chunk
    $chunkResult = Invoke-RestMethod -Uri "$ApiBase/documents/$($doc.id)/chunks" -Method Post -TimeoutSec 120

    # 3. Embed
    $vector = "failed"
    try {
        $emb = Invoke-RestMethod -Uri "$ApiBase/documents/$($doc.id)/embeddings" -Method Post -TimeoutSec 600
        $vector = "$($emb.embedding_dimension)-dim"
    } catch {
        $vector = "ERROR"
    }

    $rows += [pscustomobject]@{
        File   = $file.Name
        DocId  = $doc.id
        Chunks = $chunkResult.chunk_count
        Vector = $vector
        Status = "ok"
    }

    Write-Host ("[{0:D2}/{1:D2}] {2} -> id {3}, {4} chunks, {5}" -f $index, $files.Count, $file.Name, $doc.id, $chunkResult.chunk_count, $vector) -ForegroundColor Green
}

Write-Host ""
$rows | Format-Table -AutoSize

$totalChunks = ($rows | Where-Object { $_.Chunks -is [int] } | Measure-Object -Property Chunks -Sum).Sum
$allDocs = Invoke-RestMethod -Uri "$ApiBase/documents" -TimeoutSec 15

Write-Host ""
Write-Host "Documents in platform: $($allDocs.Count)" -ForegroundColor Cyan
Write-Host "Chunks created in this run: $totalChunks" -ForegroundColor Cyan
Write-Host ""
Write-Host "Open http://localhost:4200 to demo, or run demo/demo-questions.ps1" -ForegroundColor Yellow
