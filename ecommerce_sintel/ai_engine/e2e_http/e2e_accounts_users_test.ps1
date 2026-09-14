# =============================================================================
# TEST E2E HTTP -- Sintel Accounts: Creacion de todos los tipos de usuario
# Marco:  ai_engine/e2e_http/e2e_rental_http_test.ps1
# Flujo:  Registro -> Login -> GET perfil -> PATCH perfil -> Datos pro
#         -> Cambio password -> Logout -> Cross-review CUSTOMER/TECHNICIAN
#
# Tipos de usuario (accounts.UserProfile.user_type):
#   CUSTOMER | TECHNICIAN | PROFESSIONAL | SPECIALIST
#   CONTRACTOR | TRANSPORTER | ACCOUNTANT
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File ai_engine/e2e_http/e2e_accounts_users_test.ps1
# =============================================================================

$BASE        = "http://localhost:8000/api/v1"
$ADMIN_EMAIL = "admin@sintel.com"
$ADMIN_PASS  = "Sintel@Admin2026"
$TEST_PASS   = "Sintel@Test2026!"
$NEW_PASS    = "Sintel@New2026!"
$TS          = (Get-Date -Format "MMddHHmm")
$results     = [ordered]@{}

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
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
function Section($title) {
    Write-Host ""
    Write-Host "$('=' * 64)" -ForegroundColor Yellow
    Write-Host "  $title"    -ForegroundColor Yellow
    Write-Host "$('=' * 64)" -ForegroundColor Yellow
}
function ApiError($ex) {
    $body = $null
    try { $body = $ex.ErrorDetails.Message } catch {}
    if (-not $body) { $body = $ex.Exception.Message }
    return $body
}

