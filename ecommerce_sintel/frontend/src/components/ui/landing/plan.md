# Landing Page Premium — Plan de Arquitectura Enterprise
**Fecha:** 2026-06-28 | **Target:** `http://localhost:5173/` → `HomeView.vue`  
**Referentes visuales:** Stripe · Vercel · Linear · Notion · Cisco · Framer

---

## VISIÓN DE DISEÑO

> La landing debe comunicar en menos de 3 segundos:
> **"Somos tecnología seria, segura y de nivel enterprise."**
>
> El usuario debe sentir la misma confianza que siente al entrar a stripe.com o linear.app.
> No debe ver un e-commerce. Debe ver una plataforma tecnológica corporativa.

---

## 1. ÁRBOL DE COMPONENTES

```
HomeView.vue  ← orquestador puro (fetch + props, cero estilos de sección)
│
├── landing/HeroSection.vue               (A)
│   ├── landing/HeroBackground.vue        (A.1) — capa bg: video/imagen/gradiente animado
│   ├── landing/HeroSlide.vue             (A.2) — contenido de 1 slide: título + sub + CTA
│   └── landing/HeroCTA.vue              (A.3) — botones primary/ghost + eyebrow badge
│
├── landing/SectionHeader.vue            (B) — REUTILIZABLE en todas las secciones
│
├── landing/ModuleGrid.vue               (C) — grid de módulos de negocio
│   └── landing/ModuleCard.vue           (C.1)
│
├── landing/FlashOffers.vue              (D) — sección ofertas con fondo oscuro
│   ├── landing/FlashOfferCard.vue       (D.1)
│   └── landing/CountdownTimer.vue       (D.2) — reloj aislado con su propio timer
│
├── landing/FeaturedSection.vue          (E) — wrapper reutilizable: productos/equipos/servicios
│   ├── landing/FeaturedCarousel.vue     (E.1) — scroll horizontal con snap
│   └── landing/FeaturedCard.vue        (E.2)
│
├── landing/TrustSection.vue             (F) — home_cards agrupadas (= "¿Por qué elegirnos?")
│   └── landing/TrustCard.vue           (F.1)
│
├── landing/AnimatedCounter.vue          (G) — stats numéricas con animación count-up
│
├── landing/FooterCTA.vue               (H) — bloque CTA final antes del footer real
│
├── landing/GlassCard.vue               (I) — componente base REUTILIZABLE glassmorphism
│
├── landing/DividerWave.vue             (J) — separadores SVG curvos entre secciones
│
└── landing/LoadingSkeleton.vue         (K) — skeleton configurable con shimmer
```

**Total: 18 componentes** en `src/components/ui/landing/`.  
`HomeView.vue` importa solo los 9 componentes de nivel 1 (no los subcomponentes).

---

## 2. FLUJO DE DATOS

```
HomeView.vue
  │
  ├── onMounted → api.get('core/home-feed/')
  │     └── { banners, modules, flash_offers, featured_products,
  │            featured_equipment, featured_services, home_cards }
  │
  ├── onMounted → api.get('core/site-config/')
  │     └── { brand: { site_name, logo, tagline }, navbar_links }
  │
  └── loading = ref(true) → false en finally

PROPS hacia hijos (ninguno hace fetch propio):
  HeroSection       ← banners[], loading
  ModuleGrid        ← modules[], loading
  FlashOffers       ← offers[], loading
  FeaturedSection   ← items[], type, title, link, loading  (×3 instancias)
  TrustSection      ← cards[], loading
  FooterCTA         ← brand.site_name, brand.tagline
  AnimatedCounter   ← stats[] (calculados en HomeView desde los datos)
```

**Regla de oro:** ningún componente hijo llama a `useApi()`.  
Todo el estado viene de HomeView.vue como props.

---

## 3. SISTEMA DE DISEÑO — VARIABLES CSS GLOBALES

Las variables van en `:root` del `<style scoped>` de `HomeView.vue` para propagar via herencia CSS:

