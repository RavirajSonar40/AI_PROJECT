# Guided demo of the AI Knowledge & Action Platform.
#
# Runs the whole story in order and prints what is happening at each step:
#   0. health          -> the stack is alive
#   1. inventory       -> what is in the knowledge base
#   2. semantic search -> embeddings + pgvector, no LLM involved
#   3. RAG answer      -> retrieval + LLM with citations
#   4. agent + tool    -> the LLM decides to call a tool
#   5. agent + RAG     -> the LLM searches documents itself
#   6. human approval  -> the graph pauses, then resumes with a decision
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File demo/demo-questions.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File demo/demo-questions.ps1 -Pause

param(
    [string]$ApiBase = "http://localhost:8000",
    [int]$DelaySeconds = 4,
    [switch]$Pause
)

$ErrorActionPreference = "Stop"

# Windows PowerShell 5.1 decodes JSON as Latin-1 when the server omits a charset.
# We read raw bytes with curl and decode as UTF-8 so Spanish accents display correctly.
try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
} catch { }

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$TempDir = Join-Path $env:TEMP "ai-platform-demo"
$null = New-Item -ItemType Directory -Force -Path $TempDir

function Invoke-Api {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [string]$Method = "GET",
        $Body = $null
    )

    $outFile = Join-Path $TempDir ("out-" + [guid]::NewGuid().ToString("N") + ".json")

    if ($null -ne $Body) {
        $bodyFile = Join-Path $TempDir ("in-" + [guid]::NewGuid().ToString("N") + ".json")
        [System.IO.File]::WriteAllText($bodyFile, ($Body | ConvertTo-Json -Depth 8), $Utf8NoBom)
        $null = curl.exe -s -X $Method "$ApiBase$Path" -H "Content-Type: application/json" --data-binary "@$bodyFile" -o $outFile
        Remove-Item $bodyFile -Force -ErrorAction SilentlyContinue
    } else {
        $null = curl.exe -s -X $Method "$ApiBase$Path" -o $outFile
    }

    $text = [System.IO.File]::ReadAllText($outFile, [System.Text.Encoding]::UTF8)
    Remove-Item $outFile -Force -ErrorAction SilentlyContinue

    if ([string]::IsNullOrWhiteSpace($text)) {
        throw "Empty response from $Method $Path"
    }

    return $text | ConvertFrom-Json
}

function Section {
    param([string]$Number, [string]$Title, [string]$Why)
    Write-Host ""
    Write-Host ("=" * 78) -ForegroundColor DarkCyan
    Write-Host ("  STEP {0} - {1}" -f $Number, $Title) -ForegroundColor Cyan
    Write-Host ("  {0}" -f $Why) -ForegroundColor DarkGray
    Write-Host ("=" * 78) -ForegroundColor DarkCyan
}

function Step-Pause {
    if ($Pause) {
        Write-Host ""
        Write-Host "  [press Enter to continue]" -ForegroundColor Yellow -NoNewline
        $null = Read-Host
    }
}

function Show-Answer {
    param($Response)

    Write-Host ""
    if ($Response.status)    { Write-Host "  status      : $($Response.status)" -ForegroundColor White }
    if ($Response.route)     { Write-Host "  route       : $($Response.route)" }
    if ($Response.tool_used) { Write-Host "  tool used   : $($Response.tool_used)" -ForegroundColor Magenta }
    if ($Response.thread_id) { Write-Host "  thread id   : $($Response.thread_id)" -ForegroundColor DarkGray }

    Write-Host ""
    Write-Host "  ANSWER:" -ForegroundColor Green
    ($Response.answer -split "`n") | ForEach-Object { Write-Host "    $_" }

    if ($Response.sources -and $Response.sources.Count -gt 0) {
        Write-Host ""
        Write-Host "  SOURCES (cited from your documents):" -ForegroundColor Green
        $i = 0
        foreach ($s in $Response.sources) {
            $i++
            $preview = $s.content -replace "\s+", " "
            if ($preview.Length -gt 90) { $preview = $preview.Substring(0, 90) + "..." }
            Write-Host ("    [{0}] document {1} / chunk {2} / similarity {3}" -f $i, $s.document_id, $s.position, [math]::Round([double]$s.similarity, 4)) -ForegroundColor DarkGray
            Write-Host ("        {0}" -f $preview) -ForegroundColor DarkGray
        }
    }
}

# ---------------------------------------------------------------- STEP 0
Section "0" "Health check" "The API, PostgreSQL and Redis must all be connected."
$health = Invoke-Api -Path "/health/ready"
Write-Host ("  API status : {0}" -f $health.status) -ForegroundColor Green
Write-Host ("  Database   : {0}" -f $health.database)
Write-Host ("  Cache      : {0}" -f $health.cache)
Step-Pause

