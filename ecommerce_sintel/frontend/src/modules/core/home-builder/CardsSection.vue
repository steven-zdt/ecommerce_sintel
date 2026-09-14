<template>
  <section>
    <div class="hcb-section-header">
      <div>
        <h2 class="hcb-section-title">Tarjetas</h2>
        <p class="hcb-section-sub">Secciones informativas. Cada grupo configura su layout independientemente.</p>
      </div>
      <div class="d-flex gap-2">
        <button class="hcb-btn" @click="openGroupForm()">
          <i class="bi bi-folder-plus"></i> Nuevo grupo
        </button>
        <button class="hcb-btn hcb-btn--primary" @click="openCardForm()">
          <i class="bi bi-plus-lg"></i> Nueva tarjeta
        </button>
      </div>
    </div>

    <div v-if="loadingCards" class="hcb-loading"><div class="spinner-border text-primary"></div></div>

    <div v-else class="hcb-groups-list">
      <div v-for="(group, gName) in cardsByGroup" :key="gName" class="hcb-group-block">
        <!-- Cabecera de grupo editable -->
        <div class="hcb-group-header">
          <div class="hcb-group-header__left">
            <template v-if="editingGroupName === gName">
              <input
                v-model="editedGroupTitle"
                class="hcb-inline-input"
                placeholder="Titulo del grupo"
                @keyup.enter="saveGroupTitle(gName)"
                @keyup.escape="cancelEditGroupTitle"
              />
              <button class="hcb-icon-btn hcb-icon-btn--sm hcb-icon-btn--success" :disabled="savingGroupTitle" @click="saveGroupTitle(gName)">
                <span v-if="savingGroupTitle" class="spinner-border spinner-border-sm"></span>
                <i v-else class="bi bi-check-lg"></i>
              </button>
              <button class="hcb-icon-btn hcb-icon-btn--sm" @click="cancelEditGroupTitle"><i class="bi bi-x-lg"></i></button>
            </template>
            <template v-else>
              <span class="hcb-group-name">{{ groupTitlesMap[gName] || gName }}</span>
              <button class="hcb-icon-btn hcb-icon-btn--sm" @click="startEditGroupTitle(gName)"><i class="bi bi-pencil"></i></button>
            </template>
            <span class="hcb-badge hcb-badge--gray">{{ group.length }}</span>
          </div>
          <div class="hcb-group-header__right">
            <span class="hcb-chip">{{ GROUP_LAYOUT_LABELS[groupConfigMap[gName]?.layout_type] || 'Grid' }}</span>
            <span class="hcb-chip">{{ groupConfigMap[gName]?.columns || 3 }} col</span>
            <button class="hcb-icon-btn hcb-icon-btn--sm" title="Agregar tarjeta a este grupo" @click="openCardForm(null, gName)">
              <i class="bi bi-plus-lg"></i>
            </button>
            <button class="hcb-icon-btn hcb-icon-btn--sm" title="Configurar grupo" @click="openGroupForm(gName)">
              <i class="bi bi-gear"></i>
            </button>
          </div>
        </div>

        <!-- Tarjetas del grupo -->
        <div v-if="group.length" class="hcb-cards-grid">
          <div v-for="card in group" :key="card.uuid" class="hcb-card-thumb" :style="{ borderTop: `3px solid ${card.background_color}` }">
            <div class="hcb-card-thumb__icon" :style="{ background: card.background_color + '18', color: card.background_color }">
              <i :class="['bi', card.icon_class || 'bi-star']"></i>
            </div>
            <div class="hcb-card-thumb__body">
              <div class="hcb-card-thumb__title">{{ card.title }}</div>
              <div class="hcb-card-thumb__meta">
                <span class="hcb-chip hcb-chip--xs">{{ card.card_type || 'vertical' }}</span>
                <span :class="['hcb-chip hcb-chip--xs', card.is_active ? 'hcb-chip--green' : 'hcb-chip--gray']">
                  {{ card.is_active ? 'Activa' : 'Inactiva' }}
                </span>
              </div>
            </div>
            <div class="hcb-card-thumb__actions">
              <button class="hcb-icon-btn hcb-icon-btn--xs" @click="openCardForm(card)"><i class="bi bi-pencil"></i></button>
              <button class="hcb-icon-btn hcb-icon-btn--xs hcb-icon-btn--danger" @click="deleteCard(card)"><i class="bi bi-trash"></i></button>
            </div>
          </div>
        </div>
        <div v-else class="hcb-empty hcb-empty--sm">
          Sin tarjetas en este grupo.
          <button class="hcb-btn hcb-btn--sm" @click="openCardForm(null, gName)">Agregar la primera</button>
        </div>
      </div>
      <div v-if="!Object.keys(cardsByGroup).length" class="hcb-empty">Sin grupos ni tarjetas configuradas. Crea el primer grupo.</div>
    </div>

    <Teleport to="body">
      <!-- Modal Tarjeta -->
      <BaseModal v-model="showCardModal" :title="editingCard ? 'Editar tarjeta' : 'Nueva tarjeta'" wide body-class="bm-modal__body--two-col">
        <!-- Left: form -->
        <div class="hcb-card-form-col">
          <div class="hcb-form-grid">
            <div class="hcb-field hcb-field--full">
              <label class="hcb-label">Titulo *</label>
              <input v-model="cardForm.title" class="hcb-input" placeholder="Titulo">
            </div>
            <div class="hcb-field hcb-field--full">
              <label class="hcb-label">Subtitulo</label>
              <input v-model="cardForm.subtitle" class="hcb-input" placeholder="Subtitulo">
            </div>
            <div class="hcb-field hcb-field--full">
              <label class="hcb-label">Descripcion</label>
              <textarea v-model="cardForm.description" class="hcb-input" rows="3" placeholder="Descripcion..."></textarea>
            </div>
            <div class="hcb-field">
              <label class="hcb-label">Grupo</label>
              <input v-model="cardForm.group_name" class="hcb-input" placeholder="SECCION_1" list="group-list">
              <datalist id="group-list">
                <option v-for="g in existingGroups" :key="g" :value="g">{{ g }}</option>
              </datalist>
            </div>
            <div class="hcb-field">
              <label class="hcb-label">Tipo visual</label>
              <select v-model="cardForm.card_type" class="hcb-select">
                <option value="vertical">Vertical</option>
                <option value="horizontal">Horizontal</option>
                <option value="premium">Premium</option>
                <option value="compact">Compacta</option>
                <option value="glass">Glass</option>
                <option value="dark">Dark</option>
                <option value="gradient">Gradient</option>
                <option value="image_bg">Imagen de fondo</option>
                <option value="logo">Logo de cliente</option>
              </select>
            </div>
            <div class="hcb-field">
              <label class="hcb-label">Icono Bootstrap</label>
              <input v-model="cardForm.icon_class" class="hcb-input" placeholder="bi-star">
            </div>
            <div class="hcb-field">
              <label class="hcb-label">Color</label>
              <div class="d-flex gap-2 align-items-center">
                <input type="color" v-model="cardForm.background_color" class="hcb-color-input">
                <input v-model="cardForm.background_color" class="hcb-input" style="flex:1" placeholder="#3b82f6">
              </div>
            </div>
            <div class="hcb-field">
              <label class="hcb-label">URL destino</label>
              <input v-model="cardForm.redirect_url" class="hcb-input" placeholder="/pagina">
            </div>
            <div class="hcb-field">
              <label class="hcb-label">Tipo de URL</label>
              <select v-model="cardForm.url_type" class="hcb-select">
                <option value="INTERNA">Interna</option>
                <option value="EXTERNA">Externa</option>
                <option value="ANCHOR">Ancla</option>
              </select>
            </div>
            <div class="hcb-field" v-if="cardForm.url_type === 'EXTERNA'">
              <label class="hcb-label">Abrir en</label>
              <select v-model="cardForm.url_target" class="hcb-select">
                <option value="_self">Misma pestaña</option>
                <option value="_blank">Nueva pestaña</option>
              </select>
            </div>
            <div class="hcb-field">
              <label class="hcb-label">Orden</label>
              <input v-model.number="cardForm.display_order" type="number" class="hcb-input" min="0">
            </div>
            <div class="hcb-field">
              <label class="hcb-label">Prioridad (orden dentro del grupo)</label>
              <input v-model.number="cardForm.priority" type="number" class="hcb-input" min="0">
            </div>
            <div class="hcb-field">
              <label class="hcb-label">Animacion</label>
              <select v-model="cardForm.animation" class="hcb-select">
                <option v-for="a in CARD_ANIMATIONS" :key="a.value" :value="a.value">{{ a.label }}</option>
              </select>
            </div>
            <div class="hcb-field">
              <label class="hcb-label">Texto del badge</label>
              <input v-model="cardForm.badge_text" class="hcb-input" placeholder="Nuevo, Popular...">
            </div>
            <div class="hcb-field">
              <label class="hcb-label">Color del badge</label>
              <div class="d-flex gap-2 align-items-center">
                <input type="color" v-model="cardForm.badge_color" class="hcb-color-input">
                <input v-model="cardForm.badge_color" class="hcb-input" style="flex:1" placeholder="#2563eb">
              </div>
            </div>
            <div class="hcb-field d-flex gap-3">
              <div class="form-check form-switch">
                <input v-model="cardForm.is_active" class="form-check-input" type="checkbox">
                <label class="form-check-label small">Activa</label>
              </div>
              <div class="form-check form-switch">
                <input v-model="cardForm.is_featured" class="form-check-input" type="checkbox">
                <label class="form-check-label small">Destacada</label>
              </div>
            </div>

            <div class="hcb-field hcb-field--full hcb-subheading">Estadisticas (chips)</div>
            <div class="hcb-field hcb-field--full">
              <div v-for="(s, i) in cardForm.stats" :key="i" class="d-flex gap-2 mb-2">
                <input v-model="s.value" class="hcb-input" placeholder="Valor (ej. 8 semanas)">
                <input v-model="s.label" class="hcb-input" placeholder="Etiqueta (ej. Duracion)">
                <button type="button" class="hcb-icon-btn hcb-icon-btn--sm hcb-icon-btn--danger" @click="cardForm.stats.splice(i, 1)">
                  <i class="bi bi-trash"></i>
                </button>
              </div>
              <button type="button" class="hcb-btn hcb-btn--sm" @click="cardForm.stats.push({ value: '', label: '' })">
                <i class="bi bi-plus-lg"></i> Agregar estadistica
              </button>
            </div>

            <div class="hcb-field hcb-field--full hcb-subheading">Boton secundario (opcional)</div>
            <div class="hcb-field">
              <label class="hcb-label">Texto</label>
              <input v-model="cardForm.secondary_label" class="hcb-input" placeholder="Ver mas">
            </div>
            <div class="hcb-field">
              <label class="hcb-label">Icono Bootstrap</label>
              <input v-model="cardForm.secondary_icon" class="hcb-input" placeholder="bi-arrow-right">
            </div>
            <div class="hcb-field hcb-field--full">
              <label class="hcb-label">URL</label>
              <input v-model="cardForm.secondary_url" class="hcb-input" placeholder="/pagina">
            </div>
            <div class="hcb-field">
              <label class="hcb-label">Tipo de URL</label>
              <select v-model="cardForm.secondary_url_type" class="hcb-select">
                <option value="INTERNA">Interna</option>
                <option value="EXTERNA">Externa</option>
                <option value="ANCHOR">Ancla</option>
              </select>
            </div>
            <div class="hcb-field" v-if="cardForm.secondary_url_type === 'EXTERNA'">
              <label class="hcb-label">Abrir en</label>
              <select v-model="cardForm.secondary_target" class="hcb-select">
                <option value="_self">Misma pestaña</option>
                <option value="_blank">Nueva pestaña</option>
              </select>
            </div>
          </div>
          <!-- Imagen de fondo de la tarjeta -->
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Imagen adjunta (opcional)</label>
            <div v-if="cardImagePreview && !cardRemoveImage" class="hcb-media-current">
              <img :src="cardImagePreview" class="hcb-media-current__img" alt="">
              <div class="hcb-media-current__actions">
                <button type="button" class="hcb-btn hcb-btn--danger-sm" @click="removeCardImage">
                  <i class="bi bi-trash me-1"></i>Eliminar imagen
                </button>
                <button type="button" class="hcb-btn hcb-btn--sm" @click="$refs.cardImgInput.click()">
                  <i class="bi bi-arrow-repeat me-1"></i>Reemplazar
                </button>
              </div>
            </div>
            <div v-else class="hcb-upload-area" @click="$refs.cardImgInput.click()">
              <i class="bi bi-image"></i>
              <span>Haz clic para subir imagen</span>
            </div>
            <input ref="cardImgInput" type="file" accept="image/*" class="d-none" @change="handleCardImageSelect">
          </div>
        </div>
        <!-- Right: live preview -->
        <div class="hcb-card-preview-col">
          <div class="hcb-label mb-2">Vista previa</div>
          <div class="hcb-card-live-preview">
            <CardItem :card="cardPreviewData" :visible="true" />
          </div>
        </div>
        <div v-if="cardError" class="alert alert-danger small py-2 mx-3">{{ cardError }}</div>
        <template #footer>
          <button class="hcb-btn" @click="closeCardForm">Cancelar</button>
          <button class="hcb-btn hcb-btn--primary" :disabled="savingCard" @click="saveCard">
            <span v-if="savingCard" class="spinner-border spinner-border-sm me-1"></span>
            {{ editingCard ? 'Guardar cambios' : 'Crear tarjeta' }}
          </button>
        </template>
      </BaseModal>

      <!-- Modal Configuracion de Grupo -->
      <BaseModal v-model="showGroupModal" :title="isNewGroup ? 'Nuevo grupo de tarjetas' : `Configurar grupo — ${groupTitlesMap[editingGroupData] || editingGroupData}`">
        <div class="hcb-form-grid">
          <template v-if="isNewGroup">
            <div class="hcb-field hcb-field--full">
              <label class="hcb-label">Titulo del grupo *</label>
              <input v-model="newGroupTitle" class="hcb-input" placeholder="Casos de Exito" @input="!newGroupSlug && (newGroupSlug = slugify(newGroupTitle))">
            </div>
            <div class="hcb-field hcb-field--full">
              <label class="hcb-label">Identificador interno</label>
              <input v-model="newGroupSlug" class="hcb-input" placeholder="casos_de_exito">
              <span class="hcb-hint">Se genera solo a partir del titulo; puedes ajustarlo si lo necesitas.</span>
            </div>
          </template>
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Subtitulo</label>
            <input v-model="groupForm.subtitle" class="hcb-input" placeholder="Descripcion breve del grupo">
          </div>
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Descripcion</label>
            <textarea v-model="groupForm.description" class="hcb-input" rows="2" placeholder="Texto de apoyo..."></textarea>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Layout</label>
            <select v-model="groupForm.layout_type" class="hcb-select">
              <option value="grid">Grid</option>
              <option value="slider">Slider</option>
              <option value="cards">Cards</option>
              <option value="timeline">Timeline</option>
              <option value="accordion">Accordion</option>
              <option value="tabs">Tabs</option>
              <option value="logos">Logos de clientes</option>
              <option value="marquee">Marquee (rotacion automatica)</option>
            </select>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Columnas</label>
            <select v-model.number="groupForm.columns" class="hcb-select">
              <option :value="1">1</option>
              <option :value="2">2</option>
              <option :value="3">3</option>
              <option :value="4">4</option>
              <option :value="6">6</option>
            </select>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Padding</label>
            <select v-model="groupForm.padding" class="hcb-select">
              <option value="none">Sin padding</option>
              <option value="sm">Pequeno</option>
              <option value="normal">Normal</option>
              <option value="lg">Grande</option>
              <option value="xl">Extra grande</option>
            </select>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Hover</label>
            <select v-model="groupForm.hover" class="hcb-select">
              <option value="lift">Elevar</option>
              <option value="scale">Escalar</option>
              <option value="glow">Resplandor</option>
              <option value="none">Ninguno</option>
            </select>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Color de fondo</label>
            <div class="d-flex gap-2 align-items-center">
              <input type="color" v-model="groupForm.bg_color" class="hcb-color-input">
              <input v-model="groupForm.bg_color" class="hcb-input" style="flex:1" placeholder="#f8fafc">
            </div>
          </div>
          <div class="hcb-field d-flex gap-3">
            <div class="form-check form-switch">
              <input v-model="groupForm.divider" class="form-check-input" type="checkbox">
              <label class="form-check-label small">Divisor</label>
            </div>
            <div class="form-check form-switch">
              <input v-model="groupForm.glass" class="form-check-input" type="checkbox">
              <label class="form-check-label small">Glass</label>
            </div>
          </div>

          <div class="hcb-field hcb-field--full hcb-subheading">Responsive</div>
          <div class="hcb-field">
            <label class="hcb-label">Columnas tablet</label>
            <select v-model.number="groupForm.columns_tablet" class="hcb-select">
              <option :value="1">1</option>
              <option :value="2">2</option>
              <option :value="3">3</option>
              <option :value="4">4</option>
            </select>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Columnas mobile</label>
            <select v-model.number="groupForm.columns_mobile" class="hcb-select">
              <option :value="1">1</option>
              <option :value="2">2</option>
            </select>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Espaciado (gap, rem)</label>
            <input v-model.number="groupForm.gap" type="number" step="0.25" min="0" class="hcb-input">
          </div>

          <template v-if="groupForm.layout_type === 'slider'">
            <div class="hcb-field hcb-field--full hcb-subheading">Carrusel</div>
            <div class="hcb-field d-flex gap-3">
              <div class="form-check form-switch">
                <input v-model="groupForm.carousel_autoplay" class="form-check-input" type="checkbox">
                <label class="form-check-label small">Auto scroll</label>
              </div>
              <div class="form-check form-switch">
                <input v-model="groupForm.carousel_loop" class="form-check-input" type="checkbox">
                <label class="form-check-label small">Loop</label>
              </div>
              <div class="form-check form-switch">
                <input v-model="groupForm.show_arrows" class="form-check-input" type="checkbox">
                <label class="form-check-label small">Flechas</label>
              </div>
              <div class="form-check form-switch">
                <input v-model="groupForm.show_indicators" class="form-check-input" type="checkbox">
                <label class="form-check-label small">Indicadores</label>
              </div>
            </div>
            <div class="hcb-field" v-if="groupForm.carousel_autoplay">
              <label class="hcb-label">Velocidad (px/s)</label>
              <input v-model.number="groupForm.carousel_speed" type="number" min="1" class="hcb-input">
            </div>
          </template>

          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Imagen de fondo (opcional)</label>
            <div v-if="groupBgImagePreview && !groupRemoveBgImage" class="hcb-media-current">
              <img :src="groupBgImagePreview" class="hcb-media-current__img" alt="">
              <div class="hcb-media-current__actions">
                <button type="button" class="hcb-btn hcb-btn--danger-sm" @click="removeGroupBgImage">
                  <i class="bi bi-trash me-1"></i>Eliminar imagen
                </button>
                <button type="button" class="hcb-btn hcb-btn--sm" @click="$refs.groupBgImgInput.click()">
                  <i class="bi bi-arrow-repeat me-1"></i>Reemplazar
                </button>
              </div>
            </div>
            <div v-else class="hcb-upload-area" @click="$refs.groupBgImgInput.click()">
              <i class="bi bi-image"></i>
              <span>Haz clic para subir imagen</span>
            </div>
            <input ref="groupBgImgInput" type="file" accept="image/*" class="d-none" @change="handleGroupBgImageSelect">
          </div>
        </div>
        <div v-if="groupError" class="alert alert-danger small py-2 mt-2">{{ groupError }}</div>
        <template #footer>
          <button v-if="!isNewGroup" class="hcb-btn hcb-btn--danger-sm me-auto" @click="deleteGroup">
            <i class="bi bi-trash me-1"></i>Eliminar grupo
          </button>
          <button class="hcb-btn" @click="closeGroupForm">Cancelar</button>
          <button class="hcb-btn hcb-btn--primary" :disabled="savingGroup" @click="saveGroup">
            <span v-if="savingGroup" class="spinner-border spinner-border-sm me-1"></span>
            {{ isNewGroup ? 'Crear grupo' : 'Guardar cambios' }}
          </button>
        </template>
      </BaseModal>
    </Teleport>
  </section>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { useCoreAdminStore } from '@/store/coreAdmin';
