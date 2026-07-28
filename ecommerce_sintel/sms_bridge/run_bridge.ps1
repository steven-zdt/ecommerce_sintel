# run_bridge.ps1
# Envoltorio para la Tarea Programada "SintelSmsBridge". Fija las variables
# de entorno del puente (deben coincidir con SMS_BRIDGE_TOKEN en el .env del
# backend) y arranca bridge.py con salida redirigida a un log persistente.
#
# Usa Start-Process (no operadores de redireccion de PowerShell como *>> o
# 2>&1) porque el logging de Python escribe a stderr, y PowerShell 5.1
# envuelve cada linea de stderr de un ejecutable nativo en un
# NativeCommandError -- con $ErrorActionPreference="Stop" eso mataria el
# proceso en la primera linea de log. Start-Process redirige a nivel de
# sistema operativo, sin pasar por el pipeline de errores de PowerShell.

$env:SMS_BRIDGE_TOKEN = "mJvRZ14dJT44y6v2t1fydi69ggU6Du9EKy_mbmiXJH4"
$env:SMS_MODEM_PORT   = "COM5"
$env:SMS_BRIDGE_HOST  = "0.0.0.0"
$env:SMS_BRIDGE_PORT  = "8765"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$outLog    = Join-Path $scriptDir "bridge.log"
$errLog    = Join-Path $scriptDir "bridge_err.log"

Start-Process -FilePath "python" -ArgumentList "`"$scriptDir\bridge.py`"" `
    -RedirectStandardOutput $outLog -RedirectStandardError $errLog `
    -NoNewWindow -Wait
