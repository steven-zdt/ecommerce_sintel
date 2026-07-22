/**
 * useTheme.js — Dark mode del panel admin (2026-07-11).
 *
 * Usa el mecanismo nativo de color mode de Bootstrap 5.3
 * (atributo `data-bs-theme` en <html>) — re-tema automaticamente todos los
 * componentes de Bootstrap (.card, .table, .btn-light, .form-control, .badge)
 * en los ~190 componentes admin sin tocarlos uno por uno. Piezas de "chrome"
 * 100% custom (Navbar, .main-content de AppShell) llevan su propio override
 * dark en <style scoped> via el selector [data-bs-theme="dark"].
 *
 * Alcance actual: solo el panel admin (AppShell/Navbar). El portal customer
 * (landing/tienda/etc.) NO tiene modo oscuro — ver
 * ai_skills/frontend/design_system/tokens.md.
 */
import { ref } from 'vue';

const STORAGE_KEY = 'sintel_theme';
const theme = ref('light');

function apply(value) {
  document.documentElement.setAttribute('data-bs-theme', value);
  theme.value = value;
}

function getPreferredTheme() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'light' || stored === 'dark') return stored;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function useTheme() {
  function init() {
    apply(getPreferredTheme());
  }

  function toggle() {
    const next = theme.value === 'dark' ? 'light' : 'dark';
    localStorage.setItem(STORAGE_KEY, next);
    apply(next);
  }

  function setTheme(value) {
    if (value !== 'light' && value !== 'dark') return;
    localStorage.setItem(STORAGE_KEY, value);
    apply(value);
  }

  return { theme, init, toggle, setTheme };
}
