# Record Dots uninstaller. Removes the scheduled task. Start it with Uninstall.bat.
# It never deletes the KMZ/CSV files Max reads.

$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
if (-not $here) { $here = Split-Path -Parent $MyInvocation.MyCommand.Path }

$p = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host 'Asking Windows for administrator rights. Click Yes on the prompt.'
    try {
        $argList = '-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $PSCommandPath
        Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') -ArgumentList $argList -Verb RunAs
    } catch {
        Write-Host 'Administrator rights were not granted, so nothing was removed.' -ForegroundColor Red
        Read-Host 'Press Enter to close'
    }
    exit
}

try {
    $taskName = 'Record Dots - Fetch Daily Records'
    $installDir = $null
    $cfgPath = Join-Path $here 'config.json'
    if (Test-Path -LiteralPath $cfgPath) {
        $cfg = Get-Content -LiteralPath $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($cfg.recordDots.taskName) { $taskName = [string]$cfg.recordDots.taskName }
        if ($cfg.recordDots.installDir) { $installDir = [string]$cfg.recordDots.installDir }
    }

    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($task) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "Removed the scheduled task '$taskName'." -ForegroundColor Green
    } else {
        Write-Host "No scheduled task named '$taskName' was found. Nothing to remove."
    }

    if ($installDir -and (Test-Path -LiteralPath $installDir)) {
        Write-Host ''
        Write-Host "The script folder $installDir still exists. It holds stations.csv, which grows as new stations are learned."
        $answer = Read-Host 'Delete that folder too? (y/N)'
        if ($answer -match '^[Yy]') {
            Remove-Item -LiteralPath $installDir -Recurse -Force
            Write-Host 'Folder deleted.' -ForegroundColor Green
        } else {
            Write-Host 'Folder kept.'
        }
    }
    Write-Host 'The KMZ and CSV files that Max reads were left in place.'
} catch {
    Write-Host ('PROBLEM: ' + $_.Exception.Message) -ForegroundColor Red
}
Read-Host 'Press Enter to close'
