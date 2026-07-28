<template>
  <article class="pkg-card" :class="{ selected, clickable: selectable }" @click="selectable && $emit('select', pkg)">
    <div class="pkg-card-media">
      <img v-if="pkg.image" :src="pkg.image" :alt="pkg.name">
      <div v-else class="pkg-card-media-fallback">
        <IconRenderer :icon="pkg.icon" fallback="bi-box-seam" size="1.8rem" />
      </div>
      <span v-if="pkg.is_featured" class="pkg-card-badge">Recomendado</span>
    </div>

    <div class="pkg-card-body">
      <h3 class="pkg-card-name">{{ pkg.name }}</h3>
      <p v-if="pkg.description" class="pkg-card-desc">{{ pkg.description }}</p>

      <div class="pkg-card-meta">
        <span v-if="pkg.estimated_duration"><i class="bi bi-clock"></i>{{ pkg.estimated_duration }} h</span>
        <span v-if="pkg.included_items?.length"><i class="bi bi-check2-circle"></i>{{ pkg.included_items.length }} incluidos</span>
      </div>

      <ul v-if="pkg.included_items?.length" class="pkg-card-includes">
        <li v-for="item in pkg.included_items.slice(0, 3)" :key="item.uuid">
          <i class="bi bi-check2"></i>{{ item.title }}
        </li>
        <li v-if="pkg.included_items.length > 3" class="pkg-card-more">
          +{{ pkg.included_items.length - 3 }} mas
        </li>
      </ul>

      <div class="pkg-card-footer">
        <strong class="pkg-card-price">{{ formatCOP(pkg.base_price) }}</strong>
        <button v-if="selectable" type="button" class="pkg-card-btn" :class="{ active: selected }">
          {{ selected ? 'Seleccionado' : 'Seleccionar' }}
        </button>
        <button v-else type="button" class="pkg-card-btn" @click.stop="$emit('contract', pkg)">
          Contratar
        </button>
      </div>
    </div>
  </article>
</template>

<script setup>
import IconRenderer from '@/components/ui/IconRenderer.vue';
import { formatCOP as formatCOPBase } from '@/utils/money';

defineProps({
  pkg: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  selectable: { type: Boolean, default: false },
});
defineEmits(['select', 'contract']);

function formatCOP(value) {
  const number = parseFloat(value);
  if (!Number.isFinite(number)) return 'A cotizar';
  return formatCOPBase(number, { withSymbol: true });
}
</script>

<style scoped>
.pkg-card {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #fff;
  overflow: hidden;
  transition: border-color .15s ease, box-shadow .15s ease, transform .15s ease;
}
.pkg-card.clickable { cursor: pointer; }
.pkg-card.clickable:hover { transform: translateY(-2px); box-shadow: 0 10px 26px rgba(15, 23, 42, .08); }
.pkg-card.selected { border-color: #d97706; box-shadow: 0 0 0 2px rgba(217, 119, 6, .16); }
.pkg-card-media {
  position: relative;
  aspect-ratio: 16 / 10;
  background: #fffbeb;
}
.pkg-card-media img { width: 100%; height: 100%; object-fit: cover; }
.pkg-card-media-fallback {
  width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: #d97706;
}
.pkg-card-badge {
  position: absolute; top: .6rem; right: .6rem;
  background: #d97706; color: #fff; border-radius: 999px;
  padding: .2rem .6rem; font-size: .68rem; font-weight: 800;
}
.pkg-card-body { padding: 1rem; }
.pkg-card-name { color: #0f172a; font-size: 1rem; font-weight: 850; margin: 0 0 .3rem; }
.pkg-card-desc { color: #64748b; font-size: .8rem; line-height: 1.5; margin: 0 0 .6rem; }
.pkg-card-meta { display: flex; gap: .75rem; color: #92400e; font-size: .74rem; font-weight: 700; margin-bottom: .6rem; }
.pkg-card-meta i { margin-right: .3rem; }
.pkg-card-includes { list-style: none; margin: 0 0 .8rem; padding: 0; display: flex; flex-direction: column; gap: .3rem; }
.pkg-card-includes li { color: #475569; font-size: .78rem; }
.pkg-card-includes i { color: #16a34a; margin-right: .35rem; }
.pkg-card-more { color: #94a3b8 !important; font-style: italic; }
.pkg-card-footer { display: flex; align-items: center; justify-content: space-between; gap: .6rem; border-top: 1px solid #f1f5f9; padding-top: .75rem; }
.pkg-card-price { color: #92400e; font-size: 1rem; }
.pkg-card-btn {
  border: 1.5px solid #d97706; background: #fff; color: #d97706;
  border-radius: 999px; padding: .4rem .9rem; font-size: .78rem; font-weight: 750;
}
.pkg-card-btn.active { background: #d97706; color: #fff; }
</style>