```css
:root {
  /* ── Colores core ───────────────────────────────────── */
  --c-bg:           #ffffff;
  --c-bg-subtle:    #f8fafc;
  --c-bg-dark:      #080d1a;          /* hero, flash offers */
  --c-bg-dark-2:    #0d1526;          /* cards sobre oscuro */

  --c-primary:      #2563eb;          /* azul corporativo */
  --c-primary-d:    #1d4ed8;          /* hover state */
  --c-primary-glow: rgba(37,99,235,.28);
  --c-electric:     #06b6d4;          /* acento cian */
  --c-violet:       #7c3aed;          /* acento secundario */

  /* ── Texto ──────────────────────────────────────────── */
  --t-900:  #0a0f1e;
  --t-700:  #1e293b;
  --t-500:  #475569;
  --t-400:  #64748b;
  --t-300:  #94a3b8;
  --t-inv:  #ffffff;
  --t-inv-m: rgba(255,255,255,.72);   /* muted sobre oscuro */
  --t-inv-s: rgba(255,255,255,.45);   /* subtle sobre oscuro */

  /* ── Glassmorphism ──────────────────────────────────── */
  --glass-dark-bg:     rgba(255,255,255,.065);
  --glass-dark-border: rgba(255,255,255,.11);
  --glass-light-bg:    rgba(255,255,255,.72);
  --glass-light-border:rgba(255,255,255,.45);
  --glass-blur:        blur(14px) saturate(180%);

  /* ── Sombras ────────────────────────────────────────── */
  --shadow-xs: 0 1px 3px rgba(0,0,0,.04);
  --shadow-sm: 0 2px 10px rgba(0,0,0,.06);
  --shadow-md: 0 4px 20px rgba(0,0,0,.08), 0 1px 4px rgba(0,0,0,.04);
  --shadow-lg: 0 12px 40px rgba(0,0,0,.10), 0 3px 10px rgba(0,0,0,.06);
  --shadow-xl: 0 24px 64px rgba(0,0,0,.13), 0 6px 16px rgba(0,0,0,.07);
  --shadow-glow-p: 0 0 48px rgba(37,99,235,.22);
  --shadow-glow-e: 0 0 48px rgba(6,182,212,.18);

  /* ── Bordes / radios ────────────────────────────────── */
  --r-sm:   8px;
  --r-md:   14px;
  --r-lg:   20px;
  --r-xl:   28px;
  --r-full: 9999px;
  --border-subtle: 1px solid rgba(0,0,0,.06);
  --border-subtle-dark: 1px solid rgba(255,255,255,.09);

  /* ── Transiciones ───────────────────────────────────── */
  --tr-fast:    150ms ease;
  --tr-base:    250ms ease;
  --tr-smooth:  380ms cubic-bezier(0.16, 1, 0.3, 1);
  --tr-bounce:  500ms cubic-bezier(0.34, 1.56, 0.64, 1);

  /* ── Espaciados sección ─────────────────────────────── */
  --s-section-v: clamp(4rem, 8vw, 7rem);
  --s-section-sm: clamp(2rem, 4vw, 3.5rem);
}
```

---

## 4. TIPOGRAFÍA — JERARQUÍA

| Token | Tamaño | Peso | Uso |
|-------|--------|------|-----|
| `.t-hero` | `clamp(2.8rem, 6vw, 5.5rem)` | 800 | Título del Hero |
| `.t-hero-sub` | `clamp(1rem, 2vw, 1.3rem)` | 400 | Subtítulo Hero |
| `.t-section` | `clamp(1.75rem, 3.5vw, 2.75rem)` | 700 | Título sección |
| `.t-section-sub` | `1rem` | 400 | Descripción sección |
| `.t-card-title` | `1rem–1.1rem` | 700 | Título de card |
| `.t-caption` | `.72rem` | 600 | Labels, badges |
| `.t-eyebrow` | `.72rem` + `letter-spacing: 2px` | 700 | Eyebrow pill labels |

**Line-height:** 1.08 hero · 1.25 títulos · 1.6 cuerpo  
**Color texto:** siempre `var(--t-900)` en claro · `var(--t-inv)` en oscuro

---

## 5. ESTRATEGIA DE ANIMACIONES

### Principio: CSS first, JS solo para trigger

**Sin librerías externas.** El sistema se basa en:

1. **IntersectionObserver** (nativo, en `onMounted` de cada componente)
2. **Clase `.visible`** que activa la animación CSS
3. **`@keyframes`** y `transition` en CSS
4. **`will-change: transform, opacity`** solo en elementos animados

### Patrón universal de reveal

