# Sintel AI Engine — Guia de Operacion

Motor de inteligencia arquitectonica: LangChain + LangGraph + Knowledge Graph + Planner de 17 pasos.
Entiende el proyecto completo y genera codigo validado para Django (backend) y Vue.js (frontend).

---

## Arquitectura del motor

```
Usuario
  ↓
[Planner — 17 pasos]
  1. Detectar intencion (crear/actualizar/fix/query)
  2. Detectar apps afectadas (domain keywords + AST estructural)
  3. Consultar APP_MEMORY + restricciones por app
  4. Consultar GLOBAL_MEMORY (14 reglas criticas)
  5. Consultar Knowledge Graph (750 nodos, 1147 aristas)
  6. Consultar PROJECT_MAP (103 modelos, 76 ViewSets, 68 endpoints)
  7. Consultar AI_MANIFEST por app (arquitectura + contratos)
  8. Consultar indices especializados (ModelIndex, ViewSetIndex, etc.)
  9. Consultar frontend consumers (que Vue consume esos endpoints)
  10-12. Analisis de impacto + blast radius + tests afectados
  13. Generar plan de cambios ordenado
  ↓
[LangGraph: analyze_impact → generate_code → validate_code → emit|escalate]
  ↓
[Guardrails — CRITICAL + WARNING]
  ↓
Codigo listo
```

### Servicios externos requeridos

| Container | Puerto | Rol |
|-----------|--------|-----|
| `ecommerce_sintel_ollama` | 11434 | LLM `llama3.1:8b` + embeddings `bge-m3` |
| `ecommerce_sintel_chromadb` | 8200 | Vector store (ChromaDB) |
| `ecommerce_sintel_ai` | 8100 | FastAPI — este motor |

---

## Arranque

```powershell
cd C:\Users\Administrator\Documents\ecommerce_sintel_rest\ecommerce_sintel

# Levantar los 3 servicios de IA
docker compose up -d sintel_ollama sintel_chromadb sintel_ai

# Verificar contenedores
docker ps --filter "name=ecommerce_sintel_ollama" `
         --filter "name=ecommerce_sintel_chromadb" `
         --filter "name=ecommerce_sintel_ai" `
         --format "table {{.Names}}`t{{.Status}}"

# Confirmar motor listo
Invoke-RestMethod -Uri "http://localhost:8100/health"
# { status: "ok", chunks_indexed: 400+, vectorstore: "chromadb" }
```

---

## Generar codigo

### Backend (Django)

```powershell
$body = @{
    task = "Crear un Command en orders que cancele una orden, revierte el stock y notifica al cliente en on_commit"
    apps = @("orders", "inventory", "notifications")   # opcional — se auto-detecta
    task_type = "backend"                              # opcional — se auto-detecta
} | ConvertTo-Json

$body | Out-File "C:\tmp\req.json" -Encoding utf8NoBOM
curl.exe -s -X POST "http://localhost:8100/generate" `
  -H "Content-Type: application/json" `
  -d "@C:\tmp\req.json" -o "C:\tmp\result.json"

(Get-Content "C:\tmp\result.json" -Encoding utf8 | ConvertFrom-Json).final_code
```

### Frontend (Vue.js)

```powershell
$body = @{
    task = "Crear InventoryList.vue para el panel admin con filtro por nombre y boton de ajuste usando SintelOffcanvas"
    apps = @("shop", "inventory")
    task_type = "frontend"
} | ConvertTo-Json

$body | Out-File "C:\tmp\req.json" -Encoding utf8NoBOM
curl.exe -s -X POST "http://localhost:8100/generate" `
  -H "Content-Type: application/json" `
  -d "@C:\tmp\req.json" -o "C:\tmp\result.json"

