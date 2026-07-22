# Sintel E-Commerce — Instrucciones para el Editor IA

## REGLAS GLOBALES DEL PROYECTO
## [CRITICAL] 0. Cero Caracteres Especiales en Código Python

**REGLA FUNDAMENTAL - NO EMOJIS EN ARCHIVOS .PY**

- **[PROHIBIDO]**: Usar emojis en CUALQUIER archivo `.py`.
- **[PROHIBIDO]**: Caracteres especiales Unicode/multibyte en código Python.
- **[PERMITIDO]**: Comentarios y docstrings en texto plano SOLAMENTE.
- **RAZÓN**: Los emojis en código Python causan `SyntaxError` que rompen la compilación y generan `500 Internal Server Error` en Django.
- **ALCANCE**: Aplica a TODO el proyecto - `/apps/`, `/config/`, `/tests/`, `/tools/`, `/scripts/`.
- **VALIDACIÓN**: Toda PR debe pasar `python -m py_compile archivo.py` sin errores.
Antes de cualquier modificación, leer obligatoriamente:
- **Reglas y estándares globales:** `.AGENT.md`

## ROUTING: DOCUMENTO DE ARQUITECTURA POR APP

Cuando trabajes en cualquier archivo de una app, lee primero el documento de arquitectura correspondiente:

| App / Directorio | Documento de Arquitectura |
|-----------------|--------------------------|
| `ecommerce_sintel/accounts/` | `ecommerce_sintel/accounts/.AGENT/docs/ARQUITECTURA_COMPLETA_ACCOUNTS.md` |
| `ecommerce_sintel/cart/` | `ecommerce_sintel/cart/.AGENT/docs/ARQUITECTURA_COMPLETA_CART.md` |
| `ecommerce_sintel/core/` | `ecommerce_sintel/core/.AGENT/docs/ARQUITECTURA_COMPLETA_CORE.md` |
| `ecommerce_sintel/dashboard/` | `ecommerce_sintel/dashboard/.AGENT/docs/ARQUITECTURA_COMPLETA_DASHBOARD.md` |
| `ecommerce_sintel/ecommerce/` | `ecommerce_sintel/ecommerce/.AGENT/docs/ARQUITECTURACOMPLETA_SETTING.md` |
| `ecommerce_sintel/inventory/` | `ecommerce_sintel/inventory/.AGENT/docs/ARQUITECTURA_COMPLETA_INVENTORY.md` |
| `ecommerce_sintel/kyc/` | `ecommerce_sintel/kyc/.AGENT/docs/ARQUITECTURA_COMPLETA_KYC.md` |
| `ecommerce_sintel/marketing/` | `ecommerce_sintel/marketing/.AGENT/docs/ARQUITECTURA_COMPLETA_MARKETING.md` |
| `ecommerce_sintel/notifications/` | `ecommerce_sintel/notifications/.AGENT/docs/ARQUITECTURA_COMPLETA_NOTIFICATIONS.md` |
| `ecommerce_sintel/operations/` | `ecommerce_sintel/operations/.AGENT/docs/ARQUITECTURA_COMPLETA_OPERATIONS.md` |
| `ecommerce_sintel/orders/` | `ecommerce_sintel/orders/.AGENT/docs/ARQUITECTURA_COMPLETA_ORDERS.md` |
| `ecommerce_sintel/organization/` *(nueva, en construccion)* | `ecommerce_sintel/organization/.AGENT/docs/ARQUITECTURA_COMPLETA_ORGANIZATION.md` |
| `ecommerce_sintel/payment/` | `ecommerce_sintel/payment/.AGENT/docs/ARQUITECTURA_COMPLETA_PAYMENT.md` |
| `ecommerce_sintel/quotes/` | `ecommerce_sintel/quotes/.AGENT/docs/ARQUITECTURA_COMPLETA_QUOTES.md` |
| `ecommerce_sintel/renting/` | `ecommerce_sintel/renting/.AGENT/docs/ARQUITECTURA_COMPLETA_RENTIG.md` |
| `ecommerce_sintel/security/` | `ecommerce_sintel/security/.AGENT/docs/ARQUITECTURA_COMPLETA_SECURITY.md` |
| `ecommerce_sintel/shop/` | `ecommerce_sintel/shop/.AGENT/docs/ARQUITECTURA_COMPLETA_SHOP.md` |
| `ecommerce_sintel/support/` | `ecommerce_sintel/support/.AGENT/docs/ARQUITECTURA_COMPLETA_SUPPORT.md` |
| `ecommerce_sintel/technical_services/` | `ecommerce_sintel/technical_services/.AGENT/docs/ARQUITECTURA_COMPLETA_SERVICES.md` |
| `ecommerce_sintel/users/` | `ecommerce_sintel/users/.AGENT/docs/ARQUITECTURA_COMPLETA_USER.md` |
| `frontend/` | `frontend/.AGENT/doc/ARQUITECTURA_COMPLETAFRONEND.md` |
| `ai_engine/` | `ai_engine/.AGENT/FLIJO_COMPLETO_IA_ENGINE.md` |
| `docs/.AGENT/` (auditorias y guias cross-app) | `docs/.AGENT/GUIA_AI_ENGINE.md`, `docs/.AGENT/AUDITORIA_FLUJO_VENTA_PAGO_CONFIRMACION.md` |
| CORE v4 — certificacion arquitectura por dominios | `Documentacion/Arquitectura_general/MIGRACION_CORE_V4_DOMINIOS_FASE9_CERTIFICACION.md` (alcance real vs. backlog; ver `.AGENT.md` para el detalle) |

> Esta tabla debe coincidir linea por linea con la de `.AGENT.md` ("DOCUMENTOS DE REFERENCIA
> POR MODULO") — si agregas/renombras una app, actualiza ambos archivos en el mismo cambio
> (sincronizado por ultima vez 2026-07-12).

## FLUJO OBLIGATORIO ANTES DE MODIFICAR CÓDIGO (jerarquía de consulta)

Ver el detalle completo en `.AGENT.md` ("FLUJO OBLIGATORIO ANTES DE MODIFICAR CÓDIGO") —
resumen:

```
1. ecommerce_sintel/.AGENT.md          — SIEMPRE primero (reglas globales + tabla de arriba)
2. ecommerce_sintel/MEMORY.md          — contexto/continuidad entre sesiones
3a. App conocida  -> ir directo a su fila en la tabla de arriba
3b. App NO conocida -> Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md
4. Verificar patrones y convenciones del módulo ya localizado
5. Aplicar Karpathy Principles (sección 15 de .AGENT.md)
6. Implementar respetando: Service Layer, Soft-Delete, Snapshots, Permisos
```

## STACK

- **Backend:** Django 5 (5.2.13) + DRF + PostgreSQL + Redis + Celery + Channels
- **Frontend:** Vue.js 3 + Vite + Pinia + Vue Router + Axios
- **Auth:** JWT (simplejwt) — email como USERNAME_FIELD
- **Pagos:** Wompi Colombia
