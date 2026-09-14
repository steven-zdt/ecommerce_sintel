/**
 * useTokenRefresh.js — Single-flight refresh del access token, compartido
 * por TODA la app (useApi.js y useAuth.js).
 *
 * Por que existe (hallazgo real, 2026-08-08 — auditoria del bug "el chat de
 * soporte no responde ni inicia conversacion"): SIMPLE_JWT tiene
 * ROTATE_REFRESH_TOKENS=True + BLACKLIST_AFTER_ROTATION=True
 * (ecommerce/settings/base.py) -- el refresh token es de un solo uso, cada
 * refresh exitoso invalida el anterior. Antes de este archivo existian DOS
 * consumidores de /auth/token/refresh/ totalmente independientes y sin
 * ninguna coordinacion entre si:
 *   1. El interceptor de useApi.js (reacciona a cualquier 401 de la API REST)
 *   2. useAuth.js::refreshAccessToken(), llamado directamente por
 *      SupportChatWidget.vue y SupportDashboardView.vue ANTES de abrir su
 *      WebSocket (para no conectar con un token ya vencido)
 * Si ambos disparaban un refresh casi al mismo tiempo (tipico: el cliente
 * abre el chat justo cuando otra parte de la pagina esta reintentando una
 * peticion tras un 401, algo comun pasados los 15 min de vida del access
 * token), el segundo en llegar al backend usaba un refresh token que el
 * primero ya habia rotado/invalidado -- 401, `authStore.logout()`, y el
 * widget de chat desaparecia por completo (`v-if="authStore.isAuthenticated"`)
 * sin ningun aviso claro para el cliente. Centralizar el refresh en una unica
 * promesa compartida (module-level, dedupe natural via await) elimina la
 * carrera de raiz -- ya no importa quien la dispare primero, solo hay UNA
 * llamada de red en vuelo a la vez en toda la app.
 */
import axios from 'axios';
import { useAuthStore } from '@/store/auth';

const authClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1/',
});

let refreshPromise = null;

/**
 * Refresca el access token usando el refresh token actual del store.
 * Si ya hay un refresh en vuelo, devuelve esa MISMA promesa en vez de
 * disparar una segunda llamada de red -- este es el punto central del fix.
 * @returns {Promise<string>} el nuevo access token
 */
export function refreshAccessTokenShared() {
  if (refreshPromise) return refreshPromise;

  const authStore = useAuthStore();
  refreshPromise = authClient
    .post('auth/token/refresh/', { refresh: authStore.refreshToken })
    .then(({ data }) => {
      // data.refresh trae el token rotado (ROTATE_REFRESH_TOKENS=True) --
      // guardarlo o el proximo refresh (con el token viejo) fallara.
      authStore.setTokens({ access: data.access, refresh: data.refresh || authStore.refreshToken });
      return data.access;
    })
    .finally(() => {
      refreshPromise = null;
    });

  return refreshPromise;
}
