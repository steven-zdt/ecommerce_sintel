<template>
  <footer class="customer-footer">
    <div class="container-fluid px-3 px-lg-4">
      <div class="footer-grid">

        <!-- Columna Brand -->
        <div class="footer-col footer-col--brand">
          <span class="footer-brand">Sintel</span>
          <p class="text-secondary small mt-3 mb-0" style="max-width:280px">
            Ecosistema inteligente de e-commerce. Productos, alquiler de equipos y servicios tecnicos en un solo lugar.
          </p>

          <!-- Redes sociales dinamicas -->
          <div class="d-flex gap-3 mt-4 flex-wrap">
            <template v-if="socialLinks.length">
              <a
                v-for="link in socialLinks"
                :key="link.uuid"
                :href="link.url"
                :title="link.title"
                class="footer-social"
                target="_blank"
                rel="noopener noreferrer"
              >
                <IconRenderer :icon="link.icon_class || 'bi-link'" />
              </a>
            </template>
            <template v-else>
              <a href="#" class="footer-social"><i class="bi bi-instagram"></i></a>
              <a href="#" class="footer-social"><i class="bi bi-facebook"></i></a>
              <a href="#" class="footer-social"><i class="bi bi-linkedin"></i></a>
            </template>
          </div>
        </div>

        <!-- Columnas de navegacion dinamicas (max 6 por fila, wrap automatico) -->
        <div class="footer-nav-groups">
          <template v-if="navGroups.length">
            <div
              v-for="group in navGroups"
              :key="group.uuid"
              class="footer-col footer-col--nav"
              :style="groupStyle(group)"
            >
              <h6 class="footer-heading">
                <IconRenderer :icon="group.icon_class || 'bi-folder'" extra-class="footer-heading-icon" />
                {{ group.title }}
              </h6>
              <p v-if="group.description" class="footer-group-desc">{{ group.description }}</p>
              <ul class="list-unstyled footer-links">
                <li v-for="link in visibleLinks(group.links)" :key="link.uuid">
                  <a
                    :href="link.url"
                    :target="link.open_new_tab || isExternal(link.url) ? '_blank' : undefined"
                    :rel="link.open_new_tab || isExternal(link.url) ? 'noopener noreferrer' : undefined"
                    @click="onLinkClick(link.url, $event)"
                  >
                    <IconRenderer v-if="link.icon_class" :icon="link.icon_class" extra-class="footer-link-icon" />
                    {{ link.title }}
                  </a>
                </li>
              </ul>
            </div>
          </template>
          <template v-else>
            <div class="footer-col footer-col--nav">
              <h6 class="footer-heading">Tienda</h6>
              <ul class="list-unstyled footer-links">
                <li><RouterLink to="/tienda">Catalogo</RouterLink></li>
                <li><RouterLink to="/alquiler">Alquiler</RouterLink></li>
                <li><RouterLink to="/servicios">Servicios</RouterLink></li>
                <li><RouterLink to="/cotizar">Cotizar</RouterLink></li>
              </ul>
            </div>
            <div class="footer-col footer-col--nav">
              <h6 class="footer-heading">Mi cuenta</h6>
              <ul class="list-unstyled footer-links">
                <li><RouterLink to="/mi-cuenta">Perfil</RouterLink></li>
                <li><RouterLink to="/mi-cuenta/ordenes">Ordenes</RouterLink></li>
                <li><RouterLink to="/mi-cuenta/cotizaciones">Cotizaciones</RouterLink></li>
                <li><RouterLink to="/registro">Registrarse</RouterLink></li>
              </ul>
            </div>
            <div class="footer-col footer-col--nav">
              <h6 class="footer-heading">Empresa</h6>
              <ul class="list-unstyled footer-links">
                <li><a href="#">Nosotros</a></li>
                <li><a href="#terminos" @click="onLinkClick('#terminos', $event)">Terminos de uso</a></li>
                <li><a href="#privacidad" @click="onLinkClick('#privacidad', $event)">Politica de privacidad</a></li>
                <li><a href="/api/docs/">API Docs</a></li>
              </ul>
            </div>
          </template>
        </div>

        <!-- Contacto -->
        <div class="footer-col footer-col--contact">
          <h6 class="footer-heading">Contacto</h6>
          <ul class="list-unstyled footer-links">
            <li v-if="contact?.email" class="text-secondary small">
              <i class="bi bi-envelope me-1"></i>{{ contact.email }}
            </li>
            <li v-else class="text-secondary small">
              <i class="bi bi-envelope me-1"></i>info@sintel.co
            </li>
            <li class="mt-2" v-if="contact?.phone">
              <span class="text-secondary small"><i class="bi bi-telephone me-1"></i>{{ contact.phone }}</span>
            </li>
            <li class="mt-2" v-else>
              <span class="text-secondary small"><i class="bi bi-telephone me-1"></i>+57 300 000 0000</span>
            </li>
            <li class="mt-2" v-if="contact?.address">
              <span class="text-secondary small"><i class="bi bi-geo-alt me-1"></i>{{ contact.address }}</span>
            </li>
            <li class="mt-2" v-else>
              <span class="text-secondary small"><i class="bi bi-geo-alt me-1"></i>Colombia</span>
            </li>
            <li class="mt-2" v-if="contact?.working_hours">
              <span class="text-secondary small"><i class="bi bi-clock me-1"></i>{{ contact.working_hours }}</span>
            </li>
          </ul>
        </div>

      </div>

      <hr class="footer-divider">

      <div class="d-flex flex-column flex-md-row justify-content-between align-items-center py-4 gap-2">
        <p class="text-secondary small mb-0">&copy; {{ year }} Sintel Ecosystem. Todos los derechos reservados.</p>
        <p class="text-secondary small mb-0">Hecho con <i class="bi bi-heart-fill text-danger"></i> en Colombia</p>
      </div>
    </div>

    <LegalTextModal
      :model-value="!!legalDocOpen"
      :doc-type="legalDocOpen || 'terminos'"
      @update:model-value="closeLegalDoc"
    />
  </footer>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import useApi from '@/composables/useApi';
