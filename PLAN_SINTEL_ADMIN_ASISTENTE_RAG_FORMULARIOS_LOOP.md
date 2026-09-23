# PLAN DE ACCIÓN — SINTEL ADMIN ASSISTANT
## `/panel/asistente` + RAG de Agentes SINTEL ADMIN IA + Formularios Guiados por Intención
### Implementación por fases tipo LOOP para IA Editora

**Fecha:** 2026-09-23  
**Proyecto:** SINTEL ERP

## 0. DECISIONES ARQUITECTÓNICAS OBLIGATORIAS

### 0.1 `/panel/asistente` debe inicializar SIEMPRE SINTEL ADMIN IA

Regla absoluta:

```text
/panel/asistente
      ↓
SINTEL ADMIN IA
      ↓
Google ADK Runtime
      ↓
RAG de Agentes SINTEL
```

La pantalla no debe seleccionar libremente otro agente ni reutilizar accidentalmente el agente de soporte/customer.

La identidad real debe determinarse y validarse en backend mediante el `AgentRegistry`/perfil existente. El frontend nunca debe poder enviar un `agent_id` arbitrario.

Usar el identificador real existente después del baseline; si no existe, establecer uno canónico como `sintel_admin`.

### 0.2 Manual siempre disponible

La IA es complemento. Nunca reemplaza:

```text
/panel/productos
/panel/servicios
/panel/renta
/panel/cotizaciones
```

Todos los CRUD manuales deben seguir funcionando aunque la IA esté desactivada o ADK/RAG esté fuera de servicio.

---

# 1. PROBLEMA ACTUAL

La respuesta actual del agente es demasiado genérica. Para una solicitud de servicio pregunta por atributos propios de producto como marca y condición, y obliga al administrador a mantener una conversación larga.

La experiencia objetivo es:

```text
ADMIN
 ↓
SINTEL ADMIN IA
 ↓
DETECTAR INTENCIÓN
 ↓
PRODUCTO | SERVICIO | RENTING | COTIZACIÓN
 ↓
FORMULARIO ESPECÍFICO
 ↓
AUTOCOMPLETAR LO YA CONOCIDO
 ↓
PREGUNTAR SOLO LO FALTANTE
 ↓
VALIDAR
 ↓
PROPUESTA
 ↓
APROBACIÓN
 ↓
TOOL → COMMAND/SERVICE → MÓDULO REAL
 ↓
VERIFICACIÓN
```

---

# 2. NUEVO MODELO UX: CHAT + FORMULARIO

`/panel/asistente` debe tener conversación y formulario dinámico sincronizados.

```text
┌───────────────────────────────────────────────┐
│ SINTEL ADMIN IA                         ● ON  │
├───────────────────────┬───────────────────────┤
│ Conversación          │ Datos de la operación │
│                       │                       │
│ Usuario:              │ Tipo: SERVICIO        │
│ Crear un servicio...  │ Nombre: ...           │
│                       │ Precio: ...            │
│ Agente:               │ Categoría: ...        │
│ Claro. Completemos    │ Descripción: ...      │
│ los datos necesarios. │ Garantía: ...         │
│                       │                       │
│                       │ [Validar propuesta]    │
└───────────────────────┴───────────────────────┘
```

No obligar al administrador a escribir cada dato por chat.

---

# 3. SELECTOR DE INTENCIÓN

Al iniciar una conversación:

```text
¿Qué deseas hacer?

○ Crear producto
○ Crear servicio
○ Crear renting
○ Crear cotización
○ Describirlo en lenguaje natural
```

Si el usuario selecciona un tipo, el backend genera directamente el schema correspondiente.

Si escribe primero en lenguaje natural:

```text
"Quiero crear un nuevo servicio..."
```

el agente debe proponer:

```text
Creo que deseas crear un SERVICIO.
¿Correcto?

[Servicio] [Producto] [Renting] [Cotización]
```

No preguntar nuevamente si ya existe una selección explícita.

---

# 4. INTENT CONTRACT

Crear o reutilizar un contrato estructurado:

```json
{
  "domain": "catalog",
  "intent": "service.create",
  "entity": "service",
  "operation": "create",
  "source": "panel_assistant",
  "status": "collecting"
}
```

