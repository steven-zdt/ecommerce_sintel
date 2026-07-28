import useApi from '@/composables/useApi';

export const kycService = {
  // Autoservicio del solicitante (Mi Cuenta > Verificacion)
  myVerification() {
    return useApi().get('auth/verification/').then(r => r.data);
  },
  submitForReview() {
    return useApi().post('auth/submit-for-review/').then(r => r.data);
  },
  uploadDocument(formData) {
    return useApi().post('auth/upload-document/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },
  deleteDocument(docUuid) {
    return useApi().delete(`auth/documents/${docUuid}/`).then(r => r.data);
  },

  // Panel admin (validaciones KYC)
  adminList(params = {}) {
    return useApi().get('auth/admin/verifications/', { params }).then(r => r.data);
  },
  adminMetrics() {
    return useApi().get('auth/admin/verifications/metrics/').then(r => r.data);
  },
  adminDetail(uuid) {
    return useApi().get(`auth/admin/verifications/${uuid}/`).then(r => r.data);
  },
  downloadDocument(docUuid) {
    return useApi().get(`auth/documents/${docUuid}/download/`, { responseType: 'blob' }).then(r => r.data);
  },
  reviewDocument(verificationUuid, docUuid, payload) {
    return useApi().post(`auth/admin/verifications/${verificationUuid}/documents/${docUuid}/review/`, payload).then(r => r.data);
  },
  approve(verificationUuid) {
    return useApi().post(`auth/admin/verifications/${verificationUuid}/approve/`).then(r => r.data);
  },
  forceApprove(verificationUuid, note) {
    return useApi().post(`auth/admin/verifications/${verificationUuid}/force-approve/`, { note }).then(r => r.data);
  },
  reject(verificationUuid, reason) {
    return useApi().post(`auth/admin/verifications/${verificationUuid}/reject/`, { reason }).then(r => r.data);
  },
  requestInfo(verificationUuid, message) {
    return useApi().post(`auth/admin/verifications/${verificationUuid}/request-info/`, { message }).then(r => r.data);
  },
  block(verificationUuid, reason) {
    return useApi().post(`auth/admin/verifications/${verificationUuid}/block/`, { reason }).then(r => r.data);
  },
};
