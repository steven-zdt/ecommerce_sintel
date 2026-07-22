import { ref, Ref } from 'vue';
import useApi from '@/composables/useApi';

/**
 * TypeScript interfaces for enum cache system
 */

/**
 * Individual enum item with optional CSS class and icon
 */
export interface EnumItem {
  label: string;
  class?: string;
  icon?: string;
}

/**
 * Collection of enum values for a catalog
 */
export interface EnumValues {
  [key: string]: EnumItem;
}

/**
 * Backend response contract for enum endpoint
 */
export interface EnumCatalog {
  name: string;
  values: EnumValues;
}

/**
 * Cache statistics for debugging/monitoring
 */
export interface CacheStats {
  cached: number;
  inflight: number;
  version: string;
  ttl: string;
  items: CacheItemStats[];
}

/**
 * Individual cache item stats
 */
export interface CacheItemStats {
  name: string;
  timestamp: number;
  expired: boolean;
}

/**
 * Cache entry with timestamp
 */
interface CacheEntry {
  values: Map<string, EnumValues>;
  inflight: Map<string, Promise<EnumValues>>;
  timestamps: Map<string, number>;
}

/**
 * Options for composable initialization
 */
export interface UseEnumsOptions {
  ttlMinutes?: number;
}

/**
 * Return type of useEnums composable
 */
export interface UseEnumsComposable {
  ready: Ref<boolean>;
  ensure: (name: string, forceRefresh?: boolean) => Promise<EnumValues>;
  preload: (names: string[], forceRefresh?: boolean) => Promise<void>;
  invalidate: (name: string) => void;
  invalidateAll: () => void;
  lookup: (name: string, key: string) => EnumItem | null;
  label: (name: string, key: string, fallback?: string) => string;
  cssClass: (name: string, key: string, fallback?: string) => string;
  icon: (name: string, key: string, fallback?: string) => string;
  getCacheStats: () => CacheStats;
}

/**
 * Cache invalidation constants
 */
const CACHE_VERSION: string = '1.0.1'; // Increment when modifying fallback catalogs
const CACHE_TTL_MINUTES: number = 30; // 30 minutes default TTL
const STORAGE_KEY_PREFIX: string = 'enum_cache_';
const STORAGE_VERSION_KEY: string = 'enum_cache_version';
const STORAGE_TIMESTAMP_KEY: string = 'enum_cache_timestamp_';

/**
 * Module-level singleton cache
 */
const enumCache: CacheEntry = {
  values: new Map(),
  inflight: new Map(),
  timestamps: new Map(),
};

/**
 * Generate storage key for enum name
 */
function getStorageKey(name: string): string {
  return `${STORAGE_KEY_PREFIX}${name}`;
}

/**
 * Generate timestamp key for enum name
 */
function getTimestampKey(name: string): string {
  return `${STORAGE_TIMESTAMP_KEY}${name}`;
}

/**
 * Check if cache entry has expired based on TTL
 */
function isExpired(name: string): boolean {
  const timestamp = enumCache.timestamps.get(name);
  if (!timestamp) return true;
  const now = Date.now();
  const expiredAt = timestamp + (CACHE_TTL_MINUTES * 60 * 1000);
  return now > expiredAt;
}

/**
 * Load enum values from localStorage with version validation
 */
function loadFromLocalStorage(name: string): EnumValues | null {
  try {
    const stored = localStorage.getItem(getStorageKey(name));
    const storedVersion = localStorage.getItem(STORAGE_VERSION_KEY);

    // Invalidate if cache version mismatch
    if (storedVersion !== CACHE_VERSION || !stored) {
      return null;
    }

    return JSON.parse(stored);
  } catch {
    return null;
  }
}

/**
 * Save enum values to localStorage with version and timestamp
 */
function saveToLocalStorage(name: string, values: EnumValues): void {
  try {
    localStorage.setItem(getStorageKey(name), JSON.stringify(values));
    localStorage.setItem(getTimestampKey(name), Date.now().toString());
    localStorage.setItem(STORAGE_VERSION_KEY, CACHE_VERSION);
  } catch (err) {
    console.warn(`Failed to save enum cache for ${name}:`, err);
  }
}

/**
 * Remove enum from localStorage cache
 */
function invalidateLocalStorage(name: string): void {
  try {
    localStorage.removeItem(getStorageKey(name));
    localStorage.removeItem(getTimestampKey(name));
  } catch (err) {
    console.warn(`Failed to invalidate cache for ${name}:`, err);
  }
}

/**
 * Fallback catalog when API is unreachable
 * Used as last resort in 4-layer cache stack
 */
