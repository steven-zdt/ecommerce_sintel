# PLAN DE ACCIÓN — SINTEL MARKETING
## `/panel/marketing` + campañas CRUD + Producto/Servicio/Renting + Desde cero + Imagen/Video + Canales
### IA Editora — fases tipo LOOP
### Entorno inicial: DESARROLLO

## 0. ALCANCE Y PRINCIPIOS

Esta misión comienza en desarrollo y debe reparar primero el problema actual: `/panel/marketing` no permite crear campañas.

El CRUD manual del administrador es obligatorio y permanente:

```text
crear | listar | detalle | editar | activar/desactivar | eliminar/archivar
```

La IA/AgentRun es complemento, nunca reemplaza el CRUD.

No crear un segundo sistema de campañas, canales, notificaciones, media o scheduler si ya existe uno reutilizable.

---

## 1. BASE DOCUMENTAL VALIDADA

La documentación vigente confirma:

```text
MarketingCampaignViewSet
/api/v1/marketing/campaigns/
IsAdminUser
ModelViewSet completo

FlashOfferViewSet
/api/v1/marketing/offers/
AllowAny

AgentRunViewSet
/api/v1/marketing/agent-runs/
IsAdminUser

DashboardViewSet
/api/v1/marketing/dashboard/
IsAdminUser
```

También existen:

```text
marketing/agent/
marketing/channels/
```

con tareas Celery. La documentación indica que esta estructura no fue auditada en profundidad y, por tanto, la IA editora debe inspeccionar el código antes de decidir cambios. 

Además, en una auditoría previa se corrigió `MarketingCampaign.__str__()` porque referenciaba `channel` cuando el campo real era `channels`; el código debe tratarse como fuente de verdad y no como una implementación genérica asumida.

---

## 2. MAPA OBJETIVO

```text
/panel/marketing
      ↓
Vue Component
      ↓
Store / API Client
      ↓
/api/v1/marketing/campaigns/
      ↓
ViewSet / Serializer
      ↓
Commands / Selectors
      ↓
MarketingCampaign
      ↓
PostgreSQL
```

Difusión:

```text
Campaign
   ↓
Channel Registry existente
   ↓
marketing/channels/
   ↓
Celery
   ↓
Provider real
   ↓
Delivery / audit
```

---

## 3. FASE 0 — BASELINE FORENSE

Auditar físicamente:

```text
marketing/models.py
marketing/api/*
marketing/serializers.py
marketing/services/*
marketing/channels/*
marketing/agent/*
marketing/tasks.py
marketing/tests.py

frontend/modules/marketing/*
frontend/stores/*
frontend/router/*
frontend API clients

dashboard/
dashboard/services/admin_orchestrators.py

notifications/
core/media/
organization/
```

Buscar:

```text
MarketingCampaign
FlashOffer
AgentRun
channels
campaign
campaigns
send_campaign
```

Entregables:

```text
docs/marketing/MARKETING_BASELINE.md
docs/marketing/MARKETING_GAPS.md
docs/marketing/MARKETING_DEPENDENCY_MAP.md
```

GATE:

```text
PASS / BLOCKED
```

No inventar componentes.

---

## 4. FASE 1 — REPRODUCIR Y CORREGIR CREATE

Reproducir desde UI:

```text
/panel/marketing
→ Nueva campaña
→ Guardar
```

Capturar:

```text
request
response
HTTP status
validation errors
JS console
network error
serializer error
backend traceback
DB exception
```

Determinar la causa real:

```text
frontend
API
permissions
serializer
ViewSet
Command
model
migration
CSRF
payload
```

Corregir solo la causa necesaria.

GATE:

```text
POST campaign = PASS
```

---

## 5. FASE 2 — CRUD BASE

Verificar:

```text
CREATE
LIST
DETAIL
UPDATE
DELETE / soft-delete
ACTIVATE
DEACTIVATE
```

Con:

```text
IsAdminUser
```

y las convenciones de Service Layer existentes.

---

## 6. FASE 3 — DOS MODOS DE CREACIÓN

La UI debe permitir:

```text
Nueva campaña

[ Desde catálogo ]
[ Desde cero ]
```

Desde catálogo:

```text
Producto
Servicio
Renting
```

Desde cero:

```text
sin objeto de catálogo obligatorio
```

---

## 7. FASE 4 — PRODUCTO COMO BASE

Flujo:

```text
Nueva campaña
→ Desde catálogo
→ Producto
→ Buscar producto
→ Seleccionar
```

Cargar desde el objeto real:

```text
nombre
marca
precio
descripción
imagen(es)
beneficios
```

No duplicar datos innecesariamente.