El routing sigue siendo determinista. El LLM puede ayudar a interpretar lenguaje natural, pero no debe convertirse en autoridad de seguridad.

---

# 5. SESSION CONTRACT

La sesión debe conservar:

```json
{
  "agent_profile": "sintel_admin",
  "session_id": "...",
  "actor_id": "...",
  "surface": "panel_assistente",
  "intent": "service.create",
  "entity": "service",
  "status": "collecting",
  "draft_id": "...",
  "required_fields": [],
  "completed_fields": [],
  "missing_fields": [],
  "validation_errors": [],
  "approval_required": true
}
```

`agent_profile` se controla en backend.

---

# 6. FORM SCHEMA DINÁMICO

El backend debe entregar al frontend el formulario adecuado a la intención.

Ejemplo:

```json
{
  "form_id": "service.create",
  "version": 1,
  "title": "Crear servicio",
  "fields": [
    {
      "name": "name",
      "label": "Nombre del servicio",
      "type": "text",
      "required": true
    },
    {
      "name": "category",
      "label": "Categoría",
      "type": "select",
      "required": true,
      "source": "categories"
    },
    {
      "name": "price",
      "label": "Precio",
      "type": "currency",
      "currency": "COP",
      "required": true
    },
    {
      "name": "short_description",
      "label": "Descripción corta",
      "type": "textarea",
      "required": true
    }
  ]
}
```

No duplicar en Vue las reglas de negocio del backend.

---

# 7. TIPOS INICIALES

Implementar primero:

```text
product.create
service.create
renting.create
quotation.create
```

Preparar extensibilidad para:

```text
category.create
brand.create
variant.create
inventory.*
customer.*
order.*
marketing.*
operations.*
```

No implementar todo simultáneamente.

---

# 8. FORMULARIO DE PRODUCTO

Auditar el modelo real y generar únicamente los campos aplicables.

Posibles grupos:

### Identificación
- nombre
- SKU
- categoría
- marca

### Comercial
- precio
- costo
- impuesto/IVA
- destacado

### Catálogo
- descripción corta
- descripción completa
- imágenes
- atributos
- variantes

### Operación
- inventariable
- stock inicial
- unidad de medida

### SEO
- meta título
- meta descripción
- slug

El formulario final debe salir del contrato real del módulo, no de una lista inventada.

---

# 9. FORMULARIO DE SERVICIO

Para:

> “Quiero crear un servicio de automatización de tiendas locales…”

debe aparecer:

```text
He entendido que deseas crear un SERVICIO.

✓ Tipo: Servicio
✓ Nombre: Servicio de Automatización de Tiendas Locales - Creación de Huella Digital

Completa o confirma:
[Nombre]
[Descripción corta]
[Categoría]
[Precio COP]
[Garantía]

Opcionales:
[Destacado]
[SEO]
```

NO preguntar automáticamente:

```text
marca
condición
```

si el modelo real de servicio no los requiere.

Este punto corrige directamente el comportamiento observado.

---

# 10. FORMULARIO DE RENTING

Según los modelos reales del módulo:

```text
Equipo/recurso
Categoría
Descripción
Modalidad
Tarifa
Unidad de tiempo
Disponibilidad
Depósito si aplica
Condiciones
Entrega/recogida
Horario
Garantía/responsabilidad
Imágenes
SEO
```

No crear una segunda lógica de reservas.

---

# 11. FORMULARIO DE COTIZACIÓN

Inicialmente:

```text
Cliente
Título/referencia
Vigencia
Items
Cantidad
Producto/servicio
Precio
Descuento
IVA
Notas
Condiciones comerciales
```

Permitir:

```text
+ Producto
+ Servicio
```

Las entidades deben resolverse mediante Tools/Selectors existentes. El LLM nunca debe inventar IDs.

---

# 12. CLASIFICACIÓN DE CAMPOS

Cada campo debe ser:

```text
REQUIRED
OPTIONAL
DERIVABLE
SYSTEM_DEFAULT
```

Ejemplo:

```text
name             REQUIRED
price            REQUIRED
category         REQUIRED
description      REQUIRED
meta_title       OPTIONAL
meta_description OPTIONAL
slug             DERIVABLE
currency         SYSTEM_DEFAULT = COP
created_by       SYSTEM
tenant           SYSTEM
```

