<template>
  <QuoteModuleQuestionsPanel :template-uuid="templateUuid" module-type="LABOR" />
</template>

<script setup>
import QuoteModuleQuestionsPanel from './QuoteModuleQuestionsPanel.vue';

defineProps({ templateUuid: { type: String, required: true } });
</script>
