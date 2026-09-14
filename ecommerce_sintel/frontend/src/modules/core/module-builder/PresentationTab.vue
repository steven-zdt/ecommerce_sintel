<template>
  <div class="mb-section">
    <div class="mb-section-title"><i class="bi bi-layout-three-columns me-2"></i>Tipo de presentación</div>
    <p class="mb-section-sub">Selecciona cómo se renderizará visualmente esta sección.</p>
    <div class="mb-pt-grid">
      <button
        v-for="pt in PRESENTATION_TYPES" :key="pt.value"
        :class="['mb-pt-card', form.display_type === pt.value && 'mb-pt-card--selected']"
        @click="form.display_type = pt.value"
        :title="pt.label"
      >
        <div :class="['mb-pt-thumb', `mb-pt-thumb--${pt.value}`]">
          <div v-for="n in pt.items" :key="n" class="mb-pt-item"></div>
        </div>
        <span class="mb-pt-label">{{ pt.label }}</span>
        <i v-if="form.display_type === pt.value" class="bi bi-check-circle-fill mb-pt-check"></i>
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  form: { type: Object, required: true },
});

const PRESENTATION_TYPES = [
  { value: 'grid',        label: 'Grid clásico',     items: 6 },
  { value: 'grid_modern', label: 'Grid moderno',     items: 4 },
  { value: 'cards_h',     label: 'Cards horizontal', items: 3 },
  { value: 'cards_v',     label: 'Cards vertical',   items: 3 },
  { value: 'carousel',    label: 'Carrusel',         items: 1 },
  { value: 'slider',      label: 'Slider',           items: 1 },
  { value: 'hero',        label: 'Hero',             items: 3 },
  { value: 'banner',      label: 'Banner',           items: 2 },
  { value: 'list',        label: 'Lista',            items: 4 },
  { value: 'timeline',    label: 'Timeline',         items: 4 },
  { value: 'accordion',   label: 'Accordion',        items: 4 },
  { value: 'tabs',        label: 'Tabs',             items: 3 },
  { value: 'masonry',     label: 'Masonry',          items: 5 },
  { value: 'highlight',   label: 'Destacados',       items: 4 },
  { value: 'premium',     label: 'Premium Cards',    items: 3 },
  { value: 'compact',     label: 'Compacto',         items: 6 },
  { value: 'split',       label: 'Split Layout',     items: 2 },
  { value: 'minimal',     label: 'Minimalista',      items: 3 },
];
</script>

<style scoped src="./_shared.css"></style>

