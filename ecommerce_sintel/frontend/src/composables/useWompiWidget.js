import { onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useCartStore } from '@/store/cart';
import { useToast } from '@/composables/useToast';

const WOMPI_ORIGIN  = 'https://checkout.wompi.co';
const STUCK_TIMEOUT = 6000; // ms sin postMessage del iframe → error

/**
 * Construye el redirectUrl para Wompi.
 * Wompi rechaza localhost/127.0.0.1 con 403 en el widget — se omite en esos casos
 * y el callback de checkout.open() maneja el resultado localmente.
 * Para PSE en desarrollo usar VITE_WOMPI_REDIRECT_BASE=https://tu-ngrok.io en .env.local.
 * En produccion el origen se usa directamente; Wompi aniade ?id=<wompi_tx_id> al URL.
 * El ?tx=<uuid> incluido permite fallback si el webhook llega antes que el redirect.
 */
function _buildRedirectUrl(txUuid, redirectPath) {
  const origin = window.location.origin;
  const base   = import.meta.env.VITE_WOMPI_REDIRECT_BASE
    || (/localhost|127\.0\.0\.1/.test(origin) ? null : origin);
  return base ? `${base}${redirectPath}?tx=${txUuid}` : undefined;
}

export function useWompiWidget() {
  const router    = useRouter();
  const cartStore = useCartStore();
  const toast     = useToast();

  // Si el componente que abrio el widget se desmonta (el usuario navego a
  // otra pantalla sin cerrar el modal) antes de que Wompi resuelva el pago,
  // el callback de checkout.open() de Wompi se sigue disparando de todos
  // modos -- sin este guard, terminaba haciendo router.push() a la pantalla
  // de resultado de ESA transaccion por encima de lo que el usuario este
  // viendo en ese momento.
  let unmounted = false;
  onUnmounted(() => { unmounted = true; });

  function loadWompiWidget(widgetUrl) {
    return new Promise((resolve, reject) => {
      if (window.WidgetCheckout) { resolve(); return; }

      const src      = widgetUrl || `${WOMPI_ORIGIN}/widget.js`;
      const existing = document.querySelector(`script[src="${src}"]`);
      if (existing) {
        // Script en DOM pero WidgetCheckout aún no listo: puede ser race condition
        // porque el load event ya disparó antes de que adjuntáramos el listener.
        const poll    = setInterval(() => {
          if (window.WidgetCheckout) { clearInterval(poll); resolve(); }
        }, 50);
        const timeout = setTimeout(() => {
          clearInterval(poll);
          reject(new Error('Timeout cargando widget Wompi'));
        }, 8000);
        existing.addEventListener('load',  () => { clearTimeout(timeout); clearInterval(poll); resolve(); });
        existing.addEventListener('error', () => { clearTimeout(timeout); clearInterval(poll); reject(new Error('Error cargando widget Wompi')); });
        return;
      }

      const script   = document.createElement('script');
      script.src     = src;
      script.onload  = resolve;
      script.onerror = () => reject(new Error('No se pudo cargar el widget de Wompi'));
      document.head.appendChild(script);
    });
  }

  /**
   * Elimina el overlay huérfano de Wompi cuando el iframe falla (403, timeout, etc.).
   */
  function _forceCloseStuckWidget() {
    const iframe = document.querySelector(`iframe[src*="${WOMPI_ORIGIN}"]`);
    if (iframe) {
      let node = iframe;
      while (node.parentElement && node.parentElement !== document.body) {
        node = node.parentElement;
      }
      node.remove();
      return;
    }
    // Fallback: cualquier overlay de posición fija de Wompi
    document.querySelectorAll('div[style*="position: fixed"]').forEach(el => {
      if (el.querySelector(`iframe[src*="${WOMPI_ORIGIN}"]`) || el.style.zIndex > 9000) {
        el.remove();
      }
    });
  }

  /**
   * Abre el widget de pago de Wompi y gestiona el ciclo de vida completo.
   *
   * @param {object} txData    { uuid, amount_in_cents, public_key, integrity_signature, widget_url }
   * @param {object} options   { onApproved?, onDeclined?, onPending?: (resultQuery: {tx, id}) => void,
   *                             onStuck?: () => void, redirectPath?: string }
   *                           Sin onDeclined/onPending: comportamiento por defecto sin cambios
   *                           (toast + router.push a /payment/result), igual que siempre.
   *                           onStuck: se invoca ademas del toast cuando el widget nunca responde
   *                           (STUCK_TIMEOUT) -- para que el llamador pueda sacar su propia UI de
   *                           un estado "procesando" que de otro modo queda congelado para siempre
   *                           (bug real: ServiceCheckoutModal.vue quedaba con canClose=false y sin
   *                           ningun camino de vuelta cuando PSE/Otros no respondia).
   *
   * Wompi aniade ?id=<wompi_tx_id> al redirect_url automaticamente.
   * El callback de checkout.open() maneja pagos de tarjeta/Nequi in-widget.
   * Para PSE en produccion configurar VITE_WOMPI_REDIRECT_BASE=https://tudominio.com en .env.
   */
  async function openWompiWidget(txData, options = {}) {
    try {
      await loadWompiWidget(txData.widget_url);
    } catch {
      toast.error('No se pudo cargar la pasarela de pago. Verifica tu conexión a internet.');
      return;
    }

    const redirectPath = options.redirectPath || '/payment/result';
    const redirectUrl  = _buildRedirectUrl(txData.uuid, redirectPath);
    let done        = false;
    let iframeAlive = false;

    const messageHandler = (event) => {
      if (event.origin === WOMPI_ORIGIN) iframeAlive = true;
    };
    window.addEventListener('message', messageHandler);

    const stuckTimer = setTimeout(() => {
      if (!done && !iframeAlive) {
        done = true;
        window.removeEventListener('message', messageHandler);
        _forceCloseStuckWidget();
        // Si no se limpia aqui, el guard de router.js (recuperacion PSE: "el navegador
        // volvio tras la redireccion bancaria") intercepta la SIGUIENTE navegacion del
        // usuario -- aunque ya haya vuelto al selector de metodo de pago -- y lo manda
        // a /payment/result para un tx que nunca llego a iniciarse de verdad.
        sessionStorage.removeItem('wompi_pending_tx');
        if (!unmounted) {
          toast.error(
            'La pasarela de pago no respondió. ' +
            'Si el problema persiste, intenta con otro método de pago.'
          );
          options.onStuck?.();
        }
      }
    }, STUCK_TIMEOUT);

    const wompiConfig = {
      currency:      'COP',
      amountInCents: txData.amount_in_cents,
      reference:     txData.uuid,
      publicKey:     txData.public_key,
      signature:     { integrity: txData.integrity_signature },
    };
    if (redirectUrl) wompiConfig.redirectUrl = redirectUrl;

    // Guardar UUID antes de que PSE/bancolombia redirija al banco.
    // Si el navegador abandona la SPA, /checkout puede recuperar este UUID al volver.
    sessionStorage.setItem('wompi_pending_tx', txData.uuid);

    const checkout = new window.WidgetCheckout(wompiConfig);

    checkout.open(function (result) {
      if (done) return;
      done = true;
      clearTimeout(stuckTimer);
      window.removeEventListener('message', messageHandler);
      sessionStorage.removeItem('wompi_pending_tx');

      // El componente que abrio el pago ya no esta montado (el usuario
      // navego lejos sin cerrar el widget) -- no navegar ni mostrar toasts
      // sobre una pantalla que el usuario ya abandono.
      if (unmounted) return;

      const tx = result?.transaction;
      if (!tx) return; // Usuario cerró el widget sin pagar

      // tx.id es el ID propio de Wompi para esta transaccion, disponible de
      // inmediato en el callback del widget -- sin esto, /payment/result no tiene
      // forma de consultar la API de Wompi antes de que llegue el webhook (que es
      // lo que causaba que la pantalla quedara en "Pago en proceso" para siempre).
      // Nunca se usa tx.status como fuente de verdad (solo para UX inmediata) --
      // el status real se resuelve en el backend via _sync_wompi_status/webhook.
      const resultQuery = { tx: txData.uuid, id: tx.id };

      if (tx.status === 'APPROVED') {
        if (options.onApproved) {
          options.onApproved(resultQuery);
        } else {
          cartStore.reset();
          router.push({ path: '/payment/result', query: resultQuery });
        }
      } else if (tx.status === 'DECLINED') {
        if (options.onDeclined) {
          options.onDeclined(resultQuery);
        } else {
          toast.error('Pago rechazado. Verifica los datos de tu tarjeta e intenta de nuevo.');
          router.push({ path: '/payment/result', query: resultQuery });
        }
      } else if (tx.status === 'PENDING') {
        if (options.onPending) {
          options.onPending(resultQuery);
        } else {
          toast.info('Pago en proceso. Te notificaremos cuando se confirme.');
          router.push({ path: '/payment/result', query: resultQuery });
        }
      }
    });
  }

  return { openWompiWidget };
}
