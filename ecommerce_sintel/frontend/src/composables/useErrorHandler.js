/**
 * useErrorHandler.js — Patron estandar de manejo de errores de API (SPRINT 4,
 * 2026-07-16, ver AUDITORIA/12_CHECKLIST_IMPLEMENTACION.md "FE-M5: patrones
 * de loading inconsistentes").
 *
 * Antes de esto, cada componente repetia inline la misma extraccion de
 * mensaje de error de axios (err.response?.data?.detail, o el primer
 * error de validacion de un serializer de DRF, con un fallback fijo) --
 * variaciones del mismo patron en decenas de archivos. Este composable
 * centraliza esa extraccion; no reemplaza `useToast()` (sigue siendo el
 * sistema de notificaciones), solo el paso de "convertir un error de axios
 * en un mensaje legible".
 *
 * Uso tipico:
 *   const { handleError } = useErrorHandler();
 *   try { ... } catch (err) { handleError(err, 'Error al guardar.'); }
 */
import { useToast } from '@/composables/useToast';

/**
 * Extrae un mensaje legible de un error de axios/DRF.
 * Orden de prioridad (igual al que ya usaban la mayoria de componentes):
 *   1. err.response.data.detail (errores de negocio/permiso explicitos)
 *   2. Primer error de campo de un serializer DRF (objeto {campo: [msg]})
 *   3. fallback provisto por el caller
 */
export function extractErrorMessage(err, fallback = 'Ocurrio un error inesperado.') {
  const data = err?.response?.data;
  if (!data) return fallback;
  if (data.detail) return data.detail;
  if (typeof data === 'object') {
    const first = Object.values(data)[0];
    const msg = Array.isArray(first) ? first[0] : first;
    if (msg) return msg;
  }
  return fallback;
}

export function useErrorHandler() {
  const toast = useToast();

  function handleError(err, fallback) {
    toast.error(String(extractErrorMessage(err, fallback)));
  }

  return { handleError, extractErrorMessage };
}
