<#
.SYNOPSIS
    Registers (or removes) the hoops-lab data refresh as a per-user Scheduled Task.

.DESCRIPTION
    The task "hoops-lab data refresh" (weekly by default; -Daily for every morning after the
    NBA night) runs, from the repo root that contains this script:

        .venv\Scripts\python.exe scripts\refresh_season.py --push

    appending stdout and stderr to data\raw\refresh.log (gitignored). It runs in a hidden
    console (conhost --headless), so Task Scheduler's "Last Run Result" is always 0: the
    log's last line ("finished, exit code N") is the real result.

    No admin rights needed: the task belongs to the current user and runs while that user
    is logged on. If the PC was off or asleep at the scheduled time, it runs at the next
    logon/wake (StartWhenAvailable). It needs a network, stops after 2 hours and never
    overlaps itself. Git must be able to push without prompting (run "git push --dry-run"
    once by hand so Git Credential Manager stores your login).

    Keep the schedule active on ONE PC at a time: before scheduling it on a new PC, run
    "scripts\schedule_refresh.ps1 -Unregister" on the old one. Two PCs refreshing the same
    season race each other and one of the two runs fails on a rebase conflict.

.PARAMETER Day
    Day of the week for the weekly schedule (default Monday).

.PARAMETER Daily
    Run every day instead: each morning publishes the previous night's games. A day without
    games changes no data and pushes nothing.

.PARAMETER Time
    Local start time as HH:mm (default 09:00).

.PARAMETER Unregister
    Remove the task instead of registering it.

.PARAMETER DryRun
    Print what would be registered (or removed) without touching Task Scheduler.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\schedule_refresh.ps1 -Day Tuesday -Time 07:30

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\schedule_refresh.ps1 -Daily -Time 09:00
#>
[CmdletBinding()]
param(
    [System.DayOfWeek]$Day = 'Monday',
    [switch]$Daily,
    [ValidatePattern('^\d{1,2}:\d{2}$')][string]$Time = '09:00',
    [switch]$Unregister,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$TaskName = 'hoops-lab data refresh'
$LegacyTaskName = 'hoops-lab weekly refresh'  # the name before -Daily existed
$Root = Split-Path -Parent $PSScriptRoot

# Drop the task registered under the old name, so one PC never runs two schedules.
if (-not $DryRun -and (Get-ScheduledTask -TaskName $LegacyTaskName -ErrorAction SilentlyContinue)) {
    Unregister-ScheduledTask -TaskName $LegacyTaskName -Confirm:$false
    Write-Host "Removed the legacy task '$LegacyTaskName'."
}

if ($Unregister) {
    if (-not (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue)) {
        Write-Host "No task named '$TaskName' on this PC - nothing to remove."
    } elseif ($DryRun) {
        Write-Host "[dry run] would unregister '$TaskName'"
    } else {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Removed '$TaskName'."
    }
    exit 0
}

if (-not (Test-Path (Join-Path $Root '.venv\Scripts\python.exe'))) {
    Write-Warning "No .venv in $Root - run scripts\setup_machine.ps1 first."
}

# Hidden console: no window pops up mid-refresh (or gets closed by mistake).
$command = '.venv\Scripts\python.exe scripts\refresh_season.py --push >> data\raw\refresh.log 2>&1'
$actionArgs = @{
    Execute          = Join-Path $env:SystemRoot 'System32\conhost.exe'
    Argument         = "--headless cmd.exe /d /s /c `"$command`""
    WorkingDirectory = $Root
}
$settingsArgs = @{
    StartWhenAvailable          = $true
    RunOnlyIfNetworkAvailable   = $true
    ExecutionTimeLimit          = New-TimeSpan -Hours 2
    MultipleInstances           = 'IgnoreNew'
    AllowStartIfOnBatteries     = $true  # laptops: otherwise the run is silently skipped
    DontStopIfGoingOnBatteries  = $true
}
if ($Daily) {
    $trigger = New-ScheduledTaskTrigger -Daily -At $Time
    $when = "every day at $Time"
} else {
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Day -At $Time
    $when = "every $Day at $Time"
}
# -At yields a UTC ("...Z") boundary that drifts an hour at DST; local time follows the clock.
$trigger.StartBoundary = ([datetime]$Time).ToString('s')
$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$task = @{
    TaskName    = $TaskName
    Description = "hoops-lab data refresh, $when (log: $Root\data\raw\refresh.log)"
    Action      = New-ScheduledTaskAction @actionArgs
    Trigger     = $trigger
    Settings    = New-ScheduledTaskSettingsSet @settingsArgs
    Principal   = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
}

if ($DryRun) {
    Write-Host "[dry run] would register '$TaskName' for $user (no admin, runs while logged on)"
    $s = $task.Settings
    Write-Host "  when:     $when (start boundary $($task.Trigger.StartBoundary))"
    Write-Host "  settings: StartWhenAvailable=$($s.StartWhenAvailable)"
    Write-Host "            RunOnlyIfNetworkAvailable=$($s.RunOnlyIfNetworkAvailable)"
    Write-Host "            ExecutionTimeLimit=$($s.ExecutionTimeLimit) MultipleInstances=$($s.MultipleInstances)"
    Write-Host "            DisallowStartIfOnBatteries=$($s.DisallowStartIfOnBatteries)"
    Write-Host "  run in:   $Root"
    Write-Host "  command:  $($task.Action.Execute) $($task.Action.Arguments)"
    exit 0
}

Register-ScheduledTask @task -Force | Out-Null
$next = (Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime
Write-Host "Registered '$TaskName' ($when) - next run: $next"
Write-Host "Log: $Root\data\raw\refresh.log"
Write-Host "Run it now: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host 'Keep it active on ONE PC: run this script with -Unregister on any other PC.'
