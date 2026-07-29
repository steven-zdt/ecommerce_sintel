<template>
  <section v-if="faq && faq.length > 0" class="faq-section">
    <div class="container-xl">
      <h2>Preguntas Frecuentes</h2>
      <div class="accordion">
        <div v-for="(item, idx) in faq" :key="idx" class="accordion-item">
          <h2 class="accordion-header">
            <button class="accordion-button" type="button" data-bs-toggle="collapse" :data-bs-target="`#faq-${idx}`">
              {{ item.question }}
            </button>
          </h2>
          <div :id="`faq-${idx}`" class="accordion-collapse collapse" data-bs-parent=".accordion">
            <div class="accordion-body">{{ item.answer }}</div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup>
defineProps({
  faq: Array
});
</script>
<style scoped>
.detail-section { padding: 3rem 0; border-bottom: 1px solid #dee2e6; }
</style>
