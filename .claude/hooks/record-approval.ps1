<#
  record-approval.ps1 - PostToolUse hook on AskUserQuestion. Windows PowerShell 5.1.

  Turns the user's own answer into an approval record (pipeline/schemas/approval.schema.json). Only questions
  that carry a marker are considered:
      [studio-approve <CODE> policy sha256=<64 hex>]
      [studio-approve <CODE> R-### sha256=<64 hex>]
  (pipeline\tools\ticket.py marker prints it). The hook recomputes the SHA-256 of the file the marker names
  (00_admin\policy_proposal.json or 00_admin\run_tickets\R-###.json); if it differs, nothing is recorded.
  An answer whose label starts with "Approve" records an approval; "Reject"/"No"/"Decline" records a rejection;
  anything else (free text) records nothing, and the Producer asks again.
  A previous record moves to approvals\history\. Agents cannot write approvals themselves (guard.ps1, settings).
#>
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
$raw = [Console]::In.ReadToEnd()
$repo = $env:CLAUDE_PROJECT_DIR
if (-not $repo) { $repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path }

# Raw log, to see the exact answer shape this Claude Code build sends (ignored by git).
$logDir = Join-Path $repo '.claude\hooks\runtime'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
[IO.File]::AppendAllText((Join-Path $logDir 'askuser.jsonl'), ($raw -replace "`r?`n", ' ') + "`n", (New-Object System.Text.UTF8Encoding($false)))

try { $in = $raw | ConvertFrom-Json } catch { exit 0 }
$questions = @($in.tool_input.questions)

function Get-AnswerFor([string]$question) {
    # Measured on Claude Code 2.1.296 (2026-10-10): the answer map is in both tool_input.answers and
    # tool_response.answers, keyed by the question text. A tool_response that is itself the map is also accepted.
    foreach ($src in @($in.tool_response.answers, $in.tool_input.answers, $in.tool_response)) {
        if ($null -eq $src) { continue }
        if ($src -is [string]) {
            if ($src -match [regex]::Escape($question) + '"?\s*[:=]\s*"([^"]+)"') { return $Matches[1] }
            continue
        }
        $p = $src.PSObject.Properties[$question]
        if ($p) { return [string]$p.Value }
    }
    return $null
}

function Get-Sha256([string]$path) { return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }

$notes = @()
foreach ($q in $questions) {
    $text = [string]$q.question
    $m = [regex]::Match($text, '\[studio-approve\s+([A-Z]{3})\s+(policy|R-\d{3,})\s+sha256=([0-9a-f]{64})\]')
    if (-not $m.Success) { continue }
    $code = $m.Groups[1].Value; $what = $m.Groups[2].Value; $sha = $m.Groups[3].Value
    $proj = Join-Path $repo "projects\$code"
    if ($what -eq 'policy') { $subjectRel = '00_admin/policy_proposal.json'; $name = 'policy.json' }
    else { $subjectRel = "00_admin/run_tickets/$what.json"; $name = "$what.json" }
    $subject = Join-Path $proj ($subjectRel -replace '/', '\')
    if (-not (Test-Path -LiteralPath $subject)) { $notes += "NOT recorded ($code $what): $subjectRel does not exist."; continue }
    if ((Get-Sha256 $subject) -ne $sha) { $notes += "NOT recorded ($code $what): $subjectRel changed since the question was written; ask again."; continue }

    $answer = Get-AnswerFor $text
    if (-not $answer) { $notes += "NOT recorded ($code $what): no answer found for the marked question."; continue }
    if ($answer -match '^(?i)\s*approve') { $decision = 'approved' }
    elseif ($answer -match '^(?i)\s*(reject|no\b|decline|do not|don''t)') { $decision = 'rejected' }
    else { $notes += "NOT recorded ($code $what): the answer '$answer' is neither an approval nor a rejection; clarify and ask again."; continue }

    $rec = [ordered]@{
        kind           = $(if ($what -eq 'policy') { 'policy' } else { 'run_ticket' })
        project        = $code
        subject        = $subjectRel
        subject_sha256 = $sha
        decision       = $decision
        question       = $text
        answer         = $answer
        answered_at    = (Get-Date).ToString('yyyy-MM-ddTHH:mm:sszzz')
        recorded_by    = 'hook:record-approval'
    }
    $subjectData = Get-Content -LiteralPath $subject -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($what -ne 'policy') {
        $rec.run_id = $what
        if ($decision -eq 'approved') { $rec.window = [ordered]@{ start = $subjectData.window.start; end = $subjectData.window.end } }
    } elseif ($decision -eq 'approved') {
        $rec.policy = $subjectData
    }

    $dir = Join-Path $proj '00_admin\approvals'
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $target = Join-Path $dir $name
    if (Test-Path -LiteralPath $target) {
        $hist = Join-Path $dir 'history'
        New-Item -ItemType Directory -Force -Path $hist | Out-Null
        Move-Item -LiteralPath $target -Destination (Join-Path $hist ("{0}.{1}.json" -f [IO.Path]::GetFileNameWithoutExtension($name), (Get-Date -Format 'yyyyMMddHHmmss')))
    }
    $json = $rec | ConvertTo-Json -Depth 30
    [IO.File]::WriteAllText($target, $json + "`n", (New-Object System.Text.UTF8Encoding($false)))
    $notes += "Recorded: $code $what $decision (00_admin/approvals/$name)."
}

if ($notes.Count -gt 0) {
    $out = @{ hookSpecificOutput = @{ hookEventName = 'PostToolUse'; additionalContext = ($notes -join ' ') } }
    $out | ConvertTo-Json -Depth 5 -Compress
}
exit 0
