# WHATSAPP_QR_SESSION

**Misión "Migración Arquitectónica de WhatsApp", 2026-09-16.**

## Clasificación explícita (Regla dura de la misión, FASE 7)

```
QR Web Session = EXPERIMENTAL
                = THIRD-PARTY
                = NON-OFFICIAL META API
```

**Nunca** describir esto como "API oficial por QR" — no lo es. Es una simulación de sesión de
WhatsApp Web usando una librería de terceros que automatiza/reimplementa el protocolo no
publicado de WhatsApp.

## Estado real (2026-09-16)

**BLOQUEADO para el número de producción real de SINTEL.** Ver
`AUDITORIA/WHATSAPP_QR_PROVIDER_EVALUATION.md` (FASE 8) para la evaluación completa de
proveedores (Baileys, whatsapp-web.js) y el razonamiento del bloqueo — en resumen: el número real
de SINTEL ya tiene Meta Cloud API oficial activa, y conectar una librería no oficial al mismo
número viola los Términos de Servicio de WhatsApp Business, arriesgando perder también la
integración oficial ya funcionando.

## Arquitectura real construida (independiente de la decisión de negocio)

- `whatsapp/adapters/qr_web_session_adapter.py::QRWebSessionAdapter` — cumple
  `WhatsAppConnectionPort` en su totalidad, fail-loud explícito (`WhatsAppQRNotImplementedError`)
  en cada método real.
- `whatsapp/adapters/session_manager.py::WhatsAppSessionManager` — máquina de estados real (10
  estados: `DISABLED`, `NOT_CONFIGURED`, `QR_REQUIRED`, `QR_READY`, `SCANNING`,
  `AUTHENTICATING`, `CONNECTED`, `RECONNECTING`, `DISCONNECTED`, `ERROR`), con transiciones
  válidas explícitas — lista para conectar un gateway real sin rediseño, si algún día se
  autoriza.
- Capacidades declaradas: `qr_pairing=True`, `polling=True` (típico de estos gateways),
  `session_persistence=False` (una sesión de navegador no sobrevive un reinicio sin trabajo
  adicional que no existe hoy), resto `False` — honesto, no aspiracional.

## Qué se necesitaría para activar esto de verdad (documentado, no ejecutado)

1. Decisión de negocio explícita aceptando el riesgo (ver evaluación de proveedores).
2. Un número de WhatsApp **separado** del número de producción real — nunca el mismo.
3. Un microservicio Node.js nuevo (Baileys o whatsapp-web.js no tienen equivalente Python maduro)
   — nuevo contenedor Docker, nuevo runtime, nueva superficie de mantenimiento.
4. Persistencia real de la sesión (archivo de credenciales multi-device o perfil de navegador) —
   hoy `session_persistence=False` porque no hay nada que persistir.
5. Implementar los métodos reales de `QRWebSessionAdapter` (`connect`, `send_message`,
   `generate_pairing_qr`, `translate_inbound`) contra el gateway elegido.
6. Conectar `WhatsAppSessionManager` a las transiciones reales que ese gateway reporte.

## Seguridad específica de este mecanismo (si algún día se activa)

- La sesión de un gateway QR real equivale a tener acceso completo a la cuenta de WhatsApp — el
  archivo/token de sesión debe protegerse igual que una credencial (nunca en logs, nunca en el
  frontend, cifrado en reposo).
- `logout()` (FASE 32 de la misión) debe invalidar la sesión real, no solo el estado en memoria.
- Nunca exponer el endpoint de generación de QR fuera del panel admin protegido.
