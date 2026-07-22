import { ref } from 'vue';

/**
 * Mecanica compartida de "consultar cada N ms hasta timeout" -- extraida de
 * las 3 implementaciones independientes que existian (ServiceCheckoutModal.vue,
 * PaymentResultView.vue, NequiPendingView.vue), documentadas en
 * PLAN_MAESTRO_UNIFICACION_PAYMENT_UI.md seccion 2 (hallazgo 1).
 *
 * Deliberadamente NO decide que pasa en cada tick ni que pasa si `checkFn`
 * falla -- eso sigue siendo responsabilidad de cada caller (algunos siguen
 * intentando ante un error de red hasta el timeout, otros paran de inmediato,
 * ver PLAN_MAESTRO... seccion "Riesgos"). Este composable solo deduplica el
 * setInterval/clearInterval y el conteo de tiempo transcurrido/timeout.
 */
export function usePaymentPolling({ intervalMs = 5000, timeoutMs = 120000, onTimeout } = {}) {
  const timedOut = ref(false);
  const elapsedMs = ref(0);
  let timer = null;

  function stop() {
    if (timer) { clearInterval(timer); timer = null; }
  }

  function start(checkFn) {
    if (timer) return;
    elapsedMs.value = 0;
    timedOut.value = false;

    timer = setInterval(() => {
      elapsedMs.value += intervalMs;
      if (elapsedMs.value >= timeoutMs) {
        timedOut.value = true;
        stop();
        onTimeout?.();
        return;
      }
      checkFn();
    }, intervalMs);
  }

  return { timedOut, elapsedMs, start, stop };
}
