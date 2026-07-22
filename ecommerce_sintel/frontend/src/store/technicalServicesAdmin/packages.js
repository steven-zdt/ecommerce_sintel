/**
 * technicalServicesAdmin/packages.js — Pinia store para Paquetes de
 * Servicio, sus items incluidos y costos adicionales.
 *
 * Dividido desde technicalServicesAdmin.js (SPRINT 4, 2026-07-16) -- ver
 * 12_CHECKLIST_IMPLEMENTACION.md.
 */
import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

// Solo empaqueta como multipart si hay un archivo real (image); si no, deja el
// objeto plano para que axios lo envie como JSON (el ViewSet acepta ambos).
function buildFormData(payload) {
  const hasFile = Object.values(payload).some((v) => v instanceof File || v instanceof Blob);
  if (!hasFile) return payload;
  const fd = new FormData();
  Object.entries(payload).forEach(([key, value]) => {
    if (value === null || value === undefined) return;
    fd.append(key, value);
  });
  return fd;
}

export const useTechnicalServicePackagesStore = defineStore('technicalServicePackages', {
  state: () => ({
    packages: [],
    packageIncludedItems: [],
    packageAdditionalCosts: [],
    loading: false,
    actionLoading: false,
    error: null,
  }),

  actions: {
    _api() {
      return useApi();
    },

    _clearError() {
      this.error = null;
    },

    // ─── Packages ──────────────────────────────────────────────────────────────

    async fetchPackages(serviceUuid) {
      this._clearError();
      this.loading = true;
      try {
        const { data } = await this._api().get('dashboard/service-packages/', {
          params: { service: serviceUuid },
        });
        this.packages = data.results ?? data;
        return this.packages;
      } catch (err) {
        this.error = 'Error cargando paquetes.';
        return [];
      } finally {
        this.loading = false;
      }
    },

    async createPackage(serviceUuid, payload) {
      this.actionLoading = true;
      try {
        const fd = buildFormData({ service: serviceUuid, ...payload });
        const { data } = await this._api().post('dashboard/service-packages/', fd);
        await this.fetchPackages(serviceUuid);
        return { ok: true, data };
      } catch (err) {
        const msg = err.response?.data?.detail || JSON.stringify(err.response?.data) || 'Error al crear paquete.';
        return { ok: false, error: msg };
      } finally {
        this.actionLoading = false;
      }
    },

    async updatePackage(packageUuid, serviceUuid, payload) {
      this.actionLoading = true;
      try {
        const fd = buildFormData(payload);
        const { data } = await this._api().patch(`dashboard/service-packages/${packageUuid}/`, fd);
        if (serviceUuid) await this.fetchPackages(serviceUuid);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al actualizar paquete.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async deletePackage(packageUuid, serviceUuid) {
      this.actionLoading = true;
      try {
        await this._api().delete(`dashboard/service-packages/${packageUuid}/`);
        if (serviceUuid) await this.fetchPackages(serviceUuid);
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al eliminar paquete.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async togglePackage(packageUuid, serviceUuid) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`dashboard/service-packages/${packageUuid}/toggle-active/`);
        if (serviceUuid) await this.fetchPackages(serviceUuid);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al cambiar estado del paquete.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async duplicatePackage(packageUuid, serviceUuid) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`dashboard/service-packages/${packageUuid}/duplicate/`);
        if (serviceUuid) await this.fetchPackages(serviceUuid);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al duplicar paquete.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async reorderPackages(serviceUuid, orderedUuids) {
      this.actionLoading = true;
      try {
        await this._api().post('dashboard/service-packages/reorder/', {
          service: serviceUuid,
          ordered_uuids: orderedUuids,
        });
        await this.fetchPackages(serviceUuid);
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al reordenar paquetes.' };
      } finally {
        this.actionLoading = false;
      }
    },

    // ─── Paquete: items incluidos ──────────────────────────────────────────────

    async fetchPackageIncludedItems(packageUuid) {
      this.loading = true;
      try {
        const { data } = await this._api().get('dashboard/package-included-items/', {
          params: { package: packageUuid },
        });
        this.packageIncludedItems = data.results ?? data;
        return this.packageIncludedItems;
      } catch (err) {
        this.error = 'Error cargando items incluidos.';
        return [];
      } finally {
        this.loading = false;
      }
    },

    async createPackageIncludedItem(packageUuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post('dashboard/package-included-items/', { package: packageUuid, ...payload });
        await this.fetchPackageIncludedItems(packageUuid);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al crear item incluido.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async updatePackageIncludedItem(itemUuid, packageUuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().patch(`dashboard/package-included-items/${itemUuid}/`, payload);
        if (packageUuid) await this.fetchPackageIncludedItems(packageUuid);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al actualizar item incluido.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async deletePackageIncludedItem(itemUuid, packageUuid) {
      this.actionLoading = true;
      try {
        await this._api().delete(`dashboard/package-included-items/${itemUuid}/`);
        if (packageUuid) await this.fetchPackageIncludedItems(packageUuid);
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al eliminar item incluido.' };
      } finally {
        this.actionLoading = false;
      }
    },

    // ─── Paquete: costos adicionales ───────────────────────────────────────────

    async fetchPackageAdditionalCosts(packageUuid) {
      this.loading = true;
      try {
        const { data } = await this._api().get('dashboard/package-additional-costs/', {
          params: { package: packageUuid },
        });
        this.packageAdditionalCosts = data.results ?? data;
        return this.packageAdditionalCosts;
      } catch (err) {
        this.error = 'Error cargando costos adicionales.';
        return [];
      } finally {
        this.loading = false;
      }
    },

    async createPackageAdditionalCost(packageUuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post('dashboard/package-additional-costs/', { package: packageUuid, ...payload });
        await this.fetchPackageAdditionalCosts(packageUuid);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al crear costo adicional.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async updatePackageAdditionalCost(costUuid, packageUuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().patch(`dashboard/package-additional-costs/${costUuid}/`, payload);
        if (packageUuid) await this.fetchPackageAdditionalCosts(packageUuid);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al actualizar costo adicional.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async deletePackageAdditionalCost(costUuid, packageUuid) {
      this.actionLoading = true;
      try {
        await this._api().delete(`dashboard/package-additional-costs/${costUuid}/`);
        if (packageUuid) await this.fetchPackageAdditionalCosts(packageUuid);
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al eliminar costo adicional.' };
      } finally {
        this.actionLoading = false;
      }
    },
  },
});