import BaseModal from '@/components/base/BaseModal.vue';
import CardItem from '@/components/ui/home/cards/CardItem.vue';
import { ANIMATIONS as CARD_ANIMATIONS } from '@/constants/animations';
import { buildGroupMaps } from './cardGroupsUtil.js';

const toast = useToast();
const store = useCoreAdminStore();
const { cards, cardsLoading: loadingCards, cardGroups } = storeToRefs(store);

const showCardModal = ref(false);
const editingCard  = ref(null);
const savingCard   = ref(false);
const cardError    = ref('');
const cardImageFile      = ref(null);
const cardImagePreview   = ref('');
const cardRemoveImage    = ref(false);
const groupTitlesMap   = ref({});
const groupConfigMap   = ref({});
const editingGroupName = ref(null);
const editedGroupTitle = ref('');
const savingGroupTitle = ref(false);

const defaultCardForm = () => ({
  title: '', subtitle: '', description: '',
  group_name: '', icon_class: 'bi-star', background_color: '#3b82f6',
  redirect_url: '', display_order: 0, is_active: true,
  card_type: 'vertical', animation: '', is_featured: false, priority: 0,
  badge_text: '', badge_color: '#2563eb',
  url_type: 'INTERNA', url_target: '_self', stats: [],
  secondary_label: '', secondary_icon: '', secondary_url: '',
  secondary_url_type: 'INTERNA', secondary_target: '_self',
});
const cardForm = ref(defaultCardForm());