<style scoped>
/* ── Presentation type grid ──────────────────────────────────────────────── */
.mb-pt-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
  gap: 0.6rem;
}
.mb-pt-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  padding: 0.6rem 0.4rem;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
  cursor: pointer;
  transition: border-color .15s, background .15s, transform .15s;
}
.mb-pt-card:hover { border-color: #93c5fd; background: #eff6ff; transform: translateY(-1px); }
.mb-pt-card--selected { border-color: #2563eb; background: #eff6ff; }
.mb-pt-label { font-size: 0.68rem; font-weight: 600; color: #475569; text-align: center; }
.mb-pt-check { position: absolute; top: 4px; right: 4px; color: #2563eb; font-size: 0.7rem; }

/* Thumbnails */
.mb-pt-thumb {
  width: 80px; height: 52px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 3px;
  padding: 3px;
  background: #fff;
  border-radius: 5px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
}
.mb-pt-item {
  border-radius: 3px;
  background: linear-gradient(135deg, #93c5fd, #818cf8);
  min-height: 8px;
}

/* Grid 3x2 */
.mb-pt-thumb--grid { grid-template-columns: repeat(3, 1fr); }

/* Grid moderno - 1 big + 3 small */
.mb-pt-thumb--grid_modern { grid-template-columns: 1.5fr 1fr; grid-template-rows: 1fr 1fr; }
.mb-pt-thumb--grid_modern .mb-pt-item:first-child { grid-row: 1 / 3; background: linear-gradient(135deg, #60a5fa, #6366f1); }

/* Cards horizontal - each is a row */
.mb-pt-thumb--cards_h { grid-template-columns: 1fr; gap: 4px; }
.mb-pt-thumb--cards_h .mb-pt-item { display: flex; flex-direction: row; height: 14px; }

/* Cards vertical */
.mb-pt-thumb--cards_v { grid-template-columns: repeat(3, 1fr); }
.mb-pt-thumb--cards_v .mb-pt-item { height: 36px; }

/* Carousel - single centered */
.mb-pt-thumb--carousel { grid-template-columns: 1fr; }
.mb-pt-thumb--carousel .mb-pt-item { height: 46px; background: linear-gradient(135deg, #6366f1, #8b5cf6); border-radius: 4px; }

/* Slider - full width */
.mb-pt-thumb--slider { grid-template-columns: 1fr; }
.mb-pt-thumb--slider .mb-pt-item { height: 46px; background: linear-gradient(90deg, #1e3a8a, #3b82f6); border-radius: 4px; }

/* Hero - large + small */
.mb-pt-thumb--hero { grid-template-columns: 2fr 1fr; grid-template-rows: 1fr 1fr; }
.mb-pt-thumb--hero .mb-pt-item:first-child { grid-row: 1 / 3; background: linear-gradient(135deg, #0f172a, #1d4ed8); }

/* Banner - full width strip */
.mb-pt-thumb--banner { grid-template-columns: 2fr 1fr; gap: 3px; align-items: center; }
.mb-pt-thumb--banner .mb-pt-item:first-child { height: 32px; background: linear-gradient(90deg, #0f172a, #1e3a8a); }
.mb-pt-thumb--banner .mb-pt-item:last-child  { height: 20px; border-radius: 10px; }

/* List - stacked rows */
.mb-pt-thumb--list { grid-template-columns: 1fr; gap: 4px; }
.mb-pt-thumb--list .mb-pt-item { height: 10px; border-radius: 2px; }

/* Timeline - vertical line */
.mb-pt-thumb--timeline { grid-template-columns: 8px 1fr; gap: 3px; }
.mb-pt-thumb--timeline .mb-pt-item:nth-child(odd)  { width: 8px; border-radius: 50%; height: 8px; align-self: center; }
.mb-pt-thumb--timeline .mb-pt-item:nth-child(even) { height: 10px; border-radius: 2px; }

/* Accordion */
.mb-pt-thumb--accordion { grid-template-columns: 1fr; gap: 4px; }
.mb-pt-thumb--accordion .mb-pt-item { height: 11px; border-radius: 3px; border-bottom: 2px solid rgba(255,255,255,.4); }

/* Tabs */
.mb-pt-thumb--tabs { grid-template-rows: auto 1fr; grid-template-columns: repeat(3, 1fr); }
.mb-pt-thumb--tabs .mb-pt-item { height: 10px; border-radius: 2px; }
.mb-pt-thumb--tabs .mb-pt-item:first-child { background: #2563eb; }
.mb-pt-thumb--tabs .mb-pt-item:last-child  { grid-column: 1 / -1; height: 28px; margin-top: 2px; background: #dbeafe; }

/* Masonry - irregular heights */
.mb-pt-thumb--masonry { grid-template-columns: repeat(3, 1fr); align-items: start; }
.mb-pt-thumb--masonry .mb-pt-item:nth-child(1) { height: 28px; }
.mb-pt-thumb--masonry .mb-pt-item:nth-child(2) { height: 42px; }
.mb-pt-thumb--masonry .mb-pt-item:nth-child(3) { height: 18px; }
.mb-pt-thumb--masonry .mb-pt-item:nth-child(4) { height: 38px; }
.mb-pt-thumb--masonry .mb-pt-item:nth-child(5) { height: 24px; }

/* Highlight - 1 big left + 3 small right */
.mb-pt-thumb--highlight { grid-template-columns: 1.6fr 1fr; grid-template-rows: 1fr 1fr; }
.mb-pt-thumb--highlight .mb-pt-item:first-child { grid-row: 1 / 3; background: linear-gradient(135deg, #7c3aed, #2563eb); }

/* Premium - cards with accent lines */
.mb-pt-thumb--premium { grid-template-columns: repeat(3, 1fr); }
.mb-pt-thumb--premium .mb-pt-item {
  height: 36px; border-radius: 4px;
  background: #f8fafc; border: 1px solid #e2e8f0;
  border-top: 3px solid #7c3aed;
}

/* Compact */
.mb-pt-thumb--compact { grid-template-columns: repeat(3, 1fr); gap: 2px; }
.mb-pt-thumb--compact .mb-pt-item { height: 14px; border-radius: 2px; }

/* Split - 2 halves */
.mb-pt-thumb--split { grid-template-columns: 1fr 1fr; }
.mb-pt-thumb--split .mb-pt-item { height: 46px; }
.mb-pt-thumb--split .mb-pt-item:first-child  { background: linear-gradient(135deg, #0f172a, #1e3a8a); }
.mb-pt-thumb--split .mb-pt-item:last-child   { background: linear-gradient(135deg, #eff6ff, #dbeafe); }

/* Minimal - text lines */
.mb-pt-thumb--minimal { grid-template-columns: 1fr; gap: 5px; }
.mb-pt-thumb--minimal .mb-pt-item { height: 6px; border-radius: 3px; }
.mb-pt-thumb--minimal .mb-pt-item:first-child  { background: #1e293b; width: 70%; }
.mb-pt-thumb--minimal .mb-pt-item:nth-child(2) { background: #94a3b8; width: 90%; }
.mb-pt-thumb--minimal .mb-pt-item:last-child   { background: #2563eb; width: 40%; }
</style>
