<#
  guard.ps1 - PreToolUse guardrails for the studio (docs/studio-design.md, Tool layer -> Guardrails;
  docs/phase1-plan.md step 8). Windows PowerShell 5.1.

  Blocks a tool call (exit 2, reason on stderr) when it would:
    - touch D: (failing drive);
    - write a file outside the allowed roots: this repo, an approved project's footage folder,
      Claude Code's scratch folder (%TEMP%\claude) and this project's memory folder;
    - read or print the Gemini key or a .env file;
    - write into a project's 00_admin\approvals (only record-approval.ps1 writes there);
    - let a studio agent edit the guardrails (hooks, settings, agents, .mcp.json, restart script, watchdog config);
    - submit a ComfyUI job without the project's recorded approval, while ComfyUI's queue is busy,
      or from an agent other than the Render Wrangler / Pipeline TD;
    - interrupt ComfyUI or clear its queue or history;
    - run restart_comfyui.ps1 for real, or kill ComfyUI (only the watchdog restarts it);
    - run the terminal approval command (that is for the user's own terminal).
  Shell commands are checked best-effort; file tools are checked exactly.
#>
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.Encoding]::UTF8

function Block([string]$why) {
    [Console]::Error.WriteLine("Blocked by studio guardrail: $why")
    exit 2
}

$raw = [Console]::In.ReadToEnd()
try { $in = $raw | ConvertFrom-Json } catch { Block 'unreadable hook input' }

$repo = $env:CLAUDE_PROJECT_DIR
if (-not $repo) { $repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path }
$tool = [string]$in.tool_name
$ti = $in.tool_input
$agent = [string]$in.agent_type
$studioAgents = @('producer', 'director', 'writer', 'music-timing', 'art-director', 'asset-designer', 'storyboard',
    'prompt-writer', 'render-wrangler', 'pipeline-td', 'dailies-qc', 'editor', 'finishing', 'delivery-qc', 'librarian')
$isStudioAgent = $studioAgents -contains $agent

