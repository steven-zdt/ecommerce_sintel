import { describe, it, expect } from 'vitest';
import { mapPaymentStatus } from './paymentStatus';

describe('mapPaymentStatus', () => {
  it('mapea PENDING/APPROVED igual para Wompi y Nequi', () => {
    expect(mapPaymentStatus('PENDING', 'WOMPI')).toBe('pending');
    expect(mapPaymentStatus('PENDING', 'NEQUI')).toBe('pending');
    expect(mapPaymentStatus('APPROVED', 'WOMPI')).toBe('approved');
    expect(mapPaymentStatus('APPROVED', 'NEQUI')).toBe('approved');
  });

  it('mapea los estados reales de Wompi (DECLINED/VOIDED/ERROR) a declined', () => {
    expect(mapPaymentStatus('DECLINED', 'WOMPI')).toBe('declined');
    expect(mapPaymentStatus('VOIDED', 'WOMPI')).toBe('declined');
    expect(mapPaymentStatus('ERROR', 'WOMPI')).toBe('declined');
  });

  it('mapea los estados reales de Nequi (REJECTED/ERROR) a declined y TIMEOUT a expired', () => {
    expect(mapPaymentStatus('REJECTED', 'NEQUI')).toBe('declined');
    expect(mapPaymentStatus('ERROR', 'NEQUI')).toBe('declined');
    expect(mapPaymentStatus('TIMEOUT', 'NEQUI')).toBe('expired');
  });

  it('un estado de Nequi (TIMEOUT/REJECTED) no aplica al vocabulario de Wompi y viceversa', () => {
    expect(mapPaymentStatus('TIMEOUT', 'WOMPI')).toBeNull();
    expect(mapPaymentStatus('REJECTED', 'WOMPI')).toBeNull();
  });

  it('devuelve null para valores vacios o desconocidos', () => {
    expect(mapPaymentStatus(null, 'WOMPI')).toBeNull();
    expect(mapPaymentStatus('', 'WOMPI')).toBeNull();
    expect(mapPaymentStatus('ALGO_INVENTADO', 'WOMPI')).toBeNull();
  });
});
