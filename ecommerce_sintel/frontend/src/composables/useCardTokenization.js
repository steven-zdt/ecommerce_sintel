/**
 * useCardTokenization.js — Tokenizacion de tarjetas via Wompi (ADR-001, Fase 3)
 *
 * Llama DIRECTAMENTE a la API de Wompi desde el navegador, con la llave PUBLICA
 * (VITE_WOMPI_PUBLIC_KEY) -- nunca pasa por nuestro backend ni por useApi()/axios.
 * Esto es intencional y no negociable: los datos crudos de tarjeta (numero, cvc)
 * jamas deben viajar por nuestro servidor (requisito PCI de Wompi, confirmado en
 * docs.wompi.co -- "Card tokenization should not be done from your server").
 *
 * Base URL validada en runtime (auditoria E2E, 2026-07-22): Wompi NO tiene un host
 * unico "api.wompi.co" para tokenizacion -- exige sandbox.wompi.co con una llave
 * pub_test_* y production.wompi.co con una llave de produccion, y rechaza la
 * combinacion cruzada con "La llave proveida no corresponde a este ambiente".
 * Mismo patron que el backend ya usa en payment/online/wompi_client.py
 * (_SANDBOX_BASE_URL / _PRODUCTION_BASE_URL segun WOMPI_ENVIRONMENT) -- aqui se
 * deriva del prefijo de la propia llave publica (convencion documentada de Wompi:
 * pub_test_* vs pub_prod_*) para no depender de una variable de entorno nueva
 * que pueda desincronizarse de la llave real.
 */

export function useCardTokenization() {
  /**
   * @param {object} card { number, exp_month, exp_year, cvc, card_holder }
   * @returns {object} data de Wompi: { id, brand, last_four, exp_month, exp_year, card_holder, expires_at, ... }
   */
  async function tokenizeCard(card) {
    const publicKey = import.meta.env.VITE_WOMPI_PUBLIC_KEY;
    if (!publicKey) {
      throw new Error('Wompi no esta configurado (VITE_WOMPI_PUBLIC_KEY faltante).');
    }
    const wompiBase = publicKey.startsWith('pub_test_')
      ? 'https://sandbox.wompi.co/v1'
      : 'https://production.wompi.co/v1';
    const tokensUrl = `${wompiBase}/tokens/cards`;

    const payload = {
      number: String(card.number).replace(/\s+/g, ''),
      exp_month: String(card.exp_month).padStart(2, '0'),
      exp_year: String(card.exp_year).padStart(2, '0'),
      cvc: String(card.cvc),
      card_holder: card.card_holder,
    };

    let resp;
    try {
      resp = await fetch(tokensUrl, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${publicKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
    } catch (networkErr) {
      throw new Error('No se pudo conectar con Wompi. Verifica tu conexion e intenta de nuevo.');
    }

    let json;
    try {
      json = await resp.json();
    } catch {
      throw new Error('Wompi devolvio una respuesta invalida.');
    }

    if (!resp.ok || json.status !== 'CREATED') {
      const messages = json?.error?.messages;
      const detail = messages ? Object.values(messages).flat().join(' ') : (json?.error?.reason || '');
      throw new Error(detail || 'No se pudo procesar la tarjeta. Verifica los datos e intenta de nuevo.');
    }

    return json.data;
  }

  return { tokenizeCard };
}