// cardForm no incluye 'image' (se trackea aparte via cardImagePreview) --
// CardItem.vue si lo espera, se mezcla aqui para la vista previa real.
const cardPreviewData = computed(() => ({ ...cardForm.value, image: cardImagePreview.value }));

const cardsByGroup = computed(() => {
  const groups = {};
  // Sembrar grupos ya creados (via HomeCardGroup) aunque todavia no tengan
  // ninguna tarjeta -- de lo contrario un grupo recien creado desaparece de
  // esta vista hasta que se le agregue la primera tarjeta.
  for (const gName of Object.keys(groupTitlesMap.value)) {
    groups[gName] = [];
  }
  for (const c of cards.value) {
    if (!groups[c.group_name]) groups[c.group_name] = [];
    groups[c.group_name].push(c);
  }
  return groups;
});
const existingGroups = computed(() => Object.keys(cardsByGroup.value));

async function fetchCards() {
  await store.fetchCards();
}
// groupTitlesMap/groupConfigMap se reconstruyen reactivamente cada vez que
// store.cardGroups cambia (watch immediate, no un fetch-y-copia puntual) --
// asi quedan siempre en sync sin importar quien dispare el refetch (el padre
// en su carga inicial, o esta seccion despues de sus propias mutaciones).
// Ver home-builder/cardGroupsUtil.js: la misma funcion pura la usa el padre
// para el panel de preview compartido, ambos derivando de la MISMA lista del
// store -- sin estado duplicado que se pueda desincronizar.
watch(cardGroups, (list) => {
  const { titleMap, configMap } = buildGroupMaps(list);
  groupTitlesMap.value = titleMap;
  groupConfigMap.value = configMap;
}, { immediate: true, deep: true });
function startEditGroupTitle(gName) {
  editingGroupName.value = gName;
  editedGroupTitle.value = groupTitlesMap.value[gName] || gName;
}
function cancelEditGroupTitle() { editingGroupName.value = null; }
async function saveGroupTitle(gName) {
  if (!editedGroupTitle.value.trim()) return;
  savingGroupTitle.value = true;
  // Enviar siempre la config actual completa -- el endpoint es un upsert
  // "todo o nada": cualquier campo omitido vuelve a su default de serializer
  // (layout_type/columns/glass/hover/etc quedarian pisados si solo mandamos
  // name+title).
  const current = groupConfigMap.value[gName] || {};
  const res = await store.upsertCardGroup({
    name: gName,
    title: editedGroupTitle.value.trim(),
    display_order: current.display_order || 0,
    is_visible: current.is_visible !== false,
    subtitle: current.subtitle || '', description: current.description || '',
    bg_color: current.bg_color || '', layout_type: current.layout_type || 'grid',
    columns: current.columns || 3, padding: current.padding || 'normal',
    divider: current.divider || false, glass: current.glass || false, hover: current.hover || 'lift',
    columns_tablet: current.columns_tablet || 2, columns_mobile: current.columns_mobile || 1,
    gap: current.gap != null ? Number(current.gap) : 1.25,
    carousel_autoplay: current.carousel_autoplay || false,
    carousel_loop: current.carousel_loop !== false,
    carousel_speed: current.carousel_speed || 40,
    show_arrows: current.show_arrows !== false,
    show_indicators: current.show_indicators !== false,
  });
  if (res.ok) {
    editingGroupName.value = null;
    toast.success('Titulo actualizado.');
    await store.fetchCardGroups();
  } else {
    toast.error('Error al guardar titulo.');
  }
  savingGroupTitle.value = false;
}
// ── Configuracion de grupo (modal) ──────────────────────────────────────────────
const GROUP_LAYOUT_LABELS = {
  grid: 'Grid', slider: 'Slider', cards: 'Cards', timeline: 'Timeline',
  accordion: 'Accordion', tabs: 'Tabs', logos: 'Logos', marquee: 'Marquee',
};

