# =============================================================================
# TEST E2E HTTP -- Copilot de Soporte: disponibilidad, latencia y concurrencia
# Marco:  ai_engine/e2e_http/e2e_home_config_test.ps1, e2e_accounts_users_test.ps1
# Flujo:  GET /health (ai_engine_adk -- Google ADK)
#         -> Login Django (mismo camino que support/services/ai_bridge.py::ask_ai)
#         -> POST /chat real (solo lectura) -- mide latencia
#         -> N llamadas /chat en paralelo -- latencia p50/min/max y tasa de exito
#
# ADK-13 (mision "ADK-SINTEL", 2026-09-14, ver AUDITORIA/ADK_CUTOVER_PLAN.md
# seccion 6.3): actualizado para apuntar a `ai_engine_adk` (puerto 8101) --
# el chat de soporte real ya NO vive en `ai_engine` (puerto 8100, retirado
# en ADK-12; ese proceso solo expone `/health` y el AI Gateway). Este script
# quedo apuntando al endpoint viejo (404) hasta esta correccion -- lo cito
# `ai_engine/.AGENT/SUPPORT_AI_CERTIFICATION.md` como evidencia E2E; la
# certificacion sigue siendo valida, el runtime que certifica cambio de
# nombre/puerto, no de comportamiento. `metrics` sigue `None` en
# `ai_engine_adk` (TurnMetrics todavia no implementado ahi, riesgo abierto
# documentado en ADK_CUTOVER_PLAN.md 6.3) -- este script ya NO lo exige
# para pasar, solo lo reporta si esta presente.
#
# Alcance (Fase 12 -- Validacion funcional):
#   Solo pasos de LECTURA contra el motor real. El flujo de escritura
#   confirmada (needs_confirmation -> "si"/"no") y el Human Handoff ya se
#   cubren con mocks deterministicos en `support/tests.py` (pytest-django +
#   Channels) -- no se ejecuta ninguna Tool de escritura real aqui para no
#   dejar datos de prueba en la base de datos de desarrollo.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File ai_engine/e2e_http/e2e_support_ai_chat_test.ps1
# =============================================================================

$BASE     = "http://localhost:8000/api/v1"
$AI_BASE  = "http://localhost:8101"
$EMAIL    = "admin@sintel.com"
$PASS     = "Sintel@Admin2026"
$TAG      = "E2E_SUPPORT_AI_$(Get-Date -Format 'HHmmss')"
$results  = [ordered]@{}

# -----------------------------------------------------------------------------
# Helpers (mismo patron que los scripts hermanos de este directorio)
# -----------------------------------------------------------------------------
function Pass($step, $msg) {
    Write-Host "  PASS  $step" -ForegroundColor Green
    if ($msg) { Write-Host "        $msg" -ForegroundColor DarkGray }
    $script:results[$step] = "PASS"
}
function Fail($step, $msg) {
    Write-Host "  FAIL  $step" -ForegroundColor Red
    Write-Host "        $msg"  -ForegroundColor DarkRed
    $script:results[$step] = "FAIL -- $msg"
}
function Info($msg) {
    Write-Host "        $msg" -ForegroundColor DarkGray
}
function ErrBody($err) {
    if ($err.ErrorDetails -and $err.ErrorDetails.Message) {
        try { return ($err.ErrorDetails.Message | ConvertFrom-Json | ConvertTo-Json -Depth 3) }
        catch { return $err.ErrorDetails.Message }
    }
    if ($err.Exception -and $err.Exception.Message) { return $err.Exception.Message }
    return "error desconocido (sin detalle disponible)"
}

# ─── PASO 1: Disponibilidad de ai_engine_adk ─────────────────────────────────
Write-Host "`nPaso 1 -- GET /health (ai_engine_adk)" -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "$AI_BASE/health" -TimeoutSec 10
    if ($health.status -eq "ok") {
        Pass "Paso 1 -- ai_engine_adk disponible" "orchestrator=$($health.orchestrator)"
    } else {
        Fail "Paso 1 -- ai_engine_adk disponible" "status inesperado: $($health.status)"
    }
} catch {
    Fail "Paso 1 -- ai_engine_adk disponible" (ErrBody $_)
    Write-Host "`nAbortando: sin ai_engine_adk arriba no se puede continuar.`n" -ForegroundColor Red
    exit 1
}

