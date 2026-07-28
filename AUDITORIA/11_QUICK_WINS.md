# 11 — QUICK WINS
**Cambios de alto impacto y bajo riesgo — ejecutables en menos de 2 horas cada uno**  
**Fecha:** 2026-07-16

> ✅ **16/17 EJECUTADOS — sincronizado 2026-07-27.** QW-01 a QW-16 confirmados en
> `12_CHECKLIST_IMPLEMENTACION.md` (SPRINT 0-4) y `01_AUDITORIA_GENERAL.md`. **QW-17 (JWT
> `ACCESS_TOKEN_LIFETIME` a 15 min) no aparece marcado `[x]` en ningún checklist posterior — sigue
> abierto** (ver también `06_SEGURIDAD.md` SEC-M3, misma conclusión).

---

## Prioridad 1 — Seguridad (hacer hoy)

### QW-01 — Fix `IsAdminUser` en inventory (15 min)
**Impacto:** Seguridad crítica  
**Archivo:** `inventory/api/views.py:41, 145`

```python
# Cambiar:
from rest_framework import permissions
return [permissions.IsAdminUser()]

# A:
from users.api.permissions import IsAdminUser
return [IsAdminUser()]
```

### QW-02 — Remover `integrity_signature` de respuestas (30 min)
**Impacto:** Seguridad crítica — previene bypass de verificación Wompi  
**Archivos:** `payment/online/api/serializers.py:10`, `payment/online/api/views.py:335`

```python
# serializers.py — quitar del fields list:
# 'integrity_signature'  # eliminar esta línea

# views.py:335 — quitar de la respuesta:
# "integrity_signature": wompi_tx.integrity_signature  # eliminar
```

### QW-03 — Restringir inventory list/retrieve a admins (15 min)
**Impacto:** Seguridad alta — stock de toda la empresa visible a compradores  
**Archivo:** `inventory/api/views.py:42`

```python
return [IsAdminUser()]  # era: [permissions.IsAuthenticated()]
```

### QW-04 — Agregar rate limiting al AdminLoginView (30 min)
**Impacto:** Seguridad alta — previene brute force en superusuarios  
**Archivo:** `users/api/admin_auth.py`

```python
from rest_framework.throttling import ScopedRateThrottle

class AdminLoginView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'admin_login'

# En settings/base.py, agregar en DEFAULT_THROTTLE_RATES:
'admin_login': '5/hour'
```

### QW-05 — Bloquear /internal/ en nginx (15 min)
**Impacto:** Seguridad alta — endpoints AI accesibles externamente  
**Archivo:** `ecommerce_sintel/nginx-common.conf`

```nginx
# Agregar ANTES de location /:
location /api/v1/internal/ {
    deny all;
    return 403;
}
```

### QW-06 — Restringir /api/schema/ y /api/docs/ (15 min)
**Impacto:** Seguridad media — contrato API expuesto  
**Archivo:** `ecommerce/urls.py:29-30`

```python
from users.api.permissions import IsAdminUser

path('api/schema/', SpectacularAPIView.as_view(
    permission_classes=[IsAdminUser]
), name='schema'),
path('api/docs/', SpectacularSwaggerView.as_view(
    url_name='schema', permission_classes=[IsAdminUser]
), name='swagger-ui'),
```

---

## Prioridad 2 — Bugs funcionales (hacer esta semana)

### QW-07 — Fix ruta `/panel/ordenes/renting` inaccesible (5 min)
**Impacto:** Funcional crítico — RentalOperationBoard permanentemente inaccesible  
**Archivo:** `src/apps/admin/router.js`

```javascript
// Mover la ruta estática ANTES de la dinámica:
{ path: 'ordenes/renting', name: 'renting-operations', component: RentalOperationBoard },
{ path: 'ordenes/:uuid',   name: 'order-detail',       component: OrderDetailView },
```

### QW-08 — Eliminar `alert()` de debug en AppShell.vue (5 min)
**Impacto:** UX — debug visible en producción  
**Archivo:** `src/components/layout/AppShell.vue:48`

Eliminar la línea `@click="() => alert('Global Debug Triggered')"` o el elemento que la contiene.

