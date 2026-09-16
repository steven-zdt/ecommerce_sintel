# WHATSAPP_QR_PROVIDER_EVALUATION — FASE 8

**Misión "Migración Arquitectónica de WhatsApp", 2026-09-16.** Evaluación real de proveedores QR
antes de instalar cualquier librería — tal como exige explícitamente la FASE 8 de esta misión:
"No utilizar automatización frágil de navegador si existe una alternativa más estable. No
inventar APIs. No declarar soporte si no existe."

---

## Candidatos reales evaluados

| Proveedor | Mecanismo | Licencia | Mantenimiento | Riesgo real |
|---|---|---|---|---|
| **Baileys** (WhiskeySockets/Baileys) | Reimplementa el protocolo WebSocket de WhatsApp Web Multi-Device (reverse-engineered, sin browser) | MIT | Activo históricamente, pero depende de seguir el ritmo de cambios internos de Meta — se rompe cada vez que Meta actualiza el protocolo, sin aviso ni SLA | Alto — no oficial, viola explícitamente los Términos de Servicio de WhatsApp Business |
| **whatsapp-web.js** | Automatiza un Chrome headless real vía Puppeteer, controlando la web real de WhatsApp | Apache-2.0 | Activo, pero más pesado (requiere Chromium completo por sesión) y más frágil (crashes de navegador, fugas de memoria en sesiones largas) | Alto — mismo problema de ToS, más consumo de recursos |
| **venom-bot / otros wrappers de Puppeteer** | Similar a whatsapp-web.js | Vario | Generalmente menos activo que los 2 anteriores | Alto, mismo perfil |
| **Alternativa Python nativa madura** | — | — | **No existe** una librería Python de nivel de producción equivalente — las opciones históricas (`yowsup`) están abandonadas y usan el protocolo viejo de WhatsApp (pre-Multi-Device), no funcional hoy | N/A |

## Riesgo real específico de SINTEL (no genérico — evaluado contra el estado real del proyecto)

Este es el factor decisivo, verificado contra el estado real del sistema, no una consideración
teórica genérica:

1. **SINTEL ya tiene una integración oficial de Meta Cloud API REAL, activa, en PRODUCCIÓN**,
   verificada end-to-end esta misma sesión, atendiendo clientes reales sobre el **mismo número de
   negocio real**.
2. **Conectar ese mismo número a una librería QR no oficial (Baileys/whatsapp-web.js) viola
   directamente los Términos de Servicio de WhatsApp Business** — no es solo "riesgo de baneo
   genérico", es una violación contractual real sobre una cuenta que YA está aprobada y
   funcionando oficialmente.
3. **Si Meta banea el número por la actividad no oficial, se pierde TAMBIÉN la integración
   oficial que ya funciona** — el riesgo no está aislado al canal experimental, contamina el
   canal real de producción.
4. **Usar un número DISTINTO** (aislado, desechable) para experimentar con QR evita el riesgo de
   contaminar el canal oficial, pero entonces dejan de ser "el mismo WhatsApp de soporte" desde
   la perspectiva del cliente — dos números de WhatsApp distintos, uno oficial y uno
   experimental, sin unificación real posible sin confundir al cliente.
5. **Costo de infraestructura real**: Baileys/whatsapp-web.js son Node.js — este proyecto es
   100% Python/Django/Celery. Integrarlos exige un microservicio Node.js nuevo (contenedor
   Docker nuevo, runtime nuevo, superficie de mantenimiento nueva, alguien con conocimiento de
   Node.js para mantenerlo) por una capacidad que la integración oficial YA cubre por completo
   (texto, webhooks, estado de entrega).

## Conclusión real de esta fase

**BLOQUEADO para el número de producción real de SINTEL.** No se instala ninguna librería QR
contra el número real de negocio — el riesgo (perder la integración oficial ya funcionando, por
una capacidad que no aporta nada nuevo) supera cualquier beneficio real medible.

**No se descarta la arquitectura** — `QRWebSessionAdapter` queda construido estructuralmente
(mismo contrato, mismo nivel de detalle que `MetaCloudAPIAdapter`, con el `WhatsAppSessionManager`
de estados reales que pide FASE 9), pero **sin conectar ningún gateway real**, exactamente el
mismo criterio ya aplicado en la misión anterior — fail-loud explícito, nunca simulado.

## Condición para reabrir esta decisión

Si en el futuro se decide experimentar con QR de verdad, la recomendación técnica es:
1. Usar un número de WhatsApp **completamente separado** del número de producción real (nunca el
   mismo WABA/número).
2. Empezar con Baileys (más liviano, sin Chromium) en un entorno de prueba aislado, nunca contra
   tráfico de clientes reales.
3. Aceptar explícitamente, como decisión de negocio, el riesgo de que ese número secundario sea
   baneado en cualquier momento sin aviso de Meta.

Esta decisión requiere autorización explícita del usuario — no se toma unilateralmente en esta
sesión, dado el riesgo real sobre un canal de producción activo.

## Checkpoint FASE 8

**PASS, con conclusión BLOCKED documentada explícitamente** (no simulada, no evadida). El resto
de la misión procede construyendo `QRWebSessionAdapter`/`WhatsAppSessionManager` estructuralmente
completos, honestos sobre `NOT_IMPLEMENTED`/`DISABLED`, exactamente como permite la propia FASE 8:
"Si no existe una solución QR técnicamente aceptable: documentar... y mantener preparado el port
sin fingir funcionalidad."