# ---------------------------------------------------------------- path helpers
function Norm([string]$p) {
    if (-not $p) { return '' }
    $q = $p.Trim('"', "'", ' ') -replace '/', '\'
    if ($q -match '^\\([a-zA-Z])(\\|$)') { $q = $Matches[1] + ':\' + $q.Substring([Math]::Min(3, $q.Length)) }
    if ($q -match '^[a-zA-Z]:\\' -or $q -match '^\\\\') {
        try { $q = [System.IO.Path]::GetFullPath($q) } catch { }
    }
    return $q.TrimEnd('\').ToLowerInvariant()
}
function Within([string]$child, [string]$root) {
    $c = Norm $child; $r = Norm $root
    if (-not $r -or -not $c) { return $false }
    return ($c -eq $r) -or $c.StartsWith($r + '\')
}
function OnD([string]$p) { return (Norm $p) -match '^d:(\\|$)' }

function Get-Sha256([string]$path) { return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }

# Approved project policies: only hook/terminal-recorded approvals whose proposal is unchanged.
function Get-ApprovedPolicies {
    $out = @()
    $pattern = Join-Path $repo 'projects\*\00_admin\approvals\policy.json'
    foreach ($f in @(Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue)) {
        try {
            $rec = Get-Content -LiteralPath $f.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
            $proj = $f.Directory.Parent.Parent.FullName
            $subject = Join-Path $proj ($rec.subject -replace '/', '\')
            if ($rec.kind -eq 'policy' -and $rec.decision -eq 'approved' -and (Test-Path -LiteralPath $subject) -and
                (Get-Sha256 $subject) -eq $rec.subject_sha256) {
                $out += [pscustomobject]@{ code = $rec.project; dir = $proj; policy = $rec.policy }
            }
        } catch { }
    }
    return $out
}

function Get-WriteRoots {
    $roots = @($repo, (Join-Path $env:TEMP 'claude'), (Join-Path $env:USERPROFILE '.claude\projects\C--claude-video-agent-studio\memory'))
    if ($in.scratchpad_dir) { $roots += [string]$in.scratchpad_dir }
    foreach ($p in Get-ApprovedPolicies) { $roots += [string]$p.policy.footage_folder }
    return $roots
}

function Test-InRoots([string]$path, [object[]]$roots) {
    foreach ($r in $roots) { if (Within $path $r) { return $true } }
    return $false
}

$approvalsRe = '(?i)\\projects\\[a-z]{3}\\00_admin\\approvals(\\|$)'
function Test-SecretPath([string]$p) {
    $n = Norm $p
    return ($n -match '\\geminiapi\.txt$') -or ($n -match '\\\.env$') -or ($n -match '\\[^\\]*api[^\\]*key[^\\]*\.txt$')
}
$guardFiles = @('.claude\hooks', '.claude\settings.json', '.claude\settings.local.json', '.claude\agents', '.mcp.json',
    'pipeline\watchdog\restart_comfyui.ps1', 'pipeline\watchdog\config.json', 'pipeline\watchdog\comfyui_launch.json')
function Test-GuardFile([string]$p) {
    foreach ($g in $guardFiles) { if (Within $p (Join-Path $repo $g)) { return $true } }
    return $false
}

# ---------------------------------------------------------------- file tools (exact)
if ($tool -in @('Write', 'Edit', 'NotebookEdit', 'MultiEdit')) {
    $path = [string]$ti.file_path
    if (-not $path) { $path = [string]$ti.notebook_path }
    if (OnD $path) { Block "D: is the failing drive; nothing is written there ($path)." }
    if (Test-SecretPath $path) { Block 'key and .env files are never written by agents.' }
    if ((Norm $path) -match $approvalsRe) { Block 'approval records are written only by the record-approval hook from the user''s answer.' }
    if ($isStudioAgent -and (Test-GuardFile $path)) { Block "studio agents cannot change the guardrails ($path). Ask the user." }
    if (-not (Test-InRoots $path (Get-WriteRoots))) {
        Block "writes are allowed only in the repo, an approved project's footage folder, Claude Code's scratch folder and the project memory folder ($path)."
    }
    exit 0
}

# ---------------------------------------------------------------- commands and page scripts
$text = ''
if ($tool -in @('Bash', 'PowerShell')) { $text = [string]$ti.command }
elseif ($tool -like 'mcp__*javascript*') { $text = [string]$ti.text }
else { exit 0 }
$isShell = $tool -in @('Bash', 'PowerShell')

if ($isShell) {
    # D: in any form: D:\ D:/ /d/ or a bare D:
    if ($text -match '(?i)(^|[\s"''=(;|&,>])(d:([\\/]|$|[\s"''])|/d/)') { Block 'D: is the failing drive; commands never touch it.' }

    # Secrets: the key only as --key-file for gemini_video.py; .env never read.
    if ($text -match '(?i)geminiapi\.txt|[\\/][^\\/\s"'']*api[^\\/\s"'']*key[^\\/\s"'']*\.txt') {
        $okUse = ($text -match '(?i)gemini_video\.py') -and ($text -match '--key-file') -and
                 ($text -notmatch '(?i)(\b(cat|type|more|less|head|tail|gc|get-content|select-string|findstr|grep|copy|cp|xcopy|robocopy|copy-item|echo|write-output|write-host|base64|certutil|notepad)\b|[|>])')
        if (-not $okUse) { Block 'the Gemini key is read only by gemini_video.py via --key-file, never printed or copied.' }
    }
    if ($text -match '(?i)(^|[\s"''\\/=])\.env(\s|$|["''])' -and
        $text -match '(?i)\b(cat|type|more|less|head|tail|gc|get-content|select-string|findstr|grep|copy|cp|copy-item|base64|source)\b') {
        Block '.env files hold secrets and are never read by agents.'
    }

    $writeVerb = '(?i)(>|\b(set-content|add-content|out-file|new-item|ni|copy-item|cp|copy|move-item|mv|move|remove-item|rm|del|erase|rd|rmdir|rename-item|ren|mkdir|md|touch|tee|tee-object|robocopy|xcopy|sed|python|py|node|powershell|pwsh|cmd)\b)'
    # Approval records: never through a shell write.
    if ($text -match '(?i)00_admin[\\/]+approvals' -and $text -match $writeVerb) {
        Block 'approval records are written only by the record-approval hook from the user''s answer.'
    }
    if ($text -match '(?i)ticket\.py\s+approve') { Block 'ticket.py approve is for the user''s own terminal only.' }

    # Guardrail files: studio agents may not change them through the shell either.
    if ($isStudioAgent -and $text -match '(?i)(\.claude[\\/]+(hooks|settings|agents)|\.mcp\.json|restart_comfyui\.ps1|watchdog[\\/]+(config|comfyui_launch)\.json)' -and
        $text -match $writeVerb) {
        Block 'studio agents cannot change the guardrails. Ask the user.'
    }

    # Restart and kill: only the watchdog restarts ComfyUI.
    if ($text -match '(?i)restart_comfyui\.ps1' -and $text -notmatch '(?i)-DryRun') {
        Block 'only the VRAM watchdog runs restart_comfyui.ps1 for real, inside an approved window. Use -DryRun to inspect.'
    }
    if ($text -match '(?i)\b(taskkill|stop-process|spps|kill|pkill)\b' -and
        $text -match '(?i)(8188|comfyui|main\.py|/im\s+"?python|-name\s+"?python|cmd\.exe)') {
        Block 'ComfyUI is closed only by the watchdog''s restart procedure.'
    }

    # Writes outside the allowed roots (best effort: absolute paths in commands that write).
    if ($text -match $writeVerb) {
        $roots = Get-WriteRoots
        $targets = @()
        foreach ($m in [regex]::Matches($text, '>>?\s*"?([^\s"|;&]+)')) { $targets += $m.Groups[1].Value }
        $abs = @()
        foreach ($m in [regex]::Matches($text, '(?i)(?<![\w/\\])([a-z]:[\\/][^\s"''|;&<>]*|/[a-z]/[^\s"''|;&<>]*)')) { $abs += $m.Groups[1].Value }
        if ($text -match '(?i)\b(cp|copy|copy-item|xcopy|robocopy)\b') {
            # The destination is the -Destination value, else the last plain argument (relative = inside the working directory).
            $toks = @([regex]::Matches($text, '"[^"]*"|''[^'']*''|\S+') | ForEach-Object { $_.Value.Trim('"', "'") })
            $dest = $null
            for ($i = 0; $i -lt $toks.Count - 1; $i++) { if ($toks[$i] -match '(?i)^-(destination|dest)$') { $dest = $toks[$i + 1] } }
            if (-not $dest) {
                $plain = @($toks | Where-Object { $_ -notmatch '^-' -and $_ -notmatch '^[|;&>]' })
                if ($plain.Count -gt 1) { $dest = $plain[-1] }
            }
            if ($dest) { $targets += $dest }
        }
        elseif ($text -match '(?i)\b(set-content|add-content|out-file|new-item|ni|move-item|mv|move|remove-item|rm|del|erase|rd|rmdir|rename-item|ren|mkdir|md|touch|tee|tee-object)\b') { $targets += $abs }
        foreach ($t in $targets) {
            if ($t -match '(?i)^(/dev/null|nul|\$null|&1|&2)$') { continue }
            if (-not ($t -match '(?i)^([a-z]:[\\/]|/[a-z]/)')) { continue }   # relative paths stay in the working directory
            if (OnD $t) { Block "D: is the failing drive ($t)." }
            if (-not (Test-InRoots $t $roots)) {
                Block "writes are allowed only in the repo, an approved project's footage folder, Claude Code's scratch folder and the project memory folder ($t)."
            }
        }
    }
}

# ---------------------------------------------------------------- ComfyUI
if ($text -match '(?i)(/interrupt\b|/api/queue\b[^\n]*(post|delete|clear)|(post|delete|clear)[^\n]*/api/queue\b|/history\b[^\n]*(post|delete|clear)|interruptProcessing|api\.interrupt|clearItems)') {
    Block 'interrupting ComfyUI or clearing its queue or history is not a studio action.'
}
$postish = '(?i)(-X\s*POST|--data|\s-d\s|--json|-Method\s+Post|requests\.post|method\s*:\s*["'']POST|urlopen\([^)]*data=|data=)'
$isSubmit = ($text -match '(?i)queuePrompt') -or (($text -match '(?i)/(api/)?prompt\b') -and ($text -match $postish))
if ($isSubmit) {
    if ($isStudioAgent -and $agent -notin @('render-wrangler', 'pipeline-td')) {
        Block "only the Render Wrangler submits ComfyUI jobs (this is $agent)."
    }
    $run = [regex]::Match($text, 'studio-run:\s*([A-Z]{3})\s+(R-\d{3,})\s+([A-Za-z0-9_]+)')
    $still = [regex]::Match($text, 'studio-still:\s*([A-Z]{3})\s+([A-Za-z0-9_]+)')
    if (-not $run.Success -and -not $still.Success) {
        Block 'a ComfyUI submit must carry its marker: "studio-run: <CODE> R-### <OUTPUT_ID>" or "studio-still: <CODE> <OUTPUT_ID>".'
    }
    $code = if ($run.Success) { $run.Groups[1].Value } else { $still.Groups[1].Value }
    $proj = Join-Path $repo "projects\$code"
    if ($run.Success) {
        $runId = $run.Groups[2].Value; $outId = $run.Groups[3].Value
        $recPath = Join-Path $proj "00_admin\approvals\$runId.json"
        if (-not (Test-Path -LiteralPath $recPath)) { Block "no recorded approval for $runId." }
        $rec = Get-Content -LiteralPath $recPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($rec.kind -ne 'run_ticket' -or $rec.decision -ne 'approved' -or $rec.run_id -ne $runId) { Block "$runId is not approved." }
        $ticketPath = Join-Path $proj ($rec.subject -replace '/', '\')
        if (-not (Test-Path -LiteralPath $ticketPath) -or (Get-Sha256 $ticketPath) -ne $rec.subject_sha256) {
            Block "$runId changed after the user approved it; ask again."
        }
        $now = [DateTimeOffset]::Now
        if ($now -lt [DateTimeOffset]::Parse($rec.window.start) -or $now -ge [DateTimeOffset]::Parse($rec.window.end)) {
            Block "the approved window for $runId ($($rec.window.start) - $($rec.window.end)) is not open."
        }
        $ticket = Get-Content -LiteralPath $ticketPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if (-not (@($ticket.jobs | ForEach-Object { $_.output_id }) -contains $outId)) { Block "$outId is not a job of $runId." }
    } else {
        $outId = $still.Groups[2].Value
        $pol = @(Get-ApprovedPolicies | Where-Object { $_.code -eq $code })
        if ($pol.Count -eq 0) { Block "project $code has no approved policy, so stills need an approved run ticket." }
        if ($pol[0].policy.approvals.stills.mode -ne 'none') { Block "project $code's policy requires approval for stills; use a run ticket." }
        if ($outId -notmatch '^((CHAR|PROP|ENV|VFX|GFX)_[a-z0-9_]+_v\d{3}_c\d{2}|[A-Z]{3}_SQ\d{3}_U\d{3}_SH\d{3}_kf_v\d{3}(_c\d{2})?)$') {
            Block "$outId is not a still ID."
        }
        $specPath = Join-Path $proj "05_prompts\jobs\$outId.json"
        if (-not (Test-Path -LiteralPath $specPath)) { Block "no job spec for $outId." }
        $spec = Get-Content -LiteralPath $specPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $kreaTemplates = @($pol[0].policy.workflow_templates | Where-Object { $_.role -eq 'krea' } | ForEach-Object { $_.name })
        if ($spec.kind -ne 'krea' -or -not ($kreaTemplates -contains $spec.template)) {
            Block "$outId is not a Krea job on one of the project's approved Krea templates."
        }
    }
    # One GPU job at a time, and never while the user's own jobs run.
    $busy = $null
    if ($env:STUDIO_GUARD_TEST_QUEUE -eq 'empty') { $busy = 0 }
    elseif ($env:STUDIO_GUARD_TEST_QUEUE -eq 'busy') { $busy = 1 }
    else {
        try {
            $q = Invoke-RestMethod -Uri 'http://127.0.0.1:8188/api/queue' -TimeoutSec 5
            $busy = @($q.queue_running).Count + @($q.queue_pending).Count
        } catch { Block 'cannot reach ComfyUI to check its queue.' }
    }
    if ($busy -gt 0) { Block 'ComfyUI''s queue is not empty; the studio submits only when it is idle (one GPU job at a time).' }
}
exit 0
