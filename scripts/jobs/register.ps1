# Register (or update) the Crypto Chart AI scheduled tasks for the current user.
# No admin rights needed. Times are local (this machine runs on Pakistan Standard Time).
#
#   powershell -ExecutionPolicy Bypass -File scripts\jobs\register.ps1           # create or update
#   powershell -ExecutionPolicy Bypass -File scripts\jobs\register.ps1 -Remove   # remove every task
#
# Each task runs scripts\jobs\<Bat> daily at <At>, only while you are logged on (no stored
# password), in a hidden console, and catches up at the next wake if the PC was asleep.

param([switch]$Remove)

# One line per job. WL-038 / WL-039 / WL-042 add theirs here.
$Jobs = @(
    @{ Name = 'instruments'; At = '15:30'; Bat = 'instruments.bat' }
    @{ Name = 'calendar'; At = '16:00'; Bat = 'calendar.bat' }
    @{ Name = 'backup'; At = '20:00'; Bat = 'backup.bat' }
)

$TaskPath = '\CryptoChartAI\'
$ErrorActionPreference = 'Stop'

if ($Remove) {
    $tasks = @(Get-ScheduledTask -TaskPath $TaskPath -ErrorAction SilentlyContinue)
    foreach ($t in $tasks) {
        Unregister-ScheduledTask -TaskName $t.TaskName -TaskPath $TaskPath -Confirm:$false
        Write-Host "removed $TaskPath$($t.TaskName)"
    }
    if ($tasks.Count -eq 0) { Write-Host "no tasks under $TaskPath" }
    return
}

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$user = "$env:USERDOMAIN\$env:USERNAME"
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
# conhost --headless runs the .bat without a console window popping up.
$conhost = Join-Path $env:SystemRoot 'System32\conhost.exe'

foreach ($job in $Jobs) {
    $bat = Join-Path $here $job.Bat
    if (-not (Test-Path $bat)) { throw "missing $bat" }
    $action = New-ScheduledTaskAction -Execute $conhost `
        -Argument "--headless cmd.exe /c `"`"$bat`"`"" -WorkingDirectory $here
    $trigger = New-ScheduledTaskTrigger -Daily -At $job.At
    Register-ScheduledTask -TaskName $job.Name -TaskPath $TaskPath -Action $action `
        -Trigger $trigger -Principal $principal -Settings $settings `
        -Description "Crypto Chart AI job '$($job.Name)' ($($job.Bat)), daily at $($job.At) local" `
        -Force | Out-Null
    $info = Get-ScheduledTaskInfo -TaskName $job.Name -TaskPath $TaskPath
    Write-Host "registered $TaskPath$($job.Name) daily $($job.At), next run $($info.NextRunTime)"
}
