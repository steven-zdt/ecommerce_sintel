<template>
  <Teleport to="body">
  <div class="mb-overlay" @click.self="$emit('close')">
    <div class="mb-shell">

      <!-- HEADER -->
      <header class="mb-header">
        <div class="mb-header__info">
          <div class="mb-header__dot" :style="{ background: form.color_primary }"></div>
          <span class="mb-header__title">
            {{ props.module ? 'Editar sección' : 'Nueva sección' }}
            <span v-if="form.custom_label" class="mb-header__name">— {{ form.custom_label }}</span>
          </span>
        </div>
        <button class="mb-close" @click="$emit('close')"><i class="bi bi-x-lg"></i></button>
      </header>

      <!-- TABS -->
      <nav class="mb-tabs">
        <button
          v-for="t in TABS" :key="t.id"
          :class="['mb-tab', activeTab === t.id && 'mb-tab--active']"
          @click="activeTab = t.id"
        >
          <i :class="['bi', t.icon]"></i>
          <span>{{ t.label }}</span>
        </button>
      </nav>

      <!-- BODY -->
      <div class="mb-body">
        <div class="mb-form">

          <!-- S1: GENERAL -->
          <div v-show="activeTab === 'general'" class="mb-section">
            <div class="mb-section-title"><i class="bi bi-sliders me-2"></i>Información General</div>
            <div class="mb-grid">
              <div v-if="!props.module" class="mb-field mb-field--full">
                <label class="mb-label">Clave interna *</label>
                <input v-model="form.module_key" class="mb-input" placeholder="productos, blog, servicios...">
                <span class="mb-hint">Identificador único. Solo letras, números y guiones.</span>
              </div>
              <div class="mb-field">
                <label class="mb-label">Nombre del módulo *</label>
                <input v-model="form.custom_label" class="mb-input" placeholder="Productos destacados">
              </div>
              <div class="mb-field">
                <label class="mb-label">Subtítulo público</label>
                <input v-model="form.public_subtitle" class="mb-input" placeholder="Descripción breve de la sección">
              </div>
              <div class="mb-field mb-field--full">
                <label class="mb-label">Descripción interna</label>
                <textarea v-model="form.description" class="mb-input" rows="2" placeholder="Notas internas..."></textarea>
              </div>
              <div class="mb-field">
                <label class="mb-label">URL destino</label>
                <input v-model="form.custom_url" class="mb-input" placeholder="/tienda">
              </div>
              <div class="mb-field">
                <label class="mb-label">Orden</label>
                <input v-model.number="form.display_order" type="number" class="mb-input" min="0">
              </div>
              <div class="mb-field">
                <label class="mb-label">Items destacados</label>
                <input v-model.number="form.featured_items_limit" type="number" class="mb-input" min="1" max="24">
              </div>
              <div class="mb-field mb-field--full">
                <div class="form-check form-switch">
                  <input v-model="form.is_visible" class="form-check-input" type="checkbox" id="mb-visible">
                  <label class="form-check-label" for="mb-visible">Visible en la home</label>
                </div>
              </div>
            </div>
          </div>

          <!-- S2: PRESENTATION TYPE -->
          <div v-show="activeTab === 'presentation'" class="mb-section">
            <div class="mb-section-title"><i class="bi bi-layout-three-columns me-2"></i>Tipo de presentación</div>
            <p class="mb-section-sub">Selecciona cómo se renderizará visualmente esta sección.</p>
            <div class="mb-pt-grid">
              <button
                v-for="pt in PRESENTATION_TYPES" :key="pt.value"
                :class="['mb-pt-card', form.display_type === pt.value && 'mb-pt-card--selected']"
                @click="form.display_type = pt.value"
                :title="pt.label"
              >
                <div :class="['mb-pt-thumb', `mb-pt-thumb--${pt.value}`]">
                  <div v-for="n in pt.items" :key="n" class="mb-pt-item"></div>
                </div>
                <span class="mb-pt-label">{{ pt.label }}</span>
                <i v-if="form.display_type === pt.value" class="bi bi-check-circle-fill mb-pt-check"></i>
              </button>
            </div>
          </div>

          <!-- S3: STYLE -->
          <div v-show="activeTab === 'style'" class="mb-section">
            <div class="mb-section-title"><i class="bi bi-palette me-2"></i>Estilo Visual</div>

            <div class="mb-subsection">Tema rápido</div>
            <div class="mb-theme-grid">
              <button
                v-for="th in THEMES" :key="th.value"
                :class="['mb-theme-card', form.theme === th.value && 'mb-theme-card--active']"
                @click="applyTheme(th.value)"
              >
                <div class="mb-theme-swatch" :style="th.swatch"></div>
                <span>{{ th.label }}</span>
              </button>
            </div>

            <div class="mb-subsection mt-3">Colores</div>
            <div class="mb-grid">
              <div v-for="col in COLOR_FIELDS" :key="col.key" class="mb-field">
                <label class="mb-label">{{ col.label }}</label>
                <div class="d-flex gap-2 align-items-center">
                  <input type="color" v-model="form[col.key]" class="mb-color-input">
                  <input v-model="form[col.key]" class="mb-input" :placeholder="col.placeholder" style="flex:1">
                </div>
              </div>
            </div>

            <div class="mb-subsection mt-3">Tipografía</div>
            <div class="mb-grid">
              <div class="mb-field">
                <label class="mb-label">Tamaño título (rem)</label>
                <div class="d-flex gap-2 align-items-center">
                  <input v-model.number="form.title_size" type="range" min="1" max="5" step="0.25" class="form-range" style="flex:1">
                  <span class="mb-range-val">{{ form.title_size }}rem</span>
                </div>
              </div>
              <div class="mb-field">
                <label class="mb-label">Tamaño subtítulo (rem)</label>
                <div class="d-flex gap-2 align-items-center">
                  <input v-model.number="form.subtitle_size" type="range" min="0.7" max="2" step="0.1" class="form-range" style="flex:1">
                  <span class="mb-range-val">{{ form.subtitle_size }}rem</span>
                </div>
              </div>
              <div class="mb-field">
                <label class="mb-label">Peso tipográfico</label>
                <select v-model="form.font_weight" class="mb-select">
                  <option value="400">Normal (400)</option>
                  <option value="500">Medium (500)</option>
                  <option value="600">Semibold (600)</option>
                  <option value="700">Bold (700)</option>
                  <option value="800">Extrabold (800)</option>
                  <option value="900">Black (900)</option>
                </select>
              </div>
              <div class="mb-field">
                <label class="mb-label">Alineación</label>
                <div class="mb-align-group">
                  <button v-for="al in ['left','center','right']" :key="al"
                    :class="['mb-align-btn', form.text_align === al && 'active']"
                    @click="form.text_align = al">
                    <i :class="`bi bi-text-${al}`"></i>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- S4: ICON -->
          <div v-show="activeTab === 'icon'" class="mb-section">
            <div class="mb-section-title"><i class="bi bi-star me-2"></i>Iconografía</div>
            <div class="mb-grid">
              <div class="mb-field mb-field--full">
                <label class="mb-label">Clase Bootstrap Icons</label>
                <div class="d-flex gap-2 align-items-center">
                  <div class="mb-icon-preview" :style="{ background: form.color_primary + '22', color: form.color_primary }">
                    <i :class="['bi', form.custom_icon || 'bi-grid']"></i>
                  </div>
                  <input v-model="form.custom_icon" class="mb-input" placeholder="bi-shop" style="flex:1">
                </div>
              </div>
            </div>
            <div class="mb-subsection mt-3">Íconos frecuentes</div>
            <div class="mb-icon-grid">
              <button
                v-for="ic in COMMON_ICONS" :key="ic"
                :class="['mb-icon-btn', form.custom_icon === ic && 'active']"
                @click="form.custom_icon = ic"
                :title="ic"
              >
                <i :class="['bi', ic]"></i>
              </button>
            </div>
          </div>

          <!-- S5: MEDIA -->
          <div v-show="activeTab === 'media'" class="mb-section">
            <div class="mb-section-title"><i class="bi bi-image me-2"></i>Imagen del módulo</div>
            <div class="mb-grid">
              <div class="mb-field mb-field--full">
                <label class="mb-label">Imagen de fondo</label>
                <div
                  class="mb-upload-zone"
                  @click="$refs.bgImgInput.click()"
                  @dragover.prevent="imgDragging = true"
                  @dragleave="imgDragging = false"
                  @drop.prevent="handleImgDrop"
                  :class="imgDragging && 'mb-upload-zone--drag'"
                >
                  <img v-if="bgImgPreview && !removeImg" :src="bgImgPreview" class="mb-upload-zone__preview" alt="">
                  <div v-else class="mb-upload-zone__ph">
                    <i class="bi bi-cloud-upload" style="font-size:2rem"></i>
                    <span>Haz clic o arrastra imagen</span>
                  </div>
                  <input ref="bgImgInput" type="file" accept="image/*" class="d-none" @change="handleImgSelect">
                </div>
                <div v-if="bgImgPreview && !removeImg" class="d-flex gap-2 mt-2">
                  <button class="mb-btn-sm" @click.stop="$refs.bgImgInput.click()"><i class="bi bi-arrow-repeat me-1"></i>Cambiar</button>
                  <button class="mb-btn-sm mb-btn-sm--danger" @click.stop="removeImg = true; bgImgPreview = ''"><i class="bi bi-trash me-1"></i>Eliminar</button>
                </div>
              </div>
              <div class="mb-field">
                <label class="mb-label">Filtro de imagen</label>
                <select v-model="form.bg_filter" class="mb-select">
                  <option value="none">Sin filtro</option>
                  <option value="grayscale">Escala de grises</option>
                  <option value="blur">Desenfoque</option>
                  <option value="brightness">Brillo alto</option>
                  <option value="sepia">Sepia</option>
                </select>
              </div>
            </div>
          </div>

          <!-- S6: LAYOUT / DISTRIBUTION -->
          <div v-show="activeTab === 'layout'" class="mb-section">
            <div class="mb-section-title"><i class="bi bi-grid-3x3 me-2"></i>Distribución</div>
            <div class="mb-subsection">Columnas (desktop)</div>
            <div class="mb-cols-picker">
              <button v-for="n in [1,2,3,4,5,6]" :key="n"
                :class="['mb-col-btn', form.columns === n && 'active']"
                @click="form.columns = n">
                <div class="mb-col-vis">
                  <div v-for="i in n" :key="i" class="mb-col-bar"></div>
                </div>
                <span>{{ n }}</span>
              </button>
            </div>
            <div class="mb-grid mt-3">
              <div class="mb-field">
                <label class="mb-label">Espaciado (padding)</label>
                <select v-model="form.padding" class="mb-select">
                  <option value="none">Sin padding</option>
                  <option value="sm">Pequeño</option>
                  <option value="normal">Normal</option>
                  <option value="lg">Grande</option>
                  <option value="xl">Extra grande</option>
                </select>
              </div>
              <div class="mb-field">
                <label class="mb-label">Gap entre items (rem)</label>
                <input v-model.number="form.gap" type="number" class="mb-input" min="0" max="4" step="0.25">
              </div>
              <div class="mb-field">
                <label class="mb-label">Altura mínima (px)</label>
                <input v-model="form.min_height" class="mb-input" placeholder="Sin mínimo">
              </div>
              <div class="mb-field">
                <label class="mb-label">Ancho máximo (px)</label>
                <input v-model="form.max_width" class="mb-input" placeholder="Sin máximo">
              </div>
            </div>
          </div>

          <!-- S7: ANIMATIONS -->
          <div v-show="activeTab === 'animation'" class="mb-section">
            <div class="mb-section-title"><i class="bi bi-stars me-2"></i>Animaciones</div>
            <div class="mb-anim-grid">
              <button
                v-for="a in ANIMATIONS" :key="a.value"
                :class="['mb-anim-card', form.animation_type === a.value && 'active']"
                @click="form.animation_type = a.value"
              >
                <i :class="['bi', a.icon]"></i>
                <span>{{ a.label }}</span>
              </button>
            </div>
            <div class="mb-grid mt-3">
              <div class="mb-field">
                <label class="mb-label">Duración (ms)</label>
                <div class="d-flex gap-2 align-items-center">
                  <input v-model.number="form.animation_duration" type="range" min="100" max="2000" step="100" class="form-range" style="flex:1">
                  <span class="mb-range-val">{{ form.animation_duration }}ms</span>
                </div>
              </div>
              <div class="mb-field">
                <label class="mb-label">Delay (ms)</label>
                <div class="d-flex gap-2 align-items-center">
                  <input v-model.number="form.animation_delay" type="range" min="0" max="1000" step="50" class="form-range" style="flex:1">
                  <span class="mb-range-val">{{ form.animation_delay }}ms</span>
                </div>
              </div>
              <div class="mb-field">
                <label class="mb-label">Repetir</label>
                <div class="form-check form-switch mt-1">
                  <input v-model="form.animation_repeat" class="form-check-input" type="checkbox" id="mb-anim-repeat">
                  <label class="form-check-label" for="mb-anim-repeat">Repetir animación</label>
                </div>
              </div>
            </div>
          </div>

          <!-- S8: CONTENT TOGGLES -->
          <div v-show="activeTab === 'content'" class="mb-section">
            <div class="mb-section-title"><i class="bi bi-toggles me-2"></i>Contenido</div>
            <p class="mb-section-sub">Define qué información se muestra en cada elemento.</p>
            <div class="mb-toggle-grid">
              <label v-for="cf in CONTENT_FIELDS" :key="cf.key" class="mb-toggle-row">
                <div class="mb-toggle-info">
                  <i :class="['bi', cf.icon]"></i>
                  <span>{{ cf.label }}</span>
                </div>
                <div class="form-check form-switch mb-0">
                  <input v-model="form[cf.key]" class="form-check-input" type="checkbox">
                </div>
              </label>
            </div>

            <div v-if="form.show_badge" class="mb-grid mt-3">
              <div class="mb-field">
                <label class="mb-label">Texto del badge</label>
                <input v-model="form.badge_text" class="mb-input" placeholder="Nuevo">
              </div>
              <div class="mb-field">
                <label class="mb-label">Color del badge</label>
                <div class="d-flex gap-2 align-items-center">
                  <input type="color" v-model="form.badge_color" class="mb-color-input">
                  <input v-model="form.badge_color" class="mb-input" style="flex:1">
                </div>
              </div>
            </div>

            <div v-if="form.show_counter" class="mt-3">
              <div class="mb-section-title mb-section-title--sm"><i class="bi bi-graph-up me-2"></i>Estadísticas</div>
              <div v-for="(st, i) in form.stats" :key="i" class="mb-grid mb-stat-row">
                <div class="mb-field">
                  <label class="mb-label">Valor</label>
                  <input v-model="st.value" class="mb-input" placeholder="+500">
                </div>
                <div class="mb-field">
                  <label class="mb-label">Etiqueta</label>
                  <input v-model="st.label" class="mb-input" placeholder="Instalaciones">
                </div>
                <button class="mb-btn mb-stat-remove" @click="form.stats.splice(i, 1)"><i class="bi bi-trash"></i></button>
              </div>
              <button class="mb-btn mt-2" @click="form.stats.push({ value: '', label: '' })">
                <i class="bi bi-plus-lg me-1"></i>Agregar estadística
              </button>
            </div>
          </div>

          <!-- S9: BUTTONS -->
          <div v-show="activeTab === 'buttons'" class="mb-section">
            <div class="mb-section-title"><i class="bi bi-cursor me-2"></i>Botones CTA</div>
            <div class="mb-grid">
              <div class="mb-field">
                <label class="mb-label">Texto del botón</label>
                <input v-model="form.btn_text" class="mb-input" placeholder="Ver más">
              </div>
              <div class="mb-field">
                <label class="mb-label">Color</label>
                <div class="d-flex gap-2 align-items-center">
                  <input type="color" v-model="form.btn_color" class="mb-color-input">
                  <input v-model="form.btn_color" class="mb-input" style="flex:1">
                </div>
              </div>
              <div class="mb-field">
                <label class="mb-label">Ícono Bootstrap</label>
                <input v-model="form.btn_icon" class="mb-input" placeholder="bi-arrow-right">
              </div>
              <div class="mb-field">
                <label class="mb-label">Estilo</label>
                <div class="mb-btn-style-group">
                  <button v-for="s in ['filled','outline','ghost','minimal']" :key="s"
                    :class="['mb-btn-style-opt', form.btn_style === s && 'active']"
                    @click="form.btn_style = s">
                    {{ s }}
                  </button>
                </div>
              </div>
              <div class="mb-field">
                <label class="mb-label">Posición</label>
                <select v-model="form.btn_position" class="mb-select">
                  <option value="bottom">Abajo</option>
                  <option value="top">Arriba</option>
                  <option value="inline">Inline</option>
                  <option value="overlay">Overlay</option>
                </select>
              </div>
              <div class="mb-field">
                <label class="mb-label">Apertura</label>
                <select v-model="form.btn_target" class="mb-select">
                  <option value="_self">Misma pestaña</option>
                  <option value="_blank">Nueva pestaña</option>
                </select>
              </div>
            </div>
          </div>

          <!-- S10: BACKGROUND -->
          <div v-show="activeTab === 'background'" class="mb-section">
            <div class="mb-section-title"><i class="bi bi-paint-bucket me-2"></i>Fondo</div>
            <div class="mb-bg-type-grid">
              <button v-for="bg in BG_TYPES" :key="bg.value"
                :class="['mb-bg-card', form.bg_type === bg.value && 'active']"
                @click="form.bg_type = bg.value">
                <div :class="['mb-bg-swatch', `mb-bg-swatch--${bg.value}`]"></div>
                <span>{{ bg.label }}</span>
              </button>
            </div>
            <div class="mb-grid mt-3">
              <template v-if="form.bg_type === 'color'">
                <div class="mb-field mb-field--full">
                  <label class="mb-label">Color de fondo</label>
                  <div class="d-flex gap-2 align-items-center">
                    <input type="color" v-model="form.bg_color" class="mb-color-input">
                    <input v-model="form.bg_color" class="mb-input" style="flex:1">
                  </div>
                </div>
              </template>
              <template v-else-if="form.bg_type === 'gradient'">
                <div class="mb-field">
                  <label class="mb-label">Color inicial</label>
                  <div class="d-flex gap-2 align-items-center">
                    <input type="color" v-model="form.bg_gradient_from" class="mb-color-input">
                    <input v-model="form.bg_gradient_from" class="mb-input" style="flex:1">
                  </div>
                </div>
                <div class="mb-field">
                  <label class="mb-label">Color final</label>
                  <div class="d-flex gap-2 align-items-center">
                    <input type="color" v-model="form.bg_gradient_to" class="mb-color-input">
                    <input v-model="form.bg_gradient_to" class="mb-input" style="flex:1">
                  </div>
                </div>
                <div class="mb-field mb-field--full">
                  <label class="mb-label">Vista previa</label>
                  <div class="mb-gradient-preview" :style="{ background: `linear-gradient(135deg, ${form.bg_gradient_from}, ${form.bg_gradient_to})` }"></div>
                </div>
              </template>
              <template v-else-if="form.bg_type === 'glass'">
                <div class="mb-field mb-field--full">
                  <label class="mb-label">Color base (hex con alpha)</label>
                  <div class="d-flex gap-2 align-items-center">
                    <input type="color" v-model="form.bg_color" class="mb-color-input">
                    <input v-model="form.bg_color" class="mb-input" style="flex:1">
                  </div>
                </div>
              </template>
              <template v-else-if="form.bg_type === 'pattern'">
                <div class="mb-field mb-field--full">
                  <label class="mb-label">Patrón</label>
                  <div class="mb-pattern-grid">
                    <button v-for="p in PATTERNS" :key="p.value"
                      :class="['mb-pattern-btn', form.bg_pattern === p.value && 'active']"
                      :style="p.style"
                      @click="form.bg_pattern = p.value">
                    </button>
                  </div>
                </div>
              </template>
              <div class="mb-field mb-field--full">
                <div class="form-check form-switch">
                  <input v-model="form.bg_overlay" class="form-check-input" type="checkbox" id="mb-overlay">
                  <label class="form-check-label" for="mb-overlay">Activar overlay oscuro</label>
                </div>
              </div>
              <div v-if="form.bg_overlay" class="mb-field">
                <label class="mb-label">Opacidad overlay (%)</label>
                <div class="d-flex gap-2 align-items-center">
                  <input v-model.number="form.bg_overlay_opacity" type="range" min="0" max="100" class="form-range" style="flex:1">
                  <span class="mb-range-val">{{ form.bg_overlay_opacity }}%</span>
                </div>
              </div>
            </div>
          </div>

          <!-- S11: RESPONSIVE -->
          <div v-show="activeTab === 'responsive'" class="mb-section">
            <div class="mb-section-title"><i class="bi bi-tablet me-2"></i>Responsive</div>
            <p class="mb-section-sub">Número de columnas por dispositivo.</p>
            <div class="mb-responsive-grid">
              <div v-for="dev in DEVICES" :key="dev.key" class="mb-responsive-device">
                <div class="mb-responsive-device__label">
                  <i :class="['bi', dev.icon]"></i>
                  {{ dev.label }}
                </div>
                <div class="mb-cols-picker mb-cols-picker--sm">
                  <button v-for="n in [1,2,3,4,5,6]" :key="n"
                    :class="['mb-col-btn mb-col-btn--sm', form[dev.key] === n && 'active']"
                    @click="form[dev.key] = n">
                    {{ n }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- S12: CAROUSEL (Fase 10) -->
          <div v-show="activeTab === 'carousel'" class="mb-section">
            <div class="mb-section-title"><i class="bi bi-arrows-move me-2"></i>Carrusel (Marketplace Showcase)</div>
            <p class="mb-section-sub">Configuración del scroll horizontal, autoplay y controles.</p>

            <div class="mb-subsection">Número de items visibles</div>
            <div class="mb-responsive-grid">
              <div v-for="dev in DEVICES" :key="dev.key" class="mb-responsive-device">
                <div class="mb-responsive-device__label">
                  <i :class="['bi', dev.icon]"></i> {{ dev.label }}
                </div>
                <div class="mb-cols-picker mb-cols-picker--sm">
                  <button v-for="n in [1,2,3,4,5,6]" :key="n"
                    :class="['mb-col-btn mb-col-btn--sm', getCarouselItems(dev.key) === n && 'active']"
                    @click="setCarouselItems(dev.key, n)">
                    {{ n }}
                  </button>
                </div>
              </div>
            </div>

            <div class="mb-grid mt-3">
              <div class="mb-field">
                <label class="mb-label">Velocidad autoplay (px/s)</label>
                <input v-model.number="form.carousel.speed" type="number" class="mb-input" min="10" max="200" step="10">
              </div>
              <div class="mb-field">
                <div class="form-check form-switch">
                  <input v-model="form.carousel.autoplay" class="form-check-input" type="checkbox" id="mb-autoplay">
                  <label class="form-check-label" for="mb-autoplay">Autoplay</label>
                </div>
              </div>
              <div class="mb-field">
                <div class="form-check form-switch">
                  <input v-model="form.carousel.loop" class="form-check-input" type="checkbox" id="mb-loop">
                  <label class="form-check-label" for="mb-loop">Loop infinito</label>
                </div>
              </div>
              <div class="mb-field">
                <div class="form-check form-switch">
                  <input v-model="form.carousel.pause_on_hover" class="form-check-input" type="checkbox" id="mb-pause-hover">
                  <label class="form-check-label" for="mb-pause-hover">Pausar en hover</label>
                </div>
              </div>
              <div class="mb-field">
                <div class="form-check form-switch">
                  <input v-model="form.carousel.pause_on_touch" class="form-check-input" type="checkbox" id="mb-pause-touch">
                  <label class="form-check-label" for="mb-pause-touch">Pausar en touch</label>
                </div>
              </div>
              <div class="mb-field">
                <div class="form-check form-switch">
                  <input v-model="form.carousel.pause_on_focus" class="form-check-input" type="checkbox" id="mb-pause-focus">
                  <label class="form-check-label" for="mb-pause-focus">Pausar en foco</label>
                </div>
              </div>
              <div class="mb-field">
                <div class="form-check form-switch">
                  <input v-model="form.carousel.show_arrows" class="form-check-input" type="checkbox" id="mb-arrows">
                  <label class="form-check-label" for="mb-arrows">Mostrar flechas</label>
                </div>
              </div>
              <div class="mb-field">
                <div class="form-check form-switch">
                  <input v-model="form.carousel.show_indicators" class="form-check-input" type="checkbox" id="mb-indicators">
                  <label class="form-check-label" for="mb-indicators">Mostrar indicadores (dots)</label>
                </div>
              </div>
            </div>
          </div>

          <!-- S13: MULTIMEDIA (Fase 10) -->
          <div v-show="activeTab === 'multimedia'" class="mb-section">
            <div class="mb-section-title"><i class="bi bi-film me-2"></i>Multimedia</div>

            <div class="mb-subsection">Fondo de Card (Imagen/Video)</div>
            <div class="mb-grid">
              <div class="mb-field mb-field--full">
                <label class="mb-label">Tipo de fondo</label>
                <select v-model="form.media.type" class="mb-select">
                  <option value="color">Color sólido</option>
                  <option value="image">Imagen</option>
                  <option value="video">Video</option>
                </select>
              </div>
              <div v-if="form.media.type === 'video'" class="mb-field mb-field--full">
                <label class="mb-label">URL del video (MP4)</label>
                <input v-model="form.media.video_url" class="mb-input" placeholder="https://...">
              </div>
              <div v-if="form.media.type === 'video'" class="mb-field mb-field--full">
                <label class="mb-label">URL del video (WebM - opcional)</label>
                <input v-model="form.media.video_url_webm" class="mb-input" placeholder="https://...">
              </div>
              <div v-if="form.media.type === 'video'" class="mb-field mb-field--full">
                <label class="mb-label">Poster (imagen preview)</label>
                <input v-model="form.media.poster" class="mb-input" placeholder="https://...">
              </div>
              <div class="mb-field">
                <label class="mb-label">Desenfoque (blur px)</label>
                <input v-model.number="form.media.blur" type="number" class="mb-input" min="0" max="20" step="1">
              </div>
              <div class="mb-field mb-field--full">
                <div class="form-check form-switch">
                  <input v-model="form.media.glass" class="form-check-input" type="checkbox" id="mb-media-glass">
                  <label class="form-check-label" for="mb-media-glass">Glassmorphism (overlay)</label>
                </div>
              </div>
            </div>

            <div class="mb-subsection mt-3">Encabezado de Sección</div>
            <div class="mb-grid">
              <div class="mb-field mb-field--full">
                <label class="mb-label">Título</label>
                <input v-model="form.header.title" class="mb-input" placeholder="El ecosistema Sintel">
              </div>
              <div class="mb-field mb-field--full">
                <label class="mb-label">Subtítulo (eyebrow)</label>
                <input v-model="form.header.subtitle" class="mb-input" placeholder="Marketplace">
              </div>
              <div class="mb-field mb-field--full">
                <label class="mb-label">Descripción</label>
                <textarea v-model="form.header.description" class="mb-input" rows="2" placeholder="Detalle sobre esta sección..."></textarea>
              </div>
              <div class="mb-field">
                <label class="mb-label">CTA - Texto</label>
                <input v-model="form.header.cta_text" class="mb-input" placeholder="Explorar todo">
              </div>
              <div class="mb-field">
                <label class="mb-label">CTA - URL</label>
                <input v-model="form.header.cta_url" class="mb-input" placeholder="/tienda">
              </div>
              <div class="mb-field">
                <label class="mb-label">CTA - Target</label>
                <select v-model="form.header.cta_target" class="mb-select">
                  <option value="_self">Misma pestaña</option>
                  <option value="_blank">Nueva pestaña</option>
                </select>
              </div>
            </div>

            <div class="mb-subsection mt-3">Fondo de Sección Completa</div>
            <div class="mb-grid">
              <div class="mb-field mb-field--full">
                <label class="mb-label">Tipo</label>
                <select v-model="form.section_background.type" class="mb-select">
                  <option value="none">Ninguno</option>
                  <option value="image">Imagen</option>
                  <option value="video">Video</option>
                  <option value="color">Color sólido</option>
                </select>
              </div>
              <div v-if="form.section_background.type === 'image' || form.section_background.type === 'video'" class="mb-field mb-field--full">
                <label class="mb-label">URL de media</label>
                <input v-model="form.section_background.video_url" class="mb-input" placeholder="https://...">
              </div>
              <div v-if="form.section_background.type === 'video'" class="mb-field mb-field--full">
                <label class="mb-label">Poster</label>
                <input v-model="form.section_background.poster" class="mb-input" placeholder="https://...">
              </div>
              <div class="mb-field mb-field--full">
                <div class="form-check form-switch">
                  <input v-model="form.section_background.parallax" class="form-check-input" type="checkbox" id="mb-section-parallax">
                  <label class="form-check-label" for="mb-section-parallax">Efecto Parallax</label>
                </div>
              </div>
            </div>
          </div>

        </div><!-- /mb-form -->

        <!-- LIVE PREVIEW -->
        <aside class="mb-preview">
          <div class="mb-preview__header">
            <span>Vista previa</span>
            <div class="mb-preview__device-btns">
              <button v-for="d in ['desktop','tablet','mobile']" :key="d"
                :class="['mb-pvd-btn', previewDevice === d && 'active']"
                @click="previewDevice = d"
                :title="d">
                <i :class="pvDeviceIcon(d)"></i>
              </button>
            </div>
          </div>

          <div :class="['mb-preview__frame', `mb-preview__frame--${previewDevice}`]">
            <div class="mb-pv-section" :style="pvSectionStyle">
              <div v-if="form.bg_overlay" class="mb-pv-overlay" :style="{ opacity: form.bg_overlay_opacity / 100 }"></div>
              <div class="mb-pv-inner" :style="{ textAlign: form.text_align }">
                <div v-if="form.custom_icon" class="mb-pv-eyebrow" :style="{ color: form.color_primary }">
                  <i :class="['bi', form.custom_icon]"></i>
                </div>
                <div class="mb-pv-title" :style="{ color: form.color_text, fontSize: `${form.title_size * 0.5}rem`, fontWeight: form.font_weight }">
                  {{ form.custom_label || 'Título de la sección' }}
                </div>
                <div v-if="form.public_subtitle" class="mb-pv-subtitle" :style="{ color: form.color_text, fontSize: `${form.subtitle_size * 0.5}rem`, opacity: 0.7 }">
                  {{ form.public_subtitle }}
                </div>
                <div :class="['mb-pv-layout', `mb-pv-layout--${form.display_type}`]"
                  :style="{ '--pv-cols': pvCols, gap: `${form.gap * 0.5}rem` }">
                  <div v-for="n in pvItemCount" :key="n" class="mb-pv-item">
                    <div v-if="form.show_image" class="mb-pv-item__img"></div>
                    <div class="mb-pv-item__body">
                      <div v-if="form.show_icon" class="mb-pv-item__icon" :style="{ color: form.color_primary }">
                        <i :class="['bi', form.custom_icon || 'bi-star']"></i>
                      </div>
                      <div v-if="form.show_title" class="mb-pv-item__title" :style="{ background: form.color_text + '33' }"></div>
                      <div v-if="form.show_subtitle" class="mb-pv-item__sub" :style="{ background: form.color_text + '22' }"></div>
                      <div v-if="form.show_button" class="mb-pv-item__btn" :style="pvBtnStyle">
                        {{ form.btn_text || 'Ver más' }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <details class="mb-preview__json">
            <summary>JSON config</summary>
            <pre class="mb-preview__code">{{ JSON.stringify(configPayload, null, 2) }}</pre>
          </details>
        </aside>

      </div><!-- /mb-body -->

      <!-- FOOTER -->
      <footer class="mb-footer">
        <div v-if="error" class="mb-error">{{ error }}</div>
        <div class="mb-footer__actions">
          <button class="mb-btn" @click="$emit('close')">Cancelar</button>
          <button class="mb-btn mb-btn--primary" @click="save" :disabled="saving">
            <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
            {{ props.module ? 'Guardar cambios' : 'Crear sección' }}
          </button>
        </div>
      </footer>

    </div>
  </div>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue';
import { useToast } from '@/composables/useToast';
import { useCoreAdminStore } from '@/store/coreAdmin';
import { useLayoutEngine } from '@/composables/useLayoutEngine';
import { ANIMATIONS } from '@/constants/animations';

const { resolveModuleBackgroundStyle } = useLayoutEngine();

const props = defineProps({
  module: { type: Object, default: null },
});
const emit = defineEmits(['close', 'saved']);

const store = useCoreAdminStore();
const toast = useToast();

// ── Tabs ──────────────────────────────────────────────────────────────────────
const TABS = [
  { id: 'general',      icon: 'bi-sliders',               label: 'General' },
  { id: 'presentation', icon: 'bi-layout-three-columns',   label: 'Presentación' },
  { id: 'style',        icon: 'bi-palette',               label: 'Estilo' },
  { id: 'icon',         icon: 'bi-star',                  label: 'Icono' },
  { id: 'media',        icon: 'bi-image',                 label: 'Imagen' },
  { id: 'layout',       icon: 'bi-grid-3x3',              label: 'Distribución' },
  { id: 'animation',    icon: 'bi-stars',                 label: 'Animaciones' },
  { id: 'content',      icon: 'bi-toggles',               label: 'Contenido' },
  { id: 'buttons',      icon: 'bi-cursor',                label: 'Botones' },
  { id: 'background',   icon: 'bi-paint-bucket',          label: 'Fondo' },
  { id: 'responsive',   icon: 'bi-tablet',                label: 'Responsive' },
  { id: 'carousel',     icon: 'bi-arrows-move',           label: 'Carrusel' },
  { id: 'multimedia',   icon: 'bi-film',                  label: 'Multimedia' },
];
const activeTab = ref('general');

// ── Presentation types ────────────────────────────────────────────────────────
const PRESENTATION_TYPES = [
  { value: 'grid',        label: 'Grid clásico',     items: 6 },
  { value: 'grid_modern', label: 'Grid moderno',     items: 4 },
  { value: 'cards_h',     label: 'Cards horizontal', items: 3 },
  { value: 'cards_v',     label: 'Cards vertical',   items: 3 },
  { value: 'carousel',    label: 'Carrusel',         items: 1 },
  { value: 'slider',      label: 'Slider',           items: 1 },
  { value: 'hero',        label: 'Hero',             items: 3 },
  { value: 'banner',      label: 'Banner',           items: 2 },
  { value: 'list',        label: 'Lista',            items: 4 },
  { value: 'timeline',    label: 'Timeline',         items: 4 },
  { value: 'accordion',   label: 'Accordion',        items: 4 },
  { value: 'tabs',        label: 'Tabs',             items: 3 },
  { value: 'masonry',     label: 'Masonry',          items: 5 },
  { value: 'highlight',   label: 'Destacados',       items: 4 },
  { value: 'premium',     label: 'Premium Cards',    items: 3 },
  { value: 'compact',     label: 'Compacto',         items: 6 },
  { value: 'split',       label: 'Split Layout',     items: 2 },
  { value: 'minimal',     label: 'Minimalista',      items: 3 },
];

// ── Themes ────────────────────────────────────────────────────────────────────
const THEMES = [
  { value: 'light',     label: 'Claro',      swatch: { background: '#f8fafc', border: '1px solid #e2e8f0' } },
  { value: 'dark',      label: 'Oscuro',     swatch: { background: '#0f172a' } },
  { value: 'gradient',  label: 'Gradiente',  swatch: { background: 'linear-gradient(135deg,#0f172a,#1e3a8a)' } },
  { value: 'glass',     label: 'Glass',      swatch: { background: 'rgba(99,102,241,.18)', border: '1px solid rgba(99,102,241,.3)' } },
  { value: 'minimal',   label: 'Minimal',    swatch: { background: '#fff', border: '1px solid #e2e8f0' } },
  { value: 'corporate', label: 'Corporativo', swatch: { background: '#1d4ed8' } },
];

const THEME_PRESETS = {
  light:     { bg_type: 'color',    bg_color: '#ffffff',               color_text: '#0f172a', color_bg: '#ffffff' },
  dark:      { bg_type: 'color',    bg_color: '#0f172a',               color_text: '#f1f5f9', color_bg: '#0f172a' },
  gradient:  { bg_type: 'gradient', bg_gradient_from: '#0f172a',       bg_gradient_to: '#1e3a8a', color_text: '#ffffff', color_bg: '#0f172a' },
  glass:     { bg_type: 'glass',    bg_color: 'rgba(255,255,255,.08)', color_text: '#ffffff', color_bg: 'transparent' },
  minimal:   { bg_type: 'color',    bg_color: '#ffffff',               color_text: '#374151', color_bg: '#ffffff' },
  corporate: { bg_type: 'gradient', bg_gradient_from: '#1d4ed8',       bg_gradient_to: '#7c3aed', color_text: '#ffffff', color_bg: '#1d4ed8' },
};

const COLOR_FIELDS = [
  { key: 'color_primary',   label: 'Color principal',  placeholder: '#2563eb' },
  { key: 'color_secondary', label: 'Color secundario', placeholder: '#7c3aed' },
  { key: 'color_text',      label: 'Color de texto',   placeholder: '#0f172a' },
  { key: 'color_bg',        label: 'Color de fondo',   placeholder: '#ffffff' },
];

const COMMON_ICONS = [
  'bi-shop','bi-grid','bi-tools','bi-truck','bi-star','bi-heart','bi-award','bi-trophy',
  'bi-lightning','bi-gem','bi-briefcase','bi-building','bi-people','bi-chat','bi-phone',
  'bi-envelope','bi-globe','bi-camera','bi-laptop','bi-cpu','bi-shield-check',
  'bi-graph-up','bi-cash-stack','bi-clock','bi-calendar3','bi-box-seam','bi-basket',
  'bi-tag','bi-layers','bi-bookmark-star',
];

const CONTENT_FIELDS = [
  { key: 'show_image',       icon: 'bi-image',            label: 'Imagen' },
  { key: 'show_icon',        icon: 'bi-star',             label: 'Ícono' },
  { key: 'show_title',       icon: 'bi-type-h1',          label: 'Título' },
  { key: 'show_subtitle',    icon: 'bi-type-h2',          label: 'Subtítulo' },
  { key: 'show_description', icon: 'bi-text-paragraph',   label: 'Descripción' },
  { key: 'show_price',       icon: 'bi-currency-dollar',  label: 'Precio' },
  { key: 'show_category',    icon: 'bi-tag',              label: 'Categoría' },
  { key: 'show_button',      icon: 'bi-cursor',           label: 'Botón' },
  { key: 'show_rating',      icon: 'bi-star-half',        label: 'Calificación' },
  { key: 'show_counter',     icon: 'bi-hash',             label: 'Contador' },
  { key: 'show_tags',        icon: 'bi-tags',             label: 'Etiquetas' },
  { key: 'show_badge',       icon: 'bi-award',            label: 'Badge' },
];

const BG_TYPES = [
  { value: 'color',    label: 'Color sólido' },
  { value: 'gradient', label: 'Gradiente' },
  { value: 'glass',    label: 'Glass' },
  { value: 'pattern',  label: 'Patrón' },
];

const PATTERNS = [
  { value: 'dots',     style: { backgroundImage: 'radial-gradient(#94a3b8 1px, transparent 1px)', backgroundSize: '10px 10px', background: '#f8fafc' } },
  { value: 'grid',     style: { backgroundImage: 'linear-gradient(#e2e8f0 1px, transparent 1px), linear-gradient(90deg, #e2e8f0 1px, transparent 1px)', backgroundSize: '14px 14px', background: '#f8fafc' } },
  { value: 'diagonal', style: { backgroundImage: 'repeating-linear-gradient(45deg, #e2e8f0 0, #e2e8f0 1px, transparent 0, transparent 50%)', backgroundSize: '10px 10px', background: '#f8fafc' } },
];

const DEVICES = [
  { key: 'columns',        icon: 'bi-display', label: 'Desktop' },
  { key: 'columns_tablet', icon: 'bi-tablet',  label: 'Tablet' },
  { key: 'columns_mobile', icon: 'bi-phone',   label: 'Mobile' },
];

// ── Form state ────────────────────────────────────────────────────────────────
const DEFAULT_FORM = () => ({
  module_key:           '',
  custom_label:         '',
  public_subtitle:      '',
  description:          '',
  is_visible:           true,
  display_order:        0,
  featured_items_limit: 8,
  display_type:         'grid',
  theme:                'light',
  color_primary:        '#2563eb',
  color_secondary:      '#7c3aed',
  color_text:           '#0f172a',
  color_bg:             '#ffffff',
  title_size:           2,
  subtitle_size:        1,
  font_weight:          '700',
  text_align:           'left',
  custom_icon:          'bi-grid',
  custom_url:           '/',
  columns:              3,
  columns_tablet:       2,
  columns_mobile:       1,
  padding:              'normal',
  gap:                  1,
  min_height:           '',
  max_width:            '',
  animation_type:       'fade',
  animation_duration:   500,
  animation_delay:      0,
  animation_repeat:     false,
  show_image:           true,
  show_icon:            true,
  show_title:           true,
  show_subtitle:        true,
  show_description:     true,
  show_price:           false,
  show_category:        false,
  show_button:          true,
  show_rating:          false,
  show_counter:         false,
  show_tags:            false,
  show_badge:           false,
  badge_text:           'Nuevo',
  badge_color:          '#f59e0b',
  stats:                [],
  btn_text:             'Ver más',
  btn_color:            '#2563eb',
  btn_icon:             'bi-arrow-right',
  btn_position:         'bottom',
  btn_style:            'filled',
  btn_target:           '_self',
  bg_type:              'color',
  bg_color:             '#ffffff',
  bg_gradient_from:     '#0f172a',
  bg_gradient_to:       '#1e3a8a',
  bg_pattern:           'dots',
  bg_overlay:           false,
  bg_overlay_opacity:   50,
  bg_filter:            'none',

  // ── Marketplace Showcase Fase 10 ──
  carousel: {
    items_desktop:   6,
    items_tablet:    3,
    items_mobile:    1.2,
    autoplay:        false,
    loop:            true,
    speed:           40,
    pause_on_hover:  true,
    pause_on_touch:  true,
    pause_on_focus:  true,
    show_arrows:     true,
    show_indicators: true,
  },
  media: {
    type:           'color',
    image:          '',
    video_url:      '',
    video_url_webm: '',
    poster:         '',
    blur:           0,
    glass:          false,
  },
  header: {
    title:      '',
    subtitle:   '',
    description: '',
    cta_text:   '',
    cta_url:    '',
    cta_target: '_self',
  },
  section_background: {
    type:           'none',
    image:          '',
    video_url:      '',
    video_url_webm: '',
    poster:         '',
    parallax:       false,
  },
});

const form = reactive(DEFAULT_FORM());

// ── Media ─────────────────────────────────────────────────────────────────────
const bgImgInput   = ref(null);
const bgImgFile    = ref(null);
const bgImgPreview = ref('');
const removeImg    = ref(false);
const imgDragging  = ref(false);

// ── Preview ───────────────────────────────────────────────────────────────────
const previewDevice = ref('desktop');

// ── Error / saving ────────────────────────────────────────────────────────────
const saving = ref(false);
const error  = ref('');

// ── Populate from existing module ─────────────────────────────────────────────
function loadModule(mod) {
  const lc   = mod.layout_config  || {};
  const anim = lc.animation       || {};
  const show = lc.show            || {};
  const btn  = lc.button          || {};
  const bg   = lc.background      || {};
  const badge = lc.badge          || {};

  Object.assign(form, DEFAULT_FORM(), {
    module_key:           mod.module_key         || '',
    custom_label:         mod.custom_label        || '',
    public_subtitle:      lc.public_subtitle      || '',
    description:          lc.description          || '',
    is_visible:           mod.is_visible,
    display_order:        mod.display_order        || 0,
    featured_items_limit: mod.featured_items_limit || 8,
    display_type:         mod.display_type         || 'grid',
    theme:                lc.theme                || 'light',
    color_primary:        mod.custom_color        || '#2563eb',
    color_secondary:      lc.color_secondary      || '#7c3aed',
    color_text:           lc.color_text           || '#0f172a',
    color_bg:             lc.color_bg             || '#ffffff',
    title_size:           lc.title_size           || 2,
    subtitle_size:        lc.subtitle_size        || 1,
    font_weight:          lc.font_weight          || '700',
    text_align:           lc.text_align           || 'left',
    custom_icon:          mod.custom_icon         || 'bi-grid',
    custom_url:           mod.custom_url          || '/',
    columns:              lc.columns              || 3,
    columns_tablet:       lc.columns_tablet       || 2,
    columns_mobile:       lc.columns_mobile       || 1,
    padding:              lc.padding              || 'normal',
    gap:                  lc.gap                  || 1,
    min_height:           lc.min_height           || '',
    max_width:            lc.max_width            || '',
    animation_type:       anim.type               || 'fade',
    animation_duration:   anim.duration           || 500,
    animation_delay:      anim.delay              || 0,
    animation_repeat:     anim.repeat             || false,
    show_image:           show.image    !== false,
    show_icon:            show.icon     !== false,
    show_title:           show.title    !== false,
    show_subtitle:        show.subtitle !== false,
    show_description:     show.description !== false,
    show_price:           show.price    === true,
    show_category:        show.category === true,
    show_button:          show.button   !== false,
    show_rating:          show.rating   === true,
    show_counter:         show.counter  === true,
    show_tags:            show.tags     === true,
    show_badge:           show.badge    === true,
    badge_text:           badge.text    || 'Nuevo',
    badge_color:          badge.color   || '#f59e0b',
    stats:                Array.isArray(lc.stats) ? lc.stats.map(s => ({ value: s.value || '', label: s.label || '' })) : [],
    btn_text:             btn.text      || 'Ver más',
    btn_color:            btn.color     || '#2563eb',
    btn_icon:             btn.icon      || 'bi-arrow-right',
    btn_position:         btn.position  || 'bottom',
    btn_style:            btn.style     || 'filled',
    btn_target:           btn.target    || '_self',
    bg_type:              bg.type              || 'color',
    bg_color:             bg.color             || '#ffffff',
    bg_gradient_from:     bg.gradient_from     || '#0f172a',
    bg_gradient_to:       bg.gradient_to       || '#1e3a8a',
    bg_pattern:           bg.pattern           || 'dots',
    bg_overlay:           bg.overlay           || false,
    bg_overlay_opacity:   bg.overlay_opacity   || 50,
    bg_filter:            lc.bg_filter         || 'none',
    carousel:             lc.carousel ? {
      items_desktop:   lc.carousel.items_desktop ?? 6,
      items_tablet:    lc.carousel.items_tablet ?? 3,
      items_mobile:    lc.carousel.items_mobile ?? 1.2,
      autoplay:        lc.carousel.autoplay ?? false,
      loop:            lc.carousel.loop ?? true,
      speed:           lc.carousel.speed ?? 40,
      pause_on_hover:  lc.carousel.pause_on_hover !== false,
      pause_on_touch:  lc.carousel.pause_on_touch !== false,
      pause_on_focus:  lc.carousel.pause_on_focus !== false,
      show_arrows:     lc.carousel.show_arrows !== false,
      show_indicators: lc.carousel.show_indicators !== false,
    } : DEFAULT_FORM().carousel,
    media:                lc.media ? {
      type:           lc.media.type || 'color',
      image:          lc.media.image || '',
      video_url:      lc.media.video_url || '',
      video_url_webm: lc.media.video_url_webm || '',
      poster:         lc.media.poster || '',
      blur:           lc.media.blur || 0,
      glass:          lc.media.glass || false,
    } : DEFAULT_FORM().media,
    header:               lc.header ? {
      title:       lc.header.title || '',
      subtitle:    lc.header.subtitle || '',
      description: lc.header.description || '',
      cta_text:    lc.header.cta_text || '',
      cta_url:     lc.header.cta_url || '',
      cta_target:  lc.header.cta_target || '_self',
    } : DEFAULT_FORM().header,
    section_background:   lc.section_background ? {
      type:           lc.section_background.type || 'none',
      image:          lc.section_background.image || '',
      video_url:      lc.section_background.video_url || '',
      video_url_webm: lc.section_background.video_url_webm || '',
      poster:         lc.section_background.poster || '',
      parallax:       lc.section_background.parallax || false,
    } : DEFAULT_FORM().section_background,
  });

  bgImgPreview.value = mod.background_image || '';
  removeImg.value    = false;
}

watch(() => props.module, (mod) => {
  activeTab.value = 'general';
  if (mod) loadModule(mod);
  else Object.assign(form, DEFAULT_FORM());
}, { immediate: true });

// ── Theme preset ──────────────────────────────────────────────────────────────
function applyTheme(value) {
  form.theme = value;
  const preset = THEME_PRESETS[value] || {};
  Object.assign(form, preset);
}

// ── Config payload ────────────────────────────────────────────────────────────
const configPayload = computed(() => ({
  public_subtitle: form.public_subtitle,
  description:     form.description,
  theme:           form.theme,
  color_secondary: form.color_secondary,
  color_text:      form.color_text,
  color_bg:        form.color_bg,
  title_size:      form.title_size,
  subtitle_size:   form.subtitle_size,
  font_weight:     form.font_weight,
  text_align:      form.text_align,
  columns:         form.columns,
  columns_tablet:  form.columns_tablet,
  columns_mobile:  form.columns_mobile,
  padding:         form.padding,
  gap:             form.gap,
  min_height:      form.min_height,
  max_width:       form.max_width,
  bg_filter:       form.bg_filter,
  animation: {
    type:     form.animation_type,
    duration: form.animation_duration,
    delay:    form.animation_delay,
    repeat:   form.animation_repeat,
  },
  show: {
    image: form.show_image, icon: form.show_icon, title: form.show_title,
    subtitle: form.show_subtitle, description: form.show_description,
    price: form.show_price, category: form.show_category, button: form.show_button,
    rating: form.show_rating, counter: form.show_counter, tags: form.show_tags,
    badge: form.show_badge,
  },
  badge: {
    text:  form.badge_text,
    color: form.badge_color,
  },
  stats: form.stats,
  button: {
    text: form.btn_text, color: form.btn_color, icon: form.btn_icon,
    position: form.btn_position, style: form.btn_style, target: form.btn_target,
  },
  background: {
    type:            form.bg_type,
    color:           form.bg_color,
    gradient_from:   form.bg_gradient_from,
    gradient_to:     form.bg_gradient_to,
    pattern:         form.bg_pattern,
    overlay:         form.bg_overlay,
    overlay_opacity: form.bg_overlay_opacity,
  },
  carousel:        form.carousel,
  media:           form.media,
  header:          form.header,
  section_background: form.section_background,
}));

// ── Preview computed ──────────────────────────────────────────────────────────
const pvSectionStyle = computed(() => {
  const bgStyle = resolveModuleBackgroundStyle({
    background: {
      type: form.bg_type, color: form.bg_color,
      gradient_from: form.bg_gradient_from, gradient_to: form.bg_gradient_to,
    },
  });
  return {
    background: bgStyle.background || '#f8fafc',
    backdropFilter: bgStyle.backdropFilter,
    padding: '0.75rem', borderRadius: '8px', position: 'relative', overflow: 'hidden', minHeight: '100px',
  };
});

const pvCols = computed(() => {
  if (previewDevice.value === 'mobile') return form.columns_mobile;
  if (previewDevice.value === 'tablet') return form.columns_tablet;
  return Math.min(form.columns, 4);
});

const pvItemCount = computed(() => Math.min(pvCols.value * 2, 6));

const pvBtnStyle = computed(() => {
  if (form.btn_style === 'outline') {
    return { border: `1px solid ${form.btn_color}`, color: form.btn_color, background: 'transparent', borderRadius: '3px', padding: '1px 6px', fontSize: '0.55rem', display: 'inline-block', marginTop: '3px' };
  }
  return { background: form.btn_color, color: '#fff', borderRadius: '3px', padding: '1px 6px', fontSize: '0.55rem', display: 'inline-block', marginTop: '3px' };
});

function pvDeviceIcon(d) {
  return d === 'desktop' ? 'bi bi-display' : d === 'tablet' ? 'bi bi-tablet' : 'bi bi-phone';
}

// ── Media handlers ────────────────────────────────────────────────────────────
function handleImgSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  bgImgFile.value    = file;
  bgImgPreview.value = URL.createObjectURL(file);
  removeImg.value    = false;
}

function handleImgDrop(e) {
  imgDragging.value = false;
  const file = e.dataTransfer.files[0];
  if (!file || !file.type.startsWith('image/')) return;
  bgImgFile.value    = file;
  bgImgPreview.value = URL.createObjectURL(file);
  removeImg.value    = false;
}

// ── Carousel helpers ──────────────────────────────────────────────────────────
function getCarouselItems(device) {
  if (device === 'desktop') return form.carousel.items_desktop;
  if (device === 'tablet') return form.carousel.items_tablet;
  return form.carousel.items_mobile;
}

function setCarouselItems(device, value) {
  if (device === 'desktop') form.carousel.items_desktop = value;
  else if (device === 'tablet') form.carousel.items_tablet = value;
  else form.carousel.items_mobile = value;
}

// ── Save ──────────────────────────────────────────────────────────────────────
async function save() {
  if (!props.module && !form.module_key.trim()) {
    error.value = 'La clave interna es requerida.'; return;
  }
  if (!form.custom_label.trim()) {
    error.value = 'El nombre del módulo es requerido.'; return;
  }
  saving.value = true; error.value = '';

  const useMultipart = !!bgImgFile.value || removeImg.value;
  let payload;

  if (useMultipart) {
    const fd = new FormData();
    fd.append('custom_label',         form.custom_label);
    fd.append('custom_icon',          form.custom_icon);
    fd.append('custom_url',           form.custom_url);
    fd.append('custom_color',         form.color_primary);
    fd.append('is_visible',           form.is_visible);
    fd.append('display_order',        form.display_order);
    fd.append('featured_items_limit', form.featured_items_limit);
    fd.append('display_type',         form.display_type);
    fd.append('layout_config',        JSON.stringify(configPayload.value));
    if (!props.module) fd.append('module_key', form.module_key);
    if (bgImgFile.value) fd.append('background_image', bgImgFile.value);
    if (removeImg.value) fd.append('remove_background_image', 'true');
    payload = fd;
  } else {
    payload = {
      custom_label:         form.custom_label,
      custom_icon:          form.custom_icon,
      custom_url:           form.custom_url,
      custom_color:         form.color_primary,
      is_visible:           form.is_visible,
      display_order:        form.display_order,
      featured_items_limit: form.featured_items_limit,
      display_type:         form.display_type,
      layout_config:        configPayload.value,
    };
    if (!props.module) payload.module_key = form.module_key;
  }

  const res = props.module
    ? await store.updateModule(props.module.uuid, payload)
    : await store.createModule(payload);

  if (res.ok) {
    toast.success(props.module ? 'Sección actualizada.' : 'Sección creada.');
    emit('saved', res.data);
  } else {
    const detail = res.error?.response?.data;
    error.value = typeof detail === 'string' ? detail : JSON.stringify(detail) || 'Error al guardar.';
  }
  saving.value = false;
}
</script>

<style scoped>
/* ── Overlay & Shell ─────────────────────────────────────────────────────── */
.mb-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.6);
  backdrop-filter: blur(4px);
  z-index: 1100;
  display: flex;
  align-items: center;
  justify-content: center;
}
.mb-shell {
  width: 95vw;
  max-width: 1280px;
  height: 90vh;
  background: #ffffff;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 32px 80px rgba(0,0,0,.35);
}

