<template>
  <div class="sc-root" @click="$emit('view', service)">

    <!-- ── Imagen / placeholder ──────────────────────────────────────────────── -->
    <div class="sc-img-wrap">
      <img
        v-if="primaryImage"
        :src="primaryImage"
        :alt="service.name"
        class="sc-img"
        loading="lazy"
      >
      <div v-else class="sc-placeholder">
        <div class="sc-placeholder-icon">
          <i :class="['bi', service.icon_class || 'bi-tools']"></i>
        </div>
      </div>

      <!-- Badge destacado -->
      <span v-if="service.is_featured" class="sc-badge-star">
        <i class="bi bi-star-fill me-1"></i>Destacado
      </span>

      <!-- Badge categoria -->
      <span v-if="categoryName" class="sc-badge-cat">{{ categoryName }}</span>

      <!-- Hover overlay -->
      <div class="sc-overlay">
        <button class="sc-overlay-btn sc-overlay-view" @click.stop="$emit('view', service)">
          <i class="bi bi-eye me-1"></i>Ver detalle
        </button>
        <button class="sc-overlay-btn sc-overlay-quote" @click.stop="$emit('quote', service)">
          <i class="bi bi-file-earmark-text"></i>
        </button>
      </div>
    </div>

    <!-- ── Cuerpo ─────────────────────────────────────────────────────────────── -->
    <div class="sc-body">
      <h6 class="sc-name">{{ service.name }}</h6>
      <p v-if="service.description" class="sc-desc">{{ truncate(service.description, 90) }}</p>

      <div class="sc-meta">
        <span v-if="levelName" class="sc-level">
          <i class="bi bi-person-badge me-1"></i>{{ levelName }}
        </span>
      </div>

      <div class="sc-price-wrap">
        <span v-if="minPrice !== null" class="sc-price">
          <span class="sc-price-from">Desde </span>
          <span class="sc-price-value">{{ fmtCOP(minPrice) }}</span>
        </span>
        <span v-else class="sc-price-cotizar">
          <i class="bi bi-file-earmark-text me-1"></i>A cotizar
        </span>
      </div>
    </div>

    <!-- ── Footer ─────────────────────────────────────────────────────────────── -->
    <div class="sc-footer" @click.stop>
      <button class="sc-btn-view" @click="$emit('view', service)">
        <i class="bi bi-eye me-1"></i>Ver detalle
      </button>
      <button class="sc-btn-quote" @click="$emit('quote', service)" title="Solicitar servicio">
        <i class="bi bi-file-earmark-text"></i>
      </button>
    </div>

  </div>
</template>

<script setup>
import { computed } from 'vue';
import { formatCOP } from '@/utils/money';

const props = defineProps({ service: { type: Object, required: true } });
defineEmits(['view', 'quote']);

const categoryName = computed(() => props.service.category?.name || null);
const levelName    = computed(() => props.service.level?.name    || null);

const primaryImage = computed(() => {
  const imgs = props.service.images;
  if (!imgs?.length) return null;
  return (imgs.find(i => i.is_primary) || imgs[0]).image || null;
});

const minPrice = computed(() => {
  const variants = props.service.variants;
  if (!variants?.length) return null;
  const prices = variants.map(v => v.calculated_price).filter(p => p != null && p > 0);
  return prices.length ? Math.min(...prices) : null;
});

function truncate(str, len) {
  if (!str) return '';
  return str.length > len ? str.slice(0, len) + '…' : str;
}

const fmtCOP = (n) => formatCOP(n, { withSymbol: true });
</script>

<style scoped>
/* ── Root ───────────────────────────────────────────────────────────────────── */
.sc-root {
  background: #fff;
  border: 1px solid rgba(0,0,0,.07);
  border-radius: 18px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  height: 100%;
  transition:
    transform 0.35s cubic-bezier(0.16,1,0.3,1),
    box-shadow 0.35s ease,
    border-color 0.22s ease;
  box-shadow: 0 2px 8px rgba(0,0,0,.05);
}
.sc-root:hover {
  transform: translateY(-6px);
  box-shadow: 0 16px 40px rgba(217,119,6,.1), 0 4px 12px rgba(0,0,0,.05);
  border-color: #fde68a;
}

/* ── Imagen ─────────────────────────────────────────────────────────────────── */
.sc-img-wrap {
  position: relative;
  width: 100%;
  padding-top: 65%;
  overflow: hidden;
  background: #fffbeb;
  flex-shrink: 0;
}
.sc-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.5s ease;
}
.sc-root:hover .sc-img { transform: scale(1.06); }

