/**
 * quotesAdmin/templateBuilder.js — Pinia store para el Constructor de
 * Cuestionarios Tecnicos (Quote Template Studio).
 *
 * Responsabilidades:
 * - State centralizado de categorias, subcategorias, atributos, tipos de
 *   equipo, plantillas y la plantilla actualmente abierta (arbol completo
 *   de modulos/preguntas)
 * - Cada mutacion de una entidad hija (modulo/pregunta/opcion) refresca
 *   el arbol completo de la plantilla via fetchTemplateDetail()
 *
 * Dividido desde quotesAdmin.js (SPRINT 4, 2026-07-16) -- ver
 * 12_CHECKLIST_IMPLEMENTACION.md. La parte de "Solicitudes de Cotizacion"
 * vive en quotesAdmin/quotations.js.
 */
import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

export const useQuoteTemplateBuilderStore = defineStore('quoteTemplateBuilder', {
  state: () => ({
    categories: [],
    subcategories: [],
    attributes: [],
    equipmentTypes: [],
    templates: [],
    currentTemplate: null,
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

    // ─── Categories ────────────────────────────────────────────────────────────

    async fetchCategories() {
      this.loading = true;
      try {
        const { data } = await this._api().get('dashboard/quote-template-categories/');
        this.categories = data.results ?? data;
        return this.categories;
      } catch (err) {
        this.error = 'Error cargando categorias.';
        return [];
      } finally {
        this.loading = false;
      }
    },

    async createCategory(payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post('dashboard/quote-template-categories/', payload);
        await this.fetchCategories();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al crear categoria.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async updateCategory(uuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().patch(`dashboard/quote-template-categories/${uuid}/`, payload);
        await this.fetchCategories();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al actualizar categoria.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async deleteCategory(uuid) {
      this.actionLoading = true;
      try {
        await this._api().delete(`dashboard/quote-template-categories/${uuid}/`);
        await this.fetchCategories();
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al eliminar categoria.' };
      } finally {
        this.actionLoading = false;
      }
    },

    // ─── Subcategories ─────────────────────────────────────────────────────────

    async fetchSubcategories(categoryUuid = null) {
      this.loading = true;
      try {
        const url = categoryUuid
          ? `dashboard/quote-template-subcategories/?category=${categoryUuid}`
          : 'dashboard/quote-template-subcategories/';
        const { data } = await this._api().get(url);
        this.subcategories = data.results ?? data;
        return this.subcategories;
      } catch (err) {
        this.error = 'Error cargando subcategorias.';
        return [];
      } finally {
        this.loading = false;
      }
    },

    async createSubcategory(payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post('dashboard/quote-template-subcategories/', payload);
        await this.fetchSubcategories();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al crear subcategoria.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async updateSubcategory(uuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().patch(`dashboard/quote-template-subcategories/${uuid}/`, payload);
        await this.fetchSubcategories();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al actualizar subcategoria.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async deleteSubcategory(uuid) {
      this.actionLoading = true;
      try {
        await this._api().delete(`dashboard/quote-template-subcategories/${uuid}/`);
        await this.fetchSubcategories();
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al eliminar subcategoria.' };
      } finally {
        this.actionLoading = false;
      }
    },

    // ─── Atributos (Tipo de Servicio / Instalacion / Sistema) ──────────────────

    async fetchAttributes(kind = null, subcategoryUuid = null) {
      this.loading = true;
      try {
        const params = new URLSearchParams();
        if (kind) params.append('kind', kind);
        if (subcategoryUuid) params.append('subcategory', subcategoryUuid);
        const qs = params.toString();
        const url = `dashboard/quote-template-attributes/${qs ? `?${qs}` : ''}`;
        const { data } = await this._api().get(url);
        this.attributes = data.results ?? data;
        return this.attributes;
      } catch (err) {
        this.error = 'Error cargando atributos.';
        return [];
      } finally {
        this.loading = false;
      }
    },

    async createAttribute(payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post('dashboard/quote-template-attributes/', payload);
        await this.fetchAttributes();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al crear el atributo.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async updateAttribute(uuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().patch(`dashboard/quote-template-attributes/${uuid}/`, payload);
        await this.fetchAttributes();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al actualizar el atributo.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async deleteAttribute(uuid) {
      this.actionLoading = true;
      try {
        await this._api().delete(`dashboard/quote-template-attributes/${uuid}/`);
        await this.fetchAttributes();
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al eliminar el atributo.' };
      } finally {
        this.actionLoading = false;
      }
    },

    // ─── Templates ─────────────────────────────────────────────────────────────

    async fetchTemplates() {
      this.loading = true;
      try {
        const { data } = await this._api().get('dashboard/quote-templates/');
        this.templates = data.results ?? data;
        return this.templates;
      } catch (err) {
        this.error = 'Error cargando plantillas.';
        return [];
      } finally {
        this.loading = false;
      }
    },

    async fetchTemplateDetail(uuid) {
      this.loading = true;
      try {
        const { data } = await this._api().get(`dashboard/quote-templates/${uuid}/`);
        this.currentTemplate = data;
        return data;
      } catch (err) {
        this.error = 'Plantilla no encontrada.';
        return null;
      } finally {
        this.loading = false;
      }
    },

    async createTemplate(payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post('dashboard/quote-templates/', payload);
        await this.fetchTemplates();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || JSON.stringify(err.response?.data) || 'Error al crear plantilla.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async updateTemplate(uuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().patch(`dashboard/quote-templates/${uuid}/`, payload);
        await this.fetchTemplates();
        if (this.currentTemplate?.uuid === uuid) {
          await this.fetchTemplateDetail(uuid);
        }
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al actualizar plantilla.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async deleteTemplate(uuid) {
      this.actionLoading = true;
      try {
        await this._api().delete(`dashboard/quote-templates/${uuid}/`);
        await this.fetchTemplates();
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al eliminar plantilla.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async cloneTemplate(uuid) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`dashboard/quote-templates/${uuid}/clone/`);
        await this.fetchTemplates();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al duplicar plantilla.' };
      } finally {
        this.actionLoading = false;
      }
    },

    // Lectura de solo consulta para el picker de "Importar pregunta" (Fase C)
    // -- NO toca this.currentTemplate, para no perder el arbol de la
    // plantilla que el admin esta editando mientras busca en otra.
    async fetchTemplateDetailReadOnly(uuid) {
      try {
        const { data } = await this._api().get(`dashboard/quote-templates/${uuid}/`);
        return data;
      } catch {
        return null;
      }
    },

    // ─── Equipment Types (catalogo reutilizable, solo para modulos EQUIPMENT) ──

    async fetchEquipmentTypes() {
      this.loading = true;
      try {
        const { data } = await this._api().get('dashboard/quote-equipment-types/');
        this.equipmentTypes = data.results ?? data;
        return this.equipmentTypes;
      } catch (err) {
        this.error = 'Error cargando tipos de equipo.';
        return [];
      } finally {
        this.loading = false;
      }
    },

    async createEquipmentType(payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post('dashboard/quote-equipment-types/', payload);
        await this.fetchEquipmentTypes();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al crear tipo de equipo.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async updateEquipmentType(uuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().patch(`dashboard/quote-equipment-types/${uuid}/`, payload);
        await this.fetchEquipmentTypes();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al actualizar tipo de equipo.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async deleteEquipmentType(uuid) {
      this.actionLoading = true;
      try {
        await this._api().delete(`dashboard/quote-equipment-types/${uuid}/`);
        await this.fetchEquipmentTypes();
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al eliminar tipo de equipo.' };
      } finally {
        this.actionLoading = false;
      }
    },

    // ─── Modulos (Equipos / Materiales / Mano de Obra — mismo endpoint) ────────

    async createModule(templateUuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post('dashboard/quote-template-modules/', { template: templateUuid, ...payload });
        await this.fetchTemplateDetail(templateUuid);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al crear modulo.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async updateModule(uuid, templateUuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().patch(`dashboard/quote-template-modules/${uuid}/`, payload);
        await this.fetchTemplateDetail(templateUuid);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al actualizar modulo.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async deleteModule(uuid, templateUuid) {
      this.actionLoading = true;
      try {
        await this._api().delete(`dashboard/quote-template-modules/${uuid}/`);
        await this.fetchTemplateDetail(templateUuid);
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al eliminar modulo.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async duplicateModule(uuid, templateUuid) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`dashboard/quote-template-modules/${uuid}/duplicate/`);
        await this.fetchTemplateDetail(templateUuid);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al duplicar modulo.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async reorderModule(uuid, templateUuid, direction) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(`dashboard/quote-template-modules/${uuid}/reorder/`, { direction });
        await this.fetchTemplateDetail(templateUuid);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al mover modulo.' };
      } finally {
        this.actionLoading = false;
      }
    },

    // ─── Questions ─────────────────────────────────────────────────────────────

    async createQuestion(moduleUuid, templateUuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post('dashboard/quote-questions/', { module: moduleUuid, ...payload });
        await this.fetchTemplateDetail(templateUuid);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || JSON.stringify(err.response?.data) || 'Error al crear pregunta.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async updateQuestion(uuid, templateUuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().patch(`dashboard/quote-questions/${uuid}/`, payload);
        await this.fetchTemplateDetail(templateUuid);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al actualizar pregunta.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async deleteQuestion(uuid, templateUuid) {
      this.actionLoading = true;
      try {
        await this._api().delete(`dashboard/quote-questions/${uuid}/`);
        await this.fetchTemplateDetail(templateUuid);
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al eliminar pregunta.' };
      } finally {
        this.actionLoading = false;
      }
    },

    // Biblioteca de preguntas reutilizable (Fase C) — copia (nunca comparte
    // por referencia) una pregunta existente, de cualquier modulo/plantilla,
    // al modulo que el admin esta editando ahora mismo.
    async duplicateQuestionToModule(questionUuid, targetModuleUuid, templateUuid) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post(
          `dashboard/quote-questions/${questionUuid}/duplicate-to-module/`,
          { target_module: targetModuleUuid },
        );
        await this.fetchTemplateDetail(templateUuid);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al importar la pregunta.' };
      } finally {
        this.actionLoading = false;
      }
    },

    // ─── Question Options ──────────────────────────────────────────────────────

    async createOption(questionUuid, templateUuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post('dashboard/quote-question-options/', { question: questionUuid, ...payload });
        await this.fetchTemplateDetail(templateUuid);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al crear opcion.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async updateOption(uuid, templateUuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().patch(`dashboard/quote-question-options/${uuid}/`, payload);
        await this.fetchTemplateDetail(templateUuid);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al actualizar opcion.' };
      } finally {
        this.actionLoading = false;
      }
    },

    async deleteOption(uuid, templateUuid) {
      this.actionLoading = true;
      try {
        await this._api().delete(`dashboard/quote-question-options/${uuid}/`);
        await this.fetchTemplateDetail(templateUuid);
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err.response?.data?.detail || 'Error al eliminar opcion.' };
      } finally {
        this.actionLoading = false;
      }
    },
  },
});
