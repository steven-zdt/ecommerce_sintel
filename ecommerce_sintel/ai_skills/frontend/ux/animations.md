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

## Popovers/dropdowns con animacion de entrada Y salida — usar clase CSS, NO `<Transition>` + `v-if`

**Bug real encontrado y corregido en verificacion en vivo (2026-07-31, `CommunicationPanel.vue`):**
un popover flotante (abre/cierra con un boton, tipo dropdown) implementado con
`<Transition name="x"><div v-if="open">...` se rompio de forma reproducible: las clases
`x-enter-from`/`x-leave-from`/`x-leave-active` quedaban aplicadas SIMULTANEAMENTE en el elemento,
que nunca se desmontaba (Vue esperando un `transitionend` que nunca terminaba de limpiar el
ciclo) — quedaba un `<div>` invisible (`opacity:0`) pero vivo en el DOM para siempre despues del
primer ciclo abrir/cerrar, con foco/accesibilidad potencialmente confundidos (un `role="dialog"`
fantasma). Reproducible incluso con pausas de 1-2s entre abrir y cerrar (no era una condicion de
carrera de toggles rapidos).

**Patron correcto para este caso (popover que vive dentro de un contenedor con `position:relative`
o `position:fixed`, alternado por un boton propio, sin necesitar desmontarse del DOM):** el
elemento vive SIEMPRE en el DOM, visibilidad controlada por clase CSS (`opacity` + `visibility` +
`pointer-events`, nunca `v-if`/`v-show` combinado con `<Transition>`):

```vue
<div class="popover" :class="{ 'popover--open': open }">...</div>
```
```css
.popover {
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: opacity .18s ease, visibility 0s linear .18s;
}
.popover--open {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
  transition: opacity .18s ease, visibility 0s linear 0s;
}
```

`visibility:hidden` ya saca los elementos interactivos de adentro del tab order en todos los
navegadores (no hace falta `tabindex="-1"` manual). Este patron evita por completo la clase de
bug de arriba, porque no depende de que Vue detecte un `transitionend` para desmontar nada — el
elemento nunca se desmonta.

**Cuándo SI usar `<Transition>` + `v-if`/`v-show`:** para elementos que genuinamente necesitan
desmontarse del DOM al cerrar (listas que se reordenan, contenido pesado que no debe quedar
montado innecesariamente, modales reales via `BaseModal.vue`). Un popover pequeño y liviano
(como el Centro de Comunicacion) no tiene esa necesidad — mantenerlo siempre montado es mas
simple y mas robusto.