La campaña debe mantener referencia al objeto real cuando corresponda.

---

## 8. FASE 5 — SERVICIO COMO BASE

Flujo:

```text
Nueva campaña
→ Servicio
→ Buscar servicio
→ Seleccionar
```

Cargar:

```text
nombre
descripción
precio
categoría
beneficios
```

Usar `technical_services` real.

---

## 9. FASE 6 — RENTING COMO BASE

Flujo:

```text
Nueva campaña
→ Renting
→ Buscar equipo
→ Seleccionar equipo/variante
```

Cargar datos reales:

```text
equipo
variante
tarifa
modalidad
disponibilidad cuando aplique
imágenes
```

No alterar disponibilidad ni reservas.

---

## 10. FASE 7 — CAMPAÑAS COMPUESTAS

Debe ser posible expresar:

> “Lleva 02 cámaras y te damos transporte e instalación gratis.”

No limitar la campaña a un único target.

Modelo conceptual:

```text
Campaign
 ├── Item
 │    ├── Product × 2
 │    └── Service / labor
 │
 └── Benefits
      ├── Free shipping
      └── Free installation
```

Antes de crear modelos nuevos, comprobar si `MarketingCampaign`, `FlashOffer` u otras entidades existentes ya permiten representar el caso.

---

## 11. FASE 8 — BENEFICIOS

Implementar inicialmente los beneficios necesarios para el caso real:

```text
free shipping
free installation
discount %
discount fixed
promo price
gift/bonus si el dominio ya lo soporta
```

Separar conceptualmente:

```text
source item
```

de:

```text
benefit
```

---

## 12. FASE 9 — CAMPAÑA DESDE CERO

Debe permitir crear una campaña sin producto/servicio/renting:

```text
Título
Descripción
Mensaje principal
Beneficio
CTA
Condiciones
Vigencia
Audiencia
Canales
Medios
```

Ejemplo:

```text
Título:
02 cámaras + instalación y transporte gratis

Mensaje:
Lleva 2 cámaras de seguridad y recibe instalación y transporte gratis.

CTA:
Solicitar información
```

---

## 13. FASE 10 — CONTENIDO ESTRUCTURADO

Auditar primero el modelo actual.

Si existe contenido estructurado, reutilizarlo.

Como contrato conceptual:

```text
headline
subheadline
body
benefit_text
cta_label
cta_url
terms
```

No depender de un único HTML gigante si el modelo actual permite una estructura mejor.

---

## 14. FASE 11 — MEDIA

Permitir al menos:

```text
IMAGEN
VIDEO
```

Auditar si existe un sistema de media reusable.

Si no existe, evaluar:

```text
CampaignMedia
```

con:

```text
campaign
type
file
mime_type
size
width
height
duration
sort_order
is_active
```

No duplicar el sistema de media del resto del proyecto.

---

## 15. FASE 12 — VALIDACIÓN DE IMAGEN

Verificar:

```text
MIME real
extensión
tamaño
hash
dimensiones
```

No confiar solo en:

```text
.jpg
.png
.webp
```

---

## 16. FASE 13 — VALIDACIÓN DE VIDEO

Verificar:

```text
MIME real
extensión
tamaño
duración
dimensiones
codec si aplica
```

Definir límites reales y configurables.

No procesar archivos pesados de manera síncrona si el proyecto ya tiene patrón asíncrono.

---

## 17. FASE 14 — GALERÍA EN EL PANEL

El formulario debe permitir:

```text
subir
previsualizar
ordenar
activar/desactivar
reemplazar
eliminar
```

No perder medios existentes al editar otros campos.

---

## 18. FASE 15 — CANALES DE ENVÍO

La documentación confirma `marketing/channels/`, pero no establece en el resumen cuáles son todos los canales finales.

La IA editora debe inventariarlos primero.

La UI debe mostrar los canales realmente registrados:

```text
Canales de envío

☐ Canal A
☐ Canal B
☐ Canal C
```

No inventar nombres.

El administrador decide qué canales usar para cada campaña.

---

## 19. FASE 16 — CONTRATO DE CANAL

Reutilizar el contrato actual si ya existe.

Conceptualmente:

```text
campaign
channel
status
scheduled_at
sent_at
failed_at
external_id
error
```

No duplicar `NotificationLog` si Notifications ya cubre exactamente el tracking requerido.

---

## 20. FASE 17 — PROGRAMAR / ENVIAR

UI:

```text
Guardar borrador
Programar
Enviar ahora
Pausar
Cancelar
```

Implementar solo capacidades soportadas por el motor actual.

Para una campaña:

