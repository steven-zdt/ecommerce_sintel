import { ref, computed } from 'vue';
import { useRoute } from 'vue-router';
import useApi from '@/composables/useApi';
import { useAuthStore } from '@/store/auth';
import { useSupportContextStore } from '@/store/supportContext';
import { useToast } from '@/composables/useToast';
import { useAppConfigStore } from '@/store/appConfig';

// Mapea el prefijo de ruta al modulo de origen para el mensaje contextual y
// el evento analitico -- ver frontend/src/apps/admin/routes/customer.routes.js
// para el arbol de rutas real. Orden importa: se evalua de arriba a abajo,
// el primer prefijo que matchea gana.
const MODULE_ROUTE_MAP = [
  { prefix: '/tienda', module: 'shop', label: 'Tienda' },
  { prefix: '/alquiler', module: 'renting', label: 'Renting' },
  { prefix: '/servicios', module: 'services', label: 'Servicios' },
  { prefix: '/cotizar', module: 'quotes', label: 'Cotizaciones' },
];
const HOME_LABEL = 'Inicio';
// White-label F7 (2026-08-14): antes 'Sintel' hardcodeado como label general --
// funcion (no constante de modulo) porque appConfigStore recien tiene el dato
// real despues de fetchConfig(), que corre en runtime, no en import time.
function generalLabel() {
  return useAppConfigStore().brand.site_name || 'General';
}

function detectModule(path) {
  if (path === '/') return { module: 'home', label: HOME_LABEL };
  const match = MODULE_ROUTE_MAP.find((m) => path.startsWith(m.prefix));
  return match ? { module: match.module, label: match.label } : { module: 'general', label: generalLabel() };
}

/**
 * Centro de Comunicacion -- logica desacoplada de UI (CommunicationCenter.vue
 * y componentes hijos consumen esto, nunca arman el mensaje/URL de WhatsApp
 * ni llaman a la API de eventos por su cuenta).
 *
 * El numero institucional NUNCA se hardcodea aqui: viene de
 * organization.ContactInfo.phone (SSoT), expuesto ya publicamente via
 * `core/footer/` (mismo endpoint que ya consume CustomerFooter.vue -- con
 * cache server-side, asi que una segunda llamada desde aqui es barata, no
 * una violacion real del "no duplicar logica": es el mismo dato publico
 * cacheado, no una segunda fuente de verdad).
 */
