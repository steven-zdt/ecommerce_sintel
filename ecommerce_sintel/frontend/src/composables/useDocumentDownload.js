import useApi from '@/composables/useApi';

/**
 * Registra la descarga de un documento (contador `downloads`) y abre el
 * archivo. Compartido por EquipmentManualList/EquipmentDocumentList/
 * EquipmentDownloadSection -- las 3 secciones de "archivos" de cualquier
 * detalle publico (renting/shop) llaman el mismo patron de endpoint,
 * `<basePath>/<entityUuid>/documents/<docUuid>/register-download/`.
 *
 * `basePath` por defecto preserva el comportamiento original (renting) sin
 * tocar ningun call site existente -- shop pasa basePath="shop/products"
 * (generalizado 2026-08-03, mismo patron que CatalogListManager.parentKey).
 */
export function useDocumentDownload(entityUuid, basePath = 'renting/equipment') {
  const api = useApi();

  async function download(document) {
    try {
      const res = await api.post(
        `${basePath}/${entityUuid}/documents/${document.uuid}/register-download/`,
      );
      const url = res.data?.file || document.file;
      if (url) window.open(url, '_blank', 'noopener');
    } catch {
      if (document.file) window.open(document.file, '_blank', 'noopener');
    }
  }

  return { download };
}
