# run_bridge.ps1
# Envoltorio para la Tarea Programada "SintelSmsBridge". Fija las variables
# de entorno del puente (deben coincidir con SMS_BRIDGE_TOKEN en el .env del
# backend) y arranca bridge.py con salida redirigida a un log persistente.
#
# [CORREGIDO 2026-09-14, auditoria de hardening "PROMPT MAESTRO" seccion 25]
# El token vivia hardcodeado en texto plano en este archivo, TRACKEADO por
# git -- secreto real expuesto en el repositorio (mismo patron que ya se
# corrigio para notas.txt y la password del script E2E de certificacion,
# misma sesion). Rotado y movido a C:\Users\Administrator\sintel_secrets\
# (mismo directorio, fuera del repo, que ya usaba backup.sh/restore.sh para
# los certificados de origen de nginx -- convencion ya establecida en este
# proyecto para secretos que viven en el host, nunca en git). El valor viejo
# expuesto queda invalido desde esta rotacion; sigue visible en el historial
# de git de commits previos (no reescrito, fuera de alcance de este cambio,
# mismo criterio que la password del script E2E).
#
# Usa Start-Process (no operadores de redireccion de PowerShell como *>> o
# 2>&1) porque el logging de Python escribe a stderr, y PowerShell 5.1
# envuelve cada linea de stderr de un ejecutable nativo en un
# NativeCommandError -- con $ErrorActionPreference="Stop" eso mataria el
# proceso en la primera linea de log. Start-Process redirige a nivel de
# sistema operativo, sin pasar por el pipeline de errores de PowerShell.

$tokenFile = "C:\Users\Administrator\sintel_secrets\sms_bridge_token.txt"
if (-not (Test-Path $tokenFile)) {
    Write-Error "Falta $tokenFile -- el puente no arranca sin SMS_BRIDGE_TOKEN real."
    exit 1
}
$env:SMS_BRIDGE_TOKEN = (Get-Content -Raw $tokenFile).Trim()
$env:SMS_MODEM_PORT   = "COM5"
$env:SMS_BRIDGE_HOST  = "0.0.0.0"
$env:SMS_BRIDGE_PORT  = "8765"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$outLog    = Join-Path $scriptDir "bridge.log"
$errLog    = Join-Path $scriptDir "bridge_err.log"

Start-Process -FilePath "python" -ArgumentList "`"$scriptDir\bridge.py`"" `
    -RedirectStandardOutput $outLog -RedirectStandardError $errLog `
    -NoNewWindow -Wait