```css
/* Base: elemento invisible */
.reveal-up {
  opacity: 0;
  transform: translateY(32px);
  transition: opacity 0.65s var(--tr-smooth),
              transform 0.65s var(--tr-smooth);
}
.reveal-fade {
  opacity: 0;
  transition: opacity 0.65s ease;
}
/* Activado por JS al cruzar viewport */
.reveal-up.visible,
.reveal-fade.visible {
  opacity: 1;
  transform: translateY(0);
}
/* Stagger via delay en hijos */
.reveal-up:nth-child(1) { transition-delay: 0ms; }
.reveal-up:nth-child(2) { transition-delay: 80ms; }
.reveal-up:nth-child(3) { transition-delay: 160ms; }
.reveal-up:nth-child(4) { transition-delay: 240ms; }
```

### Activación via IntersectionObserver (en el componente)

```js
// onMounted de cada componente raíz
const el = ref(null)
const visible = ref(false)
onMounted(() => {
  const obs = new IntersectionObserver(
    ([e]) => { if (e.isIntersecting) { visible.value = true; obs.disconnect(); } },
    { threshold: 0.12 }
  );
  if (el.value) obs.observe(el.value);
});
```

### Animaciones por componente

| Componente | Animación |
|-----------|-----------|
| HeroSection | fade-in + slide-up del texto (sin observer, siempre visible) |
| HeroBackground | Ken Burns suave en imagen (scale 1→1.06, 8s) |
| ModuleCard | slide-up con stagger (0ms, 80ms, 160ms…) |
| FlashOfferCard | fade + slide desde derecha |
| FeaturedCard | scale 0.96→1 + fade |
| TrustCard | slide-up con stagger |
| AnimatedCounter | count-up al entrar en viewport |
| SectionHeader | fade + slide-up |
| FooterCTA | fade + glow del botón |

### Efectos permanentes (CSS pure, sin JS)

```css
/* Hover lift + glow en cards */
.module-card:hover {
  transform: translateY(-6px) scale(1.02);
  box-shadow: var(--shadow-lg), var(--shadow-glow-p);
}

/* Animated gradient border */
.border-gradient {
  background: linear-gradient(var(--c-bg), var(--c-bg)) padding-box,
              linear-gradient(135deg, var(--c-primary), var(--c-electric)) border-box;
  border: 1.5px solid transparent;
}

/* Pulse ring en indicadores de urgencia */
@keyframes pulse-ring {
  0%  { box-shadow: 0 0 0 0 rgba(239,68,68,.7); }
  70% { box-shadow: 0 0 0 10px rgba(239,68,68,0); }
}

/* Shimmer para skeletons */
@keyframes shimmer {
  0%   { background-position: -1000px 0; }
  100% { background-position: 1000px 0; }
}

/* Ken Burns hero */
@keyframes ken-burns {
  0%   { transform: scale(1); }
  100% { transform: scale(1.06); }
}

/* Float para elementos decorativos */
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50%       { transform: translateY(-12px); }
}

/* Glow pulse */
@keyframes glow-pulse {
  0%, 100% { opacity: .6; }
  50%       { opacity: 1; }
}
```

---

## 6. ESTRATEGIA DE LOADING (Skeletons)

**Principio:** cada componente renderiza su propio skeleton.  
`HomeView` pasa `:loading="loading"` a todos. No hay spinner global.

### `LoadingSkeleton.vue` — Componente configurable

```
Props:
  width:   String  — '100%' | '200px'
  height:  String  — '20px' | '200px'
  radius:  String  — '8px' | 'full'
  dark:    Boolean — shimmer en modo oscuro (para secciones dark)
  count:   Number  — cuántas líneas/bloques repetir
```

### Skeletons por sección

| Sección | Skeleton |
|---------|----------|
| HeroSection | bloque 80vh oscuro + 3 líneas de texto + 2 botones |
| ModuleGrid | 4 tarjetas rectangulares en fila, 130px alto |
| FlashOffers | 2 tarjetas oscuras 110px alto con shimmer invertido |
| FeaturedSection | 3 tarjetas 280px alto en fila |
| TrustSection | cabecera + 6 tarjetas 140px |
| FooterCTA | bloque 200px con texto centrado |

---

## 7. ESTRATEGIA RESPONSIVE — Mobile First

**Breakpoints Bootstrap 5.3.3:**

