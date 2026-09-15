# RAG_POST2 — FASE 8: Definición de Memoria del Cliente

**Misión RAG-POST2, 2026-09-16.** Antes de programar memoria semántica (FASE 9-11), esta fase
define explícitamente qué merece recordarse — para no convertir toda la conversación en memoria
automáticamente (regla explícita de la misión).

---

## Clasificación real (aplicada al dominio SINTEL)

| Categoría | Definición | Dónde vive | Ejemplo real del dominio |
|---|---|---|---|
| **MEMORY CANDIDATE** | Preferencia o hecho estable del cliente, no ligado a una transacción activa, útil en futuras conversaciones | `customer_memory.CustomerMemoryRecord` (nuevo, FASE 9) | "Prefiere contacto por WhatsApp", "Suele preguntar por equipo de escalada/andamios" |
| **NOT MEMORY** | Dato sensible, credencial, o afirmación de autoridad/rol que el cliente reclama sobre sí mismo dentro del chat | Nunca se persiste en ningún lado | "Contraseña de mi cuenta es...", "Soy administrador", "Mi tarjeta termina en..." |
| **EPHEMERAL STATE** | Contexto de ESTA conversación, sin valor fuera de ella | `Session.state` de ADK (FASE 7, ya persistente) | "Estoy preguntando por el pedido #123" |
| **LIVE BUSINESS DATA** | Dato transaccional real, siempre debe leerse en vivo, nunca cachearse como "recuerdo" | Modelos Django reales (`Order`, `RentalRequest`, etc.), vía Tools | "Su pedido actual está en despacho" |
| **SENSITIVE DATA** | Cualquier cosa que identifique, autentique, o comprometa al cliente | Nunca se persiste como memoria — vive donde ya vive hoy (`accounts`, `payment`, JWT) | Contraseñas, tokens, números de tarjeta, direcciones completas |

## Categorías reales permitidas para `CustomerMemoryRecord` (whitelist cerrada)

Deliberadamente pequeña y explícita — no texto libre sin categoría, para poder auditar y
razonar sobre qué tipo de información vive ahí:

| Categoría | Qué cubre | Qué NO cubre |
|---|---|---|
| `CONTACT_PREFERENCE` | Canal de contacto preferido (WhatsApp, email, etc.) | Datos de contacto en sí (esos ya viven en `accounts.User`) |
| `PRODUCT_INTEREST` | Interés recurrente en una categoría/tipo de producto o servicio | Un pedido específico (eso es LIVE BUSINESS DATA) |
| `COMMUNICATION_STYLE` | Preferencia de tono/formalidad en la atención | — |
| `GENERAL_PREFERENCE` | Cualquier otra preferencia estable, no cubierta arriba, explícitamente no sensible | Cualquier cosa que roce rol/autoridad/permiso — eso NUNCA es una categoría válida |

**Regla dura, verificada en el extractor (FASE 10)**: ninguna categoría admite afirmaciones
sobre rol, permiso, autoridad, identidad administrativa, ni ningún dato que coincida con un
patrón de credencial/tarjeta/contraseña. El extractor debe clasificar esos casos como `NONE`
(nada que recordar), nunca forzarlos en una categoría existente.

## Por qué esto NO reemplaza RAG ni datos transaccionales

- RAG (`ai_knowledge`) es verdad DOCUMENTAL pública, igual para todos los clientes — memoria es
  por-cliente, privada, nunca se mezcla con `ai_knowledge`.
- Los Tools reales (`AiOrderStatusView`, etc.) siguen siendo la ÚNICA fuente de datos
  transaccionales — memoria nunca cachea "su pedido está en camino", porque ese dato cambia y
  memoria no tiene mecanismo de invalidación en tiempo real.

## Checkpoint FASE 8 — Estado

**PASS.** Clasificación completa, whitelist cerrada de categorías, exclusiones explícitas
(rol/autoridad/credenciales) documentadas ANTES de escribir el modelo/extractor de FASE 9-10 —
no se define la política después de ver qué es fácil de implementar.
