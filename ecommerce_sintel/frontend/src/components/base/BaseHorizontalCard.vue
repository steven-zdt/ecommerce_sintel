<template>
  <div class="bhc-root" :style="accentStyle" @click="emit('view')">
    <div class="row g-0 align-items-stretch">

      <!-- Imagen -->
      <div class="col-auto bhc-img-col">
        <div class="bhc-img-wrap">
          <img v-if="image" :src="image" :alt="title" class="bhc-img" loading="lazy">
          <div v-else class="bhc-img-placeholder">
            <slot name="placeholder-icon"><i :class="['bi', placeholderIcon]"></i></slot>
          </div>
          <slot name="image-badge" />
        </div>
      </div>

      <!-- Info -->
      <div class="col bhc-info">
        <slot name="tags" />
        <h6 class="bhc-name">{{ title }}</h6>
        <p v-if="description" class="bhc-desc">{{ description }}</p>
        <slot name="badges" />
      </div>

      <!-- Precio + acciones -->
      <div class="col-auto bhc-actions" @click.stop>
        <div class="bhc-price-block">
          <slot name="price" />
        </div>
        <div class="bhc-btns">
          <slot name="actions" />
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
/**
 * BaseHorizontalCard.vue -- fusion estructural de renting/EquipmentHorizontalCard.vue,
 * services/ServiceHorizontalCard.vue y shop/ProductHorizontalCard.vue (Fase 2
 * §2.1 del PLAN_MAESTRO_FRONTEND_DESIGN_SYSTEM_Y_FORMULARIOS.md: 3 forks de
 * ~300 lineas cada uno del mismo layout). Absorbe la grilla imagen/info/
 * acciones, el hover, el clamp de texto y el responsive -- que era identico
 * en los 3 -- via props (`image`,`imageFit`,`title`,`description`,
 * `placeholderIcon`,`accentColor`) + slots para lo genuinamente distinto por
 * dominio (badge de imagen, tags/badges de info, bloque de precio, botones
 * de accion), que no se fuerza a una sola forma porque Renting cotiza,
 * Services cotiza con paquete, y Shop agrega al carrito con estado async.
 */
import { computed } from 'vue';

const props = defineProps({
  image: { type: String, default: '' },
  imageFit: { type: String, default: 'contain' }, // 'contain' | 'cover'
  placeholderIcon: { type: String, default: 'bi-box-seam' },
  placeholderBg: { type: String, default: 'linear-gradient(135deg, #f8fafc, #f1f5f9)' },
  placeholderColor: { type: String, default: '#cbd5e1' },
  title: { type: String, required: true },
  description: { type: String, default: '' },
  accentColor: { type: String, default: '#2563eb' },
  accentShadow: { type: String, default: 'rgba(37,99,235,.09)' },
  accentBorder: { type: String, default: '#bfdbfe' },
});

const emit = defineEmits(['view']);

const accentStyle = computed(() => ({
  '--bhc-accent': props.accentColor,
  '--bhc-accent-shadow': props.accentShadow,
  '--bhc-accent-border': props.accentBorder,
  '--bhc-image-fit': props.imageFit,
  '--bhc-placeholder-bg': props.placeholderBg,
  '--bhc-placeholder-color': props.placeholderColor,
}));
</script>

<style scoped>
.bhc-root {
  background: #fff;
  border: 1px solid rgba(0,0,0,.07);
  border-radius: 18px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.3s cubic-bezier(0.16,1,0.3,1), box-shadow 0.3s ease, border-color 0.22s ease;
  box-shadow: 0 2px 8px rgba(0,0,0,.04);
}
.bhc-root:hover {
  border-color: var(--bhc-accent-border);
  box-shadow: 0 8px 28px var(--bhc-accent-shadow), 0 2px 8px rgba(0,0,0,.05);
  transform: translateY(-2px);
}

.bhc-img-col { flex-shrink: 0; }
.bhc-img-wrap {
  width: 150px; height: 100%; min-height: 140px;
  position: relative; overflow: hidden; background: #f8fafc;
}
.bhc-img {
  width: 100%; height: 100%; object-fit: var(--bhc-image-fit);
  padding: 0.75rem; display: block; transition: transform 0.4s ease;
}
.bhc-root:hover .bhc-img { transform: scale(1.04); }
.bhc-img-placeholder {
  width: 100%; height: 100%; min-height: 140px;
  display: flex; align-items: center; justify-content: center;
  font-size: 2rem; color: var(--bhc-placeholder-color);
  background: var(--bhc-placeholder-bg);
}

.bhc-info { padding: 1rem 1.25rem; min-width: 0; }
.bhc-name {
  font-size: 0.95rem; font-weight: 700; color: #0f172a;
  margin: 0 0 0.4rem; line-height: 1.3;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.bhc-desc {
  font-size: 0.8rem; color: #64748b; line-height: 1.45; margin: 0 0 0.6rem;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}

.bhc-actions {
  padding: 1rem 1.25rem;
  border-left: 1px solid rgba(0,0,0,.06);
  display: flex; flex-direction: column; justify-content: center; gap: 0.75rem;
  min-width: 185px; flex-shrink: 0;
}
.bhc-price-block { display: flex; flex-direction: column; gap: 0.15rem; }
.bhc-btns { display: flex; flex-direction: column; gap: 0.4rem; }

@media (max-width: 575px) {
  .bhc-img-wrap { width: 110px; min-height: 120px; }
  .bhc-actions { padding: 0.75rem 1rem; min-width: 155px; }
}
</style>
