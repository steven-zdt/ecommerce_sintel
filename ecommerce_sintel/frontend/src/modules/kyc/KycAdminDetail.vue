<template>
  <div class="kyc-detail-module">
    <RouterLink :to="{ name: 'kyc-admin-list' }" class="btn btn-sm btn-light border mb-3">
      <i class="bi bi-arrow-left me-1"></i>Volver
    </RouterLink>

    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary"></div>
    </div>

    <KycVerificationPanel v-else-if="verification" :verification="verification" @changed="reload" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, RouterLink } from 'vue-router';
import useApi from '@/composables/useApi';
import { useEnums } from '@/composables/useEnums';
import KycVerificationPanel from './KycVerificationPanel.vue';

const route = useRoute();
const api = useApi();
const enums = useEnums();

const loading = ref(true);
const verification = ref(null);

async function reload() {
  const { data } = await api.get(`auth/admin/verifications/${route.params.uuid}/`);
  verification.value = data;
}

onMounted(async () => {
  await Promise.all([enums.ensure('kyc-verification-statuses'), enums.ensure('kyc-document-statuses')]);
  await reload();
  loading.value = false;
});
</script>
