import { describe, it, expect } from 'vitest';
import { formatCOP } from './money';

describe('formatCOP', () => {
  it('formatea sin simbolo por defecto, con separador de miles es-CO', () => {
    expect(formatCOP(1216180)).toBe('1.216.180');
  });

  it('formatea con simbolo cuando withSymbol=true', () => {
    expect(formatCOP(1216180, { withSymbol: true })).toBe('$ 1.216.180');
  });

  it('cae a 0 con valores no numericos (equivalente a parseFloat(val) || 0)', () => {
    expect(formatCOP(null)).toBe('0');
    expect(formatCOP(undefined)).toBe('0');
    expect(formatCOP('')).toBe('0');
    expect(formatCOP('abc')).toBe('0');
  });

  it('acepta strings numericos', () => {
    expect(formatCOP('50000')).toBe('50.000');
  });

  it('respeta decimals explicito', () => {
    expect(formatCOP(1216180.5, { decimals: 2 })).toBe('1.216.180,50');
    expect(formatCOP(1216180.5, { decimals: 2, withSymbol: true })).toBe('$ 1.216.180,50');
  });

  it('redondea igual que Intl.NumberFormat nativo (sin decimals explicito)', () => {
    expect(formatCOP(99.9)).toBe(new Intl.NumberFormat('es-CO').format(99.9));
  });
});
