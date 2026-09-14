<template>
  <section class="market-home">
    <div class="container-xl">
      <div class="mh-grid">
        <article
          v-for="category in marketplaceCategories"
          :key="category.title"
          class="mh-card"
        >
          <div class="mh-icon">
            <i :class="['bi', category.icon]"></i>
          </div>
          <div>
            <h2>{{ category.title }}</h2>
            <p>{{ category.copy }}</p>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup>
const marketplaceCategories = [
  { icon: 'bi-camera-video', title: 'CCTV y seguridad', copy: 'Instalacion, puesta en marcha, analitica, mantenimiento y soporte.' },
  { icon: 'bi-router', title: 'Redes y conectividad', copy: 'Cableado, WiFi, switching, routing, segmentacion y pruebas certificadas.' },
  { icon: 'bi-door-open', title: 'Control de acceso', copy: 'Lectores, biometria, torniquetes, integracion y auditoria operativa.' },
  { icon: 'bi-hdd-network', title: 'Infraestructura TI', copy: 'Servidores, racks, UPS, respaldo, monitoreo y documentacion tecnica.' },
];
</script>

<style scoped>
.market-home {
  background: linear-gradient(180deg, #f8fafc 0%, #fff 100%);
  border-bottom: 1px solid #e2e8f0;
  padding: 1.3rem 0 1.8rem;
}
.mh-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.9rem;
  margin-top: -2.35rem;
  position: relative;
  z-index: 2;
}
.mh-card {
  min-height: 148px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1rem;
  display: flex;
  gap: 0.85rem;
  box-shadow: 0 16px 34px rgba(15,23,42,.08);
}
.mh-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: #ecfeff;
  color: #0e7490;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 1.15rem;
}
.mh-card h2 {
  color: #0f172a;
  font-weight: 850;
  letter-spacing: 0;
  margin: 0;
  font-size: 0.98rem;
  line-height: 1.2;
}
.mh-card p {
  color: #64748b;
  font-size: 0.82rem;
  line-height: 1.55;
  margin: 0.35rem 0 0;
}

@media (max-width: 991px) {
  .mh-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    margin-top: 1rem;
  }
}
@media (max-width: 575px) {
  .mh-grid { grid-template-columns: 1fr; }
  .mh-card { min-height: auto; }
}
</style>
