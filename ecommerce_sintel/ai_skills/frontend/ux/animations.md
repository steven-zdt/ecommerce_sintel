---
description: Transiciones y micro-interacciones establecidas en el proyecto.
metadata:
  domain: ux
  supersedes: FRONTEND_UI_RULES.md (seccion 7)
---

# Animations

| Elemento | Transicion |
|---|---|
| Links de sidebar | `all .18s ease` |
| Hover link sidebar | `transform: translateX(4px)` |
| Toggle grupo sidebar | `all .18s ease` |
| Offcanvas panel | `transform .3s ease-in-out` |
| Offcanvas backdrop | Bootstrap fade |
| User pill footer | `background .2s` |
| Dot de modulo | `opacity .18s, box-shadow .18s` |
| Navbar search | width `320px → 400px` on focus |

**Regla:** usar `cubic-bezier(.4,0,.2,1)` (Material Design ease) para transiciones de elementos de
navegacion, `.18s ease` para micro-interacciones en tablas/formularios.

## Animaciones especificas de landing (no aplican al panel admin)

- `SectionHeader`, `ModuleCard`, `TrustCard`: animacion "reveal" activada por prop `visible`,
  disparada por `IntersectionObserver` propio del componente padre (`ModuleGrid`, `FlashOffers`,
  `TrustSection`).
- `AnimatedCounter`: count-up con `requestAnimationFrame` + easing `easeOutExpo` en 1.6s al
  entrar en viewport.
- `CountdownTimer`: `setInterval` propio iniciado en `onMounted`, limpiado en `onUnmounted` —
  patron a seguir si se agrega otro timer aislado.

Detalle de estos componentes: [../components/cards.md](../components/cards.md#3-landing-page--srccomponentsuilanding).

No hay una libreria de animacion (GSAP, Motion One, etc.) instalada — todo es CSS transitions +
`IntersectionObserver`/`requestAnimationFrame` nativos.
