/**
 * useApi.js — Cliente Axios global con autenticación JWT automática.
 *
 * Interceptores:
 * - Request: inyecta Bearer token si existe en el store.
 * - Response: en 401, intenta refresh del token y reintenta la petición.
 * - Response: en error de red (sin response del servidor), reintenta SOLO
 *   peticiones GET (idempotentes) con backoff corto; anota error.isNetworkError
 *   / error.isOffline sin alterar el mensaje — el catch/toast.error de cada
 *   caller sigue funcionando igual que antes.
 *
 * NOTA: con ROTATE_REFRESH_TOKENS=True el endpoint /auth/token/refresh/ devuelve
 * un nuevo refresh token cada vez. Hay que guardarlo o el siguiente refresh falla.
 */
import axios from 'axios';

const NETWORK_RETRY_DELAYS_MS = [500, 1500]; // maximo 2 reintentos, backoff corto

// Los tokens viven en localStorage por defecto, o en sessionStorage si el
// usuario desmarco "Recordarme" en el login (ver store/auth.js). Estos
// helpers leen/escriben en el storage correcto sin que este archivo necesite
// saber cual fue la eleccion.
function storageGet(key) {
  return localStorage.getItem(key) ?? sessionStorage.getItem(key);
}
function storageSet(key, value) {
  // Escribe en el mismo storage donde ya vivia el valor (respeta "Recordarme");
  // si no existe en ninguno todavia, localStorage por defecto.
  if (sessionStorage.getItem(key) !== null && localStorage.getItem(key) === null) {
    sessionStorage.setItem(key, value);
  } else {
    localStorage.setItem(key, value);
  }
}
function storageRemove(key) {
  localStorage.removeItem(key);
  sessionStorage.removeItem(key);
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1/',
  headers: {
    'Content-Type': 'application/json',
  },
});

// --- Request interceptor: inyecta JWT Authorization header ---
api.interceptors.request.use((config) => {
  const token = storageGet('sintel_access');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// --- Response interceptor: maneja 401 → refresh → reintento ---
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error);
    else prom.resolve(token);
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const status = error.response?.status;
    const url = originalRequest.url;

    // --- Error de red (sin respuesta del servidor): offline o conexion caida ---
    if (!error.response) {
      error.isNetworkError = true;
      error.isOffline = typeof navigator !== 'undefined' && navigator.onLine === false;

      const isRetryableRead = (originalRequest.method || 'get').toLowerCase() === 'get';
      const retryCount = originalRequest._networkRetryCount || 0;

      if (isRetryableRead && retryCount < NETWORK_RETRY_DELAYS_MS.length) {
        originalRequest._networkRetryCount = retryCount + 1;
        const delay = NETWORK_RETRY_DELAYS_MS[retryCount];
        console.warn(`[API] Error de red en GET ${url}. Reintento ${retryCount + 1}/${NETWORK_RETRY_DELAYS_MS.length} en ${delay}ms.`);
        await new Promise((resolve) => setTimeout(resolve, delay));
        return api(originalRequest);
      }

      console.error(`[API] Error de red en ${url} (isOffline=${error.isOffline}). Sin mas reintentos.`);
      return Promise.reject(error);
    }

    if (status === 401) {
      console.warn(`[API] 401 Unauthorized detected on: ${url}`);
      
      if (!originalRequest._retry) {
        if (isRefreshing) {
          console.log(`[API] Token refresh already in progress, queuing request: ${url}`);
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          })
            .then((token) => {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              return api(originalRequest);
            })
            .catch((err) => Promise.reject(err));
        }

        originalRequest._retry = true;
        isRefreshing = true;
        console.log('[API] Attempting token refresh...');

        const refreshToken = storageGet('sintel_refresh');
        if (!refreshToken) {
          console.error('[API] No refresh token available. Forcing logout.');
          storageRemove('sintel_access');
          storageRemove('sintel_refresh');
          storageRemove('sintel_user');
          return Promise.reject(error);
        }

        try {
          const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1/';
          const { data } = await axios.post(`${baseURL}auth/token/refresh/`, {
            refresh: refreshToken,
          });
          const newToken = data.access;
          console.log('[API] Token refreshed successfully.');
          storageSet('sintel_access', newToken);
          // ROTATE_REFRESH_TOKENS=True: guardar el nuevo refresh token o el siguiente refresh fallara
          if (data.refresh) {
            storageSet('sintel_refresh', data.refresh);
          }
          processQueue(null, newToken);
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return api(originalRequest);
        } catch (refreshError) {
          console.error('[API] Token refresh failed:', refreshError);
          processQueue(refreshError, null);
          storageRemove('sintel_access');
          storageRemove('sintel_refresh');
          storageRemove('sintel_user');
          // Redirigir al login para que el usuario se autentique de nuevo
          window.location.href = '/login';
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      } else {
        console.error(`[API] 401 repeated after retry on: ${url}. Aborting.`);
      }
    }

    return Promise.reject(error);
  }
);


export default function useApi() {
  return api;
}
