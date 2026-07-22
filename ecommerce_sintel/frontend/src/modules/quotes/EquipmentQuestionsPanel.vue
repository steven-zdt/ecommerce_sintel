<template>
  <QuoteModuleQuestionsPanel :template-uuid="templateUuid" module-type="EQUIPMENT" />
</template>

<script setup>
import QuoteModuleQuestionsPanel from './QuoteModuleQuestionsPanel.vue';

defineProps({ templateUuid: { type: String, required: true } });
</script>
