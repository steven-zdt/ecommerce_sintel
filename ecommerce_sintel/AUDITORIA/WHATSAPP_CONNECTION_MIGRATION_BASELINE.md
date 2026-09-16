# WHATSAPP_CONNECTION_MIGRATION_BASELINE — FASE 0

**Misión "Migración Arquitectónica de WhatsApp — QR Web Session Experimental + Meta Cloud API
Futura", 2026-09-16.** Esta misión NO parte de cero — la misión anterior ("Refactorización
Arquitectónica del Módulo WhatsApp", commit `e5bdb10`) ya construyó la arquitectura hexagonal
real (dominio, puerto, factory, 2 adapters, 31 tests, incluyendo un test de aislamiento
estructural vía AST). Esta fase audita **qué de eso ya cumple el nuevo contrato** y qué falta.

## Lo que ya existe y cumple la nueva misión tal cual (sin cambios)

| Componente | Archivo | Cumple |
|---|---|---|
| Dominio (WhatsAppService, resolvers, idempotency) | `whatsapp/domain/` | **Sí** — independiente del transporte, verificado con AST |
| Contrato canónico (Inbound/Outbound) | `whatsapp/domain/contracts.py` | Sí |
| Puerto de conexión | `whatsapp/ports/connection.py` | Sí, síncrono (decisión ya documentada) |
| Integración Support/ai_bridge/ADK sin cambios | `support/services/ai_bridge.py` (no tocado) | Sí |
| Deduplicación provider-agnostic | `whatsapp/domain/idempotency.py` | Sí |

## Lo que requiere renombrar/ampliar (nueva nomenclatura de esta misión)

| Antes | Ahora (esta misión) | Motivo real |
|---|---|---|
| `RestConnectionAdapter` | `MetaCloudAPIAdapter` | Mismo adapter real (Meta Cloud API), nombre más explícito — evita confundirlo con "REST genérico" |
| `QRConnectionAdapter` | `QRWebSessionAdapter` | Debe quedar explícitamente marcado EXPERIMENTAL/THIRD-PARTY/NON-OFFICIAL, no solo "QR" |
| `WHATSAPP_CONNECTION_TYPE=REST` | `WHATSAPP_CONNECTION_TYPE=META_CLOUD_API` | Nomenclatura explícita |
| `WHATSAPP_CONNECTION_TYPE=QR` | `WHATSAPP_CONNECTION_TYPE=QR_WEB_SESSION` | Ídem |
| `ConnectionCapabilities` (9 campos planos) | Modelo de capacidades ampliado (FASE 3) | La misión pide poder consultar capacidades reales por adapter de forma más explícita en la UI |
| Sin `WhatsAppSessionManager` | Nuevo (FASE 9) | Estados reales de sesión QR (DISABLED, NOT_CONFIGURED, QR_REQUIRED, QR_READY, SCANNING, AUTHENTICATING, CONNECTED, RECONNECTING, DISCONNECTED, ERROR) — el `ConnectionStatus` anterior (5 valores) no distingue esto |
| Sin evaluación real de proveedor QR | Nuevo (FASE 8) | **Pendiente de esta fase — ver sección siguiente** |

## Hallazgo crítico que se mantiene (heredado de la misión anterior, re-confirmado)

`AUDITORIA/WHATSAPP_CONNECTION_BASELINE.md` (misión anterior) ya documentó: no existe ningún
gateway QR real integrado. Esta misión pide ir un paso más allá — evaluar EXPLÍCITAMENTE (FASE 8)
si existe un proveedor QR técnicamente aceptable antes de construir más que la estructura. Esa
evaluación real se hace en este documento más abajo, no se pospone.

## Clasificación (DOMAIN/APPLICATION/PORT/ADAPTER/INFRASTRUCTURE/CONFIGURATION/UI)

Sin cambios respecto a la matriz de la misión anterior (`WHATSAPP_CONNECTION_BASELINE.md`) — se
referencia, no se duplica. Los puntos nuevos de esta misión (SessionManager, UI de estados) se
clasifican:

| Componente nuevo | Clasificación |
|---|---|
| `WhatsAppSessionManager` (estados de sesión QR) | APPLICATION — vive junto al adapter QR, nunca en el dominio (el dominio no conoce "SCANNING"/"QR_READY", esos son estados de TRANSPORTE) |
| UI `/panel/soporte/whatsapp` (estados distintos por tipo de conexión) | UI |
| `AUDITORIA/WHATSAPP_QR_PROVIDER_BLOCKED.md` (si aplica) | Documentación de decisión, no código |

## Checkpoint FASE 0

**PASS.** Base real sólida heredada — el trabajo real de esta misión es: renombrar/ampliar según
la nueva nomenclatura, construir el `SessionManager` real, evaluar honestamente un proveedor QR
real (FASE 8, sección dedicada abajo en `WHATSAPP_QR_PROVIDER_EVALUATION.md`), y extender
UI/observabilidad/seguridad/tests al nuevo nivel de detalle que pide esta misión.