const showGroupModal    = ref(false);
const editingGroupData  = ref(null);
const savingGroup       = ref(false);
const groupError        = ref('');
const groupBgImageFile    = ref(null);
const groupBgImagePreview = ref('');
const groupRemoveBgImage  = ref(false);

const defaultGroupForm = () => ({
  subtitle: '', description: '', bg_color: '',
  layout_type: 'grid', columns: 3, padding: 'normal',
  divider: false, glass: false, hover: 'lift',
  columns_tablet: 2, columns_mobile: 1, gap: 1.25,
  carousel_autoplay: false, carousel_loop: true, carousel_speed: 40,
  show_arrows: true, show_indicators: true,
});
const groupForm = ref(defaultGroupForm());
const isNewGroup = computed(() => editingGroupData.value === null);
const newGroupTitle = ref('');
const newGroupSlug = ref('');

function slugify(text) {
  return text.toLowerCase().trim()
    .normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
}

function openGroupForm(gName = null) {
  editingGroupData.value = gName;
  groupError.value = '';
  groupBgImageFile.value = null;
  groupRemoveBgImage.value = false;
  newGroupTitle.value = '';
  newGroupSlug.value = '';
  const cfg = gName ? (groupConfigMap.value[gName] || {}) : {};
  groupBgImagePreview.value = cfg.bg_image || '';
  groupForm.value = {
    subtitle: cfg.subtitle || '', description: cfg.description || '',
    bg_color: cfg.bg_color || '', layout_type: cfg.layout_type || 'grid',
    columns: cfg.columns || 3, padding: cfg.padding || 'normal',
    divider: cfg.divider || false, glass: cfg.glass || false, hover: cfg.hover || 'lift',
    columns_tablet: cfg.columns_tablet || 2, columns_mobile: cfg.columns_mobile || 1,
    gap: cfg.gap != null ? Number(cfg.gap) : 1.25,
    carousel_autoplay: cfg.carousel_autoplay || false,
    carousel_loop: cfg.carousel_loop !== false,
    carousel_speed: cfg.carousel_speed || 40,
    show_arrows: cfg.show_arrows !== false,
    show_indicators: cfg.show_indicators !== false,
  };
  showGroupModal.value = true;
}
function closeGroupForm() {
  showGroupModal.value = false;
  editingGroupData.value = null;
}
async function deleteGroup() {
  const gName = editingGroupData.value;
  const count = (cardsByGroup.value[gName] || []).length;
  const msg = count
    ? `Este grupo tiene ${count} tarjeta(s); no se eliminaran, pero quedaran sin grupo visual. Eliminar "${groupTitlesMap.value[gName] || gName}"?`
    : `Eliminar el grupo "${groupTitlesMap.value[gName] || gName}"?`;
  if (!confirm(msg)) return;
  const uuid = groupConfigMap.value[gName]?.uuid;
  const res = uuid ? await store.deleteCardGroup(uuid) : { ok: true };
  if (res.ok) {
    toast.success('Grupo eliminado.');
    closeGroupForm();
    await store.fetchCardGroups();
  } else {
    toast.error('No se pudo eliminar el grupo.');
  }
}
function handleGroupBgImageSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  groupBgImageFile.value    = file;
  groupRemoveBgImage.value  = false;
  groupBgImagePreview.value = URL.createObjectURL(file);
}
function removeGroupBgImage() {
  groupBgImageFile.value    = null;
  groupRemoveBgImage.value  = true;
  groupBgImagePreview.value = '';
}
async function saveGroup() {
  let gName = editingGroupData.value;
  if (isNewGroup.value) {
    if (!newGroupTitle.value.trim()) { groupError.value = 'El titulo del grupo es requerido.'; return; }
    gName = (newGroupSlug.value.trim() && slugify(newGroupSlug.value)) || slugify(newGroupTitle.value);
    if (!gName) { groupError.value = 'No se pudo generar un identificador valido para el grupo.'; return; }
    if (groupTitlesMap.value[gName]) { groupError.value = `Ya existe un grupo con el identificador "${gName}".`; return; }
  }
  savingGroup.value = true; groupError.value = '';
  const current = isNewGroup.value ? {} : (groupConfigMap.value[gName] || {});
  const payload = {
    name: gName,
    title: isNewGroup.value ? newGroupTitle.value.trim() : (groupTitlesMap.value[gName] || gName),
    display_order: current.display_order || 0,
    is_visible: current.is_visible !== false,
    ...groupForm.value,
  };
  let sendPayload = payload;
  if (groupBgImageFile.value || groupRemoveBgImage.value) {
    const fd = new FormData();
    Object.entries(payload).forEach(([k, v]) => fd.append(k, v));
    if (groupBgImageFile.value) fd.append('bg_image', groupBgImageFile.value);
    if (groupRemoveBgImage.value) fd.append('remove_bg_image', 'true');
    sendPayload = fd;
  }
  const res = await store.upsertCardGroup(sendPayload);
  if (res.ok) {
    toast.success(isNewGroup.value ? 'Grupo creado.' : 'Grupo actualizado.');
    closeGroupForm();
    await store.fetchCardGroups();
  } else {
    groupError.value = res.error?.response?.data?.detail || 'Error al guardar el grupo.';
  }
  savingGroup.value = false;
}
function openCardForm(card = null, presetGroupName = '') {
  editingCard.value    = card;
  cardError.value      = '';
  cardImageFile.value  = null;
  cardRemoveImage.value = false;
  cardImagePreview.value = card?.image || '';
  cardForm.value = card ? {
    title: card.title, subtitle: card.subtitle || '',
    description: card.description || '', group_name: card.group_name,
    icon_class: card.icon_class, background_color: card.background_color,
    redirect_url: card.redirect_url || '', display_order: card.display_order ?? 0,
    is_active: card.is_active, card_type: card.card_type || 'vertical',
    animation: card.animation || '', is_featured: card.is_featured || false,
    priority: card.priority || 0, badge_text: card.badge_text || '',
    badge_color: card.badge_color || '#2563eb',
    url_type: card.url_type || 'INTERNA', url_target: card.url_target || '_self',
    stats: Array.isArray(card.stats) ? card.stats.map(s => ({ ...s })) : [],
    secondary_label: card.secondary_label || '', secondary_icon: card.secondary_icon || '',
    secondary_url: card.secondary_url || '',
    secondary_url_type: card.secondary_url_type || 'INTERNA',
    secondary_target: card.secondary_target || '_self',
  } : { ...defaultCardForm(), group_name: presetGroupName };
  showCardModal.value = true;
}
function closeCardForm() {
  showCardModal.value = false;
  editingCard.value = null;
  cardImageFile.value = null;
  cardImagePreview.value = '';
  cardRemoveImage.value = false;
}
function handleCardImageSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  cardImageFile.value    = file;
  cardRemoveImage.value  = false;
  cardImagePreview.value = URL.createObjectURL(file);
}
function removeCardImage() {
  cardImageFile.value    = null;
  cardRemoveImage.value  = true;
  cardImagePreview.value = '';
}
async function saveCard() {
  if (!cardForm.value.title.trim() || !cardForm.value.group_name.trim()) {
    cardError.value = 'Titulo y grupo son requeridos.'; return;
  }
  savingCard.value = true; cardError.value = '';
  const hasMedia = cardImageFile.value || cardRemoveImage.value;
  let sendPayload = cardForm.value;
  if (hasMedia) {
    const fd = new FormData();
    Object.entries(cardForm.value).forEach(([k, v]) => {
      fd.append(k, k === 'stats' ? JSON.stringify(v) : v);
    });
    if (cardImageFile.value) fd.append('image', cardImageFile.value);
    if (cardRemoveImage.value) fd.append('remove_image', 'true');
    sendPayload = fd;
  }
  const res = editingCard.value
    ? await store.updateCard(editingCard.value.uuid, sendPayload)
    : await store.createCard(sendPayload);
  if (res.ok) {
    toast.success(editingCard.value ? 'Tarjeta actualizada.' : 'Tarjeta creada.');
    closeCardForm();
    await fetchCards();
  } else {
    cardError.value = res.error?.response?.data?.detail || 'Error al guardar.';
  }
  savingCard.value = false;
}
async function deleteCard(card) {
  if (!confirm(`Eliminar tarjeta "${card.title}"?`)) return;
  const res = await store.deleteCard(card.uuid);
  if (res.ok) {
    toast.success('Tarjeta eliminada.');
    await fetchCards();
  } else {
    toast.error('No se pudo eliminar.');
  }
}

// El fetch INICIAL de cards/cardGroups lo dispara el padre (onMounted, para
// que el sidebar y el preview compartido tengan datos) -- el watch de arriba
// ya se encarga de construir los mapas locales en cuanto ese fetch resuelve.
</script>