(Get-Content "C:\tmp\result.json" -Encoding utf8 | ConvertFrom-Json).final_code
```

### Respuesta de /generate

| Campo | Significado |
|-------|-------------|
| `final_code` | Codigo listo para copiar al proyecto |
| `task_type` | `"frontend"` o `"backend"` (detectado o recibido) |
| `apps_detected` | Apps que el motor identifico como afectadas |
| `impact_context` | Contexto de 4-6K chars inyectado al LLM (PROJECT_MAP + Memory + Manifests) |
| `plan_steps` | Lista ordenada de cambios que el planner identifico |
| `plan_warnings` | Advertencias de consistencia del plan |
| `escalated: false` | Generacion exitosa |
| `escalated: true` | El LLM no pudo cumplir las reglas en 3 intentos — reformular la tarea |
| `iterations` | Cuantos intentos tomo (1 = primer intento exitoso) |
| `validation_report.passed: true` | Sin violaciones criticas |
| `validation_report.warnings` | Advertencias no bloqueantes — revisar |

---

## Endpoints de inteligencia arquitectonica

### Analizar impacto sin generar codigo

```powershell
$body = @{
    task = "Agrega descuentos dinamicos al checkout segun cupon y categoria"
    apps = $null   # auto-detectado
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8100/impact" -Method Post `
  -ContentType "application/json" -Body $body
```

Devuelve: apps afectadas, modelos, serializers, viewsets, endpoints, archivos frontend, stores.

### Ver plan de cambios antes de generar

```powershell
$body = @{
    task = "Agrega descuentos dinamicos al checkout segun cupon y categoria"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8100/plan" -Method Post `
  -ContentType "application/json" -Body $body
```

Devuelve: `intent`, `apps`, `plan_steps` (lista ordenada de cambios), `warnings`, `enriched_context`.
Util para revisar el plan ANTES de pedir la generacion.

### Que se rompe si cambio X

```powershell
$body = @{ entity = "shop.Product" } | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8100/breakage" -Method Post `
  -ContentType "application/json" -Body $body
```

Responde que modelos, serializers, viewsets, frontend y stores se ven afectados si se modifica `shop.Product`.

### Buscar en indices especializados

```powershell
$body = @{ query = "como funciona el soft-delete en orders" } | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8100/search" -Method Post `
  -ContentType "application/json" -Body $body
```

El motor enruta automaticamente al indice correcto (`BusinessRulesIndex`, `ModelIndex`, etc.).

Para forzar un indice especifico:
```powershell
$body = @{ query = "ProductSerializer campos"; index = "SerializerIndex" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8100/search" -Method Post `
  -ContentType "application/json" -Body $body
```

### Ver indices disponibles

```powershell
Invoke-RestMethod -Uri "http://localhost:8100/indices"
# ModelIndex: 103, SerializerIndex: 161, ViewSetIndex: 76, FrontendIndex: 148,
# CommandIndex: 43, SelectorIndex: 43, ServiceIndex: 11,
# DependencyIndex: 300+, BusinessRulesIndex: 19
```

### Obtener AI_MANIFEST de una app

```powershell
Invoke-RestMethod -Uri "http://localhost:8100/manifest/shop"
```

Devuelve el contrato completo: modelos, viewsets, endpoints, consumers frontend, dependencias entre apps, blast radius, constraints, reglas de negocio, known_issues.

### Consultar Knowledge Graph

```powershell
# Vecindario de una entidad (profundidad 2 por defecto)
Invoke-RestMethod -Uri "http://localhost:8100/graph/node/Product"

# Cadena de impacto transitivo
Invoke-RestMethod -Uri "http://localhost:8100/graph/impact/Product"
```

### Consultar memoria del proyecto

```powershell
# Memoria global (reglas criticas, decisiones arquitectonicas)
Invoke-RestMethod -Uri "http://localhost:8100/memory"

# Memoria especifica de una app
Invoke-RestMethod -Uri "http://localhost:8100/memory?app=shop"
Invoke-RestMethod -Uri "http://localhost:8100/memory?app=payment"
```

---

## Validar codigo existente

### Archivo Python

```powershell
$code = Get-Content "ruta\al\archivo.py" -Raw -Encoding utf8
$body = @{ code = $code; app_context = "orders" } | ConvertTo-Json -Depth 5
$body | Out-File "C:\tmp\req.json" -Encoding utf8NoBOM

curl.exe -s -X POST "http://localhost:8100/validate" `
  -H "Content-Type: application/json" `
  -d "@C:\tmp\req.json" | ConvertFrom-Json
```

### Archivo Vue

```powershell
$code = Get-Content "ruta\al\Componente.vue" -Raw -Encoding utf8
$body = @{ code = $code; app_context = "frontend_shop" } | ConvertTo-Json -Depth 5
$body | Out-File "C:\tmp\req.json" -Encoding utf8NoBOM

curl.exe -s -X POST "http://localhost:8100/validate" `
  -H "Content-Type: application/json" `
  -d "@C:\tmp\req.json" | ConvertFrom-Json
```

---

## Mantener la base de conocimiento actualizada

### Actualizacion incremental (despues de cada cambio en el proyecto)

El motor detecta automaticamente que archivos cambiaron mediante hash MD5:

```powershell
# Detectar que cambio desde el ultimo refresh
Invoke-RestMethod -Uri "http://localhost:8100/refresh/detect"
# { changed_apps: ["shop", "orders"], frontend_changed: false }

# Actualizar solo las apps que cambiaron
Invoke-RestMethod -Uri "http://localhost:8100/refresh" -Method Post `
  -ContentType "application/json" `
  -Body '{ "apps": null, "frontend": false, "force_full": false }'
# El motor detecta automaticamente las apps cambiadas y re-audita solo esas
```

Para forzar actualizacion de apps especificas:

```powershell
$body = @{ apps = @("shop", "orders"); frontend = $false } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8100/refresh" -Method Post `
  -ContentType "application/json" -Body $body
```

Para rebuild completo de todo el conocimiento:

```powershell
# Opcion 1: desde el host (mas rapido)
cd C:\Users\Administrator\Documents\ecommerce_sintel_rest
python ai_engine\auditor.py
# Genera: PROJECT_MAP + KG + DG + Memory + Manifests + hash DB (~10 segundos)

# Opcion 2: dentro del contenedor
docker exec ecommerce_sintel_ai python auditor.py
```

### Re-indexar RAG (docs y codigo)

Despues de editar `docs/specs/`, agregar `commands.py` / `selectors.py`, o modificar Vue:

```powershell
# En caliente (sin reiniciar)
Invoke-RestMethod -Uri "http://localhost:8100/ingest" -Method Post

# Desde dentro del contenedor (con logs detallados)
docker exec ecommerce_sintel_ai python bootstrap.py
```

---

## Artefactos del Knowledge Base

Todos en `ai_engine/`:

| Archivo | Tamano | Contenido |
|---------|--------|-----------|
| `PROJECT_MAP.json` | ~505 KB | 18 apps, 103 modelos, 76 ViewSets, 68 endpoints, 155 frontend files |
| `KNOWLEDGE_GRAPH.json` | ~572 KB | 750 nodos, 1147 aristas tipadas |
| `DEPENDENCY_GRAPH.json` | ~232 KB | 232 entidades con blast radius, 68 endpoint consumers |
| `GLOBAL_MEMORY.json` | ~6 KB | 14 reglas criticas, 5 decisiones arquitectonicas |
| `APP_MEMORY/{app}.json` | 18 archivos | Memoria por app: purpose, constraints, events, known_issues |
| `AI_MANIFESTS/{app}_MANIFEST.json` | 18 archivos | Contrato completo por app |
| `MASTER_MANIFEST.json` | indice | Enlace a todos los manifiestos |
| `.file_hashes.json` | tracking | 519 archivos monitoreados para incremental update |

---

## Reglas que el motor garantiza

### Backend — CRITICAL (bloquean, fuerzan reintento)

| Regla | Que detecta |
|-------|-------------|
| `FLOAT_MONEY` | `total = 19.99` — usar `Decimal('19.99')` |
| `PHYSICAL_DELETE` | `.delete()` en entidades de negocio — usar soft-delete |
| `EMOJI_IN_PY` | Emojis en archivos `.py` |
| `WRONG_ADMIN_PERMISSION_IMPORT` | `from rest_framework.permissions import IsAdminUser` |
| `INCOMPLETE_ADMIN_CHECK` | `is_staff` sin `is_superuser` |
| `NOTIFY_OUTSIDE_ON_COMMIT` | `dispatch_notification()` fuera de `transaction.on_commit` |
| `WOMPI_MISSING_SIGNATURE_CHECK` | Webhook Wompi sin verificar `WOMPI_EVENTS_SECRET` |
| `VIEWSET_DIRECT_DB_WRITE` | `.save()` o `.create()` dentro de un ViewSet |

### Backend — WARNING (entrega el codigo, pero revisar)

| Regla | Que detecta |
|-------|-------------|
| `MISSING_TRANSACTION_ATOMIC` | Command sin `@transaction.atomic` |
| `MISSING_SELECT_FOR_UPDATE` | Operacion de stock sin bloqueo pesimista |
| `SELECTOR_HAS_SIDE_EFFECTS` | Selector con escrituras a BD |

### Frontend Vue — CRITICAL (bloquean, fuerzan reintento)

| Regla | Que detecta |
|-------|-------------|
| `VUE_OPTIONS_API` | `export default { data(), methods: {} }` — usar `<script setup>` |
| `VUE_DIRECT_AXIOS` | `import axios from 'axios'` — usar `useApi()` |
| `VUE_WRITE_NOT_DASHBOARD` | POST/PATCH/DELETE fuera de `dashboard/` |
| `VUE_MISSING_TRY_CATCH` | `await api.*` sin `try/catch` |
| `VUE_ID_IN_FK_PAYLOAD` | `{ category: item.id }` — usar `item.uuid` en FK |
| `VUE_INVENTED_IMPORT` | Imports de componentes inexistentes |

### Frontend Vue — WARNING

| Regla | Que detecta |
|-------|-------------|
| `VUE_MISSING_DEBOUNCE` | Input de busqueda sin debounce de 400ms |
| `VUE_NO_LAZY_ROUTE` | Ruta sin `() => import(...)` |
| `VUE_BAD_PRICE_FORMAT` | `toFixed()` / `Math.round` en precios — usar `Intl.NumberFormat('es-CO')` |

---

## Apps disponibles

### Backend Django

```
accounts  cart  core  dashboard  ecommerce  inventory  marketing
notifications  operations  orders  payment  quotes  renting
shipping  shop  support  technical_services  users
```

### Frontend Vue (modulos detectados)

```
shop  inventory  orders  renting  technical_services  quotes
users  marketing  support  core  customer  landing
```

---

## Mantenimiento

```powershell
# Logs del motor en tiempo real
docker logs ecommerce_sintel_ai -f

# Reiniciar solo el motor (sin perder ChromaDB)
docker compose restart sintel_ai

# Uso de recursos GPU/CPU/RAM
docker stats ecommerce_sintel_ollama ecommerce_sintel_ai ecommerce_sintel_chromadb

# Detener servicios de IA sin afectar Django/Redis/Postgres
docker compose stop sintel_ai sintel_chromadb sintel_ollama
```

### Cambiar modelo LLM

Editar `.env` y reiniciar — sin rebuild:

```bash
LLM_MODEL=llama3.1:8b          # calidad alta, ~14 seg con GPU RTX 4060
LLM_MODEL=qwen2.5-coder:1.5b   # mas rapido, especifico para codigo
```

```powershell
docker compose restart sintel_ai
```

### Rebuild de imagen

Solo necesario si se modifica `ai_engine/requirements.txt` o se agrega un modulo nuevo:

```powershell
docker compose build sintel_ai
docker compose up -d sintel_ai
```

### Limpiar ChromaDB y re-indexar desde cero

```powershell
docker compose stop sintel_ai sintel_chromadb
docker volume rm ecommerce_sintel_chromadb_data
docker compose up -d sintel_chromadb sintel_ai
docker exec ecommerce_sintel_ai python bootstrap.py
```

---

## GPU (RTX 4060)

```powershell
docker exec ecommerce_sintel_ollama nvidia-smi --query-gpu=name,memory.free --format=csv,noheader
# NVIDIA GeForce RTX 4060, ~7200 MiB libres
```

Velocidad esperada: **43-44 tokens/seg**, generacion completa en **12-18 segundos**.

Si Ollama no usa la GPU:

```powershell
docker compose up -d --force-recreate sintel_ollama
```

---

## Troubleshooting

### Motor no arranca — error de conexion a Ollama

```powershell
docker compose up -d sintel_ollama
Start-Sleep 10
docker compose restart sintel_ai
```

### Modelo no encontrado en Ollama

```powershell
docker exec ecommerce_sintel_ollama ollama pull bge-m3
docker exec ecommerce_sintel_ollama ollama pull llama3.1:8b
docker compose restart sintel_ai
```

### chunks_indexed muy bajo (menos de 100) en /health

```powershell
docker exec ecommerce_sintel_ai python bootstrap.py

# Verificar que el volumen este montado
docker exec ecommerce_sintel_ai ls /workspace/frontend/src/modules/
```

### PROJECT_MAP desactualizado — el motor no conoce cambios recientes

```powershell
# Detectar cambios
Invoke-RestMethod -Uri "http://localhost:8100/refresh/detect"

# Actualizar
Invoke-RestMethod -Uri "http://localhost:8100/refresh" -Method Post `
  -ContentType "application/json" -Body '{"force_full": false}'

# O desde el host (mas rapido):
cd C:\Users\Administrator\Documents\ecommerce_sintel_rest
python ai_engine\auditor.py
```

### La generacion tarda mas de 2 minutos

El modelo esta corriendo en CPU. Verificar GPU:

```powershell
docker exec ecommerce_sintel_ollama nvidia-smi
# si falla: docker compose up -d --force-recreate sintel_ollama
```

### Error "peer closed connection" o respuesta cortada

El LLM genero demasiados tokens. El limite esta en `ai_engine/llm_factory.py` (`num_predict=1500`).
Para tareas complejas, aumentar a 2500 y reiniciar.

### task_type detectado incorrectamente

Pasar `task_type` explicitamente:

```powershell
$body = @{ task = "..."; task_type = "frontend" } | ConvertTo-Json
```

### Puerto 11434 ocupado por otro proyecto

```powershell
netstat -ano | findstr :11434
# El contenedor Ollama de Sintel se llama ecommerce_sintel_ollama
```

---

## Referencia rapida

```powershell
# Estado del sistema
Invoke-RestMethod http://localhost:8100/health

# Generar backend
$t = "Crear Command para X en app Y"
$b = @{ task = $t; task_type = "backend" } | ConvertTo-Json
$b | Out-File C:\tmp\req.json -Encoding utf8NoBOM
curl.exe -s -X POST http://localhost:8100/generate -H "Content-Type: application/json" -d "@C:\tmp\req.json" -o C:\tmp\res.json
(Get-Content C:\tmp\res.json -Encoding utf8 | ConvertFrom-Json).final_code

# Generar frontend
$t = "Crear componente Vue para X"
$b = @{ task = $t; task_type = "frontend" } | ConvertTo-Json
$b | Out-File C:\tmp\req.json -Encoding utf8NoBOM
curl.exe -s -X POST http://localhost:8100/generate -H "Content-Type: application/json" -d "@C:\tmp\req.json" -o C:\tmp\res.json
(Get-Content C:\tmp\res.json -Encoding utf8 | ConvertFrom-Json).final_code

# Ver plan antes de generar
$b = @{ task = $t } | ConvertTo-Json
Invoke-RestMethod http://localhost:8100/plan -Method Post -ContentType "application/json" -Body $b

# Analizar impacto
Invoke-RestMethod http://localhost:8100/impact -Method Post -ContentType "application/json" -Body $b

# Que se rompe si cambio Product
Invoke-RestMethod http://localhost:8100/breakage -Method Post -ContentType "application/json" -Body '{"entity":"shop.Product"}'

# Buscar en indices especializados
Invoke-RestMethod http://localhost:8100/search -Method Post -ContentType "application/json" -Body '{"query":"como funciona el pago con Wompi"}'

# Ver indice de indices
Invoke-RestMethod http://localhost:8100/indices

# AI_MANIFEST de una app
Invoke-RestMethod http://localhost:8100/manifest/shop

# Knowledge Graph de una entidad
Invoke-RestMethod "http://localhost:8100/graph/node/Product"
Invoke-RestMethod "http://localhost:8100/graph/impact/Product"

# Memoria del proyecto
Invoke-RestMethod "http://localhost:8100/memory"
Invoke-RestMethod "http://localhost:8100/memory?app=payment"

# Actualizar base de conocimiento incrementalmente
Invoke-RestMethod http://localhost:8100/refresh/detect
Invoke-RestMethod http://localhost:8100/refresh -Method Post -ContentType "application/json" -Body '{"force_full":false}'

# Validar codigo
$b = @{ code = (Get-Content "archivo.py" -Raw); app_context = "orders" } | ConvertTo-Json -Depth 5
$b | Out-File C:\tmp\req.json -Encoding utf8NoBOM
curl.exe -s -X POST http://localhost:8100/validate -H "Content-Type: application/json" -d "@C:\tmp\req.json" | ConvertFrom-Json

# Re-indexar RAG
Invoke-RestMethod -Uri http://localhost:8100/ingest -Method Post

# Rebuild completo del Knowledge Base (desde host)
cd C:\Users\Administrator\Documents\ecommerce_sintel_rest
python ai_engine\auditor.py

# Logs
docker logs ecommerce_sintel_ai -f

# Reiniciar motor
docker compose restart sintel_ai
```
