[CmdletBinding()]
param(
    [Parameter()]
    [System.Management.Automation.PSCredential]$Credential,

    [Parameter()]
    [string]$TaskName = 'SintelEcommerceBackup',

    [Parameter()]
    [string]$GitBashPath = 'C:\Program Files\Git\bin\bash.exe'
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $GitBashPath)) {
    throw "No se encontro Git Bash en: $GitBashPath"
}

if (-not $Credential) {
    $Credential = Get-Credential -Message 'Ingrese la cuenta de servicio con acceso a Docker Desktop. No use SYSTEM.'
}

if ([string]::IsNullOrWhiteSpace($Credential.UserName) -or $Credential.UserName -match '^(SYSTEM|NT AUTHORITY\\SYSTEM|S-1-5-18)$') {
    throw 'Debe usar una cuenta de servicio con acceso a Docker Desktop; SYSTEM no tiene acceso al named pipe del daemon.'
}

$projectDir = Split-Path -Parent $PSScriptRoot
$backupScript = "$projectDir/deploy/backup.sh".Replace('\', '/')
$logPath = 'C:/Users/Administrator/sintel_backups/backup.log'
$bashCommand = "'$backupScript' >> '$logPath' 2>&1"

$action = New-ScheduledTaskAction -Execute $GitBashPath -Argument "-lc `"$bashCommand`"" -WorkingDirectory $projectDir
$trigger = New-ScheduledTaskTrigger -Daily -At 3:00AM
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 15) `
    -MultipleInstances IgnoreNew
$password = $Credential.GetNetworkCredential().Password
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -User $Credential.UserName `
        -Password $password `
        -RunLevel Highest `
        -Force | Out-Null
}
finally {
    $password = $null
}

$task = Get-ScheduledTask -TaskName $TaskName
$info = Get-ScheduledTaskInfo -TaskName $TaskName

Write-Host "Tarea '$TaskName' instalada para $($task.Principal.UserId)."
Write-Host "Proxima ejecucion: $($info.NextRunTime)"
Write-Host 'Ejecute Start-ScheduledTask y valide LastTaskResult=0 y un backup nuevo antes de dar por cerrado el hallazgo.'