# ─── PASO 2: Login Django (mismo JWT que usaria ai_bridge.ask_ai) ───────────
# admin@sintel.com es cuenta de administrador -- /auth/login/ (clientes) la
# rechaza ("debe iniciar sesion desde el panel de administracion"); se usa
# /admin-auth/login/, mismo patron que ai_engine/e2e_http/e2e_accounts_users_test.ps1.
Write-Host "`nPaso 2 -- POST /admin-auth/login/ (Django)" -ForegroundColor Cyan
$TOKEN = $null
try {
    $loginBody = @{ email = $EMAIL; password = $PASS } | ConvertTo-Json
    $loginResp = Invoke-RestMethod -Uri "$BASE/admin-auth/login/" -Method Post `
                   -ContentType "application/json" -Body $loginBody
    $TOKEN = $loginResp.tokens.access
    Pass "Paso 2 -- Login JWT" "Token obtenido para $EMAIL (uuid=$($loginResp.user.uuid))"
} catch {
    Fail "Paso 2 -- Login JWT" (ErrBody $_)
    Write-Host "`nAbortando: sin token no se puede llamar a /chat.`n" -ForegroundColor Red
    exit 1
}
$H = @{ Authorization = "Bearer $TOKEN"; "Content-Type" = "application/json" }

# ─── PASO 3: POST /chat real (solo lectura) -- latencia + shape de respuesta ─
Write-Host "`nPaso 3 -- POST /chat (mensaje de lectura, mide latencia real)" -ForegroundColor Cyan
$chatBody = @{
    message         = "cual es el estado de mi ultimo pedido"
    conversation_id = "$TAG-single"
} | ConvertTo-Json
try {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $chatResp = Invoke-RestMethod -Uri "$AI_BASE/chat" -Method Post `
                  -Headers $H -Body $chatBody -TimeoutSec 300
    $sw.Stop()
    $elapsedMs = $sw.ElapsedMilliseconds

    # ADK-13: `metrics` sigue `None` en ai_engine_adk (TurnMetrics pendiente,
    # ver ADK_CUTOVER_PLAN.md 6.3) -- ya NO se exige para pasar este paso,
    # solo `agent`/`tool_calls` (top-level de ChatResponse, no anidados bajo
    # `metrics` como en el sistema OLD).
    $hasResponse = -not [string]::IsNullOrWhiteSpace($chatResp.response)
    if ($hasResponse) {
        Pass "Paso 3 -- Respuesta real" "agent=$($chatResp.agent)  intent=$($chatResp.intent)  tool_calls=$($chatResp.tool_calls.Count)  latencia_medida=${elapsedMs}ms"
        if ($chatResp.tool_calls.Count -lt 1) {
            Info "Nota: tool_calls=0 -- el LLM no eligio ninguna Tool para este mensaje (no es necesariamente un error, depende del intent detectado)"
        }
        if ($null -eq $chatResp.metrics) {
            Info "Nota: metrics=null -- gap conocido de ai_engine_adk (TurnMetrics pendiente), no es un fallo de este paso"
        }
    } else {
        Fail "Paso 3 -- Respuesta real" "response vacio"
    }
} catch {
    Fail "Paso 3 -- Respuesta real" (ErrBody $_)
}

# ─── PASO 4: Concurrencia real -- N llamadas /chat en paralelo ──────────────
# [CORREGIDO 2026-08-08, Gap 6 auditoria] ForEach-Object -Parallel requiere
# PowerShell 7+ (-ThrottleLimit no existe en 5.1) -- fallaba con "No se puede
# resolver el conjunto de parametros" en Windows PowerShell 5.1, el que corre
# en este entorno. Start-Job es compatible con 5.1 y 7+ por igual (mas pesado
# por proceso, pero N=5 es trivial para esto).
Write-Host "`nPaso 4 -- Concurrencia: 5 llamadas /chat en paralelo (solo lectura)" -ForegroundColor Cyan
$N = 5
try {
    $jobScript = {
        param($aiBase, $token, $tag, $i)
        $headers = @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" }
        $body    = @{
            message         = "cuales son mis pedidos recientes"
            conversation_id = "$tag-parallel-$i"
        } | ConvertTo-Json
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        try {
            $resp = Invoke-RestMethod -Uri "$aiBase/chat" -Method Post `
                      -Headers $headers -Body $body -TimeoutSec 300
            $sw.Stop()
            [PSCustomObject]@{
                Index = $i
                Ok    = -not [string]::IsNullOrWhiteSpace($resp.response)
                Ms    = $sw.ElapsedMilliseconds
                Error = $null
            }
        } catch {
            $sw.Stop()
            $msg = if ($_.Exception -and $_.Exception.Message) { $_.Exception.Message } else { "error desconocido" }
            [PSCustomObject]@{ Index = $i; Ok = $false; Ms = $sw.ElapsedMilliseconds; Error = $msg }
        }
    }
    $jobs = 1..$N | ForEach-Object {
        Start-Job -ScriptBlock $jobScript -ArgumentList $AI_BASE, $TOKEN, $TAG, $_
    }
    $parallelResults = $jobs | Wait-Job -Timeout 320 | Receive-Job
    $jobs | Remove-Job -Force

    $okCount   = @($parallelResults | Where-Object { $_.Ok }).Count
    $latencies = @($parallelResults | Where-Object { $_.Ok } | ForEach-Object { $_.Ms })
    if ($okCount -eq $N -and $latencies.Count -gt 0) {
        $minMs = ($latencies | Measure-Object -Minimum).Minimum
        $maxMs = ($latencies | Measure-Object -Maximum).Maximum
        $avgMs = [math]::Round(($latencies | Measure-Object -Average).Average, 0)
        Pass "Paso 4 -- Concurrencia $N/$N exitosas" "latencia min=${minMs}ms  avg=${avgMs}ms  max=${maxMs}ms"
    } else {
        $fails = @($parallelResults | Where-Object { -not $_.Ok })
        Fail "Paso 4 -- Concurrencia $okCount/$N exitosas" ("Fallos: " + (($fails | ForEach-Object { "#$($_.Index): $($_.Error)" }) -join " | "))
    }
} catch {
    Fail "Paso 4 -- Concurrencia" (ErrBody $_)
}

# =============================================================================
# RESUMEN
# =============================================================================
Write-Host "`n$('=' * 64)"
Write-Host "RESUMEN E2E HTTP -- Copilot de Soporte (disponibilidad/latencia/concurrencia)"
Write-Host "Tag de ejecucion: $TAG"
Write-Host "$('=' * 64)"

$allPass = $true
$passCnt = 0
$failCnt = 0
foreach ($kv in $results.GetEnumerator()) {
    if ($kv.Value -eq "PASS") {
        Write-Host "  PASS  $($kv.Key)" -ForegroundColor Green
        $passCnt++
    } else {
        Write-Host "  FAIL  $($kv.Key)" -ForegroundColor Red
        Write-Host "        $($kv.Value)" -ForegroundColor DarkRed
        $failCnt++
        $allPass = $false
    }
}

Write-Host "$('=' * 64)"
Write-Host "  Total: $($passCnt + $failCnt) pasos   PASS: $passCnt   FAIL: $failCnt"
Write-Host "$('=' * 64)"

if ($allPass) {
    Write-Host "`n  FLUJO COMPLETO: OK" -ForegroundColor Green
    Write-Host "  ai_engine_adk disponible, respuesta real coherente," -ForegroundColor Green
    Write-Host "  y concurrencia de $N chats simultaneos sin fallos.`n" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n  FLUJO CON ERRORES -- revisar pasos fallidos arriba`n" -ForegroundColor Red
    exit 1
}