import LegalTextModal from '@/components/auth/kyc/LegalTextModal.vue';
import { LEGAL_DOCS } from '@/components/auth/kyc/legalDocs';
import IconRenderer from '@/components/ui/IconRenderer.vue';
import { useAuthStore } from '@/store/auth';

/**
 * *Override: cuando se pasan (no null), se usan en vez de hacer fetch a
 * core/footer/ -- usado por la Vista Previa de /panel/home-config para
 * reflejar el estado EN MEMORIA del formulario (aun sin guardar). El uso real
 * en CustomerLayout no pasa estas props y sigue haciendo fetch como siempre.
 * Ver ai_skills/frontend/editor/home_render_audit_2026_07_11.md (Fase 3).
 */
const props = defineProps({
  contactOverride:     { type: Object, default: null },
  socialLinksOverride: { type: Array,  default: null },
  navGroupsOverride:   { type: Array,  default: null },
});

const api        = useApi();
const route      = useRoute();
const router     = useRouter();
const authStore  = useAuthStore();
const year       = new Date().getFullYear();
const fetchedContact    = ref(null);
const fetchedSocialLinks = ref([]);
const fetchedNavGroups  = ref([]);
const legalDocOpen = ref(null);

const contact     = computed(() => props.contactOverride     || fetchedContact.value);
const socialLinks = computed(() => props.socialLinksOverride || fetchedSocialLinks.value);
const navGroups   = computed(() => props.navGroupsOverride   || fetchedNavGroups.value);

function groupStyle(group) {
  const style = {};
  if (group.background_color) style.background = group.background_color;
  if (group.text_color) style.color = group.text_color;
  return style;
}

function isExternal(url) {
  return typeof url === 'string' && url.startsWith('http');
}

// Enlaces "solo invitado" (login/registro): el footer viene de un CMS
// generico sin nocion de sesion, asi que sin este filtro un usuario ya
// autenticado seguia viendo "Iniciar Sesion"/"Crear Cuenta" en vez de
// accesos a su cuenta.
const GUEST_ONLY_PATHS = ['/login', '/register'];
function visibleLinks(links) {
  if (!authStore.isAuthenticated) return links;
  return (links || []).filter((link) => !GUEST_ONLY_PATHS.includes(link.url));
}

