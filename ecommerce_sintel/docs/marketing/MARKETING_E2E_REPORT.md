# MARKETING_E2E_REPORT

Estado a 2026-09-24. Por decision del usuario, desde esta fecha las pruebas UI/E2E son MANUALES;
no se ejecutaron tests automatizados en esta pasada.

| Gate | Estado |
|---|---|
| 0 Baseline | PASS (docs/marketing/MARKETING_BASELINE.md) |
| 1 Create base | PASS (causa real: ruta `/panel/marketing` no registrada; corregida) |
| 2 CRUD | PASS salvo activar/desactivar (N/A, sin `is_active`) |
| 3 Producto/Servicio/Renting | PASS (verificado HTTP + tests en pasadas previas) |
| 4 Compuesta + desde cero | PASS |
| 5 Imagen + Video | PASS (video sin validar duracion) |
| 6 Canales | PASS en backend; UI Preview/Enviar agregada 2026-09-24, pendiente de verificacion manual |
| 7 UI Smoke | PENDIENTE (manual) |
| 8 Documentacion | PASS |

## Checklist manual sugerido (http://localhost:5173/panel/marketing)
1. Nueva campana desde catalogo: producto x2 + beneficios transporte/instalacion gratis + imagen + video.
2. Recargar: persiste. Editar un texto: la galeria no cambia.
3. Icono enviar (avion): preview por canal coincide con el envio; enviar por email con destinatario
   autorizado; verificar log `marketing_event=...` y `CampaignLog`.
4. Desde cero, Servicio, Renting; archivo invalido/MIME falso rechazado; cliente no-admin recibe 403.