### QW-09 — `unique_together` en `ServiceReview` + migración (30 min)
**Impacto:** Integridad de datos — permite reseñas duplicadas por usuario/servicio  
**Archivo:** `technical_services/models.py:180-187`

```python
class Meta:
    unique_together = ('user', 'service')
```

Generar migración: `python manage.py makemigrations technical_services`

### QW-10 — `db_index=True` en `Quotation.status` + migración (15 min)
**Impacto:** Rendimiento — table-scan en filtros del admin CPQ  
**Archivo:** `quotes/models.py:44`

```python
status = models.CharField(max_length=25, db_index=True, ...)
```

### QW-11 — Fix N+1 en `ShipmentOrderSummarySerializer.get_items_count` (30 min)
**Impacto:** Rendimiento — 1 COUNT por envío en el panel de operaciones  
**Archivo:** `orders/api/serializers.py:130`

```python
# Cambiar:
return obj.items.filter(variant__isnull=False).count()
# A:
return sum(1 for i in obj.items.all() if i.variant_id is not None)
```

### QW-12 — Fix N+1 en `FooterGroupSerializer.get_links_count` (30 min)
**Archivo:** `core/api/serializers.py:440` + selector

```python
# En el selector: .prefetch_related('links')
# En el serializer:
return sum(1 for l in obj.links.all() if not l.is_deleted)
```

---

## Prioridad 3 — Limpieza (esta semana, bajo riesgo)

### QW-13 — Eliminar código muerto en frontend (1 hora)
- `components/shared/CostRulesView.vue` — 12KB sin importadores
- `components/ui/PriceBreakdown.vue` — sin importadores
- `views/customer/renting/RentingCatalogView.vue` — wrapper de 2 líneas sin ruta
- `views/customer/renting/EquipmentDetailView.vue` — wrapper de 2 líneas sin ruta
- `src/shared/` — directorio vacío
- Línea de Colombia locations duplicada en `ColombianAddressForm.vue:228`

### QW-14 — Agregar `@transaction.atomic` a Commands sin él (1 hora)
**Archivos con prioridad más alta:**
- `users/services/commands.py`: `change_password`, `request_email_verification`, `resend_email_verification`
- `payment/online/services/commands.py`: `initialize_transaction`
- `support/services/commands.py`: `get_or_create_room`, `mark_messages_read`

### QW-15 — Mover `_log_ai_action()` a módulo compartido (30 min)
Crear `ecommerce_sintel/ecommerce/internal_ai_utils.py`:
```python
def log_ai_action(request, tool: str, metadata: dict) -> None:
    from security.models import SecurityEvent
    from security.services.commands import SecurityCommands
    SecurityCommands.log_event(SecurityEvent.AI_ACTION_EXECUTED,
                               request=request, metadata={'tool': tool, **metadata})
```
Importar desde los archivos `internal_ai.py` en vez de redefinirla.

### QW-16 — `SuccessCase` upload: agregar `magic_bytes_check=True` (15 min)
**Archivo:** `accounts/services/commands.py:733`
```python
validate_file(img_file, max_size_mb=5,
              allowed_extensions=['.jpg', '.jpeg', '.png'],
              magic_bytes_check=True)  # AGREGAR
```

### QW-17 — Reducir `ACCESS_TOKEN_LIFETIME` a 15 minutos (5 min)
**Estado (2026-07-27): 🔶 Sigue abierto** — no confirmado en ningún checklist posterior; verificar valor actual en `ecommerce/settings/base.py` antes de asumir.
**Archivo:** `ecommerce/settings/base.py`
```python
'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),  # era 60
```

---

## Resumen por Esfuerzo Total

| Prioridad | Items | Tiempo Total |
|---|---|---|
| Seguridad (hacer hoy) | 6 | ~2h |
| Bugs funcionales | 5 | ~1.5h |
| Limpieza | 6 | ~3.5h |
| **TOTAL** | **17 quick wins** | **~7h** |

**ROI:** 7 horas de trabajo resuelven 4 hallazgos críticos de seguridad, 1 bug de funcionalidad bloqueante, 2 N+1 de rendimiento, 1 vulnerabilidad de integridad de datos, y eliminan ~15KB de código muerto.