// Enlaces del footer tipo "#terminos", "#privacidad", etc. abren el modal
// legal correspondiente en vez de navegar/saltar en la pagina.
function onLinkClick(url, event) {
  if (typeof url === 'string' && url.startsWith('#')) {
    const docType = url.slice(1);
    if (LEGAL_DOCS[docType]) {
      event.preventDefault();
      legalDocOpen.value = docType;
      router.replace({ hash: `#${docType}` }).catch(() => {});
    }
  }
}

function closeLegalDoc() {
  legalDocOpen.value = null;
  router.replace({ hash: '' }).catch(() => {});
}

// Soporta enlazar directo a https://sintel.net.co/#terminos y que el modal
// se abra solo al cargar la pagina (ej. desde un correo o WhatsApp).
function openFromHash() {
  const docType = route.hash?.replace('#', '');
  if (docType && LEGAL_DOCS[docType]) {
    legalDocOpen.value = docType;
  }
}

onMounted(async () => {
  openFromHash();
  // En modo preview (props *Override provistas) no hace falta pegarle a la API.
  if (props.contactOverride || props.socialLinksOverride || props.navGroupsOverride) return;
  try {
    const { data } = await api.get('core/footer/');
    fetchedContact.value     = data.contact || null;
    fetchedSocialLinks.value = data.social_links || [];
    fetchedNavGroups.value   = data.groups       || [];
  } catch (err) {
    console.error('[CustomerFooter] Error cargando footer:', err);
  }
});
</script>

<style scoped>
.customer-footer {
  background: #0f172a;
  color: #94a3b8;
}
.footer-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 2rem 1.5rem;
  padding: 3rem 0;
}
.footer-col { min-width: 0; }
.footer-col--brand   { flex: 0 0 260px; max-width: 260px; }
.footer-col--contact { flex: 0 0 220px; max-width: 220px; }

/* Contenedor de columnas dinamicas: reparte el ancho por igual entre las
   columnas que existan (nunca deja "huecos" reservados para columnas que no
   existen) y envuelve a una fila nueva pasado cierto ancho minimo -- eso
   aproxima el max 6/4/3/1 por fila de la Fase 7 sin reservar espacio fijo. */
.footer-nav-groups {
  flex: 1 1 0%;
  display: flex;
  flex-wrap: wrap;
  gap: 2rem 1.5rem;
  min-width: 0;
}
.footer-col--nav { flex: 1 1 0%; min-width: 140px; }

@media (max-width: 1199px) {
  .footer-col--nav { min-width: 190px; }
}
@media (max-width: 991px) {
  .footer-col--nav { min-width: 220px; }
}
@media (max-width: 767px) {
  .footer-grid, .footer-nav-groups { flex-direction: column; }
  .footer-col--brand, .footer-col--contact, .footer-col--nav {
    flex-basis: 100%; max-width: 100%; min-width: 0;
  }
}

.footer-brand {
  font-size: 1.6rem;
  font-weight: 800;
  background: linear-gradient(135deg, #60a5fa 0%, #a5b4fc 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
.footer-heading {
  display: flex;
  align-items: center;
  gap: .4rem;
  font-size: .75rem;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: #e2e8f0;
  margin-bottom: .5rem;
}
.footer-heading-icon { font-size: .85rem; }
.footer-group-desc {
  font-size: .75rem;
  color: #64748b;
  margin-bottom: .75rem;
}
.footer-links li { margin-bottom: .5rem; }
.footer-links a {
  display: inline-flex;
  align-items: center;
  gap: .35rem;
  color: #94a3b8;
  text-decoration: none;
  font-size: .875rem;
  transition: color .15s ease;
}
.footer-links a:hover { color: #60a5fa; }
.footer-link-icon { font-size: .8rem; }
.footer-social {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: rgba(255,255,255,.07);
  color: #94a3b8;
  display: flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  transition: all .15s ease;
}
.footer-social:hover { background: #2563eb; color: white; }
.footer-divider { border-color: rgba(255,255,255,.08); }
</style>