function fallbackCatalog(name: string): EnumValues {
  const defaults: Record<string, EnumValues> = {
    'order-statuses': {
      pending: { label: 'Pendiente', class: 'bg-warning-subtle text-warning border border-warning-subtle' },
      paid: { label: 'Pagado', class: 'bg-success-subtle text-success border border-success-subtle' },
      processing: { label: 'En proceso', class: 'bg-info-subtle text-info border border-info-subtle' },
      shipped: { label: 'Enviado', class: 'bg-primary-subtle text-primary border border-primary-subtle' },
      delivered: { label: 'Entregado', class: 'bg-success text-white' },
      cancelled: { label: 'Cancelado', class: 'bg-secondary-subtle text-secondary border border-secondary-subtle' },
    },
    'payment-methods': {
      CARD: { label: 'Tarjeta de credito/debito', icon: 'bi bi-credit-card text-primary' },
      PSE: { label: 'PSE - Debito bancario', icon: 'bi bi-bank text-success' },
      NEQUI: { label: 'Nequi', icon: 'bi bi-phone text-danger' },
      BANCOLOMBIA: { label: 'Bancolombia', icon: 'bi bi-building text-warning' },
      EFECTY: { label: 'Efecty', icon: 'bi bi-cash text-success' },
      CARD_INSTALLMENT: { label: 'Tarjeta en cuotas', icon: 'bi bi-credit-card text-primary' },
    },
    'payment-statuses': {
      APPROVED: { label: 'Aprobado', class: 'bg-success text-white' },
      PENDING: { label: 'Pendiente', class: 'bg-warning text-dark' },
      DECLINED: { label: 'Rechazado', class: 'bg-danger text-white' },
      REJECTED: { label: 'Rechazado', class: 'bg-danger text-white' },
      VOIDED: { label: 'Anulado', class: 'bg-danger text-white' },
      ERROR: { label: 'Error', class: 'bg-danger text-white' },
    },
    'service-priorities': {
      low: { label: 'Baja', class: 'bg-secondary-subtle text-secondary' },
      medium: { label: 'Media', class: 'bg-info-subtle text-info' },
      high: { label: 'Alta', class: 'bg-warning-subtle text-warning' },
      critical: { label: 'Critica', class: 'bg-danger-subtle text-danger' },
    },
    'rental-statuses': {
      draft: { label: 'Borrador', class: 'bg-secondary-subtle text-secondary border border-secondary-subtle' },
      pending_validation: { label: 'Pendiente de validacion', class: 'bg-info-subtle text-info border border-info-subtle' },
      pending_payment: { label: 'Pendiente de pago', class: 'bg-warning-subtle text-warning border border-warning-subtle' },
      paid: { label: 'Pagado', class: 'bg-success-subtle text-success border border-success-subtle' },
      confirmed: { label: 'Confirmado', class: 'bg-info-subtle text-info border border-info-subtle' },
      in_operation: { label: 'En operacion', class: 'bg-primary-subtle text-primary border border-primary-subtle' },
      finished: { label: 'Finalizado', class: 'bg-success-subtle text-success border border-success-subtle' },
      cancelled: { label: 'Cancelado', class: 'bg-danger-subtle text-danger border border-danger-subtle' },
      payment_conflict: { label: 'Conflicto de pago', class: 'bg-dark-subtle text-dark border border-dark-subtle' },
    },
    'quote-statuses': {
      BORRADOR: { label: 'Borrador', class: 'bg-secondary-subtle text-secondary border border-secondary-subtle' },
      RECIBIDA: { label: 'Recibida', class: 'bg-info-subtle text-info border border-info-subtle' },
      EN_REVISION: { label: 'En revisión', class: 'bg-warning-subtle text-warning border border-warning-subtle' },
      PENDIENTE_INFORMACION: { label: 'Pendiente información', class: 'bg-warning-subtle text-warning border border-warning-subtle' },
      COTIZADA: { label: 'Cotizada', class: 'bg-primary-subtle text-primary border border-primary-subtle' },
      ENVIADA: { label: 'Enviada', class: 'bg-primary-subtle text-primary border border-primary-subtle' },
      ACEPTADA: { label: 'Aceptada', class: 'bg-success-subtle text-success border border-success-subtle' },
      RECHAZADA: { label: 'Rechazada', class: 'bg-danger-subtle text-danger border border-danger-subtle' },
      VENCIDA: { label: 'Vencida', class: 'bg-danger-subtle text-danger border border-danger-subtle' },
      CANCELADA: { label: 'Cancelada', class: 'bg-danger-subtle text-danger border border-danger-subtle' },
    },
    'operation-statuses': {
      CREATED: { label: 'Creado', class: 'bg-secondary-subtle text-secondary border border-secondary-subtle' },
      DOCS_PENDING: { label: 'Documentos pendientes', class: 'bg-secondary-subtle text-secondary border border-secondary-subtle' },
      READY_TO_ASSIGN: { label: 'Listo para asignar', class: 'bg-primary-subtle text-primary border border-primary-subtle' },
      ASSIGNED: { label: 'Asignado', class: 'bg-primary-subtle text-primary border border-primary-subtle' },
      SCHEDULED: { label: 'Programado', class: 'bg-primary-subtle text-primary border border-primary-subtle' },
      EN_ROUTE: { label: 'En camino', class: 'bg-warning-subtle text-warning border border-warning-subtle' },
      IN_PROGRESS: { label: 'En ejecucion', class: 'bg-warning-subtle text-warning border border-warning-subtle' },
      COMPLETED: { label: 'Completado', class: 'bg-success-subtle text-success border border-success-subtle' },
      CANCELLED: { label: 'Cancelado', class: 'bg-danger-subtle text-danger border border-danger-subtle' },
    },
    'operation-types': {
      SHOP_DELIVERY: { label: 'Entrega de tienda' },
      RENTAL: { label: 'Alquiler de equipo' },
      SERVICE: { label: 'Servicio tecnico' },
    },
    'quote-types': {
      product: { label: 'Producto' },
      rental: { label: 'Alquiler' },
      service: { label: 'Servicio' },
      custom: { label: 'Personalizado' },
    },
    'kyc-verification-statuses': {
      PENDING: { label: 'Pendiente', class: 'bg-secondary-subtle text-secondary border border-secondary-subtle' },
      UNDER_REVIEW: { label: 'En revisión', class: 'bg-warning-subtle text-warning border border-warning-subtle' },
      APPROVED: { label: 'Aprobado', class: 'bg-success-subtle text-success border border-success-subtle' },
      REJECTED: { label: 'Rechazado', class: 'bg-danger-subtle text-danger border border-danger-subtle' },
      BLOCKED: { label: 'Bloqueado', class: 'bg-dark-subtle text-dark border border-dark-subtle' },
      EXPIRED: { label: 'Expirado', class: 'bg-secondary-subtle text-secondary border border-secondary-subtle' },
    },
    'kyc-document-statuses': {
      PENDING: { label: 'Pendiente de revisión', class: 'bg-warning-subtle text-warning border border-warning-subtle' },
      APPROVED: { label: 'Aprobado', class: 'bg-success-subtle text-success border border-success-subtle' },
      REJECTED: { label: 'Rechazado', class: 'bg-danger-subtle text-danger border border-danger-subtle' },
    },
    'user-types': {
      TECHNICIAN: { label: 'Técnico', class: 'bg-info-subtle text-info border border-info-subtle' },
      PROFESSIONAL: { label: 'Profesional', class: 'bg-primary-subtle text-primary border border-primary-subtle' },
      SPECIALIST: { label: 'Especialista', class: 'bg-primary-subtle text-primary border border-primary-subtle' },
      CUSTOMER: { label: 'Cliente', class: 'bg-secondary-subtle text-secondary border border-secondary-subtle' },
      TRANSPORTER: { label: 'Transportador', class: 'bg-warning-subtle text-warning border border-warning-subtle' },
      CONTRACTOR: { label: 'Contratista', class: 'bg-primary-subtle text-primary border border-primary-subtle' },
      ACCOUNTANT: { label: 'Contador', class: 'bg-info-subtle text-info border border-info-subtle' },
    },
  };
  return defaults[name] || {};
}

