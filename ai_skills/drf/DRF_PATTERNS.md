---
description: "[STUB - DESACTUALIZADO] Esta carpeta (raiz del repo) NO se indexa en el AI Engine. La ubicacion viva es ecommerce_sintel/ai_skills/drf/. Ademas, la version anterior de este archivo tenia un ejemplo con request.user.role, que NO existe en el modelo User — corregido en la version nueva."
metadata:
  domain: root
  redirect: ../../ecommerce_sintel/ai_skills/drf/DRF_PATTERNS.md
---

# DRF_PATTERNS.md — ubicacion incorrecta y ejemplo corregido

Ver `ecommerce_sintel/ai_skills/drf/DRF_PATTERNS.md`. Ese archivo corrige un ejemplo de
`IsAdminUser` que usaba `request.user.role` — el modelo `User` no tiene campo `role` (ver
`[[project_users_accounts_refactor]]` en memoria); el admin real se identifica por
`is_staff=True AND is_superuser=True`. Este archivo se conserva solo como puntero.