Regla:

```text
IF está en la solicitud → usarlo
ELSE IF puede resolverse determinísticamente → resolverlo
ELSE IF puede sugerirse con RAG → sugerirlo
ELSE → preguntar
```

Nunca preguntar por un dato que el sistema ya conoce.

---

# 13. SMART PREFILL

Si el administrador escribe:

```text
Quiero crear un servicio de automatización de tiendas locales por 1.500.000 pesos.
```

mostrar:

```text
Tipo: SERVICIO
Nombre: Servicio de Automatización de Tiendas Locales
Precio: $1.500.000 COP
Descripción: pendiente
Categoría: pendiente
```

El usuario completa únicamente lo pendiente.

---

# 14. CHAT Y FORMULARIO DEBEN COMPARTIR UN ÚNICO DRAFT

Crear/reutilizar una entidad temporal:

```text
AdminAIDraft
```

Conceptualmente:

```text
AdminAIDraft
├── id
├── session
├── intent
├── entity
├── payload
├── missing_fields
├── validation_errors
├── proposal_version
├── status
├── created_by
└── expires_at
```

Estados:

```text
COLLECTING
VALIDATING
READY
AWAITING_APPROVAL
EXECUTING
COMPLETED
FAILED
CANCELLED
EXPIRED
```

La conversación y el formulario nunca deben mantener dos estados independientes.

---

# 15. SINCRONIZACIÓN BIDIRECCIONAL

Debe funcionar:

```text
chat → draft
form → draft
draft → chat
draft → form
```

Ejemplo:

Usuario:

```text
“El precio es 2 millones”
```

El campo Precio cambia inmediatamente a:

```text
$2.000.000 COP
```

Usuario:

```text
“Ponlo destacado”
```

El checkbox se activa.

---

# 16. RESOLUCIÓN INTELIGENTE DE CATEGORÍAS

Ante:

```text
categoría = servicios
```

no preguntar inmediatamente “¿creo una categoría?”

Resolver:

```text
exact lookup
 ↓
normalized lookup
 ↓
database lookup
 ↓
semantic search
 ↓
categorías relacionadas
 ↓
propuesta
```

Si existe una categoría compatible:

```text
usar existente
```

Si hay varias:

```text
mostrar opciones
```

Si no existe:

```text
proponer crear categoría
```

La creación de una categoría debe pasar por aprobación y la lógica real del módulo.

---

# 17. RAG DE AGENTES SINTEL ADMIN IA

La arquitectura objetivo:

```text
/panel/asistente
       ↓
Admin AI Gateway
       ↓
SINTEL ADMIN IA
       ↓
Google ADK
       ├── Agent RAG
       ├── Business Knowledge
       ├── System Knowledge
       ├── Tool Registry
       └── Policy Layer
```

El RAG debe responder preguntas como:

```text
qué módulo usar
qué campos existen
qué relaciones existen
qué herramientas están disponibles
qué categorías existen
qué servicios existen
qué reglas/documentación aplican
```

Pero:

> RAG informa; los Services/Commands del ERP validan y ejecutan.

---

# 18. SYSTEM KNOWLEDGE VS BUSINESS KNOWLEDGE

## System Knowledge

```text
apps
models
endpoints
services
commands
selectors
tools
agents
permissions
relationships
```

Fuente principal:

```text
project_knowledge_graph
```

## Business Knowledge

```text
productos
categorías
marcas
servicios
renting
clientes
cotizaciones
precios
configuración comercial
```

Fuente:

```text
PostgreSQL
pgvector
RAG
Business Knowledge Graph si ya existe
```

No duplicar datos transaccionales innecesariamente en el RAG.

---

# 19. TOOL-FIRST

Antes de crear nuevas Tools, auditar las existentes.

Capacidades objetivo:

```text
resolve_category
resolve_brand
search_products
search_services
search_renting
search_customers
validate_product_draft
validate_service_draft
validate_renting_draft
validate_quote_draft
create_product
create_service
create_renting
create_quote
```

Si existe una Tool equivalente:

```text
REUTILIZAR
```

No duplicar.

---

# 20. SERVICE LAYER

Flujo obligatorio:

```text
Intent
 ↓
Tool
 ↓
Command / Selector
 ↓
Business Service
 ↓
Model
```

