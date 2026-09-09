[CmdletBinding()]
param(
    [switch]$Install
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$TaskName = 'NormativAI Auto Ingestion Worker'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$WorkerPath = Join-Path $ProjectRoot 'auto_ingestion_worker.py'

if (-not $Install) {
    throw 'Niciun task nu a fost creat. Rulează scriptul numai cu -Install după aprobarea explicită.'
}

if (-not (Test-Path -LiteralPath $WorkerPath -PathType Leaf)) {
    throw 'Workerul local lipsește; taskul nu a fost creat.'
}

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    throw 'Taskul există deja; scriptul nu îl modifică automat.'
}

$PythonPath = (Get-Command python -CommandType Application).Source
$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument ('"{0}"' -f $WorkerPath) -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description 'Procesează local PDF-uri noi NormativAI din documente_noi/_inbox.' | Out-Null
Write-Output 'Taskul local de ingestion a fost creat. După logon, pune PDF-uri noi în documente_noi/_inbox.'
