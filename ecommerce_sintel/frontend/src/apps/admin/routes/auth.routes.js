// Rutas de autenticacion publica (cliente). Top-level, fuera de CustomerLayout
// a proposito -- usan su propio CustomerAuthLayout de pantalla completa desde
// el rediseno de autenticacion (2026-07-17). Ver frontend/CLAUDE.md "Rutas
// publicas orientadas al cliente".
const LoginView              = () => import('@/views/auth/LoginView.vue');
const RegisterView           = () => import('@/views/auth/RegisterView.vue');
const ForgotPasswordView     = () => import('@/views/auth/ForgotPasswordView.vue');
const VerifyEmailLinkView    = () => import('@/views/auth/VerifyEmailLinkView.vue');

export const authRoutes = [
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { requiresGuest: true },
  },
  { path: '/register', name: 'register', component: RegisterView, meta: { requiresGuest: true } },
  { path: '/forgot-password', name: 'forgot-password', component: ForgotPasswordView, meta: { requiresGuest: true } },
  // SSoT de identidad: todo registro publico crea siempre un CUSTOMER (ver
  // accounts/CLAUDE.md). Convertirse en profesional es un upgrade posterior
  // desde el dashboard ('contractor-onboarding'), no una eleccion en el
  // registro -- se conserva el redirect para no romper enlaces/marcadores
  // viejos a /registro-profesional.
  { path: '/registro-profesional', redirect: { name: 'register' } },
  {
    // Publica: sin requiresAuth ni requiresGuest -- el destinatario del enlace
    // de verificacion puede o no estar autenticado en este navegador.
    path: '/verificar-cuenta',
    name: 'verify-email-link',
    component: VerifyEmailLinkView,
  },
];
