<template>
  <div class="hbg-root">
    <!-- Video de fondo -->
    <video
      v-if="video"
      class="hbg-media"
      autoplay muted loop playsinline
      :src="video"
    ></video>

    <!-- Imagen de fondo con Ken Burns -->
    <div
      v-else-if="image"
      class="hbg-media hbg-image"
      :style="`background-image: url('${image}')`"
    ></div>

    <!-- Color solido configurable (fallback con bgColor) -->
    <div v-else-if="bgColor" class="hbg-solid" :style="{ background: bgColor }">
      <div class="hbg-orb hbg-orb-1" style="opacity:.35"></div>
      <div class="hbg-orb hbg-orb-2" style="opacity:.25"></div>
      <div class="hbg-mesh"></div>
    </div>

    <!-- Gradiente animado + orbs (fallback por defecto) -->
    <div v-else class="hbg-gradient">
      <div class="hbg-orb hbg-orb-1"></div>
      <div class="hbg-orb hbg-orb-2"></div>
      <div class="hbg-orb hbg-orb-3"></div>
      <div class="hbg-mesh"></div>
    </div>

    <!-- Overlay siempre presente -->
    <div class="hbg-overlay"></div>
  </div>
</template>

<script setup>
defineProps({
  image:   { type: String, default: '' },
  video:   { type: String, default: '' },
  bgColor: { type: String, default: '' },
});
</script>

<style scoped>
.hbg-root {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

/* ── Video ──────────────────────────────────────────────────────────────────── */
.hbg-media {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

/* ── Imagen con Ken Burns ───────────────────────────────────────────────────── */
.hbg-image {
  background-size: cover;
  background-position: center;
  animation: hbg-ken-burns 10s ease-in-out infinite alternate;
}
@keyframes hbg-ken-burns {
  0%   { transform: scale(1); }
  100% { transform: scale(1.07); }
}

/* ── Color solido configurable ──────────────────────────────────────────────── */
.hbg-solid {
  position: absolute;
  inset: 0;
}

/* ── Gradiente animado con orbs ─────────────────────────────────────────────── */
.hbg-gradient {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #080d1a 0%, #0d1f4a 55%, #0f2460 100%);
}
.hbg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
}
.hbg-orb-1 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(37,99,235,.38), transparent 70%);
  top: -200px;
  left: -150px;
  animation: hbg-float-1 8s ease-in-out infinite;
}
.hbg-orb-2 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(6,182,212,.28), transparent 70%);
  bottom: -100px;
  right: 10%;
  animation: hbg-float-2 10s ease-in-out infinite;
}
.hbg-orb-3 {
  width: 350px;
  height: 350px;
  background: radial-gradient(circle, rgba(124,58,237,.22), transparent 70%);
  top: 30%;
  right: 20%;
  animation: hbg-float-1 12s ease-in-out infinite reverse;
}
.hbg-mesh {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);
  background-size: 60px 60px;
}
@keyframes hbg-float-1 {
  0%, 100% { transform: translate(0, 0); }
  50%      { transform: translate(40px, -30px); }
}
@keyframes hbg-float-2 {
  0%, 100% { transform: translate(0, 0); }
  50%      { transform: translate(-30px, 25px); }
}

/* ── Overlay ────────────────────────────────────────────────────────────────── */
.hbg-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    108deg,
    rgba(0,0,0,.72) 0%,
    rgba(0,0,0,.38) 55%,
    rgba(0,0,0,.08) 100%
  );
}
</style>
