# ═══════════════════════════════════════════════════════════════════════
# TEST E2E HTTP — Sintel Rental -> Operations Flow
# Usuario: admin@sintel.com
# Flujo:   /alquiler/equipo/259ff0c8... -> wizard -> COD -> /mi-cuenta/operaciones
# ═══════════════════════════════════════════════════════════════════════

$BASE    = "http://localhost:8000/api/v1"
$EQ_UUID = "259ff0c8-1d58-44ff-86b1-01b15641686b"
$EMAIL   = "admin@sintel.com"
$PASS    = "Sintel@Admin2026"
$results = [ordered]@{}

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

# ─── PASO 1: Login ──────────────────────────────────────────────────────────
Write-Host "`nPaso 1 -- POST /admin-auth/login/" -ForegroundColor Cyan
$loginBody = @{ email = $EMAIL; password = $PASS } | ConvertTo-Json
try {
    $loginResp = Invoke-RestMethod -Uri "$BASE/admin-auth/login/" -Method Post `
                   -ContentType "application/json" -Body $loginBody
    $TOKEN = $loginResp.tokens.access
    Pass "Paso 1 -- Login JWT" "Token obtenido para $EMAIL  (user_id=$($loginResp.user.id))"
} catch {
    Fail "Paso 1 -- Login JWT" $_.Exception.Message
    Write-Host "`nAbortando: sin token no se puede continuar." -ForegroundColor Red
    exit 1
}

$headers = @{ Authorization = "Bearer $TOKEN" }

# ─── PASO 2a: GET equipo ────────────────────────────────────────────────────
Write-Host "`nPaso 2a -- GET /renting/equipment/$EQ_UUID/" -ForegroundColor Cyan
try {
    $equip = Invoke-RestMethod -Uri "$BASE/renting/equipment/$EQ_UUID/" -Headers $headers
    Pass "Paso 2a -- GET equipo" "Nombre: $($equip.name)"
} catch {
    Fail "Paso 2a -- GET equipo" $_.Exception.Message
}

# ─── PASO 2b: GET variante ──────────────────────────────────────────────────
Write-Host "`nPaso 2b -- GET /renting/variants/?equipment=$EQ_UUID" -ForegroundColor Cyan
try {
    $variants = Invoke-RestMethod -Uri "$BASE/renting/variants/?equipment=$EQ_UUID" -Headers $headers
    $variant  = if ($variants.results) { $variants.results[0] } else { $variants[0] }
    $VAR_UUID = $variant.uuid
    Pass "Paso 2b -- GET variante" "SKU: $($variant.sku)   UUID: $VAR_UUID   Precio/dia: $($variant.rental_price_per_day)"
} catch {
    Fail "Paso 2b -- GET variante" $_.Exception.Message
    exit 1
}

# ─── PASO 3: check-availability (busca slot libre automaticamente) ──────────
Write-Host "`nPaso 3 -- GET check-availability (buscando primer slot libre...)" -ForegroundColor Cyan
$START = $null
$END   = $null
$offset = 20
$maxOffset = 120
$found = $false
try {
    while (-not $found -and $offset -le $maxOffset) {
        $candidate_start = (Get-Date).AddDays($offset).ToString("yyyy-MM-dd")
        $candidate_end   = (Get-Date).AddDays($offset + 3).ToString("yyyy-MM-dd")
        $avail = Invoke-RestMethod `
            -Uri "$BASE/renting/equipment/$EQ_UUID/check-availability/?variant=$VAR_UUID&start_date=$candidate_start&end_date=$candidate_end&quantity=1" `
            -Headers $headers
        if ($avail.available) {
            $START = $candidate_start
            $END   = $candidate_end
            $found = $true
        } else {
            $offset += 4
        }
    }
    if ($found) {
        Pass "Paso 3 -- Disponibilidad" "available=true  slot: $START -> $END  (offset +$offset dias)"
    } else {
        Fail "Paso 3 -- Disponibilidad" "No se encontro slot libre en los proximos $maxOffset dias"
    }
} catch {
    Fail "Paso 3 -- Disponibilidad" $_.Exception.Message
}
if (-not $found) { exit 1 }

# ─── PASO 4: POST rental-requests/ ────────────────────────────────────────
Write-Host "`nPaso 4 -- POST /renting/rental-requests/ (wizard completo)" -ForegroundColor Cyan
$rrBody = @{
    equipment_variant   = $VAR_UUID
    location_address    = "Calle 85A Sur # 45 - 20"
    location_city       = "Bogota"
    location_department = "Cundinamarca"
    contact_full_name   = "Test HTTP E2E"
    contact_doc_type    = "CC"
    contact_doc_number  = "000000001"
    contact_email       = $EMAIL
    contact_phone       = "3001234567"
    start_date          = $START
    end_date            = $END
    quantity            = 1
    rental_mode         = "days"
    terms_accepted      = $true
} | ConvertTo-Json

