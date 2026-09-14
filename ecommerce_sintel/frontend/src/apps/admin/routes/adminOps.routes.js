const SupportDashboardView = () => import('@/modules/support/SupportDashboardView.vue');
const AIProviderConfigView = () => import('@/modules/support/AIProviderConfigView.vue');
const SecurityDashboardView = () => import('@/modules/security/SecurityDashboardView.vue');
const NotificationsAdminView = () => import('@/modules/notifications/NotificationsAdminView.vue');
const PaymentTransactionsAdminView = () => import('@/modules/payment/PaymentTransactionsAdminView.vue');
const OperationBoard      = () => import('@/modules/operations/OperationBoard.vue');
const OperationDetail     = () => import('@/modules/operations/OperationDetail.vue');
const DispatcherList      = () => import('@/modules/operations/DispatcherList.vue');

export const adminOpsRoutes = [
  { path: 'soporte',         name: 'support',          component: SupportDashboardView },
  { path: 'soporte/ia-config', name: 'ai-provider-config', component: AIProviderConfigView },
  { path: 'seguridad',      name: 'security',         component: SecurityDashboardView },
  { path: 'notificaciones', name: 'notifications-admin', component: NotificationsAdminView },
  { path: 'pagos',          name: 'payment-transactions', component: PaymentTransactionsAdminView },
  { path: 'operaciones',     name: 'admin-operations', component: OperationBoard },
  { path: 'operaciones/:uuid', name: 'admin-operation-detail', component: OperationDetail },
  { path: 'despachadores',   name: 'admin-dispatchers', component: DispatcherList },
];