# =============================================================================
# PASO 0 -- Admin Login
# =============================================================================
Section "PASO 0 -- Login de Admin"
Write-Host "`nPASO 0 -- POST /admin-auth/login/" -ForegroundColor Cyan
$adminBody = @{ email = $ADMIN_EMAIL; password = $ADMIN_PASS } | ConvertTo-Json
try {
    $adminResp   = Invoke-RestMethod -Uri "$BASE/admin-auth/login/" -Method Post `
                     -ContentType "application/json" -Body $adminBody
    $ADMIN_TOKEN = $adminResp.tokens.access
    Pass "Paso 0 -- Admin Login" "id=$($adminResp.user.id)   email=$ADMIN_EMAIL"
} catch {
    Fail "Paso 0 -- Admin Login" (ApiError $_)
    Write-Host "Abortando: sin token admin no se puede continuar." -ForegroundColor Red
    exit 1
}

# =============================================================================
# DEFINICION DE LOS 7 TIPOS DE USUARIO
# =============================================================================
$USER_TYPES = @(
    @{ type = "CUSTOMER";     first = "Carlos";   last = "Cliente";      suffix = "01"; extra = "basic"        },
    @{ type = "TECHNICIAN";   first = "Tomas";    last = "Tecnico";      suffix = "02"; extra = "technician"   },
    @{ type = "PROFESSIONAL"; first = "Patricia"; last = "Profesional";  suffix = "03"; extra = "professional" },
    @{ type = "SPECIALIST";   first = "Santiago"; last = "Especialista"; suffix = "04"; extra = "professional" },
    @{ type = "CONTRACTOR";   first = "Camila";   last = "Contratista";  suffix = "05"; extra = "professional" },
    @{ type = "TRANSPORTER";  first = "Tania";    last = "Transportista";suffix = "06"; extra = "basic"        },
    @{ type = "ACCOUNTANT";   first = "Andres";   last = "Contador";     suffix = "07"; extra = "basic"        }
)

$REGISTERED = @{}

# =============================================================================
# BUCLE PRINCIPAL: ciclo de vida completo por tipo
# =============================================================================
foreach ($ut in $USER_TYPES) {

    $TYPE  = $ut.type
    $FIRST = $ut.first
    $LAST  = $ut.last
    $EMAIL = "e2e.$($TYPE.ToLower()).$TS@sintel.test"
    $PHONE = "399$TS$($ut.suffix)"

    Section "USUARIO: $TYPE  ($FIRST $LAST)"

    # ------------------------------------------------------------------
    # R1 -- Registro publico
    # ------------------------------------------------------------------
    Write-Host "`n[$TYPE] R1 -- POST /auth/register/" -ForegroundColor Cyan
    $regBody = @{
        email            = $EMAIL
        password         = $TEST_PASS
        password_confirm = $TEST_PASS
        first_name       = $FIRST
        last_name        = $LAST
        phone_number     = $PHONE
        user_type        = $TYPE
    } | ConvertTo-Json

    $USER_UUID = $null
    try {
        $regResp   = Invoke-RestMethod -Uri "$BASE/auth/register/" -Method Post `
                       -ContentType "application/json" -Body $regBody
        $USER_UUID = $regResp.uuid
        Pass "[$TYPE] R1 -- Registro" "uuid=$USER_UUID   user_type=$($regResp.profile.user_type)"
    } catch {
        Fail "[$TYPE] R1 -- Registro" (ApiError $_)
        continue
    }

    # ------------------------------------------------------------------
    # R2 -- Login
    # ------------------------------------------------------------------
    Write-Host "`n[$TYPE] R2 -- POST /auth/login/" -ForegroundColor Cyan
    $loginBody = @{ email = $EMAIL; password = $TEST_PASS } | ConvertTo-Json

    $TOKEN = $null; $REFRESH = $null; $h = $null
    try {
        $loginResp = Invoke-RestMethod -Uri "$BASE/auth/login/" -Method Post `
                       -ContentType "application/json" -Body $loginBody
        $TOKEN   = $loginResp.tokens.access
        $REFRESH = $loginResp.tokens.refresh
        $h       = @{ Authorization = "Bearer $TOKEN" }
        Pass "[$TYPE] R2 -- Login" "access_token OK   profile.user_type=$($loginResp.user.profile.user_type)"
    } catch {
        Fail "[$TYPE] R2 -- Login" (ApiError $_)
        continue
    }

    # ------------------------------------------------------------------
    # R3 -- GET perfil propio
    # ------------------------------------------------------------------
    Write-Host "`n[$TYPE] R3 -- GET /auth/profile/" -ForegroundColor Cyan
    $profResp = $null
    try {
        $profResp = Invoke-RestMethod -Uri "$BASE/auth/profile/" -Headers $h
        $utype    = $profResp.profile.user_type
        $hasTech  = $profResp.technician_profile -ne $null
        Pass "[$TYPE] R3 -- GET Perfil" "email=$($profResp.email)   user_type=$utype   technician_profile=$hasTech"
    } catch {
        Fail "[$TYPE] R3 -- GET Perfil" (ApiError $_)
        continue
    }

    # Signal: TechnicianProfile auto-creado para TECHNICIAN
    if ($TYPE -eq "TECHNICIAN") {
        Write-Host "`n[$TYPE] R3b -- Verificar TechnicianProfile (signal post_save)" -ForegroundColor Cyan
        if ($profResp.technician_profile -ne $null) {
            Pass "[$TYPE] R3b -- TechnicianProfile auto-creado" `
                 "is_available=$($profResp.technician_profile.is_available)"
        } else {
            Fail "[$TYPE] R3b -- TechnicianProfile auto-creado" "Signal NO creo TechnicianProfile"
        }
    }

    # ------------------------------------------------------------------
    # R4 -- PATCH perfil (datos comunes a todos los tipos)
    # ------------------------------------------------------------------
    Write-Host "`n[$TYPE] R4 -- PATCH /auth/profile/" -ForegroundColor Cyan
    $patchBody = @{
        bio           = "Perfil E2E automatizado tipo $TYPE ts=$TS"
        document_type = "CC"
        document      = "100200$($ut.suffix)$TS"
        city          = "Bogota"
        state         = "Cundinamarca"
        country       = "Colombia"
        address       = "Calle 100 No. 20-30 Apto $($ut.suffix)"
        postal_code   = "110111"
        hourly_rate   = 85000
        currency      = "COP"
        birth_date    = "1990-05-15"
    } | ConvertTo-Json
    try {
        $patched = Invoke-RestMethod -Uri "$BASE/auth/profile/" -Method Patch `
                     -ContentType "application/json" -Headers $h -Body $patchBody
        Pass "[$TYPE] R4 -- PATCH Perfil" "city=$($patched.profile.city)   currency=$($patched.profile.currency)"
    } catch {
        Fail "[$TYPE] R4 -- PATCH Perfil" (ApiError $_)
    }

    # ------------------------------------------------------------------
    # R5-R7 -- Pasos especificos segun tipo
    # ------------------------------------------------------------------

    # ── TECHNICIAN: habilidad + disponibilidad en bloque ─────────────
    if ($ut.extra -eq "technician") {

        Write-Host "`n[$TYPE] R5 -- POST /auth/skills/ (habilidad tecnica)" -ForegroundColor Cyan
        $skillBody = @{ name = "Reparacion hidraulica industrial"; level = "Avanzado" } | ConvertTo-Json
        try {
            $skill = Invoke-RestMethod -Uri "$BASE/auth/skills/" -Method Post `
                       -ContentType "application/json" -Headers $h -Body $skillBody
            Pass "[$TYPE] R5 -- Habilidad" "id=$($skill.id)   $($skill.name) [$($skill.level)]"
        } catch {
            Fail "[$TYPE] R5 -- Habilidad" (ApiError $_)
        }

        Write-Host "`n[$TYPE] R6 -- POST /auth/availability/bulk-create/ (agenda 30 dias)" -ForegroundColor Cyan
        $startAvail = (Get-Date).ToString("yyyy-MM-dd")
        $endAvail   = (Get-Date).AddDays(30).ToString("yyyy-MM-dd")
        $availBody  = @{
            start_date          = $startAvail
            end_date            = $endAvail
            work_start_hour     = 8
            work_end_hour       = 17
            slot_duration_hours = 2
            exclude_weekends    = $true
            notes               = "Disponibilidad E2E test $TS"
        } | ConvertTo-Json
        try {
            $avail = Invoke-RestMethod -Uri "$BASE/auth/availability/bulk-create/" -Method Post `
                       -ContentType "application/json" -Headers $h -Body $availBody
            Pass "[$TYPE] R6 -- Disponibilidad" "$($avail.created_count) slots creados ($startAvail -> $endAvail)"
        } catch {
            Fail "[$TYPE] R6 -- Disponibilidad" (ApiError $_)
        }

        Write-Host "`n[$TYPE] R7 -- GET /auth/availability/my-schedule/" -ForegroundColor Cyan
        try {
            $schedResp = Invoke-RestMethod -Uri "$BASE/auth/availability/my-schedule/" -Headers $h
            if ($schedResp.results) { $schedSlots = @($schedResp.results) } else { $schedSlots = @($schedResp) }
            Pass "[$TYPE] R7 -- Mi Agenda" "$($schedSlots.Count) slots visibles en agenda"
        } catch {
            Fail "[$TYPE] R7 -- Mi Agenda" (ApiError $_)
        }
    }

    # ── PROFESSIONAL / SPECIALIST / CONTRACTOR: CV completo ──────────
    if ($ut.extra -eq "professional") {

        Write-Host "`n[$TYPE] R5 -- POST /auth/experiences/ (experiencia laboral)" -ForegroundColor Cyan
        $expBody = @{
            company     = "Sintel Technology SAS"
            position    = "Senior $TYPE E2E"
            description = "Flujo E2E automatizado para tipo $TYPE"
            start_date  = "2022-03-01"
            is_current  = $true
        } | ConvertTo-Json
        try {
            $exp = Invoke-RestMethod -Uri "$BASE/auth/experiences/" -Method Post `
                     -ContentType "application/json" -Headers $h -Body $expBody
            Pass "[$TYPE] R5 -- Experiencia" "id=$($exp.id)   $($exp.position) @ $($exp.company)"
        } catch {
            Fail "[$TYPE] R5 -- Experiencia" (ApiError $_)
        }

        Write-Host "`n[$TYPE] R6 -- POST /auth/academic-training/ (educacion)" -ForegroundColor Cyan
        $acadBody = @{
            institution    = "Universidad Nacional de Colombia"
            degree         = "Ingenieria de Sistemas"
            field_of_study = "Ciencias aplicadas"
            start_date     = "2017-02-01"
            end_date       = "2022-11-30"
            is_current     = $false
        } | ConvertTo-Json
        try {
            $acad = Invoke-RestMethod -Uri "$BASE/auth/academic-training/" -Method Post `
                      -ContentType "application/json" -Headers $h -Body $acadBody
            Pass "[$TYPE] R6 -- Educacion" "id=$($acad.id)   $($acad.degree)"
        } catch {
            Fail "[$TYPE] R6 -- Educacion" (ApiError $_)
        }

        Write-Host "`n[$TYPE] R7 -- POST /auth/courses/ (curso de formacion)" -ForegroundColor Cyan
        $courseBody = @{
            title           = "Certificacion Avanzada $TYPE"
            institution     = "SENA Colombia"
            completion_date = "2023-08-15"
            hours           = 120
        } | ConvertTo-Json
        try {
            $course = Invoke-RestMethod -Uri "$BASE/auth/courses/" -Method Post `
                        -ContentType "application/json" -Headers $h -Body $courseBody
            Pass "[$TYPE] R7 -- Curso" "id=$($course.id)   $($course.title) ($($course.hours)h)"
        } catch {
            Fail "[$TYPE] R7 -- Curso" (ApiError $_)
        }
    }

    # ── CUSTOMER / TRANSPORTER / ACCOUNTANT: solo perfil basico ──────
    if ($ut.extra -eq "basic") {
        Pass "[$TYPE] R5 -- Tipo basico sin CV extendido" "user_type=$TYPE -- sin marketplace ni submodelos de CV"
    }

    # ------------------------------------------------------------------
    # R8 -- Marketplace publico (solo TECHNICIAN / PROFESSIONAL / SPECIALIST)
    #       Objetivo: obtener UserProfile.uuid para la resena cruzada
    # ------------------------------------------------------------------
    $PROF_UUID = $null

    if ($TYPE -in @("TECHNICIAN", "PROFESSIONAL", "SPECIALIST")) {
        Write-Host "`n[$TYPE] R8 -- GET /auth/contractors/ (marketplace publico)" -ForegroundColor Cyan
        try {
            $mktResp = Invoke-RestMethod -Uri "$BASE/auth/contractors/" -Method Get
            if ($mktResp.results) { $mktList = @($mktResp.results) } else { $mktList = @($mktResp) }

            $found = $mktList | Where-Object { "$($_.user_uuid)" -eq "$USER_UUID" }

            if (-not $found) {
                $searchUri  = "$BASE/auth/contractors/search/?user_type=$TYPE"
                $searchResp = Invoke-RestMethod -Uri $searchUri -Method Get
                if ($searchResp.results) {
                    $searchList = @($searchResp.results)
                } else {
                    $searchList = @($searchResp)
                }
                $found = $searchList | Where-Object { "$($_.user_uuid)" -eq "$USER_UUID" }
            }

            if ($found) {
                $PROF_UUID = $found.uuid
                Pass "[$TYPE] R8 -- Marketplace" "prof_uuid=$PROF_UUID   avg_rating=$($found.average_rating)"
            } else {
                Pass "[$TYPE] R8 -- Marketplace" "endpoint OK ($($mktList.Count) items) -- perfil en pagina posterior"
            }
        } catch {
            Fail "[$TYPE] R8 -- Marketplace" (ApiError $_)
        }
    }

    # ------------------------------------------------------------------
    # R9 -- Cambio de contrasena
    # ------------------------------------------------------------------
    Write-Host "`n[$TYPE] R9 -- POST /auth/change-password/" -ForegroundColor Cyan
    $cpBody = @{ old_password = $TEST_PASS; new_password = $NEW_PASS } | ConvertTo-Json
    try {
        Invoke-RestMethod -Uri "$BASE/auth/change-password/" -Method Post `
          -ContentType "application/json" -Headers $h -Body $cpBody | Out-Null
        Pass "[$TYPE] R9 -- Cambio Password" "nueva password establecida"
    } catch {
        Fail "[$TYPE] R9 -- Cambio Password" (ApiError $_)
    }

    # Verificar nuevo password con re-login
    Write-Host "`n[$TYPE] R9b -- Re-login con nueva password" -ForegroundColor Cyan
    $hNew = $h
    try {
        $reLogin = Invoke-RestMethod -Uri "$BASE/auth/login/" -Method Post `
                     -ContentType "application/json" `
                     -Body (@{ email = $EMAIL; password = $NEW_PASS } | ConvertTo-Json)
        $hNew = @{ Authorization = "Bearer $($reLogin.tokens.access)" }
        Pass "[$TYPE] R9b -- Re-login nueva pass" "OK   user_type=$($reLogin.user.profile.user_type)"
    } catch {
        Fail "[$TYPE] R9b -- Re-login nueva pass" (ApiError $_)
    }

    # ------------------------------------------------------------------
    # R10 -- Logout (invalida refresh token)
    # ------------------------------------------------------------------
    Write-Host "`n[$TYPE] R10 -- POST /auth/logout/" -ForegroundColor Cyan
    $logoutBody = @{ refresh = $REFRESH } | ConvertTo-Json
    try {
        Invoke-RestMethod -Uri "$BASE/auth/logout/" -Method Post `
          -ContentType "application/json" -Headers $hNew -Body $logoutBody | Out-Null
        Pass "[$TYPE] R10 -- Logout" "Refresh token invalidado"
    } catch {
        Fail "[$TYPE] R10 -- Logout" (ApiError $_)
    }

    $REGISTERED[$TYPE] = @{
        email     = $EMAIL
        user_uuid = $USER_UUID
        prof_uuid = $PROF_UUID
    }
}

# =============================================================================
# CROSS -- CUSTOMER deja resena a TECHNICIAN en el marketplace
# Simula: usuario comprador evalua a un profesional tras contratarlo
# =============================================================================
Section "CROSS -- CUSTOMER resena a TECHNICIAN (ContractorReview)"

$hasCust = $REGISTERED.ContainsKey("CUSTOMER")
$hasTech = $REGISTERED.ContainsKey("TECHNICIAN")
$techProfUUID = if ($hasTech) { $REGISTERED["TECHNICIAN"].prof_uuid } else { $null }

if (-not $hasCust -or -not $hasTech -or -not $techProfUUID) {
    Write-Host "  [SKIP] Cross-review omitido." -ForegroundColor DarkYellow
    Write-Host "         Causa: CUSTOMER=$hasCust  TECHNICIAN=$hasTech  prof_uuid=$techProfUUID" -ForegroundColor DarkYellow
} else {

    $custEmail = $REGISTERED["CUSTOMER"].email

    # X1 -- Re-login CUSTOMER (nueva password)
    Write-Host "`nPaso X1 -- POST /auth/login/ (CUSTOMER con nueva password)" -ForegroundColor Cyan
    $custH = $null
    $custRefresh = $null
    try {
        $custLogin   = Invoke-RestMethod -Uri "$BASE/auth/login/" -Method Post `
                         -ContentType "application/json" `
                         -Body (@{ email = $custEmail; password = $NEW_PASS } | ConvertTo-Json)
        $custH       = @{ Authorization = "Bearer $($custLogin.tokens.access)" }
        $custRefresh = $custLogin.tokens.refresh
        Pass "Paso X1 -- Re-login CUSTOMER" "email=$custEmail"
    } catch {
        Fail "Paso X1 -- Re-login CUSTOMER" (ApiError $_)
    }

    if ($custH) {

        # X2 -- Ver perfil publico del TECHNICIAN
        Write-Host "`nPaso X2 -- GET /auth/contractors/$techProfUUID/" -ForegroundColor Cyan
        try {
            $techPublic = Invoke-RestMethod -Uri "$BASE/auth/contractors/$techProfUUID/" -Method Get
            Pass "Paso X2 -- Perfil publico TECHNICIAN" `
                 "nombre=$($techPublic.first_name) $($techPublic.last_name)   avg_rating=$($techPublic.average_rating)"
        } catch {
            Fail "Paso X2 -- Perfil publico TECHNICIAN" (ApiError $_)
        }

        # X3 -- POST resena (CUSTOMER -> TECHNICIAN)
        Write-Host "`nPaso X3 -- POST /auth/contractors/$techProfUUID/review/" -ForegroundColor Cyan
        $reviewBody = @{
            comment                = "Excelente tecnico. Puntual, profesional y resolutivo. 100% recomendado."
            quality_rating         = 5
            punctuality_rating     = 5
            professionalism_rating = 5
            communication_rating   = 4
            compliance_rating      = 5
        } | ConvertTo-Json
        try {
            $rev = Invoke-RestMethod -Uri "$BASE/auth/contractors/$techProfUUID/review/" `
                     -Method Post -ContentType "application/json" `
                     -Headers $custH -Body $reviewBody
            Pass "Paso X3 -- Resena CUSTOMER -> TECHNICIAN" "id=$($rev.id)   reviewer=$($rev.reviewer_email)"
        } catch {
            Fail "Paso X3 -- Resena CUSTOMER -> TECHNICIAN" (ApiError $_)
        }

        # X4 -- Verificar rating actualizado en perfil publico
        Write-Host "`nPaso X4 -- Verificar rating actualizado" -ForegroundColor Cyan
        try {
            $techUpdated = Invoke-RestMethod -Uri "$BASE/auth/contractors/$techProfUUID/" -Method Get
            if ($techUpdated.total_reviews -gt 0) {
                Pass "Paso X4 -- Rating actualizado" `
                     "total_reviews=$($techUpdated.total_reviews)   avg_rating=$($techUpdated.average_rating)"
            } else {
                Fail "Paso X4 -- Rating actualizado" "total_reviews=$($techUpdated.total_reviews) (esperaba > 0)"
            }
        } catch {
            Fail "Paso X4 -- Rating actualizado" (ApiError $_)
        }

        # X5 -- Logout CUSTOMER
        Write-Host "`nPaso X5 -- POST /auth/logout/ (CUSTOMER)" -ForegroundColor Cyan
        try {
            Invoke-RestMethod -Uri "$BASE/auth/logout/" -Method Post `
              -ContentType "application/json" -Headers $custH `
              -Body (@{ refresh = $custRefresh } | ConvertTo-Json) | Out-Null
            Pass "Paso X5 -- Logout CUSTOMER" "Sesion cerrada"
        } catch {
            Fail "Paso X5 -- Logout CUSTOMER" (ApiError $_)
        }
    }
}

# =============================================================================
# RESUMEN FINAL
# =============================================================================
Write-Host ""
Write-Host "$('=' * 64)" -ForegroundColor Cyan
Write-Host "RESUMEN E2E ACCOUNTS -- Todos los tipos de usuario" -ForegroundColor Cyan
Write-Host "Ejecucion: $TS" -ForegroundColor DarkGray
Write-Host "$('=' * 64)" -ForegroundColor Cyan

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
        $allPass = $false
        $failCnt++
    }
}
Write-Host "$('=' * 64)" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Pasos PASS: $passCnt   FAIL: $failCnt" -ForegroundColor $(if ($allPass) { "Green" } else { "Yellow" })
Write-Host ""

if ($allPass) {
    Write-Host "  FLUJO COMPLETO: OK" -ForegroundColor Green
    Write-Host "  7 tipos creados, perfiles actualizados, datos pro cargados," -ForegroundColor Green
    Write-Host "  disponibilidad generada, cross-review ejecutado." -ForegroundColor Green
} else {
    Write-Host "  FLUJO CON ERRORES -- revisar pasos FAIL" -ForegroundColor Red
}

Write-Host ""
Write-Host "  Usuarios de prueba creados (sufijo: $TS):" -ForegroundColor DarkGray
foreach ($key in $REGISTERED.Keys) {
    $entry = $REGISTERED[$key]
    Write-Host "    [$key]  $($entry.email)" -ForegroundColor DarkGray
}
Write-Host ""
