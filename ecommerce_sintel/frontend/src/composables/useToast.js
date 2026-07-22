/**
 * useToast.js — Sistema de notificaciones global (reemplaza toast_container.html HTMX)
 */
import { ref } from 'vue';

const toasts = ref([]);
let nextId = 0;

export function useToast() {
  function addToast({ message, type = 'info', duration = 4000 }) {
    const id = ++nextId;
    toasts.value.push({ id, message, type });
    setTimeout(() => removeToast(id), duration);
  }

  function removeToast(id) {
    toasts.value = toasts.value.filter((t) => t.id !== id);
  }

  const success = (msg) => addToast({ message: msg, type: 'success' });
  const error = (msg) => addToast({ message: msg, type: 'error' });
  const info = (msg) => addToast({ message: msg, type: 'info' });
  const warning = (msg) => addToast({ message: msg, type: 'warning' });

  return { toasts, success, error, info, warning, removeToast };
}