export function useCommunication() {
  const route = useRoute();
  const api = useApi();
  const authStore = useAuthStore();
  const supportContextStore = useSupportContextStore();
  const toast = useToast();

  const isPanelOpen = ref(false);
  const phoneDigits = ref('');
  const phoneLoaded = ref(false);
  const phoneLoadFailed = ref(false);

  const moduleInfo = computed(() => detectModule(route.path));
  const currentModule = computed(() => moduleInfo.value.module);

  // WhatsApp esta listo para usarse solo si ya se cargo un numero real --
  // evita abrir wa.me con un numero vacio si `core/footer/` fallo o
  // ContactInfo.phone quedo sin configurar.
  const isWhatsAppReady = computed(() => phoneLoaded.value && !!phoneDigits.value);

  async function ensurePhoneLoaded() {
    if (phoneLoaded.value) return;
    try {
      const { data } = await api.get('core/footer/');
      const raw = data?.contact?.phone || '';
      phoneDigits.value = raw.replace(/\D/g, '');
    } catch {
      phoneLoadFailed.value = true;
    } finally {
      phoneLoaded.value = true;
    }
  }

  /**
   * Mensaje inicial contextual (requisito 5): modulo de origen, nombre del
   * item cuando aplica, URL actual, usuario autenticado cuando aplica.
   * El nombre del item se lee de document.title -- unico punto de la app
   * que ya lo setea de forma consistente por pagina (useSeo.js, usado por
   * las 3 vistas de detalle: producto/equipo/servicio), asi que reusarlo
   * evita instrumentar cada vista una por una solo para este boton.
   */
  function buildContextMessage() {
    const { label } = moduleInfo.value;
    const rawTitle = (document.title || '').trim();
    const itemName = rawTitle && rawTitle !== generalLabel() ? rawTitle : '';

    // White-label F7 (2026-08-14): antes 'sintel.net.co' hardcodeado -- usa el
    // dominio real de la request, funciona para cualquier despliegue.
    const hostname = typeof window !== 'undefined' ? window.location.hostname : '';
    let msg = `Hola, vengo desde ${label}${hostname ? ` en ${hostname}` : ''}`;
    if (itemName) msg += ` (${itemName})`;
    if (authStore.isAuthenticated && authStore.user?.first_name) {
      msg += `. Soy ${authStore.user.first_name}`;
    }
    msg += `.\n${window.location.href}`;
    return msg;
  }

  // `message` es opcional: sin el, se usa el mensaje contextual generico. Los
  // botones que ya conocen la intencion (ej. "Agendar visita" en el detalle de
  // un servicio) mandan su propio texto.
  function buildWhatsAppUrl(message = '') {
    if (!phoneDigits.value) return null;
    const text = message || buildContextMessage();
    return `https://wa.me/${phoneDigits.value}?text=${encodeURIComponent(text)}`;
  }

  /** Fire-and-forget: la telemetria nunca debe bloquear ni romper la UI real. */
  function trackEvent(eventType, { channel = '', metadata = {} } = {}) {
    api.post('organization/communication-events/', {
      event_type: eventType,
      channel,
      module: currentModule.value,
      metadata: {
        page_path: route.fullPath,
        is_authenticated: authStore.isAuthenticated,
        ...metadata,
      },
    }).catch(() => {});
  }

  function openPanel() {
    if (isPanelOpen.value) return;
    isPanelOpen.value = true;
    ensurePhoneLoaded();
    trackEvent('panel_open');
  }

  function closePanel() {
    // Las 4 opciones del panel (WhatsApp/Asistente IA/Solicitar llamada/Enviar
    // mensaje) llaman closePanel() justo despues del click, con el boton
    // clickeado todavia enfocado -- sin este blur(), aria-hidden pasaba a
    // "true" en el panel mientras un descendiente retenia el foco (bloqueado
    // por Chrome, warning real en consola: "Blocked aria-hidden on an
    // element because its descendant retained focus").
    if (document.activeElement instanceof HTMLElement) {
      document.activeElement.blur();
    }
    isPanelOpen.value = false;
  }

  function togglePanel() {
    if (isPanelOpen.value) closePanel();
    else openPanel();
  }

  function openWhatsApp(message = '') {
    // Si se enlaza directo como handler (@click="openWhatsApp") el primer
    // argumento es el evento del click, no un texto: se ignora.
    const url = buildWhatsAppUrl(typeof message === 'string' ? message : '');
    if (!url) return;
    trackEvent('channel_click', { channel: 'whatsapp' });
    window.open(url, '_blank', 'noopener,noreferrer');
    closePanel();
  }

  /**
   * Migra el chat de soporte en vivo (antes su propio boton flotante
   * "Soporte", ver SupportChatWidget.vue) a una opcion mas de este panel.
   * Reusa el canal REAL existente (WebSocket + agente humano/IA segun
   * configuracion de backend, `support` app) -- no crea un canal nuevo.
   * Sirve para las 3 opciones "Asistente IA"/"Solicitar llamada"/"Enviar
   * mensaje": mismo chat real, distinto `channel` (para el evento
   * analitico) y distinto texto inicial segun la intencion del usuario.
   *
   * El chat exige sesion iniciada (SupportChatWidget.vue ya lo exigia antes
   * de esta migracion) -- si el visitante no esta autenticado, se le avisa
   * en vez de abrir un chat que fallaria silenciosamente sin WebSocket.
   */
  function openSupportChat(channel, prefillText = '') {
    if (!authStore.isAuthenticated) {
      toast.info('Inicia sesión para chatear con nuestro equipo de soporte.');
      closePanel();
      return;
    }
    trackEvent('channel_click', { channel });
    supportContextStore.requestOpen(prefillText);
    closePanel();
  }

  return {
    isPanelOpen,
    isWhatsAppReady,
    ensurePhoneLoaded,
    currentModule,
    openPanel,
    closePanel,
    togglePanel,
    openWhatsApp,
    openSupportChat,
    trackEvent,
  };
}