try {
    $rr = Invoke-RestMethod -Uri "$BASE/renting/rental-requests/" -Method Post `
            -ContentType "application/json" -Headers $headers -Body $rrBody
    $RR_UUID = $rr.uuid
    Pass "Paso 4 -- Crear RentalRequest" "UUID: $RR_UUID   Status: $($rr.status)   Total: $($rr.grand_total)"
} catch {
    $msg = $_.ErrorDetails.Message
    Fail "Paso 4 -- Crear RentalRequest" $msg
    exit 1
}

# ─── PASO 5: process-payment COD ──────────────────────────────────────────
Write-Host "`nPaso 5 -- POST /renting/rental-requests/$RR_UUID/process-payment/ (COD)" -ForegroundColor Cyan
$payBody = @{ payment_method = "COD" } | ConvertTo-Json
try {
    $payResp = Invoke-RestMethod `
        -Uri "$BASE/renting/rental-requests/$RR_UUID/process-payment/" `
        -Method Post -ContentType "application/json" -Headers $headers -Body $payBody
    Pass "Paso 5 -- Pago COD" "status=$($payResp.status)   rental_uuid=$($payResp.rental_uuid)"
} catch {
    $msg = $_.ErrorDetails.Message
    Fail "Paso 5 -- Pago COD" $msg
    exit 1
}

# ─── PASO 6: GET /operations/my/ ───────────────────────────────────────────
Write-Host "`nPaso 6 -- GET /operations/my/ (pantalla /mi-cuenta/operaciones)" -ForegroundColor Cyan
Start-Sleep -Milliseconds 600
try {
    $opsResp = Invoke-RestMethod -Uri "$BASE/operations/my/" -Headers $headers
    $opsList = @(if ($opsResp.results) { $opsResp.results } else { $opsResp })
    $ticket  = $opsList | Select-Object -First 1
    if ($ticket -and $ticket.ticket_number) {
        Pass "Paso 6 -- Lista operaciones" "$($opsList.Count) operacion(es)   Ticket: $($ticket.ticket_number)   Tipo: $($ticket.operation_type)   Status: $($ticket.status)"
    } else {
        Fail "Paso 6 -- Lista operaciones" "El ticket NO aparece en la lista"
    }
} catch {
    Fail "Paso 6 -- Lista operaciones" $_.Exception.Message
}

# ─── PASO 7: GET detalle del ticket ────────────────────────────────────────
if ($ticket -and $ticket.uuid) {
    Write-Host "`nPaso 7 -- GET /operations/my/$($ticket.uuid)/ (detalle)" -ForegroundColor Cyan
    try {
        $detail = Invoke-RestMethod -Uri "$BASE/operations/my/$($ticket.uuid)/" -Headers $headers
        Pass "Paso 7 -- Detalle ticket" "Ticket: $($detail.ticket_number)   Eventos: $($detail.tracking_events.Count)   Docs: $($detail.documents.Count)"
        $detail.tracking_events | ForEach-Object {
            Write-Host "          [$($_.milestone)] $($_.description)" -ForegroundColor DarkGray
        }
    } catch {
        Fail "Paso 7 -- Detalle ticket" $_.Exception.Message
    }

    # ─── PASO 8: GET timeline ───────────────────────────────────────────────
    Write-Host "`nPaso 8 -- GET /operations/my/$($ticket.uuid)/timeline/" -ForegroundColor Cyan
    try {
        $timeline = Invoke-RestMethod -Uri "$BASE/operations/my/$($ticket.uuid)/timeline/" -Headers $headers
        $tl = @(if ($timeline.results) { $timeline.results } else { $timeline })
        Pass "Paso 8 -- Timeline cliente" "$($tl.Count) evento(s) visibles al cliente"
        $tl | ForEach-Object {
            Write-Host "          [$($_.milestone)] $($_.description)" -ForegroundColor DarkGray
        }
    } catch {
        Fail "Paso 8 -- Timeline cliente" $_.Exception.Message
    }
}

# ─── RESUMEN ──────────────────────────────────────────────────────────────
Write-Host "`n$('─' * 64)"
Write-Host "RESUMEN E2E HTTP -- $EMAIL"
Write-Host "$('─' * 64)"
$allPass = $true
foreach ($kv in $results.GetEnumerator()) {
    if ($kv.Value -eq "PASS") {
        Write-Host "  PASS  $($kv.Key)" -ForegroundColor Green
    } else {
        Write-Host "  FAIL  $($kv.Key)" -ForegroundColor Red
        Write-Host "        $($kv.Value)" -ForegroundColor DarkRed
        $allPass = $false
    }
}
Write-Host "$('─' * 64)"
if ($allPass) {
    Write-Host "`n  FLUJO COMPLETO: OK" -ForegroundColor Green
    Write-Host "  /alquiler/equipo/... -> wizard -> COD -> /mi-cuenta/operaciones`n" -ForegroundColor Green
} else {
    Write-Host "`n  FLUJO CON ERRORES -- revisar pasos fallidos`n" -ForegroundColor Red
}