.sc-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #fffbeb, #fef3c7);
}
.sc-placeholder-icon {
  width: 60px;
  height: 60px;
  border-radius: 16px;
  background: rgba(217,119,6,.12);
  border: 1.5px solid rgba(217,119,6,.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.6rem;
  color: #d97706;
}

/* ── Badges ─────────────────────────────────────────────────────────────────── */
.sc-badge-star {
  position: absolute;
  top: 0.55rem;
  right: 0.55rem;
  background: rgba(245,158,11,.9);
  color: #78350f;
  font-size: 0.6rem;
  font-weight: 700;
  border-radius: 9999px;
  padding: 0.2rem 0.55rem;
  display: inline-flex;
  align-items: center;
  backdrop-filter: blur(4px);
}
.sc-badge-cat {
  position: absolute;
  top: 0.55rem;
  left: 0.55rem;
  background: rgba(255,251,235,.9);
  color: #92400e;
  border: 1px solid rgba(253,230,138,.7);
  font-size: 0.6rem;
  font-weight: 700;
  border-radius: 9999px;
  padding: 0.2rem 0.55rem;
  backdrop-filter: blur(4px);
}

/* ── Hover overlay ──────────────────────────────────────────────────────────── */
.sc-overlay {
  position: absolute;
  inset: 0;
  background: rgba(30,10,0,.45);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
  opacity: 0;
  transition: opacity 0.25s ease;
}
.sc-root:hover .sc-overlay { opacity: 1; }

.sc-overlay-btn {
  display: inline-flex;
  align-items: center;
  font-size: 0.8rem;
  font-weight: 600;
  border: none;
  border-radius: 9999px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  transition: transform 0.2s ease;
}
.sc-overlay-btn:hover { transform: scale(1.04); }
.sc-overlay-view {
  background: #fff;
  color: #92400e;
  box-shadow: 0 2px 10px rgba(0,0,0,.2);
}
.sc-overlay-quote {
  background: linear-gradient(135deg, #d97706, #b45309);
  color: #fff;
  box-shadow: 0 2px 10px rgba(217,119,6,.35);
  padding: 0.5rem 0.7rem;
  font-size: 1rem;
}

/* ── Body ───────────────────────────────────────────────────────────────────── */
.sc-body {
  padding: 0.9rem 1rem 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  flex: 1;
}
.sc-name {
  font-size: 0.9rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.sc-desc {
  font-size: 0.78rem;
  color: #64748b;
  line-height: 1.5;
  margin: 0;
}
.sc-meta { margin-top: 0.15rem; }
.sc-level {
  font-size: 0.68rem;
  color: #94a3b8;
  display: inline-flex;
  align-items: center;
}
.sc-price-wrap { margin-top: auto; padding-top: 0.5rem; }
.sc-price { display: flex; align-items: baseline; gap: 0.2rem; }
.sc-price-from { font-size: 0.72rem; color: #94a3b8; }
.sc-price-value { font-size: 1rem; font-weight: 800; color: #d97706; }
.sc-price-cotizar {
  font-size: 0.78rem;
  font-weight: 600;
  color: #d97706;
  background: rgba(217,119,6,.08);
  border: 1px solid rgba(217,119,6,.18);
  border-radius: 9999px;
  padding: 0.2rem 0.6rem;
  display: inline-flex;
  align-items: center;
}

/* ── Footer ─────────────────────────────────────────────────────────────────── */
.sc-footer {
  padding: 0.65rem 0.9rem;
  border-top: 1px solid rgba(0,0,0,.06);
  display: flex;
  gap: 0.5rem;
}
.sc-btn-view {
  flex: 1;
  font-size: 0.8rem;
  font-weight: 600;
  color: #d97706;
  background: rgba(217,119,6,.07);
  border: 1px solid rgba(217,119,6,.2);
  border-radius: 9999px;
  padding: 0.45rem 0.75rem;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
  white-space: nowrap;
}
.sc-btn-view:hover { background: #d97706; color: #fff; border-color: #d97706; }
.sc-btn-quote {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: linear-gradient(135deg, #d97706, #b45309);
  color: #fff;
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(217,119,6,.3);
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}
.sc-btn-quote:hover { transform: scale(1.1); box-shadow: 0 4px 12px rgba(217,119,6,.4); }
</style>
