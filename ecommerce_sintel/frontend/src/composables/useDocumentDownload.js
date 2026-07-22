import useApi from '@/composables/useApi';

/**
 * Registra la descarga de un RentalDocument (contador `downloads`) y abre el
 * archivo. Compartido por EquipmentManualList/EquipmentDocumentList/
 * EquipmentDownloadSection -- las 3 secciones de "archivos" del detalle de
 * renting llaman el mismo endpoint publico.
 */
export function useDocumentDownload(equipmentUuid) {
  const api = useApi();

  async function download(document) {
    try {
      const res = await api.post(
        `renting/equipment/${equipmentUuid}/documents/${document.uuid}/register-download/`,
      );
      const url = res.data?.file || document.file;
      if (url) window.open(url, '_blank', 'noopener');
    } catch {
      if (document.file) window.open(document.file, '_blank', 'noopener');
    }
  }

  return { download };
}
