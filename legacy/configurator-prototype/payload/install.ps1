# Record Dots installer. Reads config.json from this folder.
# Start it with Install.bat (double-click). SETUP.txt lists everything it does.

$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
if (-not $here) { $here = Split-Path -Parent $MyInvocation.MyCommand.Path }

function Test-Admin {
    $p = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin)) {
    Write-Host 'Asking Windows for administrator rights. Click Yes on the prompt.'
    try {
        $argList = '-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $PSCommandPath
        Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') -ArgumentList $argList -Verb RunAs
    } catch {
        Write-Host 'Administrator rights were not granted, so nothing was installed.' -ForegroundColor Red
        Read-Host 'Press Enter to close'
    }
    exit
}

try { Start-Transcript -Path (Join-Path $here 'install_log.txt') -Force | Out-Null } catch { }

function Step([string]$Message) { Write-Host ''; Write-Host ('== ' + $Message) -ForegroundColor Cyan }
function Good([string]$Message) { Write-Host ('   OK    ' + $Message) -ForegroundColor Green }
function Warn([string]$Message) { Write-Host ('   CHECK ' + $Message) -ForegroundColor Yellow }
function Stop-WithProblem([string]$Message) {
    Write-Host ''
    Write-Host ('PROBLEM: ' + $Message) -ForegroundColor Red
    Write-Host 'Nothing is half-finished: you can fix the problem and run Install.bat again.'
    Write-Host 'A copy of this window was saved as install_log.txt in the setup folder.'
    try { Stop-Transcript | Out-Null } catch { }
    Read-Host 'Press Enter to close'
    exit 1
}

function Get-RepoFile([string]$Name, [string]$Marker, [bool]$KeepExisting) {
    $dest = Join-Path $script:installDir $Name
    if ($KeepExisting -and (Test-Path -LiteralPath $dest)) { Good "$Name already present (kept as is)"; return }
    $tmp = $dest + '.download'
    try {
        Invoke-WebRequest -Uri ($script:base + $Name) -OutFile $tmp -UseBasicParsing -TimeoutSec 60
        $text = [System.IO.File]::ReadAllText($tmp)
        if ($text.Length -lt 200) { throw 'the downloaded file is too small to be right' }
        if ($Marker -and $text.IndexOf($Marker) -lt 0) { throw "the downloaded file does not contain '$Marker'" }
        Move-Item -LiteralPath $tmp -Destination $dest -Force
        Good "$Name downloaded"
    } catch {
        $why = $_.Exception.Message
        if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue }
        $local = Join-Path $here $Name
        if (Test-Path -LiteralPath $local) {
            Copy-Item -LiteralPath $local -Destination $dest -Force
            Good "$Name copied from the setup folder (download failed: $why)"
        } elseif (Test-Path -LiteralPath $dest) {
            Warn "$Name could not be updated ($why); keeping the installed copy"
        } else {
            throw "Could not get $Name from GitHub ($why). Check that this PC can reach raw.githubusercontent.com."
        }
    }
}

