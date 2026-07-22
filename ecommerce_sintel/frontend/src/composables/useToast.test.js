import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useToast } from './useToast';

// useToast usa un ref() a nivel de modulo (no de componente) -- el estado de
// `toasts` persiste entre llamadas a useToast() dentro del mismo proceso de
// test, asi que cada test debe limpiar lo que agrego.
describe('useToast', () => {
  beforeEach(() => {
    const { toasts } = useToast();
    toasts.value = [];
  });

  it('agrega un toast de exito con el tipo correcto', () => {
    const { toasts, success } = useToast();
    success('Producto creado');
    expect(toasts.value).toHaveLength(1);
    expect(toasts.value[0]).toMatchObject({ message: 'Producto creado', type: 'success' });
  });

  it('agrega un toast de error, info y warning con sus tipos', () => {
    const { toasts, error, info, warning } = useToast();
    error('Error al guardar');
    info('Procesando...');
    warning('Revisa los datos');
    expect(toasts.value.map((t) => t.type)).toEqual(['error', 'info', 'warning']);
  });

  it('asigna un id incremental unico a cada toast', () => {
    const { toasts, success } = useToast();
    success('Uno');
    success('Dos');
    expect(toasts.value[0].id).not.toBe(toasts.value[1].id);
  });

  it('removeToast quita solo el toast indicado', () => {
    const { toasts, success, removeToast } = useToast();
    success('Uno');
    success('Dos');
    const idToRemove = toasts.value[0].id;
    removeToast(idToRemove);
    expect(toasts.value).toHaveLength(1);
    expect(toasts.value[0].message).toBe('Dos');
  });

  it('se auto-remueve despues de la duracion por defecto (4000ms)', () => {
    vi.useFakeTimers();
    const { toasts, success } = useToast();
    success('Se va solo');
    expect(toasts.value).toHaveLength(1);

    vi.advanceTimersByTime(3999);
    expect(toasts.value).toHaveLength(1);

    vi.advanceTimersByTime(1);
    expect(toasts.value).toHaveLength(0);

    vi.useRealTimers();
  });
});
