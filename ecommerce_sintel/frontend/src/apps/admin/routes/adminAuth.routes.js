// Login del panel admin -- aislado del /login de clientes.
// REGLA: esta ruta llama a api/v1/admin-auth/login/ unicamente.
// No fusionar con /login ni con auth/login/. Ver AdminLoginPage.vue.
const AdminLoginPage          = () => import('@/views/admin/AdminLoginPage.vue');
const AdminForgotPasswordView = () => import('@/views/admin/AdminForgotPasswordView.vue');

export const adminAuthRoutes = [
  {
    path: '/panel/login',
    name: 'admin-login',
    component: AdminLoginPage,
    meta: { requiresAdminGuest: true },
  },
  {
    path: '/panel/forgot-password',
    name: 'admin-forgot-password',
    component: AdminForgotPasswordView,
    // Tambien puede usarse desde /panel/perfil cuando el administrador ya
    // tiene sesion: el OTP se envia solo al correo de una cuenta admin.
    meta: {},
  },
];