Nunca:

```text
LLM → ORM
LLM → SQL
LLM → Model.save()
```

La propuesta anterior debe alinearse con el principio existente:

> ADK ORQUESTA. SINTEL CONOCE, AUTORIZA, EJECUTA Y VERIFICA.

---

# 21. PREVISUALIZACIÓN Y APROBACIÓN

Cuando todos los datos estén completos:

```text
┌──────────────────────────────────┐
│ Revisar creación                 │
├──────────────────────────────────┤
│ Tipo: Servicio                   │
│ Nombre: ...                      │
│ Categoría: ...                   │
│ Precio: $1.500.000 COP           │
│ Garantía: 12 meses               │
│                                  │
│ [Editar] [Cancelar] [Crear]     │
└──────────────────────────────────┘
```

La escritura requiere aprobación según la política de riesgo existente.

---

# 22. EJECUCIÓN Y VERIFICACIÓN

```text
Draft
 ↓
Validation
 ↓
Proposal
 ↓
Approval
 ↓
Tool
 ↓
Command
 ↓
Service Layer
 ↓
DB
 ↓
Verification
```

Después:

```text
✓ Servicio creado correctamente

[Ver servicio]
[Editar]
[Crear otro]
```

`Ver servicio` debe llevar al módulo real del `/panel/`.

---

# 23. SINCRONIZACIÓN CON CRUD MANUAL

Después de crear:

```text
AI Assistant
 ↓
DB real
 ↓
refresh/invalidate
 ↓
/panel/servicios
```

La IA nunca crea un catálogo paralelo.

Los mismos Commands/Services deben servir para:

```text
CRUD manual
AI Assistant
otros clientes administrativos autorizados
```

---

# 24. ACCIONES IA DENTRO DEL CRUD

Agregar progresivamente:

```text
✨ Completar con IA
✨ Generar descripción
✨ Sugerir categoría
✨ Generar SEO
✨ Revisar datos
```

Estas acciones son complementarias.

Si la IA está apagada:

```text
formulario manual = 100% funcional
```

---

# 25. CONFIGURACIÓN VISIBLE EN `/panel/`

Crear/reutilizar:

```text
/panel/asistente
/panel/ai-admin
/panel/configuracion/ai-admin
```

Configuraciones:

```text
IA administrativa ON/OFF
SINTEL ADMIN IA ON/OFF
Productos ON/OFF
Servicios ON/OFF
Renting ON/OFF
Cotizaciones ON/OFF

Modo:
READ
PROPOSE
APPROVAL
LIMITED

Autocompletado ON/OFF
Sugerencias de categoría ON/OFF
SEO automático ON/OFF
```

Nunca desactivar el CRUD manual.

---

# 26. AGENT PROFILE LOCK

Backend debe validar:

```text
surface == panel_assistente
AND authenticated admin
AND permission allowed
AND agent_profile == SINTEL_ADMIN
```

Si llega un perfil distinto, rechazar.

Nunca permitir:

```json
{
  "agent": "generic"
}
```

desde el navegador como mecanismo de selección.

El frontend solo envía:

```json
{
  "surface": "panel_assistente",
  "message": "crear un servicio..."
}
```

El backend decide el agente.

---

# 27. RESPUESTA OBJETIVO PARA EL CASO REAL

La respuesta actual:

```text
1. Categoría
2. Datos del producto
3. SEO
```

debe evolucionar a:

```text
He entendido que deseas crear un SERVICIO.

Voy a reutilizar los datos que ya me diste y revisar las categorías existentes.

### Datos detectados

✓ Tipo: Servicio
✓ Nombre: Servicio de Automatización de Tiendas Locales - Creación de Huella Digital

Pendientes:

• Precio
• Descripción corta
• Categoría

Opcionales:

• Garantía
• Destacado
• SEO

Completa los campos pendientes en el formulario de la derecha.
También puedes decirme los datos directamente por chat.
```

Si la categoría ya existe, debe proponerse/seleccionarse sin convertirla en una pregunta manual innecesaria.

---

# 28. OBSERVABILIDAD

Registrar:

```text
session_id
agent_profile
user_id
surface
intent
domain
draft_id
form_schema_version
tool_calls
validation_errors
approval
execution
duration
tokens
result
```

