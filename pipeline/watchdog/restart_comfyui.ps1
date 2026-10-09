<#
.SYNOPSIS
  Close ComfyUI (the process serving the port and the console window that started it), wait, check that GPU
  memory was released, reopen ComfyUI with the user's launcher, and wait until its API answers.

.DESCRIPTION
  Design: docs/studio-design.md, Tool layer -> ComfyUI restart procedure, steps 3-7.
  Only the VRAM watchdog runs this for real, inside an approved window. -DryRun only reports what it would do.
  The last output line is a JSON result. Exit codes: 0 ok / dry run, 2 refused, 3 still listening,
  4 memory not released, 5 API did not come back.
  Windows PowerShell 5.1 syntax.
#>
[CmdletBinding()]
param(
    [switch]$DryRun,
    [string]$Launcher = 'C:\Users\david\Desktop\ComfyUI.bat',
    [int]$Port = 8188,
    [int]$WaitSeconds = 15,
    [int]$StartTimeoutSeconds = 180,
    [double]$ReleasedMaxUsedGB = 8
)
$ErrorActionPreference = 'Stop'

function Write-Result([System.Collections.IDictionary]$r, [int]$code) {
    ($r | ConvertTo-Json -Compress -Depth 5)
    exit $code
}

function Get-GpuUsedGB {
    $line = & nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | Select-Object -First 1
    return [math]::Round([double]$line / 1024, 2)
}

function Test-ComfyApi {
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/system_stats" -TimeoutSec 5 | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Describe([object]$p) {
    $cmd = ''
    if ($p.CommandLine) { $cmd = ($p.CommandLine -replace '\s+', ' ').Trim() }
    return [ordered]@{ pid = [int]$p.ProcessId; name = $p.Name; command = $cmd }
}

$result = [ordered]@{ dry_run = [bool]$DryRun; launcher = $Launcher; port = $Port; status = $null }

if (-not (Test-Path -LiteralPath $Launcher)) {
    $result.status = 'launcher_missing'
    Write-Result $result 2
}

# Find the listener and walk up to the console (cmd.exe running a .bat). Only python.exe may sit in between.
$listen = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
$chain = New-Object System.Collections.ArrayList
$console = $null
$listener = $null
if ($listen) {
    $listener = Get-CimInstance Win32_Process -Filter "ProcessId=$($listen.OwningProcess)"
    if (-not $listener -or $listener.Name -ne 'python.exe' -or $listener.CommandLine -notmatch 'main\.py') {
        $result.status = 'not_comfyui'
        if ($listener) { $result.listener = Describe $listener }
        Write-Result $result 2
    }
    $cur = $listener
    while ($cur) {
        [void]$chain.Add((Describe $cur))
        if ($cur.Name -eq 'cmd.exe') {
            if ($cur.CommandLine -match '\.bat') { $console = $cur }
            break
        }
        if ($cur.Name -ne 'python.exe') { break }
        $cur = Get-CimInstance Win32_Process -Filter "ProcessId=$($cur.ParentProcessId)"
    }
}
$result.found = $chain
if ($console) {
    $result.close = "taskkill /PID $($console.ProcessId) /T /F"
    $result.console_launcher_matches = ($console.CommandLine -like "*$Launcher*")
} elseif ($listener) {
    $result.close = "taskkill /PID $($listener.ProcessId) /T /F (no console found)"
} else {
    $result.close = 'nothing to close: no process listens on the port'
}
$result.relaunch = "explorer.exe `"$Launcher`""
$result.gpu_used_gb_before = Get-GpuUsedGB

if ($DryRun) {
    $result.status = 'dry_run'
    Write-Result $result 0
}

# --- for real: close, wait, check memory, relaunch, wait for the API ---
if ($console) {
    & taskkill.exe /PID $console.ProcessId /T /F | Out-Null
} elseif ($listener) {
    & taskkill.exe /PID $listener.ProcessId /T /F | Out-Null
}
Start-Sleep -Seconds $WaitSeconds

$still = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
$result.gpu_used_gb_after_close = Get-GpuUsedGB
if ($still) {
    $result.status = 'still_listening'
    Write-Result $result 3
}
if ($result.gpu_used_gb_after_close -gt $ReleasedMaxUsedGB) {
    $result.status = 'memory_not_released'
    Write-Result $result 4
}

$started = Get-Date
Start-Process -FilePath 'explorer.exe' -ArgumentList "`"$Launcher`""
$deadline = $started.AddSeconds($StartTimeoutSeconds)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 5
    if (Test-ComfyApi) {
        $result.status = 'restarted'
        $result.api_back_after_s = [int]((Get-Date) - $started).TotalSeconds
        Write-Result $result 0
    }
}
$result.status = 'start_timeout'
Write-Result $result 5