/* ── Header ──────────────────────────────────────────────────────────────── */
.mb-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1.25rem;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
  flex-shrink: 0;
}
.mb-header__info { display: flex; align-items: center; gap: 0.6rem; }
.mb-header__dot  { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.mb-header__title { font-size: 0.9rem; font-weight: 600; color: #1e293b; }
.mb-header__name  { color: #64748b; font-weight: 400; }
.mb-close {
  background: none; border: none; padding: 0.35rem 0.5rem;
  border-radius: 6px; color: #64748b; cursor: pointer; font-size: 1rem;
  transition: background .15s, color .15s;
}
.mb-close:hover { background: #fee2e2; color: #dc2626; }

/* ── Tabs ────────────────────────────────────────────────────────────────── */
.mb-tabs {
  display: flex;
  gap: 2px;
  padding: 0.5rem 1rem;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
  overflow-x: auto;
  flex-shrink: 0;
  scrollbar-width: none;
}
.mb-tabs::-webkit-scrollbar { display: none; }
.mb-tab {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.38rem 0.75rem;
  border: none;
  background: none;
  border-radius: 6px;
  font-size: 0.78rem;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  white-space: nowrap;
  transition: background .15s, color .15s;
}
.mb-tab:hover  { background: #e2e8f0; color: #334155; }
.mb-tab--active { background: #eff6ff; color: #2563eb; font-weight: 600; }

/* ── Body ────────────────────────────────────────────────────────────────── */
.mb-body {
  display: grid;
  grid-template-columns: 1fr 300px;
  flex: 1;
  overflow: hidden;
}

/* ── Form area ───────────────────────────────────────────────────────────── */
.mb-form {
  overflow-y: auto;
  padding: 1.25rem;
  border-right: 1px solid #e2e8f0;
}
.mb-section { display: flex; flex-direction: column; gap: 0.75rem; }
.mb-section-title {
  font-size: 0.85rem;
  font-weight: 700;
  color: #1e293b;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #e2e8f0;
}
.mb-section-sub { font-size: 0.8rem; color: #64748b; margin: -0.25rem 0 0.5rem; }
.mb-subsection  { font-size: 0.75rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: .06em; }
.mb-section-title--sm { font-size: 0.78rem; border-bottom: none; padding-bottom: 0.25rem; }
.mb-stat-row { grid-template-columns: 1fr 1fr auto; align-items: end; margin-bottom: 0.5rem; }
.mb-stat-remove { color: #ef4444; padding: 0.4rem 0.6rem; }

.mb-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}
.mb-field { display: flex; flex-direction: column; gap: 0.3rem; }
.mb-field--full { grid-column: 1 / -1; }
.mb-label  { font-size: 0.75rem; font-weight: 600; color: #374151; }
.mb-hint   { font-size: 0.7rem; color: #94a3b8; }
.mb-input  {
  border: 1px solid #d1d5db; border-radius: 6px; padding: 0.4rem 0.6rem;
  font-size: 0.82rem; color: #1e293b; background: #fff;
  outline: none; transition: border-color .15s;
}
.mb-input:focus  { border-color: #2563eb; box-shadow: 0 0 0 2px rgba(37,99,235,.1); }
textarea.mb-input { resize: vertical; }
.mb-select {
  border: 1px solid #d1d5db; border-radius: 6px; padding: 0.4rem 0.6rem;
  font-size: 0.82rem; color: #1e293b; background: #fff; outline: none;
  cursor: pointer;
}
.mb-color-input {
  width: 36px; height: 32px; border: 1px solid #d1d5db; border-radius: 6px;
  padding: 2px; cursor: pointer; background: none;
}
.mb-range-val { font-size: 0.75rem; color: #64748b; min-width: 42px; text-align: right; }

/* ── Presentation type grid ──────────────────────────────────────────────── */
.mb-pt-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
  gap: 0.6rem;
}
.mb-pt-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  padding: 0.6rem 0.4rem;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
  cursor: pointer;
  transition: border-color .15s, background .15s, transform .15s;
}
.mb-pt-card:hover { border-color: #93c5fd; background: #eff6ff; transform: translateY(-1px); }
.mb-pt-card--selected { border-color: #2563eb; background: #eff6ff; }
.mb-pt-label { font-size: 0.68rem; font-weight: 600; color: #475569; text-align: center; }
.mb-pt-check { position: absolute; top: 4px; right: 4px; color: #2563eb; font-size: 0.7rem; }

/* Thumbnails */
.mb-pt-thumb {
  width: 80px; height: 52px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 3px;
  padding: 3px;
  background: #fff;
  border-radius: 5px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
}
.mb-pt-item {
  border-radius: 3px;
  background: linear-gradient(135deg, #93c5fd, #818cf8);
  min-height: 8px;
}

/* Grid 3x2 */
.mb-pt-thumb--grid { grid-template-columns: repeat(3, 1fr); }

/* Grid moderno - 1 big + 3 small */
.mb-pt-thumb--grid_modern { grid-template-columns: 1.5fr 1fr; grid-template-rows: 1fr 1fr; }
.mb-pt-thumb--grid_modern .mb-pt-item:first-child { grid-row: 1 / 3; background: linear-gradient(135deg, #60a5fa, #6366f1); }

/* Cards horizontal - each is a row */
.mb-pt-thumb--cards_h { grid-template-columns: 1fr; gap: 4px; }
.mb-pt-thumb--cards_h .mb-pt-item { display: flex; flex-direction: row; height: 14px; }

/* Cards vertical */
.mb-pt-thumb--cards_v { grid-template-columns: repeat(3, 1fr); }
.mb-pt-thumb--cards_v .mb-pt-item { height: 36px; }

/* Carousel - single centered */
.mb-pt-thumb--carousel { grid-template-columns: 1fr; }
.mb-pt-thumb--carousel .mb-pt-item { height: 46px; background: linear-gradient(135deg, #6366f1, #8b5cf6); border-radius: 4px; }

/* Slider - full width */
.mb-pt-thumb--slider { grid-template-columns: 1fr; }
.mb-pt-thumb--slider .mb-pt-item { height: 46px; background: linear-gradient(90deg, #1e3a8a, #3b82f6); border-radius: 4px; }

/* Hero - large + small */
.mb-pt-thumb--hero { grid-template-columns: 2fr 1fr; grid-template-rows: 1fr 1fr; }
.mb-pt-thumb--hero .mb-pt-item:first-child { grid-row: 1 / 3; background: linear-gradient(135deg, #0f172a, #1d4ed8); }

/* Banner - full width strip */
.mb-pt-thumb--banner { grid-template-columns: 2fr 1fr; gap: 3px; align-items: center; }
.mb-pt-thumb--banner .mb-pt-item:first-child { height: 32px; background: linear-gradient(90deg, #0f172a, #1e3a8a); }
.mb-pt-thumb--banner .mb-pt-item:last-child  { height: 20px; border-radius: 10px; }

/* List - stacked rows */
.mb-pt-thumb--list { grid-template-columns: 1fr; gap: 4px; }
.mb-pt-thumb--list .mb-pt-item { height: 10px; border-radius: 2px; }

/* Timeline - vertical line */
.mb-pt-thumb--timeline { grid-template-columns: 8px 1fr; gap: 3px; }
.mb-pt-thumb--timeline .mb-pt-item:nth-child(odd)  { width: 8px; border-radius: 50%; height: 8px; align-self: center; }
.mb-pt-thumb--timeline .mb-pt-item:nth-child(even) { height: 10px; border-radius: 2px; }

/* Accordion */
.mb-pt-thumb--accordion { grid-template-columns: 1fr; gap: 4px; }
.mb-pt-thumb--accordion .mb-pt-item { height: 11px; border-radius: 3px; border-bottom: 2px solid rgba(255,255,255,.4); }

/* Tabs */
.mb-pt-thumb--tabs { grid-template-rows: auto 1fr; grid-template-columns: repeat(3, 1fr); }
.mb-pt-thumb--tabs .mb-pt-item { height: 10px; border-radius: 2px; }
.mb-pt-thumb--tabs .mb-pt-item:first-child { background: #2563eb; }
.mb-pt-thumb--tabs .mb-pt-item:last-child  { grid-column: 1 / -1; height: 28px; margin-top: 2px; background: #dbeafe; }

/* Masonry - irregular heights */
.mb-pt-thumb--masonry { grid-template-columns: repeat(3, 1fr); align-items: start; }
.mb-pt-thumb--masonry .mb-pt-item:nth-child(1) { height: 28px; }
.mb-pt-thumb--masonry .mb-pt-item:nth-child(2) { height: 42px; }
.mb-pt-thumb--masonry .mb-pt-item:nth-child(3) { height: 18px; }
.mb-pt-thumb--masonry .mb-pt-item:nth-child(4) { height: 38px; }
.mb-pt-thumb--masonry .mb-pt-item:nth-child(5) { height: 24px; }

/* Highlight - 1 big left + 3 small right */
.mb-pt-thumb--highlight { grid-template-columns: 1.6fr 1fr; grid-template-rows: 1fr 1fr; }
.mb-pt-thumb--highlight .mb-pt-item:first-child { grid-row: 1 / 3; background: linear-gradient(135deg, #7c3aed, #2563eb); }

/* Premium - cards with accent lines */
.mb-pt-thumb--premium { grid-template-columns: repeat(3, 1fr); }
.mb-pt-thumb--premium .mb-pt-item {
  height: 36px; border-radius: 4px;
  background: #f8fafc; border: 1px solid #e2e8f0;
  border-top: 3px solid #7c3aed;
}

/* Compact */
.mb-pt-thumb--compact { grid-template-columns: repeat(3, 1fr); gap: 2px; }
.mb-pt-thumb--compact .mb-pt-item { height: 14px; border-radius: 2px; }

/* Split - 2 halves */
.mb-pt-thumb--split { grid-template-columns: 1fr 1fr; }
.mb-pt-thumb--split .mb-pt-item { height: 46px; }
.mb-pt-thumb--split .mb-pt-item:first-child  { background: linear-gradient(135deg, #0f172a, #1e3a8a); }
.mb-pt-thumb--split .mb-pt-item:last-child   { background: linear-gradient(135deg, #eff6ff, #dbeafe); }

/* Minimal - text lines */
.mb-pt-thumb--minimal { grid-template-columns: 1fr; gap: 5px; }
.mb-pt-thumb--minimal .mb-pt-item { height: 6px; border-radius: 3px; }
.mb-pt-thumb--minimal .mb-pt-item:first-child  { background: #1e293b; width: 70%; }
.mb-pt-thumb--minimal .mb-pt-item:nth-child(2) { background: #94a3b8; width: 90%; }
.mb-pt-thumb--minimal .mb-pt-item:last-child   { background: #2563eb; width: 40%; }

/* ── Themes ──────────────────────────────────────────────────────────────── */
.mb-theme-grid {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.mb-theme-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  padding: 0.5rem 0.6rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  background: none;
  cursor: pointer;
  font-size: 0.72rem;
  font-weight: 500;
  color: #475569;
  transition: border-color .15s;
}
.mb-theme-card:hover   { border-color: #93c5fd; }
.mb-theme-card--active { border-color: #2563eb; color: #2563eb; }
.mb-theme-swatch       { width: 36px; height: 22px; border-radius: 4px; }

/* ── Align group ─────────────────────────────────────────────────────────── */
.mb-align-group { display: flex; gap: 4px; }
.mb-align-btn {
  padding: 0.3rem 0.6rem; border: 1px solid #d1d5db; border-radius: 5px;
  background: none; cursor: pointer; color: #64748b; font-size: 0.9rem;
  transition: background .15s, color .15s;
}
.mb-align-btn.active { background: #2563eb; border-color: #2563eb; color: #fff; }

/* ── Icon picker ─────────────────────────────────────────────────────────── */
.mb-icon-preview {
  width: 44px; height: 38px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.mb-icon-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.mb-icon-btn {
  width: 36px; height: 34px; border: 1px solid #e2e8f0; border-radius: 6px;
  background: #f8fafc; cursor: pointer; font-size: 1rem; color: #475569;
  transition: background .12s, border-color .12s, color .12s;
  display: flex; align-items: center; justify-content: center;
}
.mb-icon-btn:hover  { background: #eff6ff; border-color: #93c5fd; color: #2563eb; }
.mb-icon-btn.active { background: #2563eb; border-color: #2563eb; color: #fff; }

/* ── Upload zone ─────────────────────────────────────────────────────────── */
.mb-upload-zone {
  border: 2px dashed #d1d5db; border-radius: 10px;
  background: #f8fafc; min-height: 120px;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: border-color .15s, background .15s;
  position: relative; overflow: hidden;
}
.mb-upload-zone:hover         { border-color: #60a5fa; background: #eff6ff; }
.mb-upload-zone--drag         { border-color: #2563eb; background: #dbeafe; }
.mb-upload-zone__ph           { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; color: #94a3b8; font-size: 0.8rem; }
.mb-upload-zone__preview      { width: 100%; height: 120px; object-fit: cover; }
.mb-btn-sm {
  padding: 0.25rem 0.65rem; border: 1px solid #d1d5db; border-radius: 5px;
  background: #fff; font-size: 0.75rem; cursor: pointer; color: #374151;
}
.mb-btn-sm:hover          { background: #f1f5f9; }
.mb-btn-sm--danger        { color: #dc2626; }
.mb-btn-sm--danger:hover  { background: #fee2e2; border-color: #fca5a5; }

/* ── Column picker ───────────────────────────────────────────────────────── */
.mb-cols-picker { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.mb-col-btn {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  padding: 0.5rem 0.6rem; border: 2px solid #e2e8f0; border-radius: 8px;
  background: #f8fafc; cursor: pointer; font-size: 0.7rem; color: #64748b;
  transition: border-color .15s;
}
.mb-col-btn:hover  { border-color: #93c5fd; }
.mb-col-btn.active { border-color: #2563eb; background: #eff6ff; color: #2563eb; }
.mb-col-vis { display: flex; gap: 2px; }
.mb-col-bar { width: 8px; height: 20px; background: #cbd5e1; border-radius: 2px; }
.mb-col-btn.active .mb-col-bar { background: #93c5fd; }
.mb-cols-picker--sm { gap: 0.35rem; }
.mb-col-btn--sm {
  width: 30px; height: 28px; padding: 0; border: 2px solid #e2e8f0;
  border-radius: 6px; background: #f8fafc; cursor: pointer; font-size: 0.75rem;
  color: #64748b; transition: border-color .15s;
  display: flex; align-items: center; justify-content: center;
}
.mb-col-btn--sm:hover  { border-color: #93c5fd; }
.mb-col-btn--sm.active { border-color: #2563eb; background: #eff6ff; color: #2563eb; }

/* ── Gradient preview ────────────────────────────────────────────────────── */
.mb-gradient-preview { height: 48px; border-radius: 8px; border: 1px solid rgba(0,0,0,.08); }

/* ── Animations ──────────────────────────────────────────────────────────── */
.mb-anim-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem; }
.mb-anim-card {
  display: flex; flex-direction: column; align-items: center; gap: 0.3rem;
  padding: 0.6rem 0.4rem; border: 2px solid #e2e8f0; border-radius: 8px;
  background: #f8fafc; cursor: pointer; font-size: 0.7rem; color: #64748b;
  transition: border-color .15s;
}
.mb-anim-card:hover  { border-color: #93c5fd; background: #eff6ff; }
.mb-anim-card.active { border-color: #2563eb; background: #eff6ff; color: #2563eb; }
.mb-anim-card i { font-size: 1.2rem; }

/* ── Content toggles ─────────────────────────────────────────────────────── */
.mb-toggle-grid { display: flex; flex-direction: column; gap: 0; }
.mb-toggle-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.55rem 0.5rem; cursor: pointer;
  border-bottom: 1px solid #f1f5f9;
  transition: background .12s;
}
.mb-toggle-row:hover { background: #f8fafc; }
.mb-toggle-info { display: flex; align-items: center; gap: 0.5rem; font-size: 0.82rem; color: #374151; }
.mb-toggle-info i { color: #64748b; }

/* ── Button style picker ─────────────────────────────────────────────────── */
.mb-btn-style-group { display: flex; gap: 4px; flex-wrap: wrap; }
.mb-btn-style-opt {
  padding: 0.25rem 0.55rem; border: 1px solid #d1d5db; border-radius: 5px;
  background: none; cursor: pointer; font-size: 0.72rem; color: #64748b;
  text-transform: capitalize; transition: background .12s;
}
.mb-btn-style-opt:hover  { background: #f1f5f9; }
.mb-btn-style-opt.active { background: #2563eb; border-color: #2563eb; color: #fff; }

/* ── Background type picker ──────────────────────────────────────────────── */
.mb-bg-type-grid { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.mb-bg-card {
  display: flex; flex-direction: column; align-items: center; gap: 0.35rem;
  padding: 0.5rem 0.7rem; border: 2px solid #e2e8f0; border-radius: 8px;
  background: none; cursor: pointer; font-size: 0.72rem; color: #64748b;
  transition: border-color .15s;
}
.mb-bg-card:hover  { border-color: #93c5fd; }
.mb-bg-card.active { border-color: #2563eb; color: #2563eb; }
.mb-bg-swatch { width: 40px; height: 24px; border-radius: 5px; }
.mb-bg-swatch--color    { background: #f1f5f9; border: 1px solid #e2e8f0; }
.mb-bg-swatch--gradient { background: linear-gradient(135deg, #0f172a, #1e3a8a); }
.mb-bg-swatch--glass    { background: rgba(99,102,241,.15); border: 1px solid rgba(99,102,241,.3); backdrop-filter: blur(4px); }
.mb-bg-swatch--pattern  { background-image: radial-gradient(#94a3b8 1px, transparent 1px); background-size: 6px 6px; background-color: #f8fafc; }

/* Pattern picker */
.mb-pattern-grid { display: flex; gap: 0.5rem; }
.mb-pattern-btn {
  width: 56px; height: 38px; border-radius: 6px; border: 2px solid #e2e8f0; cursor: pointer;
  transition: border-color .15s;
}
.mb-pattern-btn:hover  { border-color: #93c5fd; }
.mb-pattern-btn.active { border-color: #2563eb; }

/* ── Responsive layout ───────────────────────────────────────────────────── */
.mb-responsive-grid { display: flex; flex-direction: column; gap: 1.25rem; }
.mb-responsive-device { display: flex; flex-direction: column; gap: 0.5rem; }
.mb-responsive-device__label { font-size: 0.8rem; font-weight: 600; color: #374151; display: flex; align-items: center; gap: 0.4rem; }

/* ── Preview panel ───────────────────────────────────────────────────────── */
.mb-preview {
  display: flex;
  flex-direction: column;
  background: #f1f5f9;
  overflow-y: auto;
}
.mb-preview__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.6rem 0.85rem;
  background: #e2e8f0;
  font-size: 0.75rem;
  font-weight: 600;
  color: #475569;
  flex-shrink: 0;
}
.mb-preview__device-btns { display: flex; gap: 4px; }
.mb-pvd-btn {
  padding: 0.2rem 0.4rem; border: 1px solid #cbd5e1; border-radius: 5px;
  background: none; cursor: pointer; color: #64748b; font-size: 0.75rem;
  transition: background .12s;
}
.mb-pvd-btn:hover  { background: #fff; }
.mb-pvd-btn.active { background: #fff; border-color: #2563eb; color: #2563eb; }

.mb-preview__frame {
  flex: 1;
  padding: 0.75rem;
  display: flex;
  align-items: flex-start;
  justify-content: center;
}
.mb-preview__frame--desktop { align-items: flex-start; }
.mb-preview__frame--tablet  { max-width: 260px; margin: 0 auto; }
.mb-preview__frame--mobile  { max-width: 180px; margin: 0 auto; }

.mb-pv-section {
  width: 100%;
  min-height: 90px;
}
.mb-pv-overlay {
  position: absolute;
  inset: 0;
  background: #000;
  pointer-events: none;
}
.mb-pv-inner { position: relative; z-index: 1; }
.mb-pv-eyebrow { font-size: 0.7rem; margin-bottom: 0.3rem; }
.mb-pv-title   { font-size: 1rem; margin-bottom: 0.15rem; }
.mb-pv-subtitle { font-size: 0.65rem; margin-bottom: 0.4rem; }

.mb-pv-layout {
  display: grid;
  grid-template-columns: repeat(var(--pv-cols, 3), 1fr);
  gap: 0.4rem;
  margin-top: 0.5rem;
}
.mb-pv-layout--list,
.mb-pv-layout--timeline,
.mb-pv-layout--accordion { grid-template-columns: 1fr; }
.mb-pv-layout--carousel,
.mb-pv-layout--slider,
.mb-pv-layout--banner     { grid-template-columns: 1fr; }
.mb-pv-layout--split      { grid-template-columns: 1fr 1fr; }
.mb-pv-layout--minimal    { grid-template-columns: 1fr; }

.mb-pv-item {
  background: rgba(255,255,255,.15);
  border-radius: 5px;
  padding: 5px;
  min-height: 30px;
}
.mb-pv-item__img   { height: 28px; background: rgba(0,0,0,.12); border-radius: 3px; margin-bottom: 4px; }
.mb-pv-item__body  { display: flex; flex-direction: column; gap: 2px; }
.mb-pv-item__icon  { font-size: 0.7rem; }
.mb-pv-item__title { height: 6px; border-radius: 2px; }
.mb-pv-item__sub   { height: 4px; border-radius: 2px; width: 70%; }

.mb-preview__json {
  margin: 0;
  border-top: 1px solid #e2e8f0;
  background: #fff;
}
.mb-preview__json summary {
  padding: 0.5rem 0.85rem;
  font-size: 0.7rem;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  user-select: none;
}
.mb-preview__code {
  padding: 0.5rem 0.85rem;
  font-size: 0.62rem;
  color: #334155;
  margin: 0;
  max-height: 180px;
  overflow-y: auto;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
}

/* ── Footer ──────────────────────────────────────────────────────────────── */
.mb-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.25rem;
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
  flex-shrink: 0;
  gap: 1rem;
}
.mb-footer__actions { display: flex; gap: 0.6rem; margin-left: auto; }
.mb-error   { font-size: 0.78rem; color: #dc2626; background: #fee2e2; padding: 0.35rem 0.75rem; border-radius: 6px; }
.mb-btn {
  padding: 0.45rem 1.1rem; border: 1px solid #d1d5db; border-radius: 7px;
  background: #fff; font-size: 0.82rem; font-weight: 500; color: #374151;
  cursor: pointer; transition: background .15s;
}
.mb-btn:hover         { background: #f1f5f9; }
.mb-btn--primary      { background: #2563eb; border-color: #2563eb; color: #fff; }
.mb-btn--primary:hover { background: #1d4ed8; }
.mb-btn--primary:disabled { opacity: .6; cursor: not-allowed; }
</style>
