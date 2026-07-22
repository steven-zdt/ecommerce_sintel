---
trigger: always_on
description: Protocolo maestro de ejecucion IA para Sintel E-Commerce. Rige toda interaccion sin excepcion.
---

# PROTOCOLO DE EJECUCION — Sintel E-Commerce

> Este archivo rige COMO trabajas. El QUE (reglas tecnicas) vive en `.AGENT.md`.
> No dupliques reglas aqui: enlaza a la fuente de verdad.

## FUENTE DE VERDAD (leer segun corresponda)

1. `.AGENT.md` (raiz) — reglas y estandares globales del proyecto. Seccion 14 = Karpathy Principles.
2. `ecommerce_sintel/<app>/CLAUDE.md` — carga el doc de arquitectura de esa app.
3. `ecommerce_sintel/<app>/.AGENT/docs/ARQUITECTURA_COMPLETA_*.md` — detalle del modulo.

---

## EL BUCLE OBLIGATORIO (5 fases, en orden, sin saltar)

Ante CUALQUIER prompt, ejecuta este ciclo. No empieces a escribir codigo antes de la FASE 2.

### FASE 0 — INGESTA (entender el prompt)
- Reformula en 1-2 frases lo que el usuario pide. Confirma que entendiste.
- Declara tus SUPOSICIONES explicitamente (Karpathy P1).
- Si hay ambiguedad real o multiples interpretaciones: **DETENTE y pregunta** antes de codificar.
- Si existe un enfoque mas simple: proponlo.

### FASE 1 — CONTEXTO (cargar lo necesario, nada mas)
- Identifica que app(s) toca la tarea.
- Lee el `CLAUDE.md` de esa app y su doc de arquitectura.
- Lee `.AGENT.md` solo si la tarea cruza varios modulos.
- Verifica patrones del modulo: Service Layer, Soft-Delete, Snapshots, Permisos, UUID lookup.

### FASE 2 — PLAN (detallar antes de actuar)
- Produce un PLAN numerado. Cada paso DEBE tener un criterio de exito verificable (Karpathy P4).
- Preséntalo como CHECKLIST (formato `- [ ]`).
- Ejemplo de paso bien definido:
  `- [ ] Agregar campo phone_number a UserProfile -> verificar: migracion sin errores`
- Pasos vagos ("que funcione") estan PROHIBIDOS.

### FASE 3 — EJECUCION (tarea por tarea)
- Ejecuta UNA tarea del checklist a la vez. No avances a la siguiente sin cerrar la actual.
- Marca cada item como completado (`- [x]`) en cuanto lo verificas.
- Cambios QUIRURGICOS (Karpathy P3): toca solo las lineas necesarias. No refactorices lo que no esta roto. No "mejores" codigo adyacente.
- Codigo MINIMO (Karpathy P2): sin features, abstracciones ni configurabilidad no pedidas.
- Cada linea cambiada debe trazarse directamente a la solicitud del usuario.

### FASE 4 — VERIFICACION (cerrar con evidencia)
- Verifica el criterio de exito de cada tarea Y del objetivo global.
- Comandos de verificacion segun el cambio:
  - Python: `python -m py_compile <archivo>.py` y `python manage.py check`
  - Si hay contenedor: `docker compose exec django python manage.py check`
  - Frontend: revisar diagnosticos del IDE (sin variables declaradas-no-usadas).
- Elimina SOLO los huerfanos que TUS cambios generaron (imports/vars sin uso).
- Reporta codigo muerto pre-existente que notes — NO lo borres.
- Reporta resultados con honestidad: si algo fallo o se omitio, dilo con la evidencia.

---

## REGLAS DURAS (no negociables, ver `.AGENT.md` para el detalle)

- [PROHIBIDO] Emojis o caracteres Unicode/multibyte en archivos `.py` (rompen Django -> 500).
- Soft-delete siempre: nunca DELETE fisico. `is_active=False` + `is_deleted=True` segun el caso.
- Selectores de admin filtran `is_deleted=False`.
- Logica de negocio en `services/commands.py` (escritura) y `services/selectors.py` (lectura), nunca en vistas.
- `lookup_field = 'uuid'` — nunca `pk` en URLs.
- `Decimal` para dinero, nunca `float`.
- Frontend: siempre `useApi()`, nunca `axios` directo; debounce 400ms en busqueda; `<script setup>`.
- No cambiar `DJANGO_SETTINGS_MODULE` ni elevar a produccion sin instruccion explicita.

---

## RESUMEN OPERATIVO (pegar mentalmente en cada tarea)

```
ENTENDER  -> reformula + declara suposiciones (pregunta si hay duda)
CONTEXTO  -> lee CLAUDE.md de la app + arquitectura
PLAN      -> checklist numerado, cada paso con criterio verificable
EJECUTAR  -> una tarea a la vez, cambios quirurgicos, marca [x] al cerrar
VERIFICAR -> py_compile / manage.py check, limpia tus huerfanos, reporta honesto
```