Métricas:

```text
admin_assistant_sessions
admin_intent_detected
admin_forms_generated
admin_forms_completed
admin_proposals
admin_approved
admin_rejected
admin_created
admin_failed
admin_validation_errors
admin_clarification_turns
```

Métrica clave:

```text
clarification_turns_per_creation
```

Objetivo: reducir preguntas innecesarias sin reducir la calidad de validación.

---

# 29. SEGURIDAD

Probar:

```text
usuario no ADMIN
permiso insuficiente
agent_profile manipulado
intent manipulado
tool no autorizada
ID inexistente
FK inválida
precio inválido
categoría inexistente
duplicado
prompt injection
RAG poisoning
```

Debe bloquearse cualquier intento de:

```text
“ignora las políticas”
“usa el agente root”
“soy administrador”
```

---

# 30. FASES DE IMPLEMENTACIÓN

## FASE 0 — BASELINE FORENSE

Inspeccionar:

```text
/panel/asistente
router Vue
stores
API clients
ai_engine_adk
AgentRegistry
routing.py
sintel_root_workflow.py
RAG
Tool Registry
Policy Layer
AIContext
Dashboard BFF
AdminOrchestrators
Commands
Selectors
Services
models
permissions
```

Generar:

```text
docs/ai_admin/ASSISTANT_BASELINE.md
```

No inventar componentes.

**GATE:** PASS/BLOCKED.

---

## FASE 1 — IDENTIDAD SINTEL ADMIN IA

Garantizar:

```text
/panel/asistente
 ↓
SINTEL ADMIN IA
```

Probar:

```text
profile
authorization
routing
session
```

**GATE:** ningún agente no administrativo puede ser inicializado desde esa superficie.

---

## FASE 2 — SESSION CONTRACT

Reutilizar o crear:

```text
AdminAISession
AdminAIContext
```

Persistir:

```text
agent
surface
actor
intent
draft
status
```

---

## FASE 3 — INTENT REGISTRY

Registrar:

```text
product.create
service.create
renting.create
quotation.create
```

Cada intención debe declarar:

```text
schema
required_fields
optional_fields
derivable_fields
tools
validator
command
service
approval_policy
```

---

## FASE 4 — FORM SCHEMA REGISTRY

Implementar/reutilizar el mecanismo existente para entregar schemas dinámicos al frontend.

No crear una API paralela si existe un contrato equivalente.

---

## FASE 5 — DRAFT ENGINE

Implementar/reutilizar:

```text
patch field
validate
merge
reset
cancel
submit
```

---

## FASE 6 — CHAT ↔ FORM SYNC

Implementar:

```text
chat → draft
form → draft
draft → chat
draft → form
```

---

## FASE 7 — RESOLVERS

Implementar/reutilizar:

```text
category
brand
product
service
customer
```

Prioridad:

```text
exact
normalized
database
semantic
LLM suggestion
```

---

## FASE 8 — SMART PREFILL

Extraer:

```text
nombre
precio
categoría
descripción
cliente
equipo
cantidad
fecha
```

desde el lenguaje natural.

---

## FASE 9 — VALIDATION ENGINE

Validación estructurada por dominio.

La validación de backend es la fuente de verdad.

---

## FASE 10 — PROPOSAL UI

Mostrar:

```text
datos
cambios
advertencias
errores
pendientes
```

Botones:

```text
Editar
Cancelar
Aprobar y crear
```

---

## FASE 11 — EXECUTION TOOLS

Conectar Tools existentes y crear únicamente las faltantes.

---

## FASE 12 — SERVICE LAYER

Verificar que todas las escrituras terminen en Commands/Services y nunca en ORM directo desde el agente.

---

## FASE 13 — PANEL REFRESH

Tras creación:

```text
invalidate
refresh
navigate
```

siguiendo el patrón Vue existente.

---

## FASE 14 — CONFIGURACIÓN

Hacer visibles y configurables:

```text
AI
capabilities
autonomy
prefill
suggestions
SEO
approval
```

---

## FASE 15 — INTEGRACIÓN CRUD MANUAL

Agregar acciones IA contextuales sin modificar ni romper el flujo manual.

---

## FASE 16 — AUDITORÍA

