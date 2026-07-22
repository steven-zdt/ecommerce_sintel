/**
 * rentingAdmin/catalog.js — Pinia store para administración de Equipos de Renting.
 *
 * Responsabilidades: Equipment, Variants, Logistics Config, Equipment Blocks
 * (mantenimiento/daño/inventario) -- todo lo que gira alrededor de la ficha
 * de un equipo (EquipmentDetailView.vue + sus panels).
 * Dividido desde rentingAdmin.js (SPRINT 4, 2026-07-16) -- ver 12_CHECKLIST_IMPLEMENTACION.md.
 */
import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

export const useRentingCatalogAdminStore = defineStore('rentingCatalogAdmin', {
  state: () => ({
    equipment: [],
    totalEquipment: 0,
    currentEquipment: null,
    variants: [],
    logisticsConfig: null,
    equipmentBlocks: [],
    loading: false,
    actionLoading: false,
    error: null,
  }),

  getters: {
    activeEquipment: (state) => state.equipment.filter((e) => e.is_active),
  },

  actions: {
    _api() {
      return useApi();
    },

    _clearError() {
      this.error = null;
    },

    // ─── Equipment ────────────────────────────────────────────────────────────

    async fetchEquipment(params = {}) {
      this._clearError();
      this.loading = true;
      try {
        const query = new URLSearchParams(params).toString();
        const { data } = await this._api().get(`dashboard/equipment/?${query}`);
        this.equipment = data.results ?? data;
        this.totalEquipment = data.count ?? data.length;
      } catch (err) {
        this.error = err.response?.data?.detail || 'Error cargando equipos.';
      } finally {
        this.loading = false;
      }
    },

    async fetchEquipmentDetail(uuid) {
      this._clearError();
      this.loading = true;
      try {
        const { data } = await this._api().get(`dashboard/equipment/${uuid}/`);
        this.currentEquipment = data;
        return data;
      } catch (err) {
        this.error = err.response?.data?.detail || 'Equipo no encontrado.';
        return null;
      } finally {
        this.loading = false;
      }
    },

    async createEquipment(payload) {
      this._clearError();
      this.actionLoading = true;
      try {
        const { data } = await this._api().post('dashboard/equipment/', payload);
        await this.fetchEquipment();  // invalidar cache
        return { ok: true, data };
      } catch (err) {
        const msg = err.response?.data?.detail || JSON.stringify(err.response?.data) || 'Error al crear equipo.';
        return { ok: false, error: msg };
      } finally {
        this.actionLoading = false;
      }
    },

    async updateEquipment(uuid, payload) {
      this._clearError();
      this.actionLoading = true;
      try {
        const { data } = await this._api().patch(`dashboard/equipment/${uuid}/`, payload);
        await this.fetchEquipment();
        if (this.currentEquipment?.uuid === uuid) {
          this.currentEquipment = data;
        }
        return { ok: true, data };
      } catch (err) {
        const msg = err.response?.data?.detail || JSON.stringify(err.response?.data) || 'Error al actualizar equipo.';
        return { ok: false, error: msg };
      } finally {
        this.actionLoading = false;
      }
    },

    async deleteEquipment(uuid) {
      this._clearError();
      this.actionLoading = true;
      try {
        await this._api().delete(`dashboard/equipment/${uuid}/`);
        await this.fetchEquipment();
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al eliminar equipo.' };
      } finally {
        this.actionLoading = false;
      }
    },

    // ─── Variants ─────────────────────────────────────────────────────────────

    async fetchVariants(equipmentUuid) {
      this._clearError();
      this.loading = true;
      try {
        const { data } = await this._api().get(`dashboard/equipment/${equipmentUuid}/variants/`);
        this.variants = data.results ?? data;
        return this.variants;
      } catch (err) {
        this.error = 'Error cargando variantes.';
        return [];
      } finally {
        this.loading = false;
      }
    },

    async createVariant(equipmentUuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(
          `dashboard/equipment/${equipmentUuid}/variants/create/`,
          { ...payload, equipment: equipmentUuid }
        );
        await this.fetchVariants(equipmentUuid);
        return { ok: true, data };
      } catch (err) {
        const msg = err.response?.data?.detail || JSON.stringify(err.response?.data) || 'Error al crear variante.';
        return { ok: false, error: msg };
      } finally {
        this.actionLoading = false;
      }
    },

    async updateVariant(equipmentUuid, variantUuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().patch(
          `dashboard/equipment/${equipmentUuid}/variants/${variantUuid}/`,
          payload
        );
        await this.fetchVariants(equipmentUuid);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al actualizar variante.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async deleteVariant(equipmentUuid, variantUuid) {
      this.actionLoading = true;
      try {
        await this._api().delete(`dashboard/equipment/${equipmentUuid}/variants/${variantUuid}/delete/`);
        await this.fetchVariants(equipmentUuid);
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al eliminar variante.' };
      } finally {
        this.actionLoading = false;
      }
    },

    // ─── Logistics Config ─────────────────────────────────────────────────────

    async fetchLogisticsConfig(equipmentUuid) {
      try {
        const { data } = await this._api().get(`dashboard/equipment/${equipmentUuid}/logistics/`);
        this.logisticsConfig = data;
        return data;
      } catch (err) {
        this.logisticsConfig = null;
        return null;
      }
    },

    async upsertLogisticsConfig(equipmentUuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().put(`dashboard/equipment/${equipmentUuid}/logistics/`, payload);
        this.logisticsConfig = data;
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error guardando configuración logística.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async deleteLogisticsConfig(equipmentUuid) {
      this.actionLoading = true;
      try {
        await this._api().delete(`dashboard/equipment/${equipmentUuid}/logistics/`);
        this.logisticsConfig = null;
        return { ok: true };
      } catch (err) {
        return { ok: false, error: 'Error eliminando configuración logística.' };
      } finally {
        this.actionLoading = false;
      }
    },

    // ─── Equipment Blocks (mantenimiento/daño/inventario) ──────────────────────
    // Pega directo a renting/equipment-blocks/ (no a dashboard/), permiso
    // por-accion (IsAdminUser) -- no es una excepcion respecto al resto de
    // este store en particular (todo este store administra equipos).

    async fetchEquipmentBlocks(equipmentUuid) {
      this._clearError();
      this.loading = true;
      try {
        const { data } = await this._api().get(`renting/equipment-blocks/?equipment=${equipmentUuid}`);
        this.equipmentBlocks = data.results ?? data;
        return data;
      } catch (err) {
        this.error = err.response?.data?.detail || 'Error cargando bloqueos del equipo.';
        return null;
      } finally {
        this.loading = false;
      }
    },

    async createEquipmentBlock(payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post('renting/equipment-blocks/', payload);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al crear el bloqueo.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async releaseEquipmentBlock(uuid, reason = '') {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`renting/equipment-blocks/${uuid}/release/`, { reason });
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al liberar el bloqueo.' };
      } finally {
        this.actionLoading = false;
      }
    },
  },
});
