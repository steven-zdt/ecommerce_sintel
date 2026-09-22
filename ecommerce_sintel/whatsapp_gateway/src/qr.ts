/**
 * src/qr.ts
 *
 * Fase 5 del plan: convierte el string QR crudo que emite Baileys
 * (`connection.update`) a una representacion que el frontend puede pintar
 * directamente -- un data URL PNG -- sin que el string crudo salga nunca
 * tal cual por HTTP ni por logs (ver src/logger.ts, redact de "*.qr").
 */
import QRCode from "qrcode";

export async function encodeQrAsDataUrl(rawQr: string): Promise<string> {
  return QRCode.toDataURL(rawQr, { errorCorrectionLevel: "M", margin: 2, scale: 6 });
}