/**
 * useEnums Composable
 *
 * Production-grade enum cache with:
 * - 4-layer cache stack (memory → localStorage → API → fallback)
 * - TTL-based invalidation (default 30 minutes)
 * - Version-based cache busting
 * - Inflight deduplication (no thundering herd)
 * - Case-insensitive lookup with fallback
 *
 * @example
 * const { ensure, label, cssClass } = useEnums();
 * await ensure('order-statuses');
 * const label = label('order-statuses', 'COMPLETED', 'Unknown');
 * const className = cssClass('order-statuses', 'COMPLETED');
 */
export function useEnums(options: UseEnumsOptions = {}): UseEnumsComposable {
  const api = useApi();
  const ready: Ref<boolean> = ref(false);
  const cacheTTL: number = options.ttlMinutes || CACHE_TTL_MINUTES;

  /**
   * Ensure enum is cached, fetching if necessary
   * Implements 4-layer cache stack with deduplication
   */
  async function ensure(name: string, forceRefresh: boolean = false): Promise<EnumValues> {
    // Layer 1: Memory cache (check if valid and not expired)
    if (!forceRefresh && enumCache.values.has(name) && !isExpired(name)) {
      return enumCache.values.get(name)!;
    }

    // Layer 2: Inflight deduplication (merge concurrent requests)
    if (enumCache.inflight.has(name)) {
      return enumCache.inflight.get(name)!;
    }

    // Layer 3: localStorage (before API call)
    if (!forceRefresh) {
      const fromStorage = loadFromLocalStorage(name);
      if (fromStorage) {
        enumCache.values.set(name, fromStorage);
        enumCache.timestamps.set(name, Date.now());
        return fromStorage;
      }
    }

    // Layer 4: API fetch with fallback
    const promise = api
      .get(`core/enums/${name}/`)
      .then(({ data }: { data: EnumCatalog }) => {
        const values = data?.values || {};
        enumCache.values.set(name, values);
        enumCache.timestamps.set(name, Date.now());
        saveToLocalStorage(name, values);
        return values;
      })
      .catch(() => {
        // Fallback: use local catalog
        const fallback = fallbackCatalog(name);
        enumCache.values.set(name, fallback);
        enumCache.timestamps.set(name, Date.now());
        console.warn(`[useEnums] Using fallback catalog for ${name} (API unavailable)`);
        return fallback;
      })
      .finally(() => {
        enumCache.inflight.delete(name);
      });

    enumCache.inflight.set(name, promise);
    return promise;
  }

  /**
   * Preload multiple enums concurrently
   */
  async function preload(names: string[], forceRefresh: boolean = false): Promise<void> {
    await Promise.all(names.map((n) => ensure(n, forceRefresh)));
    ready.value = true;
  }

  /**
   * Invalidate specific enum from all cache layers
   */
  function invalidate(name: string): void {
    // Layer 1: Memory cache
    enumCache.values.delete(name);
    enumCache.timestamps.delete(name);
    enumCache.inflight.delete(name);

    // Layer 2: localStorage
    invalidateLocalStorage(name);
  }

  /**
   * Invalidate all enums from all cache layers
   */
  function invalidateAll(): void {
    // Layer 1: Memory cache
    enumCache.values.clear();
    enumCache.timestamps.clear();
    enumCache.inflight.clear();

    // Layer 2: localStorage
    try {
      const keys = Object.keys(localStorage);
      keys.forEach((key) => {
        if (key.startsWith(STORAGE_KEY_PREFIX) || key.startsWith(STORAGE_TIMESTAMP_KEY)) {
          localStorage.removeItem(key);
        }
      });
      localStorage.removeItem(STORAGE_VERSION_KEY);
    } catch (err) {
      console.warn('Failed to clear localStorage:', err);
    }
  }

  /**
   * Lookup enum item with case-insensitive fallback
   * Returns null if not found anywhere
   */
  function lookup(name: string, key: string): EnumItem | null {
    const values = enumCache.values.get(name) || fallbackCatalog(name);
    const direct = values[key];
    if (direct) return direct;

    // Case-insensitive fallback
    if (typeof key === 'string') {
      const upper = values[key.toUpperCase()];
      if (upper) return upper;
      const lower = values[key.toLowerCase()];
      if (lower) return lower;
    }
    return null;
  }

  /**
   * Get label for enum item
   * Returns label if found, otherwise fallback or key
   */
  function label(name: string, key: string, fallback: string = ''): string {
    const item = lookup(name, key);
    return item?.label || fallback || key || '';
  }

  /**
   * Get CSS class for enum item
   * Used for styling (status badges, etc)
   */
  function cssClass(name: string, key: string, fallback: string = 'bg-secondary-subtle text-secondary'): string {
    const item = lookup(name, key);
    return item?.class || fallback;
  }

  /**
   * Get icon class for enum item
   * Used with Bootstrap Icons
   */
  function icon(name: string, key: string, fallback: string = 'bi bi-wallet2 text-secondary'): string {
    const item = lookup(name, key);
    return item?.icon || fallback;
  }

  /**
   * Get cache statistics for debugging/monitoring
   */
  function getCacheStats(): CacheStats {
    return {
      cached: enumCache.values.size,
      inflight: enumCache.inflight.size,
      version: CACHE_VERSION,
      ttl: `${cacheTTL} minutes`,
      items: Array.from(enumCache.values.keys()).map((name) => ({
        name,
        timestamp: enumCache.timestamps.get(name) || 0,
        expired: isExpired(name),
      })),
    };
  }

  return {
    ready,
    ensure,
    preload,
    invalidate,
    invalidateAll,
    lookup,
    label,
    cssClass,
    icon,
    getCacheStats,
  };
}
