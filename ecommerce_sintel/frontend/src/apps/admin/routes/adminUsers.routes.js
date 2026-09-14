const UserList      = () => import('@/modules/users/UserList.vue');
// [2026-07-12] Movido de modules/accounts/ a modules/proveedores/ (CORE v4, Fase 6):
// es portafolio profesional de contratistas/tecnicos, no configuracion de cuenta/auth.
const ProfessionalsAdminList = () => import('@/modules/proveedores/ProfessionalsAdminList.vue');
const KycAdminList = () => import('@/modules/kyc/KycAdminList.vue');
const KycAdminDetail = () => import('@/modules/kyc/KycAdminDetail.vue');

// 'validaciones' (estatico) antes de 'validaciones/:uuid' (dinamico, mismo
// nivel) -- mismo patron de riesgo que ordenes/renting vs ordenes/:uuid, no
// reordenar.
export const adminUsersRoutes = [
  { path: 'usuarios',     name: 'users-list',   component: UserList },
  { path: 'profesionales', name: 'professionals-admin-list', component: ProfessionalsAdminList },
  { path: 'validaciones',       name: 'kyc-admin-list',   component: KycAdminList },
  { path: 'validaciones/:uuid', name: 'kyc-admin-detail', component: KycAdminDetail },
];