# ---------------------------------------------------------------- STEP 1
Section "1" "Knowledge base inventory" "These documents were uploaded, split into chunks and embedded."
$docs = Invoke-Api -Path "/documents"
Write-Host ("  Documents: {0}" -f @($docs).Count) -ForegroundColor Green
Write-Host ""
$docs | Select-Object id, filename, @{n = "size"; e = { "{0:N0} B" -f $_.size_bytes } } | Format-Table -AutoSize
Step-Pause

# ---------------------------------------------------------------- STEP 2
Section "2" "Semantic search (no LLM)" "The question becomes a 384-dim vector and pgvector returns the closest chunks."
$question = "How many vacation days do I get and how do I request them?"

$search = Invoke-Api -Path "/documents/search" "POST" @{ query = $question; limit = 3 }

Write-Host ("  Query: {0}" -f $question) -ForegroundColor White
Write-Host ""
$i = 0
foreach ($r in $search.results) {
    $i++
    $preview = $r.content -replace "\s+", " "
    if ($preview.Length -gt 110) { $preview = $preview.Substring(0, 110) + "..." }
    Write-Host ("  [{0}] similarity {1}  (document {2}, chunk {3})" -f $i, [math]::Round([double]$r.similarity, 4), $r.document_id, $r.position) -ForegroundColor Yellow
    Write-Host ("      {0}" -f $preview) -ForegroundColor DarkGray
}
Write-Host ""
Write-Host "  Note: no language model was called yet. This is pure vector math." -ForegroundColor DarkCyan
Step-Pause

Start-Sleep -Seconds $DelaySeconds

# ---------------------------------------------------------------- STEP 3
Section "3" "RAG answer with citations" "Retrieval feeds the best chunks into the LLM, which answers from evidence only."
$rag = Invoke-Api -Path "/rag/ask" "POST" @{ question = $question; limit = 3; min_similarity = 0.2 }
Show-Answer $rag
Step-Pause

Start-Sleep -Seconds $DelaySeconds

# ---------------------------------------------------------------- STEP 4
Section "4" "Agent decides to use a tool: get_system_info" "The model reads the question, picks a tool and calls it."
$agentSystem = Invoke-Api -Path "/agent/ask" "POST" @{ question = "What version and environment does this platform run?"; thread_id = "demo-system" }
Show-Answer $agentSystem
Step-Pause

Start-Sleep -Seconds $DelaySeconds

# ---------------------------------------------------------------- STEP 5
Section "5" "Agent searches your documents itself: search_knowledge" "The agent calls the RAG tool, reads the result and cites the sources."
$agentKnowledge = Invoke-Api -Path "/agent/ask" "POST" @{
    question  = "According to my documents, what does the health insurance cover and how big is the training budget?"
    thread_id = "demo-knowledge"
}
Show-Answer $agentKnowledge
Step-Pause

Start-Sleep -Seconds $DelaySeconds

# ---------------------------------------------------------------- STEP 6
Section "6" "Human approval before a sensitive action" "The graph stops mid-execution and waits for a person to decide."
$interrupted = Invoke-Api -Path "/agent/ask" "POST" @{
    question  = "Clear the embedding cache now. Call clear_embedding_cache without asking me."
    thread_id = "demo-approval"
}

Write-Host ("  status: {0}" -f $interrupted.status) -ForegroundColor Yellow

if ($interrupted.status -eq "interrupted") {
    Write-Host "  The graph is PAUSED and saved in PostgreSQL:" -ForegroundColor Yellow
    Write-Host ("    action  : {0}" -f $interrupted.interrupt.value.action)
    Write-Host ("    message : {0}" -f $interrupted.interrupt.value.message)
    Write-Host ""
    Write-Host "  Resuming with approved = true ..." -ForegroundColor Cyan

    Start-Sleep -Seconds $DelaySeconds
    $resumed = Invoke-Api -Path "/agent/resume" "POST" @{
        thread_id = "demo-approval"
        approved  = $true
        note      = "approved during the demo"
    }
    Show-Answer $resumed
} else {
    Write-Host "  (the model answered without calling the tool; run the script again)" -ForegroundColor DarkYellow
}
Step-Pause

# ---------------------------------------------------------------- SUMMARY
Write-Host ""
Write-Host ("=" * 78) -ForegroundColor DarkCyan
Write-Host "  WHAT JUST HAPPENED" -ForegroundColor Cyan
Write-Host ("=" * 78) -ForegroundColor DarkCyan
Write-Host "  1. The demo documents were split into chunks of 1000 characters with 200 overlap."
Write-Host "  2. Each chunk became a 384-number vector stored in pgvector."
Write-Host "  3. Semantic search compared vectors, not keywords."
Write-Host "  4. RAG passed the best chunks to the LLM and asked for an answer with sources."
Write-Host "  5. The agent chose tools on its own: get_system_info and search_knowledge."
Write-Host "  6. A destructive tool paused the graph until a human approved it."
Write-Host ""
Write-Host ("  API docs : {0}/docs" -f $ApiBase) -ForegroundColor Green
Write-Host "  Frontend : http://localhost:4200" -ForegroundColor Green
Write-Host ""