| Token | px | Uso |
|-------|----|-----|
| `xs` | <576 | Mobile portrait |
| `sm` | 576 | Mobile landscape |
| `md` | 768 | Tablet |
| `lg` | 992 | Desktop |
| `xl` | 1200 | Desktop wide |
| `xxl`| 1400 | Ultrawide |

### Hero
- **Mobile:** 90vh, texto stack vertical, sin imagen flotante, solo CTA apilados
- **Tablet:** 80vh, texto más grande, imagen parcial
- **Desktop:** 80vh, layout 7/5 cols, floating glass panel

### Módulos
- **Mobile:** 2×N grid (150px alto)
- **Tablet:** 3×N grid
- **Desktop:** 4×N grid (180px alto)
- **XL:** 6×N auto-fill

### Featured (Productos/Equipos/Servicios)
- **Mobile:** scroll horizontal snap (1 card visible + peek 20%)
- **Tablet:** 2 cols grid
- **Desktop:** 3-4 cols grid, no scroll

### TrustCards
- **Mobile:** 1 col
- **Tablet:** 2 cols
- **Desktop:** 3 cols
- **XL:** 4 cols auto-fill

---

## 8. DESCRIPCIÓN DETALLADA POR COMPONENTE

### A. `HeroSection.vue`
- Carrusel Bootstrap `carousel-fade` (crossfade, 5.5s)
- Indicadores customizados: círculos que se expanden en línea al activarse
- Controles prev/next: íconos dentro de círculos glassmorphism
- Animación de entrada del texto en cada slide: `.hero-text.enter-active`
- Si `banners.length === 0`: héroe estático con panel glass flotante (animación float)

### A.1 `HeroBackground.vue`
- Recibe: `image`, `video`, `hasMedia` (boolean)
- Si video: `<video autoplay muted loop playsinline>`
- Si imagen: `<div>` con `background-image` + Ken Burns animation
- Si nada: gradiente animado dark-navy con orbs de color flotantes
- Overlay: `linear-gradient(105deg, rgba(0,0,0,.75) 0%, rgba(0,0,0,.25) 60%, transparent)`

### A.2 `HeroSlide.vue`
- Contiene `HeroCTA.vue`
- Texto: eyebrow pill → h1 hero → párrafo → botones
- Clases de animación: `reveal-fade` + `reveal-up` en secuencia

### A.3 `HeroCTA.vue`
- Props: `primaryLabel`, `primaryUrl`, `ghostLabel`, `ghostUrl`
- Botón primary: gradiente azul + sombra glow + hover scale + arrow icon
- Botón ghost: fondo glass + border rgba + hover fill suave

### B. `SectionHeader.vue` — REUTILIZABLE
- Props: `eyebrow` (pill text) | `title` | `subtitle` | `align` ('center'|'left')
- Eyebrow: pill pequeño con background primary subtle
- Título: `.t-section` con posible `<em>` en color gradiente
- Subtítulo: `.t-section-sub` muted
- Línea decorativa: `::after` 40px wide, 2px, gradiente primary→electric

### C. `ModuleGrid.vue` + `ModuleCard.vue`
- Grid CSS: `repeat(auto-fill, minmax(160px, 1fr))`
- `ModuleCard`: imagen de fondo o color dinámico via `--mc`
- Hover: elevación 8px + scale 1.03 + glow del color del módulo
- Icono: glassmorphism circle, escala en hover
- Label: siempre visible en la parte inferior, texto blanco con sombra

### D. `FlashOffers.vue` + `FlashOfferCard.vue` + `CountdownTimer.vue`
- Sección: fondo `var(--c-bg-dark)`, padding generoso, curva SVG top
- `FlashOfferCard`: layout horizontal (imagen | info | badge descuento | CTA)
- Badge descuento: gradiente orange-red, font-size 2.5rem, rotado -3deg
- `CountdownTimer.vue`: recibe `secondsRemaining`, hace su propio setInterval
- Efecto urgencia: borde rojo pulsante si `secondsRemaining < 3600`

### E. `FeaturedSection.vue` + `FeaturedCarousel.vue` + `FeaturedCard.vue`
- En mobile: scroll horizontal con CSS scroll snap + `peek` visual de siguiente card
- En desktop: CSS Grid `auto-fill, minmax(220px, 1fr)`
- `FeaturedCard`: imagen 16:9 → info → precio → hover CTA aparece
- Hover: translateY(-6px) + imagen zoom 1.06 + botón CTA slide-up

