import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { useTheme } from './useTheme';

describe('useTheme', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-bs-theme');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('init() usa prefers-color-scheme cuando no hay preferencia guardada', () => {
    window.matchMedia = vi.fn().mockReturnValue({ matches: true }); // simula dark del SO
    const { init, theme } = useTheme();
    init();
    expect(theme.value).toBe('dark');
    expect(document.documentElement.getAttribute('data-bs-theme')).toBe('dark');
  });

  it('init() respeta la preferencia guardada en localStorage por encima del SO', () => {
    localStorage.setItem('sintel_theme', 'light');
    window.matchMedia = vi.fn().mockReturnValue({ matches: true }); // SO dice dark
    const { init, theme } = useTheme();
    init();
    expect(theme.value).toBe('light'); // localStorage gana
  });

  it('toggle() alterna entre light y dark y persiste en localStorage', () => {
    window.matchMedia = vi.fn().mockReturnValue({ matches: false });
    const { init, toggle, theme } = useTheme();
    init(); // light
    expect(theme.value).toBe('light');

    toggle();
    expect(theme.value).toBe('dark');
    expect(localStorage.getItem('sintel_theme')).toBe('dark');
    expect(document.documentElement.getAttribute('data-bs-theme')).toBe('dark');

    toggle();
    expect(theme.value).toBe('light');
    expect(localStorage.getItem('sintel_theme')).toBe('light');
  });

  it('setTheme() ignora valores invalidos', () => {
    window.matchMedia = vi.fn().mockReturnValue({ matches: false });
    const { init, setTheme, theme } = useTheme();
    init();
    setTheme('purple');
    expect(theme.value).toBe('light'); // sin cambios
  });

  it('el estado persiste tras "recargar" (nueva llamada a init con localStorage ya seteado)', () => {
    window.matchMedia = vi.fn().mockReturnValue({ matches: false });
    const { init, toggle } = useTheme();
    init();
    toggle(); // ahora dark, guardado en localStorage

    // Simula un "reload": nueva instancia logica llamando init() de nuevo
    document.documentElement.removeAttribute('data-bs-theme');
    const { init: initAgain, theme: themeAgain } = useTheme();
    initAgain();
    expect(themeAgain.value).toBe('dark');
    expect(document.documentElement.getAttribute('data-bs-theme')).toBe('dark');
  });
});