try {
    Step 'Reading config.json'
    $cfgPath = Join-Path $here 'config.json'
    if (-not (Test-Path -LiteralPath $cfgPath)) {
        Stop-WithProblem 'config.json is missing. Unzip the whole package first, then run Install.bat from the unzipped folder.'
    }
    $cfg = Get-Content -LiteralPath $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $rd = $cfg.recordDots

    $script:installDir = [string]$rd.installDir
    $kmlFolder = [string]$rd.kmlFolder
    $navFolder = [string]$rd.navDataFolder
    $taskName = [string]$rd.taskName
    $mins = [int]$rd.intervalMinutes
    $ref = [string]$rd.scriptsRef
    if (-not $ref) { $ref = 'main' }

    if (-not $cfg.station.name -or -not $cfg.station.contactEmail) { Stop-WithProblem 'config.json has no station name or contact email. Fill them in on the configurator page and download a new package.' }
    foreach ($p in @($script:installDir, $kmlFolder, $navFolder)) {
        if ($p -notmatch '^[A-Za-z]:\\') { Stop-WithProblem "'$p' is not a full Windows path like D:\Folder." }
    }
    if (-not $taskName) { Stop-WithProblem 'config.json has no task name.' }
    if ($mins -lt 15 -or $mins -gt 1440) { Stop-WithProblem 'The refresh interval in config.json is out of range.' }
    Good ("Station {0}, refresh every {1} minutes" -f $cfg.station.name, $mins)

    Step 'Checking drives and creating folders'
    foreach ($p in @($script:installDir, $kmlFolder, $navFolder)) {
        $drive = Split-Path -Qualifier $p
        if (-not (Test-Path -LiteralPath ($drive + '\'))) {
            Stop-WithProblem "Drive $drive does not exist on this PC (needed for $p). If your Max folders are somewhere else, change them under Advanced on the configurator page."
        }
        New-Item -ItemType Directory -Path $p -Force | Out-Null
        Good $p
    }
    New-Item -ItemType Directory -Path (Join-Path $script:installDir 'icons') -Force | Out-Null

    Step 'Getting the latest scripts from GitHub'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $script:base = 'https://raw.githubusercontent.com/justingehrts/daily-record-dots/' + $ref + '/'
    Get-RepoFile 'FetchDailyRecords.ps1' 'config.json' $false
    Get-RepoFile 'station_manager.ps1' $null $false
    Get-RepoFile 'stations.csv' $null $true

    Step 'Copying your settings and icons'
    Copy-Item -LiteralPath $cfgPath -Destination (Join-Path $script:installDir 'config.json') -Force
    Good 'config.json'
    foreach ($t in @('himax', 'himin', 'lomax', 'lomin')) {
        $src = Join-Path $here ('icons\' + $t + '.png')
        if (-not (Test-Path -LiteralPath $src)) { throw "icons\$t.png is missing from the setup folder." }
        Copy-Item -LiteralPath $src -Destination (Join-Path $script:installDir ('icons\' + $t + '.png')) -Force
    }
    Good 'icons (4)'
    Get-ChildItem -LiteralPath $script:installDir -Recurse -File | Unblock-File
    Good 'Files unblocked so Windows will run them'

    Step "Setting up the scheduled task '$taskName'"
    $psExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $scriptPath = Join-Path $script:installDir 'FetchDailyRecords.ps1'
    $taskArgs = '-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $scriptPath
    $action = New-ScheduledTaskAction -Execute $psExe -Argument $taskArgs -WorkingDirectory $script:installDir
    $now = Get-Date
    $startAt = $now.Date.AddMinutes([math]::Ceiling($now.TimeOfDay.TotalMinutes / $mins) * $mins)
    $trigger = New-ScheduledTaskTrigger -Once -At $startAt -RepetitionInterval (New-TimeSpan -Minutes $mins) -RepetitionDuration (New-TimeSpan -Days 3650)
    $user = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    $principal = New-ScheduledTaskPrincipal -UserId $user -LogonType S4U -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
    Good "Runs as $user whether or not anyone is logged on, every $mins minutes, starting $($startAt.ToString('h:mm tt'))"

    Step 'Test run (same account and settings as the schedule). This can take a few minutes.'
    $before = Get-Date
    Start-ScheduledTask -TaskName $taskName
    Start-Sleep -Seconds 3
    $deadline = (Get-Date).AddMinutes(10)
    do {
        Start-Sleep -Seconds 5
        Write-Host -NoNewline '.'
        $state = (Get-ScheduledTask -TaskName $taskName).State
    } while ($state -eq 'Running' -and (Get-Date) -lt $deadline)
    Write-Host ''

    $runLog = Join-Path $script:installDir 'run_log.txt'
    $doneLine = $null
    if (Test-Path -LiteralPath $runLog) {
        $doneLine = Get-Content -LiteralPath $runLog | Where-Object { $_ -match 'Done\.' } | Select-Object -Last 1
    }
    $fresh = @(Get-ChildItem -LiteralPath $kmlFolder -Filter '*.kmz' -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -ge $before })

    if ($fresh.Count -ge 28) {
        Good "Test run wrote $($fresh.Count) of 28 KMZ files"
    } elseif ($fresh.Count -gt 0) {
        Warn "Test run wrote only $($fresh.Count) of 28 KMZ files. Open run_log.txt in $($script:installDir) to see which downloads failed."
    } else {
        if (Test-Path -LiteralPath $runLog) { Get-Content -LiteralPath $runLog -Tail 15 | ForEach-Object { Write-Host ('   ' + $_) } }
        Stop-WithProblem "The test run did not write any KMZ files to $kmlFolder. The last lines of run_log.txt are shown above."
    }
    if ($doneLine) { Write-Host ('   ' + $doneLine) }

    Write-Host ''
    Write-Host 'Installed. Next steps (also in SETUP.txt):' -ForegroundColor Green
    Write-Host '  1. In Max, point each record-dots KML layer at its KMZ file.'
    Write-Host '  2. After new data arrives, refresh each layer''s plot locations in Max by hand.'
    Write-Host ('  To check on it later, open ' + $runLog)
    try { Stop-Transcript | Out-Null } catch { }
    Read-Host 'Press Enter to close'
} catch {
    Stop-WithProblem $_.Exception.Message
}