Crear/reutilizar:

```text
/panel/ai-admin/history
```

---

## FASE 17 — TESTS

### Unit

```text
agent identity
intent
schema
draft
resolver
policy
tool
```

### Integration

```text
assistant
→ ADK
→ tool
→ command
→ service
```

### E2E

```text
panel
→ assistant
→ form
→ proposal
→ approval
→ creation
→ module
```

### Regression

```text
manual CRUD
```

---

# 31. CASOS DE ACEPTACIÓN

## Producto

```text
"crear cámara Hikvision 4MP por 450000"
→ PRODUCTO
→ formulario prellenado
→ marca/categoría resueltas
→ precio COP
→ propuesta
→ aprobación
→ creación
```

## Servicio

```text
"crear servicio de automatización de tiendas por 1500000"
→ SERVICIO
→ formulario específico
→ NO preguntar marca/condición si no aplican
→ categoría resuelta/propuesta
→ descripción
→ propuesta
→ aprobación
→ creación
```

## Renting

```text
"crear renting de cámara por día"
→ RENTING
→ equipo
→ tarifa
→ unidad
→ disponibilidad
→ condiciones
→ aprobación
```

## Cotización

```text
"crear cotización para Cliente X con cámara + instalación"
→ COTIZACIÓN
→ cliente
→ items
→ cantidades
→ precios
→ IVA
→ total
→ aprobación
```

---

# 32. LOOP OBLIGATORIO PARA LA IA EDITORA

Para cada fase:

```text
1. LEER documentación relacionada
2. INSPECCIONAR código real
3. IDENTIFICAR componentes existentes
4. NO asumir que existe algo
5. COMPARAR documentación vs código
6. IDENTIFICAR GAP
7. DISEÑAR CAMBIO MÍNIMO
8. IMPLEMENTAR
9. EJECUTAR TESTS
10. EJECUTAR SMOKE TEST
11. VALIDAR UI
12. VALIDAR SEGURIDAD
13. ACTUALIZAR DOCUMENTACIÓN
14. REPORTAR PASS/BLOCKED
15. DECIDIR SIGUIENTE FASE
```

No avanzar si:

```text
agent identity falla
routing falla
permisos fallan
tests críticos fallan
manual CRUD falla
```

---

# 33. CRITERIOS DE NO REGRESIÓN

Debe permanecer funcionando:

```text
/panel/*
CRUD manual
Dashboard BFF
Commands
Selectors
Services
Google ADK
RAG
Knowledge Graph
Tool Registry
Policy Layer
```

No:

```text
reemplazar CRUD manual
duplicar dominio
duplicar modelos
duplicar lógica de negocio
crear segundo ERP
crear agente genérico paralelo
permitir ORM desde LLM
```

---

# 34. RESULTADO FINAL

```text
ADMIN
 ↓
/panel/asistente
 ↓
SINTEL ADMIN IA
 ↓
PRODUCTO | SERVICIO | RENTING | COTIZACIÓN
 ↓
FORMULARIO ESPECÍFICO
 ↓
AUTOCOMPLETADO
 ↓
CHAT + FORMULARIO SINCRONIZADOS
 ↓
RAG / KNOWLEDGE GRAPH
 ↓
RESOLVERS
 ↓
VALIDACIÓN
 ↓
PROPUESTA
 ↓
APROBACIÓN
 ↓
TOOL
 ↓
SERVICE LAYER
 ↓
CREACIÓN REAL
 ↓
VERIFICACIÓN
 ↓
/panel/* REAL
```

## PRINCIPIOS

```text
MANUAL FIRST
AI ASSISTED
SINTEL ADMIN IA FIXED
CHAT + FORM
ONE DRAFT
RAG GROUNDED
DETERMINISTIC ROUTING
TOOL-FIRST
SERVICE-LAYER ENFORCED
HUMAN APPROVAL
AUDITABLE
REVERSIBLE
NO ORM FROM LLM
NO DUPLICATE BUSINESS LOGIC
```

**Objetivo final:** que SINTEL ADMIN IA entienda la intención del administrador, abra automáticamente el formulario correcto, complete lo que ya conoce, solicite solamente los datos realmente necesarios y ejecute la operación mediante la arquitectura real de SINTEL.
