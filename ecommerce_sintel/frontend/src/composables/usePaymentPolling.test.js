import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { usePaymentPolling } from './usePaymentPolling';

describe('usePaymentPolling', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('llama checkFn en cada intervalo', () => {
    const { start, stop } = usePaymentPolling({ intervalMs: 5000, timeoutMs: 120000 });
    const checkFn = vi.fn();

    start(checkFn);
    expect(checkFn).not.toHaveBeenCalled();

    vi.advanceTimersByTime(5000);
    expect(checkFn).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(5000);
    expect(checkFn).toHaveBeenCalledTimes(2);

    stop();
    vi.advanceTimersByTime(5000);
    expect(checkFn).toHaveBeenCalledTimes(2); // stop() detiene el timer
  });

  it('marca timedOut y deja de llamar checkFn al superar timeoutMs', () => {
    const onTimeout = vi.fn();
    const { start, timedOut } = usePaymentPolling({ intervalMs: 5000, timeoutMs: 15000, onTimeout });
    const checkFn = vi.fn();

    start(checkFn);
    vi.advanceTimersByTime(5000); // tick 1: 5000ms transcurridos, checkFn llamado
    vi.advanceTimersByTime(5000); // tick 2: 10000ms transcurridos, checkFn llamado
    expect(checkFn).toHaveBeenCalledTimes(2);
    expect(timedOut.value).toBe(false);

    vi.advanceTimersByTime(5000); // tick 3: 15000ms >= timeoutMs -> timeout, no llama checkFn
    expect(timedOut.value).toBe(true);
    expect(onTimeout).toHaveBeenCalledTimes(1);
    expect(checkFn).toHaveBeenCalledTimes(2); // no crecio en el tick de timeout

    vi.advanceTimersByTime(5000);
    expect(checkFn).toHaveBeenCalledTimes(2); // el timer ya se detuvo solo
  });

  it('start() es un no-op si ya hay un polling en curso', () => {
    const { start } = usePaymentPolling({ intervalMs: 5000, timeoutMs: 120000 });
    const checkFn1 = vi.fn();
    const checkFn2 = vi.fn();

    start(checkFn1);
    start(checkFn2); // segundo start ignorado mientras el primero sigue activo

    vi.advanceTimersByTime(5000);
    expect(checkFn1).toHaveBeenCalledTimes(1);
    expect(checkFn2).not.toHaveBeenCalled();
  });

  it('reinicia elapsedMs/timedOut al llamar start() de nuevo tras stop()', () => {
    const { start, stop, timedOut, elapsedMs } = usePaymentPolling({ intervalMs: 5000, timeoutMs: 10000 });

    start(vi.fn());
    vi.advanceTimersByTime(10000); // fuerza timeout
    expect(timedOut.value).toBe(true);

    stop();
    start(vi.fn());
    expect(timedOut.value).toBe(false);
    expect(elapsedMs.value).toBe(0);
  });
});