```text
DRAFT
→ READY
→ SCHEDULED
→ RUNNING
→ COMPLETED
```

más estados de fallo/cancelación si realmente corresponden.

---

## 21. FASE 18 — DIFUSIÓN MEDIANTE SISTEMA EXISTENTE

Flujo obligatorio:

```text
Campaign
 ↓
Validation
 ↓
Selected Channels
 ↓
Existing Channel Service
 ↓
Celery
 ↓
Provider
 ↓
Result
```

No:

```text
Vue → provider
```

No:

```text
View → SMTP
```

---

## 22. FASE 19 — EMAIL

Si Email es uno de los canales actuales:

```text
Marketing
→ existing notifications/email service
```

No crear SMTP propio dentro de Marketing.

---

## 23. FASE 20 — WHATSAPP / OTROS

Si existen como canales actuales:

```text
Marketing
→ channel abstraction existente
```

No crear sender paralelo.

Respetar la arquitectura real de `whatsapp/` y del proveedor activo.

---

## 24. FASE 21 — AI / AGENTRUN

Una vez estable el CRUD manual, permitir acciones complementarias:

```text
✨ Generar campaña
✨ Mejorar copy
✨ Generar CTA
✨ Proponer beneficio
✨ Adaptar contenido al canal
```

`AgentRun` puede asistir, pero el resultado definitivo debe persistirse como:

```text
MarketingCampaign
```

La IA no debe ser el SSoT de campañas.

---

## 25. FASE 22 — PREVISUALIZACIÓN

Antes de enviar:

```text
Preview
```

por cada canal realmente soportado:

```text
Email
WhatsApp
Social/Web/otros existentes
```

No mostrar preview de canales inexistentes.

---

## 26. FASE 23 — PERMISOS

Verificar:

```text
Admin → CRUD
Customer → no CRUD administrativo
```

Los endpoints deben conservar `IsAdminUser` para operaciones administrativas.

---

## 27. FASE 24 — TESTS BACKEND

Crear/completar pruebas:

```text
create base campaign
product-based campaign
service-based campaign
renting-based campaign
composite campaign
from-scratch campaign
image
video
channel selection
schedule
send
permissions
invalid FK
invalid channel
invalid media
invalid dates
```

---

## 28. FASE 25 — TEST CRUD UI

Desde:

```text
http://localhost:5173/panel/marketing
```

probar:

```text
crear
listar
ver
editar
activar
desactivar
eliminar/archivar
```

Después de cada operación:

```text
reload
```

para demostrar persistencia en DB.

---

## 29. FASE 26 — SMOKE TEST PRODUCTO

```text
Nueva campaña
→ Producto
→ seleccionar cámara
→ cantidad 2
→ transporte gratis
→ instalación gratis
→ imagen
→ guardar
```

Verificar:

```text
DB
media
benefits
channel
```

---

## 30. FASE 27 — SMOKE TEST SERVICIO

```text
Nueva campaña
→ Servicio
→ seleccionar servicio
→ contenido
→ imagen
→ guardar
→ editar
→ activar
```

---

## 31. FASE 28 — SMOKE TEST RENTING

```text
Nueva campaña
→ Renting
→ equipo
→ variante
→ video
→ guardar
```

---

## 32. FASE 29 — SMOKE TEST DESDE CERO

```text
Nueva campaña
→ Desde cero
→ título
→ texto
→ beneficio
→ CTA
→ imagen
→ video opcional
→ canales
→ guardar
```

Debe quedar persistida aunque no exista un target de catálogo.

---

## 33. FASE 30 — SMOKE TEST DIFUSIÓN

```text
abrir campaña
→ seleccionar canal real
→ enviar
```

Comprobar:

```text
campaign state
channel state
Celery task
provider response
audit/tracking
```

---

## 34. FASE 31 — MEDIA TEST

Probar:

```text
JPG
PNG
WEBP
MP4
archivo inválido
MIME incorrecto
archivo demasiado grande
video corrupto
```

---

## 35. FASE 32 — SEGURIDAD

Probar:

```text
customer intentando POST campaign
ID inválido
FK inválida
channel inválido
path traversal en media
filename malicioso
archivo enorme
```

---

## 36. FASE 33 — OBSERVABILIDAD

Registrar como mínimo:

```text
campaign_created
campaign_updated
campaign_activated
campaign_deactivated
campaign_sent
campaign_failed
campaign_scheduled
media_uploaded
media_removed
channel_selected
channel_send_started
channel_send_success
channel_send_failed
```

Reutilizar auditoría existente si ya existe.

---

## 37. FASE 34 — DOCUMENTACIÓN FINAL

Actualizar:

```text
marketing/.AGENT/docs/ARQUITECTURA_COMPLETA_MARKETING.md
```

y generar:

```text
docs/marketing/MARKETING_BASELINE.md
docs/marketing/MARKETING_CAMPAIGN_MODEL.md
docs/marketing/MARKETING_CHANNELS.md
docs/marketing/MARKETING_MEDIA.md
docs/marketing/MARKETING_E2E_REPORT.md
```

No modificar documentación no afectada.

---

# 38. GATES

## GATE 0

```text
Baseline completo
```

## GATE 1

```text
Create base PASS
```

## GATE 2

```text
CRUD PASS
```

## GATE 3

```text
Product/Service/Renting PASS
```

## GATE 4

```text
Composite + From Scratch PASS
```

## GATE 5

```text
Image + Video PASS
```

## GATE 6

```text
Channels PASS
```

## GATE 7

```text
UI Smoke PASS
```

## GATE 8

```text
Documentation PASS
```

---

# 39. LOOP OBLIGATORIO PARA LA IA EDITORA

Para cada fase:

```text
LEER DOCUMENTACIÓN
      ↓
INSPECCIONAR CÓDIGO REAL
      ↓
MAPEAR COMPONENTES EXISTENTES
      ↓
REPRODUCIR
      ↓
IDENTIFICAR CAUSA
      ↓
DISEÑAR CAMBIO MÍNIMO
      ↓
IMPLEMENTAR
      ↓
MIGRAR SI APLICA
      ↓
TEST UNITARIO
      ↓
TEST INTEGRACIÓN
      ↓
SMOKE TEST UI
      ↓
VERIFICAR DB
      ↓
VERIFICAR MEDIA
      ↓
VERIFICAR CHANNEL
      ↓
ACTUALIZAR DOCUMENTACIÓN
      ↓
PASS / PARTIAL / BLOCKED
      ↓
SIGUIENTE FASE
```

No avanzar si:

```text
CRUD base falla
permissions fallan
migraciones fallan
media falla
channel contract falla
Celery falla
regresión detectada
```

---

# 40. NO REGRESIÓN

Debe mantenerse funcionando:

```text
FlashOffer
AgentRun
Marketing Dashboard
marketing/channels existentes
notificaciones
productos
servicios
renting
```

No romper:

```text
Product
TechnicalService
Renting
Orders
Notifications
```

---

# 41. RESULTADO FINAL

```text
/panel/marketing
        ↓
Nueva campaña
        ↓
Desde catálogo
   ├── Producto
   ├── Servicio
   └── Renting

o

Desde cero
        ↓
Contenido
        ↓
Oferta / Beneficios
        ↓
Imagen / Video
        ↓
Canales de envío
        ↓
Guardar en DB
        ↓
Editar / activar / programar
        ↓
Difundir
        ↓
marketing/channels
        ↓
Celery
        ↓
Provider
        ↓
Estado + auditoría
```

---

# 42. CASO DE ACEPTACIÓN PRINCIPAL

El siguiente caso debe funcionar completamente desde el panel:

```text
/panel/marketing
```

Crear:

```text
Campaña:
“02 cámaras + transporte e instalación gratis”
```

Base:

```text
Producto → Cámara × 2
```

Beneficios:

```text
Transporte gratis
Instalación gratis
```

Media:

```text
1 imagen publicitaria
1 video publicitario
```

Canales:

```text
seleccionar los canales realmente existentes
```

Guardar:

```text
PostgreSQL
```

Editar:

```text
CRUD completo
```

Difundir:

```text
Campaign
→ Channel
→ Celery
→ Provider
→ resultado
```

---

# 43. PRINCIPIOS FINALES

```text
MANUAL FIRST
FULL CRUD
DATABASE PERSISTENCE
PRODUCT SOURCE
SERVICE SOURCE
RENTING SOURCE
COMPOSITE CAMPAIGNS
FROM SCRATCH
BENEFITS
IMAGE
VIDEO
EXISTING CHANNELS
EXISTING CELERY
EXISTING NOTIFICATIONS
AI AS COMPLEMENT
ADMIN CONTROL
NO DUPLICATE SYSTEMS
DEVELOPMENT FIRST
PRODUCTION LATER
AUDITABLE
TESTED
```

> Objetivo final: transformar `/panel/marketing` en un módulo de campañas realmente operativo, donde el administrador pueda crear campañas manualmente desde un producto, servicio o renting, combinar varios elementos y beneficios, crear campañas desde cero, adjuntar imágenes/videos, guardar todo en PostgreSQL mediante el Service Layer y difundir por los canales de envío que ya existen en SINTEL, sin duplicar la arquitectura actual.
