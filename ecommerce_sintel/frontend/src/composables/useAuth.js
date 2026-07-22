/**
 * useAuth.js — Composable para autenticación JWT
 *
 * Encapsula: login, logout, refresh de token,
 * e inyecta el header Authorization en cada request de Axios.
 */
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/store/auth';
import axios from 'axios';

// Cliente dedicado para operaciones de auth (sin interceptor circular)
const authClient = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1/' });

export function useAuth() {
  const authStore = useAuthStore();
  const router = useRouter();

  const isAuthenticated = computed(() => authStore.isAuthenticated);
  const isAdmin = computed(() => authStore.isAdmin);
  const user = computed(() => authStore.user);

  /**
   * Login: POST /api/v1/auth/login/
   * Guarda tokens y datos del usuario en el store. `remember` decide si la sesion
   * persiste en localStorage (true, default) o solo en sessionStorage (false --
   * checkbox "Recordarme" desmarcado, se cierra al cerrar el navegador).
   * @returns {Object} user data
   */
  async function login(email, password, remember = true) {
    const { data } = await authClient.post('auth/login/', { email, password });
    authStore.setTokens({ access: data.tokens.access, refresh: data.tokens.refresh }, remember);
    authStore.setUser(data.user, remember);
    return data.user;
  }

  /**
   * Logout: POST /api/v1/auth/logout/ (invalida el refresh token)
   * Limpia el store y redirige al login.
   */
  async function logout() {
    try {
      if (authStore.refreshToken) {
        await authClient.post(
          'auth/logout/',
          { refresh: authStore.refreshToken },
          { headers: { Authorization: `Bearer ${authStore.accessToken}` } }
        );
      }
    } catch (_) {
      // Si falla el logout remoto, aún así limpiamos localmente
    } finally {
      const wasAdmin = authStore.isAdmin;
      authStore.logout();
      router.push(wasAdmin ? '/panel/login' : '/login');
    }
  }

  /**
   * Refresh: POST /api/v1/auth/token/refresh/
   * Renueva el access token usando el refresh token persisitdo.
   * @returns {string} nuevo access token
   */
  async function refreshAccessToken() {
    const { data } = await authClient.post('auth/token/refresh/', {
      refresh: authStore.refreshToken,
    });
    // data.refresh contiene el token rotado cuando ROTATE_REFRESH_TOKENS=True
    authStore.setTokens({ access: data.access, refresh: data.refresh || authStore.refreshToken });
    return data.access;
  }

  /**
   * Obtiene el perfil del usuario autenticado desde la API.
   * Sincroniza el store con los datos más recientes.
   */
  async function fetchProfile() {
    const { data } = await authClient.get('auth/profile/', {
      headers: { Authorization: `Bearer ${authStore.accessToken}` },
    });
    authStore.setUser(data);
    return data;
  }

  return { isAuthenticated, isAdmin, user, login, logout, refreshAccessToken, fetchProfile };
}
