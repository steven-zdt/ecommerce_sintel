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
import { onMounted } from 'vue';
import { useRoute, RouterLink } from 'vue-router';
import { storeToRefs } from 'pinia';
import { useEnums } from '@/composables/useEnums';
import { useKycAdminStore } from '@/store/kycAdmin';
import KycVerificationPanel from './KycVerificationPanel.vue';

const route = useRoute();
const enums = useEnums();
const store = useKycAdminStore();
const { currentVerification: verification, detailLoading: loading } = storeToRefs(store);

function reload() {
  return store.fetchDetail(route.params.uuid);
}

onMounted(async () => {
  await Promise.all([
    enums.ensure('kyc-verification-statuses'),
    enums.ensure('kyc-document-statuses'),
    reload(),
  ]);
});
</script>
