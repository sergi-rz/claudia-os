# Claudia OS — Instalar notificaciones locales via Task Scheduler (Windows)
# Instala: recordatorios (siempre) + briefings (si briefing.json existe)
#
# Uso: powershell -ExecutionPolicy Bypass -File setup-local-reminders.ps1
# Desinstalar: powershell -ExecutionPolicy Bypass -File setup-local-reminders.ps1 -Uninstall

param([switch]$Uninstall)

$ErrorActionPreference = "Stop"
$ClaudiaRoot = (Resolve-Path "$PSScriptRoot\..\..\..").Path
$SkillDir = $PSScriptRoot
$CredsFile = Join-Path $ClaudiaRoot "user\credentials\.env"
$BriefingConfig = Join-Path $ClaudiaRoot "user\config\briefing.json"
$LogDir = Join-Path $ClaudiaRoot "user\logs"

$TaskReminders = "ClaudiaOS-Reminders"
$TaskBriefingPrefix = "ClaudiaOS-Briefing"

# --- Uninstall ---
if ($Uninstall) {
    Write-Host "Desinstalando notificaciones locales..."
    Unregister-ScheduledTask -TaskName $TaskReminders -Confirm:$false -ErrorAction SilentlyContinue
    Get-ScheduledTask | Where-Object { $_.TaskName -like "$TaskBriefingPrefix-*" } | ForEach-Object {
        Unregister-ScheduledTask -TaskName $_.TaskName -Confirm:$false
    }
    $wrappers = Get-ChildItem -Path $SkillDir -Filter "run-*.cmd" -ErrorAction SilentlyContinue
    if ($wrappers) { $wrappers | Remove-Item -Force }
    Write-Host "Hecho. Todas las tareas programadas de Claudia OS han sido eliminadas."
    exit 0
}

# --- Validaciones ---
if (-not (Test-Path $CredsFile)) {
    Write-Error "No existe $CredsFile. Crea el fichero con TELEGRAM_BOT_TOKEN y TELEGRAM_USER_ID."
    exit 1
}

$envVars = @{}
Get-Content $CredsFile | Where-Object { $_ -match '^\s*[^#]' } | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        $envVars[$Matches[1].Trim()] = $Matches[2].Trim()
    }
}

if (-not $envVars['TELEGRAM_BOT_TOKEN'] -or -not $envVars['TELEGRAM_USER_ID']) {
    Write-Error "TELEGRAM_BOT_TOKEN o TELEGRAM_USER_ID no definidos en .env"
    exit 1
}

$nodePath = (Get-Command node -ErrorAction SilentlyContinue).Source
if (-not $nodePath) {
    Write-Error "node no encontrado. Instala Node.js 18+."
    exit 1
}

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

# Helper: crear wrapper .cmd con env vars
function New-Wrapper {
    param([string]$Name, [string]$Script, [string[]]$Args)
    $logFile = Join-Path $LogDir "$Name.log"
    $lines = @(
        "@echo off"
        "set TELEGRAM_BOT_TOKEN=$($envVars['TELEGRAM_BOT_TOKEN'])"
        "set TELEGRAM_USER_ID=$($envVars['TELEGRAM_USER_ID'])"
        "cd /d `"$SkillDir`""
    )
    $argStr = if ($Args) { " $($Args -join ' ')" } else { "" }
    $lines += "`"$nodePath`" `"$Script`"$argStr >> `"$logFile`" 2>&1"
    $wrapperPath = Join-Path $SkillDir "run-$Name.cmd"
    Set-Content -Path $wrapperPath -Value ($lines -join "`r`n") -Encoding ASCII
    return $wrapperPath
}

# ============================================================
# 1. RECORDATORIOS (siempre)
# ============================================================

Unregister-ScheduledTask -TaskName $TaskReminders -Confirm:$false -ErrorAction SilentlyContinue

$wrapper = New-Wrapper -Name "reminders" -Script (Join-Path $SkillDir "check_reminders.js")
$action = New-ScheduledTaskAction -Execute $wrapper
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 5) `
    -RepetitionDuration ([TimeSpan]::MaxValue)
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2)

Register-ScheduledTask -TaskName $TaskReminders -Action $action -Trigger $trigger -Settings $settings `
    -Description "Claudia OS - Check reminders every 5 minutes" | Out-Null

Write-Host ""
Write-Host "Recordatorios instalados (check cada 5 min)"

# ============================================================
# 2. BRIEFINGS (solo si briefing.json existe)
# ============================================================

# Limpiar briefings anteriores
Get-ScheduledTask | Where-Object { $_.TaskName -like "$TaskBriefingPrefix-*" } | ForEach-Object {
    Unregister-ScheduledTask -TaskName $_.TaskName -Confirm:$false
}

if (Test-Path $BriefingConfig) {
    $config = Get-Content $BriefingConfig -Raw | ConvertFrom-Json

    if ($config.enabled) {
        foreach ($schedule in $config.schedules) {
            $safeName = $schedule.name -replace '[^a-zA-Z0-9_-]', '_'
            $taskName = "$TaskBriefingPrefix-$safeName"

            $wrapper = New-Wrapper -Name "briefing-$safeName" `
                -Script (Join-Path $SkillDir "send_briefing.js") `
                -Args @($schedule.name)

            $action = New-ScheduledTaskAction -Execute $wrapper
            $trigger = New-ScheduledTaskTrigger -Daily `
                -At "$($schedule.hour):$($schedule.minute.ToString('D2'))"
            $settings = New-ScheduledTaskSettingsSet `
                -StartWhenAvailable `
                -DontStopIfGoingOnBatteries `
                -AllowStartIfOnBatteries `
                -ExecutionTimeLimit (New-TimeSpan -Minutes 2)

            Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings `
                -Description "Claudia OS - Briefing '$($schedule.name)'" | Out-Null

            $timeStr = "$($schedule.hour):$($schedule.minute.ToString('D2'))"
            Write-Host "Briefing '$($schedule.name)' instalado ($timeStr)"
        }
    }
} else {
    Write-Host "  (Sin briefing - crea user\config\briefing.json para activarlo)"
}

Write-Host ""
Write-Host "Logs en: $LogDir"
Write-Host ""
Write-Host "Notas:"
Write-Host "  - Funciona mientras el PC este encendido (no necesita VPS)"
Write-Host "  - 'StartWhenAvailable' envia notificaciones pendientes al encender"
Write-Host "  - Los recordatorios con ctx=yes se envian como notificacion simple"
Write-Host "    (el enriquecimiento con Claude requiere el bot completo)"
Write-Host ""
Write-Host "Para desinstalar: powershell -File $PSCommandPath -Uninstall"
Write-Host "Para actualizar tras cambiar briefing.json: volver a ejecutar este script"