### F. `TrustSection.vue` + `TrustCard.vue`
- Fondo sección: `var(--c-bg-subtle)` con blob decoration sutil
- `TrustCard`: glassmorphism sobre fondo claro
  - Si `card.video` → video de fondo (muted loop autoplay)
  - Si `card.image` → imagen de fondo con overlay
  - Si solo color → gradiente del `background_color` + icono grande
- Icono: 52×52 glass circle centrado
- Hover: borde gradiente animado + sombra glow suave

### G. `AnimatedCounter.vue`
- Props: `value` (número target) | `label` | `suffix` ('+', '%', 'k')
- Al entrar en viewport: count-up de 0 → value en 1.8s (easeOut)
- Implementación: `requestAnimationFrame` + `easeOutExpo` math function
- Estilo: número grande, label muted debajo

**Stats calculadas en HomeView:**
```js
[
  { value: featured_products.length + featured_equipment.length + featured_services.length,
    label: 'Items destacados', suffix: '+' },
  { value: modules.length, label: 'Módulos activos' },
  { value: flash_offers.length, label: 'Ofertas activas', suffix: '' },
]
```

### H. `FooterCTA.vue`
- Bloque antes del footer real (que ya existe como CustomerFooter)
- Fondo: gradiente primary con glow
- Título grande + subtítulo + 2 botones
- Props: `siteName`, `tagline`
- Efecto: línea decorativa top con gradiente blanco

### I. `GlassCard.vue` — BASE REUTILIZABLE
- Props: `dark` (boolean) | `hoverable` (boolean) | `padded` (boolean)
- Slot default para contenido
- Cuando `dark=true`: usa `--glass-dark-bg` y `--glass-dark-border`
- Cuando `dark=false`: usa `--glass-light-bg` y `--glass-light-border`
- Cuando `hoverable=true`: añade hover lift + glow

### J. `DividerWave.vue`
- Props: `fill` (color del elemento siguiente) | `flip` (boolean, voltea la curva)
- SVG inline de 1440×60px con curva suave
- Color dinámico via `:fill` binding en `<path>`
- Elimina el "corte brusco" entre secciones de diferente color

### K. `LoadingSkeleton.vue`
- Props: `width`, `height`, `radius`, `dark`, `count`, `gap`
- Si `count > 1`: genera N bloques en flex/grid
- Shimmer: `--shimmer-light` (claro) o `--shimmer-dark` (invertido para fondos oscuros)

---

## 9. ORDEN DE IMPLEMENTACIÓN

```
Paso 1 → Variables CSS + HomeView.vue (orquestador)
Paso 2 → LoadingSkeleton.vue + GlassCard.vue + SectionHeader.vue + DividerWave.vue
Paso 3 → HeroBackground.vue → HeroSlide.vue → HeroCTA.vue → HeroSection.vue
Paso 4 → ModuleCard.vue → ModuleGrid.vue
Paso 5 → CountdownTimer.vue → FlashOfferCard.vue → FlashOffers.vue
Paso 6 → FeaturedCard.vue → FeaturedCarousel.vue → FeaturedSection.vue
Paso 7 → TrustCard.vue → TrustSection.vue
Paso 8 → AnimatedCounter.vue → FooterCTA.vue
```

---

## 10. GUÍA VISUAL FINAL — REGLAS QUE NO SE NEGOCIAN

1. **Nunca**: sombras de color negro puro. Siempre usar `rgba(0,0,0,0.04-0.13)` o `var(--shadow-*)`.
2. **Nunca**: border `1px solid #ccc`. Siempre `rgba(0,0,0,.06)` en claro o `rgba(255,255,255,.09)` en oscuro.
3. **Nunca**: spinners. Solo skeletons con shimmer.
4. **Nunca**: tarjetas con border-radius < 12px.
5. **Siempre**: el hero usa mínimo `80vh`.
6. **Siempre**: secciones con `padding-block: var(--s-section-v)`.
7. **Siempre**: `DividerWave` entre secciones de diferente color de fondo.
8. **Siempre**: texto sobre fondo oscuro usa `text-shadow: 0 1px 6px rgba(0,0,0,.3)`.
9. **Siempre**: botones con `border-radius: var(--r-full)` (pill) o `var(--r-lg)` (redondeado).
10. **Siempre**: hover animation con `transition: var(--tr-smooth)`.
