<template>
  <div class="hcb-shell">

    <!-- ══ SIDEBAR ══════════════════════════════════════════════════════════ -->
    <aside class="hcb-sidebar">
      <div class="hcb-logo">
        <i class="bi bi-layout-wtf"></i>
        <span>Home Builder</span>
      </div>

      <nav class="hcb-nav">
        <button
          v-for="s in sections"
          :key="s.id"
          :class="['hcb-nav-btn', currentSection === s.id ? 'hcb-nav-btn--active' : '']"
          @click="currentSection = s.id"
        >
          <i :class="['bi', s.icon]"></i>
          <span>{{ s.label }}</span>
          <span v-if="s.count" class="hcb-badge">{{ s.count }}</span>
        </button>
      </nav>

      <div class="hcb-sidebar-footer">
        <a href="/" target="_blank" class="hcb-preview-btn">
          <i class="bi bi-eye"></i> Ver sitio
        </a>
      </div>
    </aside>

    <!-- ══ EDITOR ════════════════════════════════════════════════════════════ -->
    <main class="hcb-editor" :key="currentSection">

      <!-- ── MÓDULOS ─────────────────────────────────────────────────────── -->
      <section v-if="currentSection === 'modules'">
        <div class="hcb-section-header">
          <div>
            <h2 class="hcb-section-title">Modulos</h2>
            <p class="hcb-section-sub">Controla que secciones se muestran, su layout y cuantos items destacados.</p>
          </div>
          <button class="hcb-btn hcb-btn--primary" @click="openModuleForm()">
            <i class="bi bi-plus-lg"></i> Nuevo modulo
          </button>
        </div>

        <div v-if="loadingModules" class="hcb-loading">
          <div class="spinner-border text-primary"></div>
        </div>

        <div v-else class="hcb-modules-grid">
          <div
            v-for="mod in modulesOrdered"
            :key="mod.uuid"
            :class="['hcb-module-card', !mod.is_visible && 'hcb-module-card--hidden']"
          >
            <div class="hcb-module-card__color" :style="{ background: mod.module_color }">
              <i :class="['bi', mod.module_icon]"></i>
            </div>
            <div class="hcb-module-card__body">
              <div class="hcb-module-card__label">{{ mod.module_label }}</div>
              <div class="hcb-module-card__meta">
                <span class="hcb-chip">{{ displayTypeLabel(mod.display_type) }}</span>
                <span class="hcb-chip">{{ mod.featured_items_limit }} items</span>
                <span :class="['hcb-chip', mod.is_visible ? 'hcb-chip--green' : 'hcb-chip--gray']">
                  {{ mod.is_visible ? 'Visible' : 'Oculto' }}
                </span>
              </div>
            </div>
            <div class="hcb-module-card__actions">
              <button class="hcb-icon-btn" @click="openModuleForm(mod)"><i class="bi bi-pencil"></i></button>
              <button
                v-if="!mod.is_core"
                class="hcb-icon-btn hcb-icon-btn--danger"
                @click="deleteModule(mod)"
              ><i class="bi bi-trash"></i></button>
            </div>
          </div>
          <div v-if="!modulesOrdered.length" class="hcb-empty">Sin modulos configurados.</div>
        </div>
      </section>

      <!-- ── BANNERS ─────────────────────────────────────────────────────── -->
      <section v-if="currentSection === 'banners'">
        <div class="hcb-section-header">
          <div>
            <h2 class="hcb-section-title">Banners</h2>
            <p class="hcb-section-sub">Carrusel hero de la pagina principal. Soporta imagen y video.</p>
          </div>
          <button class="hcb-btn hcb-btn--primary" @click="openBannerForm()">
            <i class="bi bi-plus-lg"></i> Nuevo banner
          </button>
        </div>

        <div v-if="loadingBanners" class="hcb-loading"><div class="spinner-border text-primary"></div></div>

        <div v-else class="hcb-banners-list">
          <div
            v-for="b in banners"
            :key="b.uuid"
            :class="['hcb-banner-row', !b.is_active && 'hcb-banner-row--inactive']"
          >
            <div class="hcb-banner-thumb">
              <img v-if="b.image" :src="b.image" alt="">
              <div v-else-if="b.video" class="hcb-banner-video-icon"><i class="bi bi-play-circle"></i></div>
              <div v-else class="hcb-banner-placeholder"><i class="bi bi-image"></i></div>
            </div>
            <div class="hcb-banner-info">
              <div class="hcb-banner-title">{{ b.title }}</div>
              <div class="hcb-banner-meta">
                <span class="hcb-chip" :class="b.is_active ? 'hcb-chip--green' : 'hcb-chip--gray'">
                  {{ b.is_active ? 'Activo' : 'Inactivo' }}
                </span>
                <span class="hcb-chip">Orden {{ b.display_order }}</span>
                <span v-if="b.link_url" class="hcb-chip">{{ b.link_label || b.link_url }}</span>
              </div>
            </div>
            <div class="hcb-banner-actions">
              <button class="hcb-icon-btn" @click="openBannerForm(b)"><i class="bi bi-pencil"></i></button>
              <button class="hcb-icon-btn hcb-icon-btn--danger" @click="deleteBanner(b)"><i class="bi bi-trash"></i></button>
            </div>
          </div>
          <div v-if="!banners.length" class="hcb-empty">Sin banners. Crea el primero.</div>
        </div>
      </section>

      <!-- ── TARJETAS ────────────────────────────────────────────────────── -->
      <section v-if="currentSection === 'cards'">
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
      </section>

      <!-- ── FOOTER ──────────────────────────────────────────────────────── -->
      <section v-if="currentSection === 'footer'">
        <div class="hcb-section-header">
          <div>
            <h2 class="hcb-section-title">Footer</h2>
            <p class="hcb-section-sub">Contacto, redes sociales y enlaces de navegacion.</p>
          </div>
          <button class="hcb-btn hcb-btn--primary" @click="openFooterGroupForm()">
            <i class="bi bi-plus-lg"></i> Nuevo grupo
          </button>
        </div>

        <div v-if="loadingFooter || loadingFooterGroups" class="hcb-loading"><div class="spinner-border text-primary"></div></div>
        <template v-else>
          <!-- Contacto -->
          <div class="hcb-card-section">
            <h6 class="hcb-subsection-title"><i class="bi bi-telephone me-2"></i>Datos de contacto</h6>
            <div class="hcb-form-grid">
              <div class="hcb-field">
                <label class="hcb-label">Telefono</label>
                <input v-model="contactForm.phone" class="hcb-input" placeholder="+57 1 234 5678">
              </div>
              <div class="hcb-field">
                <label class="hcb-label">Email</label>
                <input v-model="contactForm.email" class="hcb-input" placeholder="info@sintel.com">
              </div>
              <div class="hcb-field hcb-field--full">
                <label class="hcb-label">Direccion</label>
                <input v-model="contactForm.address" class="hcb-input" placeholder="Cra 7 # 123, Bogota">
              </div>
              <div class="hcb-field hcb-field--full">
                <label class="hcb-label">Horario</label>
                <input v-model="contactForm.working_hours" class="hcb-input" placeholder="Lunes a Viernes 8-18h">
              </div>
            </div>
            <button class="hcb-btn hcb-btn--primary mt-3" :disabled="savingContact" @click="saveContact">
              <span v-if="savingContact" class="spinner-border spinner-border-sm me-1"></span>
              Guardar contacto
            </button>
          </div>

          <!-- Grupos (columnas) -->
          <div class="hcb-card-section mt-4">
            <h6 class="hcb-subsection-title"><i class="bi bi-columns-gap me-2"></i>Columnas de navegacion</h6>
            <p class="hcb-section-sub mb-3">Arrastra para reordenar. Maximo 6 columnas por fila en la Home publica (se ajusta solo).</p>
            <div v-if="!footerGroups.length" class="hcb-empty">Sin columnas. Crea la primera.</div>
            <div v-else class="hcb-fg-grid">
              <div
                v-for="(group, idx) in footerGroups"
                :key="group.uuid"
                :class="['hcb-fg-card', !group.is_active && 'hcb-fg-card--inactive', selectedGroupUuid === group.uuid && 'hcb-fg-card--selected']"
                draggable="true"
                @dragstart="handleGroupDragStart(idx)"
                @dragover.prevent
                @drop="handleGroupDrop(idx)"
                @click="selectGroup(group)"
              >
                <span class="hcb-drag-handle" title="Arrastrar para reordenar"><i class="bi bi-grip-vertical"></i></span>
                <div class="hcb-fg-card__icon">
                  <IconRenderer :icon="group.icon_class" />
                </div>
                <div class="hcb-fg-card__body">
                  <div class="hcb-fg-card__title">{{ group.title }}</div>
                  <div class="hcb-fg-card__meta">{{ group.links_count }} enlace(s)</div>
                </div>
                <span :class="['hcb-chip', group.is_active ? 'hcb-chip--green' : 'hcb-chip--gray']">
                  {{ group.is_active ? 'Activo' : 'Inactivo' }}
                </span>
                <div class="d-flex gap-1">
                  <button class="hcb-icon-btn hcb-icon-btn--xs" @click.stop="openFooterGroupForm(group)"><i class="bi bi-pencil"></i></button>
                  <button class="hcb-icon-btn hcb-icon-btn--xs hcb-icon-btn--danger" @click.stop="deleteFooterGroup(group)"><i class="bi bi-trash"></i></button>
                </div>
              </div>
            </div>
          </div>

          <!-- Enlaces del grupo seleccionado -->
          <div v-if="selectedGroup" class="hcb-card-section mt-4">
            <div class="hcb-section-header">
              <h6 class="hcb-subsection-title mb-0">
                <IconRenderer :icon="selectedGroup.icon_class" extra-class="me-2" />
                Enlaces de "{{ selectedGroup.title }}"
              </h6>
              <button class="hcb-btn hcb-btn--primary hcb-btn--sm" @click="openFooterLinkForm()">
                <i class="bi bi-plus-lg"></i> Nuevo enlace
              </button>
            </div>
            <div v-if="!groupLinks.length" class="hcb-empty">Sin enlaces en este grupo. Agrega el primero.</div>
            <div v-else class="hcb-links-list">
              <div
                v-for="(link, idx) in groupLinks"
                :key="link.uuid"
                class="hcb-link-row"
                draggable="true"
                @dragstart="handleLinkDragStart(idx)"
                @dragover.prevent
                @drop="handleLinkDrop(idx)"
              >
                <span class="hcb-drag-handle" title="Arrastrar para reordenar"><i class="bi bi-grip-vertical"></i></span>
                <IconRenderer :icon="link.icon_class || 'bi-link'" extra-class="hcb-link-icon" />
                <div class="hcb-link-info">
                  <span class="hcb-link-title">{{ link.title }}</span>
                  <span class="hcb-chip hcb-chip--xs">{{ link.url }}</span>
                  <span v-if="link.open_new_tab" class="hcb-chip hcb-chip--xs">Nueva pestana</span>
                  <span :class="['hcb-chip hcb-chip--xs', link.is_active ? 'hcb-chip--green' : 'hcb-chip--gray']">
                    {{ link.is_active ? 'Activo' : 'Inactivo' }}
                  </span>
                </div>
                <div class="d-flex gap-1">
                  <button class="hcb-icon-btn hcb-icon-btn--xs" @click="openFooterLinkForm(link)"><i class="bi bi-pencil"></i></button>
                  <button class="hcb-icon-btn hcb-icon-btn--xs hcb-icon-btn--danger" @click="deleteFooterLink(link)"><i class="bi bi-trash"></i></button>
                </div>
              </div>
            </div>
          </div>

          <!-- Redes sociales -->
          <div class="hcb-card-section mt-4">
            <div class="hcb-section-header">
              <h6 class="hcb-subsection-title mb-0"><i class="bi bi-share me-2"></i>Redes sociales</h6>
              <button class="hcb-btn hcb-btn--primary hcb-btn--sm" @click="openSocialLinkForm()">
                <i class="bi bi-plus-lg"></i> Nueva red social
              </button>
            </div>
            <div v-if="!socialLinksFlat.length" class="hcb-empty">Sin redes sociales.</div>
            <div v-else class="hcb-links-list">
              <div v-for="link in socialLinksFlat" :key="link.uuid" class="hcb-link-row">
                <IconRenderer :icon="link.icon_class || 'bi-share'" extra-class="hcb-link-icon" />
                <div class="hcb-link-info">
                  <span class="hcb-link-title">{{ link.title }}</span>
                  <span class="hcb-chip hcb-chip--xs">{{ link.url }}</span>
                </div>
                <div class="d-flex gap-1">
                  <button class="hcb-icon-btn hcb-icon-btn--xs" @click="openSocialLinkForm(link)"><i class="bi bi-pencil"></i></button>
                  <button class="hcb-icon-btn hcb-icon-btn--xs hcb-icon-btn--danger" @click="deleteFooterLink(link)"><i class="bi bi-trash"></i></button>
                </div>
              </div>
            </div>
          </div>
        </template>
      </section>

      <!-- ── MARCA ───────────────────────────────────────────────────────── -->
      <section v-if="currentSection === 'brand'">
        <div class="hcb-section-header">
          <div>
            <h2 class="hcb-section-title">Marca</h2>
            <p class="hcb-section-sub">Identidad visual del sitio: nombre, logo y eslogan.</p>
          </div>
        </div>

        <div v-if="loadingBrand" class="hcb-loading"><div class="spinner-border text-primary"></div></div>
        <div v-else class="hcb-card-section">
          <!-- Preview live -->
          <div class="hcb-brand-preview">
            <div class="hcb-brand-preview__logo">
              <img v-if="brandPreviewLogo" :src="brandPreviewLogo" alt="Logo" class="hcb-brand-preview__img">
              <div v-else class="hcb-brand-preview__placeholder">
                <i class="bi bi-building"></i>
              </div>
            </div>
            <div>
              <div class="hcb-brand-preview__name">{{ brandForm.site_name || 'Nombre del sitio' }}</div>
              <div class="hcb-brand-preview__tagline">{{ brandForm.tagline || 'Tu eslogan aqui' }}</div>
            </div>
          </div>

          <div class="hcb-form-grid mt-4">
            <div class="hcb-field">
              <label class="hcb-label">Nombre del sitio</label>
              <input v-model="brandForm.site_name" class="hcb-input" placeholder="Sintel">
            </div>
            <div class="hcb-field">
              <label class="hcb-label">Eslogan</label>
              <input v-model="brandForm.tagline" class="hcb-input" placeholder="Tu plataforma de confianza">
            </div>
            <div class="hcb-field hcb-field--full">
              <label class="hcb-label">Logo</label>
              <div class="hcb-upload-area" @click="$refs.logoInput.click()" @dragover.prevent @drop.prevent="handleLogoDrop">
                <i class="bi bi-cloud-upload"></i>
                <span>Haz clic o arrastra el logo aqui</span>
                <span class="hcb-upload-hint">PNG, SVG, WEBP recomendado</span>
              </div>
              <input ref="logoInput" type="file" accept="image/*" class="d-none" @change="handleLogoSelect">
              <button v-if="brandForm.site_name" class="hcb-btn-link text-danger mt-1" @click="removeLogo">
                <i class="bi bi-trash me-1"></i>Eliminar logo
              </button>
            </div>
          </div>
          <button class="hcb-btn hcb-btn--primary mt-4" :disabled="savingBrand" @click="saveBrand">
            <span v-if="savingBrand" class="spinner-border spinner-border-sm me-1"></span>
            Guardar marca
          </button>
        </div>
      </section>

      <!-- ── NAVBAR ──────────────────────────────────────────────────────── -->
      <section v-if="currentSection === 'navbar'">
        <div class="hcb-section-header">
          <div>
            <h2 class="hcb-section-title">Navbar</h2>
            <p class="hcb-section-sub">Links de navegacion principal visibles en todas las paginas.</p>
          </div>
          <button class="hcb-btn hcb-btn--primary" @click="openNavForm()"><i class="bi bi-plus-lg"></i> Nuevo enlace</button>
        </div>

        <div v-if="loadingNavbar" class="hcb-loading"><div class="spinner-border text-primary"></div></div>
        <div v-else>
          <div class="hcb-nav-preview">
            <div class="hcb-nav-preview__bar">
              <span class="hcb-nav-preview__brand">{{ brandForm.site_name || 'Sintel' }}</span>
              <div class="hcb-nav-preview__links">
                <span v-for="link in navbarLinks.filter(l => l.is_visible)" :key="link.uuid" class="hcb-nav-preview__link">
                  <i v-if="link.icon_class" :class="['bi', link.icon_class, 'me-1']"></i>{{ link.label }}
                </span>
              </div>
            </div>
          </div>

          <div class="hcb-links-list mt-3">
            <div v-for="link in navbarLinks" :key="link.uuid" class="hcb-link-row">
              <i :class="['bi', link.icon_class || 'bi-link', 'hcb-link-icon']"></i>
              <div class="hcb-link-info">
                <span class="hcb-link-title">{{ link.label }}</span>
                <span class="hcb-chip hcb-chip--xs">{{ link.url }}</span>
                <span :class="['hcb-chip hcb-chip--xs', link.is_visible ? 'hcb-chip--green' : 'hcb-chip--gray']">
                  {{ link.is_visible ? 'Visible' : 'Oculto' }}
                </span>
              </div>
              <div class="d-flex gap-1">
                <button class="hcb-icon-btn hcb-icon-btn--xs" @click="openNavForm(link)"><i class="bi bi-pencil"></i></button>
                <button class="hcb-icon-btn hcb-icon-btn--xs hcb-icon-btn--danger" @click="deleteNavLink(link)"><i class="bi bi-trash"></i></button>
              </div>
            </div>
            <div v-if="!navbarLinks.length" class="hcb-empty">Sin enlaces de navbar.</div>
          </div>
        </div>
      </section>

      <!-- ── CTA FINAL ───────────────────────────────────────────────────── -->
      <section v-if="currentSection === 'cta'">
        <div class="hcb-section-header">
          <div>
            <h2 class="hcb-section-title">CTA Final</h2>
            <p class="hcb-section-sub">Bloque de llamada a la accion que aparece antes del footer en la pagina principal.</p>
          </div>
          <button class="hcb-btn hcb-btn--primary" :disabled="savingCta" @click="saveCTA">
            <span v-if="savingCta" class="spinner-border spinner-border-sm me-1"></span>
            Guardar cambios
          </button>
        </div>

        <div v-if="loadingCta" class="hcb-loading"><div class="spinner-border text-primary"></div></div>
        <div v-else class="hcb-form-grid">
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Eyebrow (texto pequeno sobre el titulo)</label>
            <input v-model="ctaForm.eyebrow" class="hcb-input" placeholder="Empieza hoy">
          </div>
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Linea 1 del titulo</label>
            <input v-model="ctaForm.title_prefix" class="hcb-input" placeholder="Impulsa tu empresa con">
          </div>
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Nombre destacado (en color gradiente)</label>
            <input v-model="ctaForm.title_highlighted" class="hcb-input" placeholder="Sintel Technology">
          </div>
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Subtitulo</label>
            <textarea v-model="ctaForm.subtitle" class="hcb-input" rows="2"
              placeholder="Soluciones tecnologicas, equipos y servicios profesionales en un solo lugar."></textarea>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Texto boton principal</label>
            <input v-model="ctaForm.btn_primary_label" class="hcb-input" placeholder="Solicitar cotizacion">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">URL boton principal</label>
            <input v-model="ctaForm.btn_primary_url" class="hcb-input" placeholder="/cotizar">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Texto boton secundario</label>
            <input v-model="ctaForm.btn_ghost_label" class="hcb-input" placeholder="Explorar catalogo">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">URL boton secundario</label>
            <input v-model="ctaForm.btn_ghost_url" class="hcb-input" placeholder="/tienda">
          </div>
          <div v-if="ctaError" class="hcb-field hcb-field--full">
            <div class="alert alert-danger small py-2 mb-0">{{ ctaError }}</div>
          </div>
        </div>
      </section>

      <!-- ── SLIDER DE MARCAS ────────────────────────────────────────────── -->
      <section v-if="currentSection === 'brand_slider'">
        <div class="hcb-section-header">
          <div>
            <h2 class="hcb-section-title">Slider de Marcas / Clientes</h2>
            <p class="hcb-section-sub">Logos con desplazamiento horizontal continuo, entre el CTA final y el footer.</p>
          </div>
          <button class="hcb-btn hcb-btn--primary" @click="openBrandItemForm()">
            <i class="bi bi-plus-lg"></i> Nuevo logo
          </button>
        </div>

        <div v-if="loadingBrandConfig" class="hcb-loading"><div class="spinner-border text-primary"></div></div>
        <div v-else class="hcb-form-grid mb-4">
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Titulo de la seccion</label>
            <input v-model="brandConfigForm.title" class="hcb-input" placeholder="Marcas y clientes">
          </div>
          <div class="hcb-field hcb-field--full">
            <label class="hcb-label">Subtitulo</label>
            <input v-model="brandConfigForm.subtitle" class="hcb-input" placeholder="Empresas que confian en nosotros">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Velocidad (ms)</label>
            <input v-model.number="brandConfigForm.speed" type="number" class="hcb-input" min="500" step="100">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Direccion</label>
            <select v-model="brandConfigForm.direction" class="hcb-input">
              <option value="left">Izquierda</option>
              <option value="right">Derecha</option>
            </select>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Logos visibles (desktop)</label>
            <input v-model.number="brandConfigForm.items_desktop" type="number" class="hcb-input" min="1" max="12">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Logos visibles (tablet)</label>
            <input v-model.number="brandConfigForm.items_tablet" type="number" class="hcb-input" min="1" max="10">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Logos visibles (mobile)</label>
            <input v-model.number="brandConfigForm.items_mobile" type="number" class="hcb-input" min="1" max="6">
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Color de fondo</label>
            <div class="d-flex gap-2">
              <input v-model="brandConfigForm.background_color" type="color" class="hcb-color-input">
              <input v-model="brandConfigForm.background_color" class="hcb-input" placeholder="#ffffff" style="flex:1">
            </div>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Padding superior</label>
            <select v-model="brandConfigForm.padding_top" class="hcb-input">
              <option value="none">Sin padding</option>
              <option value="sm">Pequeno</option>
              <option value="normal">Normal</option>
              <option value="lg">Grande</option>
              <option value="xl">Extra grande</option>
            </select>
          </div>
          <div class="hcb-field">
            <label class="hcb-label">Padding inferior</label>
            <select v-model="brandConfigForm.padding_bottom" class="hcb-input">
              <option value="none">Sin padding</option>
              <option value="sm">Pequeno</option>
              <option value="normal">Normal</option>
              <option value="lg">Grande</option>
              <option value="xl">Extra grande</option>
            </select>
          </div>
          <div class="hcb-field hcb-field--full d-flex gap-4 flex-wrap">
            <div class="form-check form-switch">
              <input v-model="brandConfigForm.autoplay" class="form-check-input" type="checkbox">
              <label class="form-check-label small">Autoplay</label>
            </div>
            <div class="form-check form-switch">
              <input v-model="brandConfigForm.loop" class="form-check-input" type="checkbox">
              <label class="form-check-label small">Loop infinito</label>
            </div>
            <div class="form-check form-switch">
              <input v-model="brandConfigForm.pause_on_hover" class="form-check-input" type="checkbox">
              <label class="form-check-label small">Pausar al pasar el mouse</label>
            </div>
            <div class="form-check form-switch">
              <input v-model="brandConfigForm.is_visible" class="form-check-input" type="checkbox">
              <label class="form-check-label small">Visible en la Home</label>
            </div>
          </div>
          <div v-if="brandConfigError" class="hcb-field hcb-field--full">
            <div class="alert alert-danger small py-2 mb-0">{{ brandConfigError }}</div>
          </div>
          <div class="hcb-field hcb-field--full">
            <button class="hcb-btn hcb-btn--primary" :disabled="savingBrandConfig" @click="saveBrandConfig">
              <span v-if="savingBrandConfig" class="spinner-border spinner-border-sm me-1"></span>
              Guardar configuracion
            </button>
          </div>
        </div>

        <div v-if="loadingBrandItems" class="hcb-loading"><div class="spinner-border text-primary"></div></div>
        <div v-else class="hcb-banners-list">
          <div
            v-for="(item, idx) in brandItems"
            :key="item.uuid"
            :class="['hcb-banner-row', !item.is_active && 'hcb-banner-row--inactive']"
            draggable="true"
            @dragstart="handleBrandItemDragStart(idx)"
            @dragover.prevent
            @drop="handleBrandItemDrop(idx)"
          >
            <span class="hcb-drag-handle" title="Arrastrar para reordenar"><i class="bi bi-grip-vertical"></i></span>
            <div class="hcb-banner-thumb">
              <img v-if="item.logo" :src="item.logo" alt="">
              <div v-else class="hcb-banner-placeholder"><i class="bi bi-image"></i></div>
            </div>
            <div class="hcb-banner-info">
              <div class="hcb-banner-title">{{ item.name }}</div>
              <div class="hcb-banner-meta">
                <span class="hcb-chip" :class="item.is_active ? 'hcb-chip--green' : 'hcb-chip--gray'">
                  {{ item.is_active ? 'Activo' : 'Inactivo' }}
                </span>
                <span v-if="item.website" class="hcb-chip">{{ item.website }}</span>
              </div>
            </div>
            <div class="hcb-banner-actions">
              <button class="hcb-icon-btn" @click="openBrandItemForm(item)"><i class="bi bi-pencil"></i></button>
              <button class="hcb-icon-btn hcb-icon-btn--danger" @click="deleteBrandItem(item)"><i class="bi bi-trash"></i></button>
            </div>
          </div>
          <div v-if="!brandItems.length" class="hcb-empty">Sin logos. Crea el primero.</div>
        </div>
      </section>

    </main>

    <!-- ══ PREVIEW ═══════════════════════════════════════════════════════════ -->
    <aside class="hcb-preview-panel">
      <div class="hcb-preview-header">
        <span class="hcb-preview-label">Vista previa</span>
        <div class="hcb-preview-viewport-btns">
          <button :class="['hcb-vp-btn', previewDevice === 'desktop' ? 'active' : '']" @click="previewDevice = 'desktop'" title="Desktop">
            <i class="bi bi-display"></i>
          </button>
          <button :class="['hcb-vp-btn', previewDevice === 'tablet' ? 'active' : '']" @click="previewDevice = 'tablet'" title="Tablet">
            <i class="bi bi-tablet"></i>
          </button>
          <button :class="['hcb-vp-btn', previewDevice === 'mobile' ? 'active' : '']" @click="previewDevice = 'mobile'" title="Mobile">
            <i class="bi bi-phone"></i>
          </button>
        </div>
      </div>

      <div class="hcb-preview-frame-wrap">
        <div :class="['hcb-preview-frame', `hcb-preview-frame--${previewDevice}`, 'hcb-preview-frame--real']">

          <!-- Vista previa REAL: mismo <HomeRenderer/> que la Landing publica,
               alimentado con el estado EN MEMORIA del formulario (sin guardar).
               Ver ai_skills/frontend/editor/home_render_audit_2026_07_11.md (Fase 3). -->
          <HomeRenderer
            v-if="sectionRendererKey"
            :sections="[sectionRendererKey]"
            :banners="banners"
            :modules="modulesOrdered"
            :home-cards="cards"
            :card-groups="previewCardGroups"
            :card-group-titles="groupTitlesMap"
            :footer-cta="ctaForm"
            :brand-slider="{ config: brandConfigForm, items: brandItems }"
            :loading="false"
          />

          <CustomerNavbar
            v-else-if="currentSection === 'brand' || currentSection === 'navbar'"
            standalone
            :brand-override="previewBrand"
            :nav-links-override="navbarLinks"
          />

          <CustomerFooter
            v-else-if="currentSection === 'footer'"
            :contact-override="contactForm"
            :nav-groups-override="previewNavGroups"
            :social-links-override="previewSocialLinks"
          />

        </div>
      </div>
    </aside>

    <!-- Module Builder: has its own Teleport, must live outside the parent Teleport -->
    <ModuleBuilderModal
      v-if="showModuleModal"
      :module="editingModule"
      @close="closeModuleForm"
      @saved="onModuleSaved"
    />

    <!-- ══ MODALES ═══════════════════════════════════════════════════════════ -->
    <Teleport to="body">

      <!-- Modal Banner -->
      <BaseModal v-model="showBannerModal" :title="editingBanner ? 'Editar banner' : 'Nuevo banner'">
            <!-- Preview live del banner -->
            <div class="hcb-banner-live-preview">
              <img v-if="bannerMediaPreview && bannerMediaType === 'image' && !bannerRemoveMedia" :src="bannerMediaPreview" alt="" class="hcb-blp-img">
              <video v-else-if="bannerMediaPreview && bannerMediaType === 'video' && !bannerRemoveMedia" :src="bannerMediaPreview" class="hcb-blp-img" muted loop autoplay></video>
              <div v-else class="hcb-blp-placeholder" :style="bannerForm.background_color ? { background: bannerForm.background_color } : {}">
                <i class="bi bi-image" v-if="!bannerForm.background_color"></i>
                <span>{{ bannerForm.title || 'Titulo del banner' }}</span>
              </div>
              <div v-if="bannerForm.title" class="hcb-blp-overlay">
                <div v-if="bannerForm.eyebrow" class="hcb-blp-eyebrow">{{ bannerForm.eyebrow }}</div>
                <div class="hcb-blp-title">{{ bannerForm.title }}</div>
                <div v-if="bannerForm.subtitle" class="hcb-blp-subtitle">{{ bannerForm.subtitle }}</div>
                <div class="d-flex gap-2 flex-wrap mt-1">
                  <button v-if="bannerForm.link_label" class="hcb-blp-cta">{{ bannerForm.link_label }}</button>
                  <button v-if="bannerForm.cta_ghost_label" class="hcb-blp-cta hcb-blp-cta--ghost">{{ bannerForm.cta_ghost_label }}</button>
                </div>
              </div>
            </div>

            <div class="hcb-form-grid mt-3">
              <div class="hcb-field hcb-field--full">
                <label class="hcb-label">Titulo *</label>
                <input v-model="bannerForm.title" class="hcb-input" placeholder="Titulo del banner">
              </div>
              <div class="hcb-field hcb-field--full">
                <label class="hcb-label">Subtitulo</label>
                <input v-model="bannerForm.subtitle" class="hcb-input" placeholder="Descripcion breve">
              </div>
              <div class="hcb-field hcb-field--full">
                <label class="hcb-label">Eyebrow (texto pequeño sobre el titulo)</label>
                <input v-model="bannerForm.eyebrow" class="hcb-input" placeholder="Sintel Technology">
              </div>
              <div class="hcb-field">
                <label class="hcb-label">URL boton principal</label>
                <input v-model="bannerForm.link_url" class="hcb-input" placeholder="/tienda">
              </div>
              <div class="hcb-field">
                <label class="hcb-label">Texto boton principal</label>
                <input v-model="bannerForm.link_label" class="hcb-input" placeholder="Ver ahora">
              </div>
              <div class="hcb-field">
                <label class="hcb-label">Texto boton secundario</label>
                <input v-model="bannerForm.cta_ghost_label" class="hcb-input" placeholder="Solicitar cotizacion">
              </div>
              <div class="hcb-field">
                <label class="hcb-label">URL boton secundario</label>
                <input v-model="bannerForm.cta_ghost_url" class="hcb-input" placeholder="/cotizar">
              </div>
              <div class="hcb-field">
                <label class="hcb-label">Color de fondo</label>
                <div class="d-flex gap-2 align-items-center">
                  <input v-model="bannerForm.background_color" type="color" class="hcb-color-input"
                    title="Selecciona color de fondo (se usa si no hay imagen/video)">
                  <input v-model="bannerForm.background_color" class="hcb-input" placeholder="#080d1a" style="flex:1">
                  <button v-if="bannerForm.background_color" type="button" class="hcb-btn--sm hcb-btn--danger-sm"
                    @click="bannerForm.background_color = ''" title="Quitar color">
                    <i class="bi bi-x"></i>
                  </button>
                </div>
              </div>
              <div class="hcb-field">
                <label class="hcb-label">Orden</label>
                <input v-model.number="bannerForm.display_order" type="number" class="hcb-input" min="0">
              </div>
              <div class="hcb-field d-flex align-items-end">
                <div class="form-check form-switch">
                  <input v-model="bannerForm.is_active" class="form-check-input" type="checkbox">
                  <label class="form-check-label">Activo</label>
                </div>
              </div>
              <div class="hcb-field hcb-field--full">
                <label class="hcb-label">Media (imagen o video)</label>
                <!-- Imagen/video actual con opcion de eliminar -->
                <div v-if="bannerMediaPreview && !bannerRemoveMedia" class="hcb-media-current">
                  <img v-if="bannerMediaType === 'image'" :src="bannerMediaPreview" class="hcb-media-current__img" alt="">
                  <video v-else :src="bannerMediaPreview" class="hcb-media-current__img" muted></video>
                  <div class="hcb-media-current__actions">
                    <button type="button" class="hcb-btn hcb-btn--danger-sm" @click="removeBannerMedia">
                      <i class="bi bi-trash me-1"></i>Eliminar media
                    </button>
                    <button type="button" class="hcb-btn hcb-btn--sm" @click="$refs.bannerFileInput.click()">
                      <i class="bi bi-arrow-repeat me-1"></i>Reemplazar
                    </button>
                  </div>
                </div>
                <div
                  v-else
                  class="hcb-upload-area"
                  :class="bannerIsDragging ? 'hcb-upload-area--dragging' : ''"
                  @click="$refs.bannerFileInput.click()"
                  @dragover.prevent="bannerIsDragging = true"
                  @dragleave="bannerIsDragging = false"
                  @drop.prevent="handleBannerDrop"
                >
                  <i class="bi bi-cloud-upload"></i>
                  <span>Haz clic o arrastra imagen/video</span>
                </div>
                <input ref="bannerFileInput" type="file" accept="image/*,video/*" class="d-none" @change="handleBannerSelect">
              </div>
            </div>
            <div v-if="bannerError" class="alert alert-danger small py-2 mt-2">{{ bannerError }}</div>
        <template #footer>
          <button class="hcb-btn" @click="closeBannerForm">Cancelar</button>
          <button class="hcb-btn hcb-btn--primary" :disabled="savingBanner" @click="saveBanner">
            <span v-if="savingBanner" class="spinner-border spinner-border-sm me-1"></span>
            {{ editingBanner ? 'Guardar cambios' : 'Crear banner' }}
          </button>
        </template>
      </BaseModal>

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

      <!-- Modal Enlace Footer (nav, ligado al grupo seleccionado; o social) -->
      <BaseModal
        v-model="showFooterLinkModal"
        :title="editingFooterLink ? 'Editar enlace' : (footerLinkForm.category === 'social' ? 'Nueva red social' : `Nuevo enlace de '${selectedGroup?.title || ''}'`)"
      >
            <div class="hcb-form-grid">
              <div class="hcb-field hcb-field--full">
                <label class="hcb-label">Titulo *</label>
                <input v-model="footerLinkForm.title" class="hcb-input" placeholder="Facebook">
              </div>
              <div class="hcb-field hcb-field--full">
                <label class="hcb-label">URL *</label>
                <input v-model="footerLinkForm.url" class="hcb-input" placeholder="https://...">
              </div>
              <div class="hcb-field">
                <label class="hcb-label">Icono (Bootstrap o atajo: telephone, camera...)</label>
                <div class="d-flex align-items-center gap-2">
                  <IconRenderer :icon="normalizeIconInput(footerLinkForm.icon_class)" size="1.3rem" />
                  <input v-model="footerLinkForm.icon_class" class="hcb-input" placeholder="bi-facebook">
                </div>
              </div>
              <div class="hcb-field">
                <label class="hcb-label">Orden</label>
                <input v-model.number="footerLinkForm.display_order" type="number" class="hcb-input" min="0">
              </div>
              <div class="hcb-field hcb-field--full d-flex gap-3">
                <div class="form-check form-switch">
                  <input v-model="footerLinkForm.is_active" class="form-check-input" type="checkbox">
                  <label class="form-check-label small">Activo</label>
                </div>
                <div v-if="footerLinkForm.category === 'nav'" class="form-check form-switch">
                  <input v-model="footerLinkForm.open_new_tab" class="form-check-input" type="checkbox">
                  <label class="form-check-label small">Abrir en nueva pestana</label>
                </div>
              </div>
            </div>
            <div v-if="footerLinkError" class="alert alert-danger small py-2 mt-2">{{ footerLinkError }}</div>
        <template #footer>
          <button class="hcb-btn" @click="closeFooterLinkForm">Cancelar</button>
          <button class="hcb-btn hcb-btn--primary" :disabled="savingFooterLink" @click="saveFooterLink">
            <span v-if="savingFooterLink" class="spinner-border spinner-border-sm me-1"></span>
            {{ editingFooterLink ? 'Guardar cambios' : 'Crear enlace' }}
          </button>
        </template>
      </BaseModal>

      <!-- Modal Grupo del Footer -->
      <BaseModal v-model="showFooterGroupModal" :title="editingFooterGroup ? 'Editar columna' : 'Nueva columna'">
            <div class="hcb-form-grid">
              <div class="hcb-field hcb-field--full">
                <label class="hcb-label">Titulo *</label>
                <input v-model="footerGroupForm.title" class="hcb-input" placeholder="Empresa">
              </div>
              <div class="hcb-field hcb-field--full">
                <label class="hcb-label">Icono (Bootstrap o atajo: building, shop...)</label>
                <div class="d-flex align-items-center gap-2">
                  <IconRenderer :icon="normalizeIconInput(footerGroupForm.icon_class)" size="1.3rem" />
                  <input v-model="footerGroupForm.icon_class" class="hcb-input" placeholder="bi-building">
                </div>
              </div>
              <div class="hcb-field hcb-field--full">
                <label class="hcb-label">Descripcion (opcional)</label>
                <input v-model="footerGroupForm.description" class="hcb-input" placeholder="Texto breve de apoyo">
              </div>
              <div class="hcb-field">
                <label class="hcb-label">Color de fondo</label>
                <div class="d-flex gap-2">
                  <input v-model="footerGroupForm.background_color" type="color" class="hcb-color-input">
                  <input v-model="footerGroupForm.background_color" class="hcb-input" placeholder="" style="flex:1">
                </div>
              </div>
              <div class="hcb-field">
                <label class="hcb-label">Color de texto</label>
                <div class="d-flex gap-2">
                  <input v-model="footerGroupForm.text_color" type="color" class="hcb-color-input">
                  <input v-model="footerGroupForm.text_color" class="hcb-input" placeholder="" style="flex:1">
                </div>
              </div>
              <div class="hcb-field d-flex align-items-end">
                <div class="form-check form-switch">
                  <input v-model="footerGroupForm.is_active" class="form-check-input" type="checkbox">
                  <label class="form-check-label small">Activo</label>
                </div>
              </div>
            </div>
            <div v-if="footerGroupError" class="alert alert-danger small py-2 mt-2">{{ footerGroupError }}</div>
        <template #footer>
          <button class="hcb-btn" @click="closeFooterGroupForm">Cancelar</button>
          <button class="hcb-btn hcb-btn--primary" :disabled="savingFooterGroup" @click="saveFooterGroup">
            <span v-if="savingFooterGroup" class="spinner-border spinner-border-sm me-1"></span>
            {{ editingFooterGroup ? 'Guardar cambios' : 'Crear columna' }}
          </button>
        </template>
      </BaseModal>

      <!-- Modal Navbar -->
      <BaseModal v-model="showNavModal" :title="editingNavLink ? 'Editar enlace' : 'Nuevo enlace navbar'">
            <div class="hcb-form-grid">
              <div class="hcb-field">
                <label class="hcb-label">Etiqueta *</label>
                <input v-model="navForm.label" class="hcb-input" placeholder="Tienda">
              </div>
              <div class="hcb-field">
                <label class="hcb-label">URL *</label>
                <input v-model="navForm.url" class="hcb-input" placeholder="/tienda">
              </div>
              <div class="hcb-field">
                <label class="hcb-label">Icono Bootstrap</label>
                <input v-model="navForm.icon_class" class="hcb-input" placeholder="bi-shop">
              </div>
              <div class="hcb-field">
                <label class="hcb-label">Orden</label>
                <input v-model.number="navForm.display_order" type="number" class="hcb-input" min="0">
              </div>
              <div class="hcb-field hcb-field--full d-flex gap-3">
                <div class="form-check form-switch">
                  <input v-model="navForm.is_visible" class="form-check-input" type="checkbox">
                  <label class="form-check-label small">Visible</label>
                </div>
                <div class="form-check form-switch">
                  <input v-model="navForm.open_in_new_tab" class="form-check-input" type="checkbox">
                  <label class="form-check-label small">Abrir en nueva pestana</label>
                </div>
              </div>
            </div>
            <div v-if="navError" class="alert alert-danger small py-2 mt-2">{{ navError }}</div>
        <template #footer>
          <button class="hcb-btn" @click="closeNavForm">Cancelar</button>
          <button class="hcb-btn hcb-btn--primary" :disabled="savingNav" @click="saveNavLink">
            <span v-if="savingNav" class="spinner-border spinner-border-sm me-1"></span>
            {{ editingNavLink ? 'Guardar cambios' : 'Crear enlace' }}
          </button>
        </template>
      </BaseModal>

      <!-- Modal Slider de Marcas -->
      <BaseModal v-model="showBrandItemModal" :title="editingBrandItem ? 'Editar logo' : 'Nuevo logo'">
            <div class="hcb-form-grid">
              <div class="hcb-field hcb-field--full">
                <label class="hcb-label">Nombre *</label>
                <input v-model="brandItemForm.name" class="hcb-input" placeholder="Nombre de la marca">
              </div>
              <div class="hcb-field hcb-field--full">
                <label class="hcb-label">Sitio web</label>
                <input v-model="brandItemForm.website" class="hcb-input" placeholder="https://...">
              </div>
              <div class="hcb-field">
                <label class="hcb-label">Orden</label>
                <input v-model.number="brandItemForm.display_order" type="number" class="hcb-input" min="0">
              </div>
              <div class="hcb-field d-flex align-items-end gap-3">
                <div class="form-check form-switch">
                  <input v-model="brandItemForm.is_active" class="form-check-input" type="checkbox">
                  <label class="form-check-label small">Activo</label>
                </div>
                <div class="form-check form-switch">
                  <input v-model="brandItemForm.open_new_tab" class="form-check-input" type="checkbox">
                  <label class="form-check-label small">Abrir en nueva pestana</label>
                </div>
              </div>
              <div class="hcb-field hcb-field--full">
                <label class="hcb-label">Logo</label>
                <div v-if="brandItemLogoPreview && !brandItemRemoveLogo" class="hcb-media-current">
                  <img :src="brandItemLogoPreview" class="hcb-media-current__img" alt="">
                  <div class="hcb-media-current__actions">
                    <button type="button" class="hcb-btn hcb-btn--danger-sm" @click="removeBrandItemLogo">
                      <i class="bi bi-trash me-1"></i>Eliminar logo
                    </button>
                    <button type="button" class="hcb-btn hcb-btn--sm" @click="$refs.brandItemFileInput.click()">
                      <i class="bi bi-arrow-repeat me-1"></i>Reemplazar
                    </button>
                  </div>
                </div>
                <div v-else class="hcb-upload-area" @click="$refs.brandItemFileInput.click()">
                  <i class="bi bi-cloud-upload"></i>
                  <span>Haz clic para subir el logo</span>
                </div>
                <input ref="brandItemFileInput" type="file" accept="image/*" class="d-none" @change="handleBrandItemLogoSelect">
              </div>
            </div>
            <div v-if="brandItemError" class="alert alert-danger small py-2 mt-2">{{ brandItemError }}</div>
        <template #footer>
          <button class="hcb-btn" @click="closeBrandItemForm">Cancelar</button>
          <button class="hcb-btn hcb-btn--primary" :disabled="savingBrandItem" @click="saveBrandItem">
            <span v-if="savingBrandItem" class="spinner-border spinner-border-sm me-1"></span>
            {{ editingBrandItem ? 'Guardar cambios' : 'Crear logo' }}
          </button>
        </template>
      </BaseModal>

    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import ModuleBuilderModal from './ModuleBuilderModal.vue';
import BaseModal from '@/components/base/BaseModal.vue';
import HomeRenderer from '@/renderers/HomeRenderer.vue';
import CustomerNavbar from '@/components/customer/CustomerNavbar.vue';
import CustomerFooter from '@/components/customer/CustomerFooter.vue';
import CardItem from '@/components/ui/home/cards/CardItem.vue';
import IconRenderer from '@/components/ui/IconRenderer.vue';
import { normalizeIconInput } from '@/utils/iconShorthand';
import { ANIMATIONS as CARD_ANIMATIONS } from '@/constants/animations';

const api   = useApi();
const toast = useToast();

// ── Navegacion lateral ────────────────────────────────────────────────────────
const currentSection = ref('modules');

const sections = computed(() => [
  { id: 'modules', label: 'Modulos',  icon: 'bi-grid',          count: modules.value.length || null },
  { id: 'banners', label: 'Banners',  icon: 'bi-images',         count: banners.value.length || null },
  { id: 'cards',   label: 'Tarjetas', icon: 'bi-grid-1x2',       count: cards.value.length || null },
  { id: 'footer',  label: 'Footer',   icon: 'bi-layout-text-window', count: footerGroups.value.length || null },
  { id: 'brand',   label: 'Marca',    icon: 'bi-building',       count: null },
  { id: 'navbar',  label: 'Navbar',   icon: 'bi-list',           count: navbarLinks.value.length || null },
  { id: 'cta',     label: 'CTA Final', icon: 'bi-megaphone',     count: null },
  { id: 'brand_slider', label: 'Slider de Marcas', icon: 'bi-collection', count: brandItems.value.length || null },
]);

// ── Preview device ─────────────────────────────────────────────────────────────
const previewDevice = ref('desktop');

// ── Vista previa REAL (Fase 3, 2026-07-11) ──────────────────────────────────────
// Mapea la seccion activa del builder a la seccion equivalente de HomeRenderer.
// 'footer'/'brand'/'navbar' no son parte del cuerpo de Home (viven en
// CustomerLayout) y se resuelven aparte, mas abajo en el template, con los
// componentes reales CustomerNavbar/CustomerFooter.
const SECTION_TO_RENDERER = { banners: 'hero', modules: 'modules', cards: 'cards', cta: 'cta', brand_slider: 'brand_slider' };
const sectionRendererKey = computed(() => SECTION_TO_RENDERER[currentSection.value] || null);

// Transforma groupTitlesMap/groupConfigMap (shape del builder) al shape de
// "card_groups" que espera SectionRenderer/useLayoutEngine (igual al que
// entrega core/home-feed/ en produccion).
const previewCardGroups = computed(() =>
  Object.keys(cardsByGroup.value).map((gName) => ({
    uuid: gName,
    name: gName,
    title: groupTitlesMap.value[gName] || gName,
    layout_type: groupConfigMap.value[gName]?.layout_type || 'grid',
    columns: groupConfigMap.value[gName]?.columns || 3,
    is_visible: true,
    display_order: groupConfigMap.value[gName]?.display_order || 0,
  }))
);

const previewBrand = computed(() => ({
  site_name: brandForm.value.site_name,
  tagline:   brandForm.value.tagline,
  logo:      brandPreviewLogo.value,
}));

// footerGroups (FooterGroup reales) + footerLinks (flat, category='nav'|'social')
// -> shape que espera CustomerFooter (igual al de core/footer/: groups[].links[]).
const previewNavGroups = computed(() =>
  [...footerGroups.value]
    .filter((g) => g.is_active !== false)
    .sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
    .map((g) => ({
      ...g,
      links: footerLinks.value
        .filter((l) => l.category === 'nav' && l.group === g.uuid)
        .sort((a, b) => (a.display_order || 0) - (b.display_order || 0)),
    }))
);
const previewSocialLinks = computed(() => footerLinks.value.filter((l) => l.category === 'social'));

// ══ MÓDULOS ═══════════════════════════════════════════════════════════════════
const modules             = ref([]);
const loadingModules      = ref(false);
const showModuleModal     = ref(false);
const editingModule       = ref(null);
const pendingModuleDelete = ref(null);

const modulesOrdered = computed(() =>
  [...modules.value].sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
);

const DISPLAY_TYPE_LABELS = {
  grid: 'Grid', grid_modern: 'Grid moderno', slider: 'Slider', carousel: 'Carrusel',
  cards_h: 'Cards H', cards_v: 'Cards V', hero: 'Hero', banner: 'Banner',
  list: 'Lista', timeline: 'Timeline', accordion: 'Accordion', tabs: 'Tabs',
  masonry: 'Masonry', highlight: 'Destacados', premium: 'Premium', compact: 'Compacto',
  split: 'Split', minimal: 'Minimalista',
};
function displayTypeLabel(t) { return DISPLAY_TYPE_LABELS[t] || t || 'Grid'; }

async function fetchModules() {
  loadingModules.value = true;
  try {
    const { data } = await api.get('dashboard/home-config/modules/');
    modules.value = data;
  } finally {
    loadingModules.value = false;
  }
}
function openModuleForm(mod = null) {
  editingModule.value = mod;
  showModuleModal.value = true;
}
function closeModuleForm() { showModuleModal.value = false; editingModule.value = null; }
async function onModuleSaved() {
  closeModuleForm();
  await fetchModules();
}
async function deleteModule(mod) {
  if (!confirm(`Eliminar modulo "${mod.module_label}"?`)) return;
  try {
    await api.delete(`dashboard/home-config/modules/${mod.uuid}/delete/`);
    toast.success('Modulo eliminado.');
    await fetchModules();
  } catch { toast.error('No se pudo eliminar.'); }
}

// ══ BANNERS ════════════════════════════════════════════════════════════════════
const banners       = ref([]);
const loadingBanners = ref(false);
const showBannerModal = ref(false);
const editingBanner = ref(null);
const savingBanner  = ref(false);
const bannerError   = ref('');
const bannerFileInput = ref(null);
const bannerSelectedFile = ref(null);
const bannerMediaPreview = ref('');
const bannerMediaType   = ref('');
const bannerIsDragging  = ref(false);
const bannerRemoveMedia  = ref(false);

const defaultBannerForm = () => ({
  title: '', subtitle: '', eyebrow: '',
  link_url: '', link_label: '',
  background_color: '', cta_ghost_label: '', cta_ghost_url: '',
  display_order: 0, is_active: true,
});
const bannerForm = ref(defaultBannerForm());

async function fetchBanners() {
  loadingBanners.value = true;
  try {
    const { data } = await api.get('dashboard/home-config/banners/');
    banners.value = data;
  } finally { loadingBanners.value = false; }
}
function openBannerForm(b = null) {
  editingBanner.value      = b;
  bannerError.value        = '';
  bannerSelectedFile.value = null;
  bannerRemoveMedia.value  = false;
  bannerMediaPreview.value = b?.image || b?.video || '';
  bannerMediaType.value    = b?.video ? 'video' : 'image';
  bannerForm.value = b ? {
    title: b.title, subtitle: b.subtitle || '', eyebrow: b.eyebrow || '',
    link_url: b.link_url || '', link_label: b.link_label || '',
    background_color: b.background_color || '',
    cta_ghost_label: b.cta_ghost_label || '', cta_ghost_url: b.cta_ghost_url || '',
    display_order: b.display_order ?? 0, is_active: b.is_active,
  } : defaultBannerForm();
  showBannerModal.value = true;
}
function removeBannerMedia() {
  bannerRemoveMedia.value  = true;
  bannerSelectedFile.value = null;
  bannerMediaPreview.value = '';
}
function closeBannerForm() { showBannerModal.value = false; editingBanner.value = null; }
function handleBannerSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  bannerSelectedFile.value = file;
  bannerMediaType.value = file.type.startsWith('video') ? 'video' : 'image';
  bannerMediaPreview.value = URL.createObjectURL(file);
}
function handleBannerDrop(e) {
  bannerIsDragging.value = false;
  const file = e.dataTransfer.files[0];
  if (!file) return;
  bannerSelectedFile.value = file;
  bannerMediaType.value = file.type.startsWith('video') ? 'video' : 'image';
  bannerMediaPreview.value = URL.createObjectURL(file);
}
async function saveBanner() {
  if (!bannerForm.value.title.trim()) { bannerError.value = 'El titulo es requerido.'; return; }
  savingBanner.value = true; bannerError.value = '';
  try {
    const fd = new FormData();
    Object.entries(bannerForm.value).forEach(([k, v]) => fd.append(k, v));
    if (bannerSelectedFile.value) {
      const key = bannerMediaType.value === 'video' ? 'video' : 'image';
      fd.append(key, bannerSelectedFile.value);
    }
    if (bannerRemoveMedia.value) {
      fd.append('remove_image', 'true');
      fd.append('remove_video', 'true');
    }
    const cfg = { headers: { 'Content-Type': 'multipart/form-data' } };
    if (editingBanner.value) {
      await api.patch(`dashboard/home-config/banners/${editingBanner.value.uuid}/`, fd, cfg);
      toast.success('Banner actualizado.');
    } else {
      await api.post('dashboard/home-config/banners/create/', fd, cfg);
      toast.success('Banner creado.');
    }
    closeBannerForm();
    await fetchBanners();
  } catch (err) {
    bannerError.value = err?.response?.data?.detail || 'Error al guardar.';
  } finally { savingBanner.value = false; }
}
async function deleteBanner(b) {
  if (!confirm(`Eliminar banner "${b.title}"?`)) return;
  try {
    await api.delete(`dashboard/home-config/banners/${b.uuid}/delete/`);
    toast.success('Banner eliminado.');
    await fetchBanners();
  } catch { toast.error('No se pudo eliminar.'); }
}

// ══ TARJETAS ═══════════════════════════════════════════════════════════════════
const cards       = ref([]);
const loadingCards = ref(false);
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
  badge_text: '',
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
  loadingCards.value = true;
  try {
    const { data } = await api.get('dashboard/home-cards/');
    cards.value = data;
  } finally { loadingCards.value = false; }
}
async function fetchGroupTitles() {
  try {
    const { data } = await api.get('dashboard/home-card-groups/');
    const titleMap = {}, configMap = {};
    for (const g of data) {
      titleMap[g.name] = g.title;
      configMap[g.name] = g;
    }
    groupTitlesMap.value = titleMap;
    groupConfigMap.value = configMap;
  } catch { /* silent */ }
}
function startEditGroupTitle(gName) {
  editingGroupName.value = gName;
  editedGroupTitle.value = groupTitlesMap.value[gName] || gName;
}
function cancelEditGroupTitle() { editingGroupName.value = null; }
async function saveGroupTitle(gName) {
  if (!editedGroupTitle.value.trim()) return;
  savingGroupTitle.value = true;
  try {
    // Enviar siempre la config actual completa -- el endpoint es un upsert
    // "todo o nada": cualquier campo omitido vuelve a su default de serializer
    // (layout_type/columns/glass/hover/etc quedarian pisados si solo mandamos
    // name+title).
    const current = groupConfigMap.value[gName] || {};
    const { data } = await api.post('dashboard/home-card-groups/upsert/', {
      name: gName,
      title: editedGroupTitle.value.trim(),
      display_order: current.display_order || 0,
      is_visible: current.is_visible !== false,
      subtitle: current.subtitle || '', description: current.description || '',
      bg_color: current.bg_color || '', layout_type: current.layout_type || 'grid',
      columns: current.columns || 3, padding: current.padding || 'normal',
      divider: current.divider || false, glass: current.glass || false, hover: current.hover || 'lift',
    });
    groupTitlesMap.value[gName] = editedGroupTitle.value.trim();
    groupConfigMap.value[gName] = data;
    editingGroupName.value = null;
    toast.success('Titulo actualizado.');
  } catch { toast.error('Error al guardar titulo.'); }
  finally { savingGroupTitle.value = false; }
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
  try {
    const uuid = groupConfigMap.value[gName]?.uuid;
    if (uuid) await api.delete(`dashboard/home-card-groups/${uuid}/delete/`);
    delete groupTitlesMap.value[gName];
    delete groupConfigMap.value[gName];
    toast.success('Grupo eliminado.');
    closeGroupForm();
  } catch { toast.error('No se pudo eliminar el grupo.'); }
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
  try {
    const current = isNewGroup.value ? {} : (groupConfigMap.value[gName] || {});
    const payload = {
      name: gName,
      title: isNewGroup.value ? newGroupTitle.value.trim() : (groupTitlesMap.value[gName] || gName),
      display_order: current.display_order || 0,
      is_visible: current.is_visible !== false,
      ...groupForm.value,
    };
    let result;
    if (groupBgImageFile.value || groupRemoveBgImage.value) {
      const fd = new FormData();
      Object.entries(payload).forEach(([k, v]) => fd.append(k, v));
      if (groupBgImageFile.value) fd.append('bg_image', groupBgImageFile.value);
      if (groupRemoveBgImage.value) fd.append('remove_bg_image', 'true');
      const { data } = await api.post('dashboard/home-card-groups/upsert/', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      result = data;
    } else {
      const { data } = await api.post('dashboard/home-card-groups/upsert/', payload);
      result = data;
    }
    groupTitlesMap.value[gName] = result.title;
    groupConfigMap.value[gName] = result;
    toast.success(isNewGroup.value ? 'Grupo creado.' : 'Grupo actualizado.');
    closeGroupForm();
  } catch (err) {
    groupError.value = err?.response?.data?.detail || 'Error al guardar el grupo.';
  } finally { savingGroup.value = false; }
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
  try {
    const hasMedia = cardImageFile.value || cardRemoveImage.value;
    if (hasMedia) {
      const fd = new FormData();
      Object.entries(cardForm.value).forEach(([k, v]) => fd.append(k, v));
      if (cardImageFile.value) fd.append('image', cardImageFile.value);
      if (cardRemoveImage.value) fd.append('remove_image', 'true');
      const cfg = { headers: { 'Content-Type': 'multipart/form-data' } };
      if (editingCard.value) {
        await api.patch(`dashboard/home-cards/${editingCard.value.uuid}/`, fd, cfg);
      } else {
        await api.post('dashboard/home-cards/create/', fd, cfg);
      }
    } else {
      if (editingCard.value) {
        await api.patch(`dashboard/home-cards/${editingCard.value.uuid}/`, cardForm.value);
      } else {
        await api.post('dashboard/home-cards/create/', cardForm.value);
      }
    }
    toast.success(editingCard.value ? 'Tarjeta actualizada.' : 'Tarjeta creada.');
    closeCardForm();
    await fetchCards();
  } catch (err) {
    cardError.value = err?.response?.data?.detail || 'Error al guardar.';
  } finally { savingCard.value = false; }
}
async function deleteCard(card) {
  if (!confirm(`Eliminar tarjeta "${card.title}"?`)) return;
  try {
    await api.delete(`dashboard/home-cards/${card.uuid}/delete/`);
    toast.success('Tarjeta eliminada.');
    await fetchCards();
  } catch { toast.error('No se pudo eliminar.'); }
}

// ══ FOOTER ═════════════════════════════════════════════════════════════════════
const footerLinks       = ref([]);
const loadingFooter     = ref(false);
const savingContact     = ref(false);
const showFooterLinkModal = ref(false);
const editingFooterLink = ref(null);
const savingFooterLink  = ref(false);
const footerLinkError   = ref('');

const contactForm = ref({ phone: '', email: '', address: '', working_hours: '' });

const defaultFooterLinkForm = (category = 'nav') => ({
  title: '', url: '', category, group: null,
  icon_class: '', open_new_tab: false, is_active: true, display_order: 0,
});
const footerLinkForm = ref(defaultFooterLinkForm());

const socialLinksFlat = computed(() => footerLinks.value.filter((l) => l.category === 'social'));

async function fetchFooter() {
  loadingFooter.value = true;
  try {
    const { data } = await api.get('dashboard/footer/');
    footerLinks.value = data.links || [];
    const c = data.contact;
    if (c) {
      contactForm.value = { phone: c.phone || '', email: c.email || '', address: c.address || '', working_hours: c.working_hours || '' };
    }
  } finally { loadingFooter.value = false; }
}
async function saveContact() {
  savingContact.value = true;
  try {
    await api.post('dashboard/footer/contact/', contactForm.value);
    toast.success('Contacto guardado.');
  } catch { toast.error('Error al guardar contacto.'); }
  finally { savingContact.value = false; }
}

// Enlaces de navegacion (ligados al grupo seleccionado) -- abre el mismo modal
// que las redes sociales, pero con category='nav' y el grupo implicito.
function openFooterLinkForm(link = null) {
  editingFooterLink.value = link;
  footerLinkError.value   = '';
  footerLinkForm.value = link ? {
    title: link.title, url: link.url, category: link.category, group: link.group,
    icon_class: link.icon_class || '', open_new_tab: link.open_new_tab || false,
    is_active: link.is_active, display_order: link.display_order ?? 0,
  } : { ...defaultFooterLinkForm('nav'), group: selectedGroupUuid.value };
  showFooterLinkModal.value = true;
}
function openSocialLinkForm(link = null) {
  editingFooterLink.value = link;
  footerLinkError.value   = '';
  footerLinkForm.value = link ? {
    title: link.title, url: link.url, category: 'social', group: null,
    icon_class: link.icon_class || '', open_new_tab: false,
    is_active: link.is_active, display_order: link.display_order ?? 0,
  } : defaultFooterLinkForm('social');
  showFooterLinkModal.value = true;
}
function closeFooterLinkForm() { showFooterLinkModal.value = false; editingFooterLink.value = null; }
async function saveFooterLink() {
  if (!footerLinkForm.value.title || !footerLinkForm.value.url) {
    footerLinkError.value = 'Titulo y URL son requeridos.'; return;
  }
  savingFooterLink.value = true; footerLinkError.value = '';
  try {
    const payload = { ...footerLinkForm.value, icon_class: normalizeIconInput(footerLinkForm.value.icon_class) };
    if (editingFooterLink.value) {
      await api.patch(`dashboard/footer/links/${editingFooterLink.value.uuid}/`, payload);
    } else {
      await api.post('dashboard/footer/links/create/', payload);
    }
    toast.success('Enlace guardado.');
    closeFooterLinkForm();
    await fetchFooter();
  } catch (err) {
    footerLinkError.value = err?.response?.data?.detail || 'Error al guardar.';
  } finally { savingFooterLink.value = false; }
}
async function deleteFooterLink(link) {
  if (!confirm(`Eliminar "${link.title}"?`)) return;
  try {
    await api.delete(`dashboard/footer/links/${link.uuid}/delete/`);
    toast.success('Enlace eliminado.');
    await fetchFooter();
  } catch { toast.error('No se pudo eliminar.'); }
}

const linkDragIndex = ref(null);
function handleLinkDragStart(index) { linkDragIndex.value = index; }
async function handleLinkDrop(targetIndex) {
  const fromIndex = linkDragIndex.value;
  linkDragIndex.value = null;
  if (fromIndex === null || fromIndex === targetIndex) return;
  const reordered = [...groupLinks.value];
  const [moved] = reordered.splice(fromIndex, 1);
  reordered.splice(targetIndex, 0, moved);
  // Actualizacion optimista: reordena localmente reasignando display_order
  // dentro de footerLinks para que groupLinks (computed) refleje el cambio ya.
  reordered.forEach((link, idx) => { link.display_order = idx; });
  try {
    await api.post('dashboard/footer/links/reorder/', { items: reordered.map((l) => l.uuid) });
  } catch {
    toast.error('No se pudo guardar el nuevo orden.');
    await fetchFooter();
  }
}

// ══ FOOTER GROUPS (columnas) ═════════════════════════════════════════════════
const footerGroups        = ref([]);
const loadingFooterGroups = ref(false);
const showFooterGroupModal = ref(false);
const editingFooterGroup  = ref(null);
const savingFooterGroup   = ref(false);
const footerGroupError    = ref('');
const selectedGroupUuid   = ref(null);
const groupDragIndex      = ref(null);

const defaultFooterGroupForm = () => ({
  title: '', icon_class: 'bi-folder', description: '',
  background_color: '', text_color: '', is_active: true, display_order: 0,
});
const footerGroupForm = ref(defaultFooterGroupForm());

const selectedGroup = computed(() => footerGroups.value.find((g) => g.uuid === selectedGroupUuid.value) || null);
const groupLinks = computed(() =>
  footerLinks.value
    .filter((l) => l.category === 'nav' && l.group === selectedGroupUuid.value)
    .sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
);

async function fetchFooterGroups() {
  loadingFooterGroups.value = true;
  try {
    const { data } = await api.get('dashboard/footer-groups/');
    footerGroups.value = data;
    if (!selectedGroupUuid.value && data.length) selectedGroupUuid.value = data[0].uuid;
  } finally { loadingFooterGroups.value = false; }
}
function selectGroup(group) { selectedGroupUuid.value = group.uuid; }
function openFooterGroupForm(group = null) {
  editingFooterGroup.value = group;
  footerGroupError.value   = '';
  footerGroupForm.value = group ? {
    title: group.title, icon_class: group.icon_class || 'bi-folder',
    description: group.description || '', background_color: group.background_color || '',
    text_color: group.text_color || '', is_active: group.is_active, display_order: group.display_order ?? 0,
  } : defaultFooterGroupForm();
  showFooterGroupModal.value = true;
}
function closeFooterGroupForm() { showFooterGroupModal.value = false; editingFooterGroup.value = null; }
async function saveFooterGroup() {
  if (!footerGroupForm.value.title.trim()) { footerGroupError.value = 'El titulo es requerido.'; return; }
  savingFooterGroup.value = true; footerGroupError.value = '';
  try {
    const payload = { ...footerGroupForm.value, icon_class: normalizeIconInput(footerGroupForm.value.icon_class) };
    if (editingFooterGroup.value) {
      await api.patch(`dashboard/footer-groups/${editingFooterGroup.value.uuid}/`, payload);
    } else {
      await api.post('dashboard/footer-groups/create/', payload);
    }
    toast.success('Columna guardada.');
    closeFooterGroupForm();
    await fetchFooterGroups();
  } catch (err) {
    footerGroupError.value = err?.response?.data?.detail || 'Error al guardar.';
  } finally { savingFooterGroup.value = false; }
}
async function deleteFooterGroup(group) {
  if (!confirm(`Eliminar columna "${group.title}" y desvincular sus enlaces?`)) return;
  try {
    await api.delete(`dashboard/footer-groups/${group.uuid}/delete/`);
    toast.success('Columna eliminada.');
    if (selectedGroupUuid.value === group.uuid) selectedGroupUuid.value = null;
    await fetchFooterGroups();
  } catch { toast.error('No se pudo eliminar.'); }
}
function handleGroupDragStart(index) { groupDragIndex.value = index; }
async function handleGroupDrop(targetIndex) {
  const fromIndex = groupDragIndex.value;
  groupDragIndex.value = null;
  if (fromIndex === null || fromIndex === targetIndex) return;
  const reordered = [...footerGroups.value];
  const [moved] = reordered.splice(fromIndex, 1);
  reordered.splice(targetIndex, 0, moved);
  footerGroups.value = reordered;
  try {
    await api.post('dashboard/footer-groups/reorder/', { items: reordered.map((g) => g.uuid) });
  } catch {
    toast.error('No se pudo guardar el nuevo orden.');
    await fetchFooterGroups();
  }
}

// ══ MARCA ══════════════════════════════════════════════════════════════════════
const loadingBrand   = ref(false);
const savingBrand    = ref(false);
const brandPreviewLogo = ref('');
const logoInput      = ref(null);
const logoFile       = ref(null);

const brandForm = ref({ site_name: 'Sintel', tagline: '' });

async function fetchBrand() {
  loadingBrand.value = true;
  try {
    const { data } = await api.get('dashboard/site-brand/');
    if (data) {
      brandForm.value = { site_name: data.site_name || '', tagline: data.tagline || '' };
      brandPreviewLogo.value = data.logo || '';
    }
  } finally { loadingBrand.value = false; }
}
function handleLogoSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  logoFile.value = file;
  brandPreviewLogo.value = URL.createObjectURL(file);
}
function handleLogoDrop(e) {
  const file = e.dataTransfer.files[0];
  if (!file) return;
  logoFile.value = file;
  brandPreviewLogo.value = URL.createObjectURL(file);
}
function removeLogo() { logoFile.value = null; brandPreviewLogo.value = ''; }
async function saveBrand() {
  savingBrand.value = true;
  try {
    const fd = new FormData();
    fd.append('site_name', brandForm.value.site_name);
    fd.append('tagline', brandForm.value.tagline);
    if (logoFile.value) fd.append('logo', logoFile.value);
    if (!logoFile.value && !brandPreviewLogo.value) fd.append('remove_logo', 'true');
    await api.patch('dashboard/site-brand/update/', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
    toast.success('Marca guardada.');
    logoFile.value = null;
  } catch { toast.error('Error al guardar marca.'); }
  finally { savingBrand.value = false; }
}

// ══ NAVBAR ═════════════════════════════════════════════════════════════════════
const navbarLinks    = ref([]);
const loadingNavbar  = ref(false);
const showNavModal   = ref(false);
const editingNavLink = ref(null);
const savingNav      = ref(false);
const navError       = ref('');

const defaultNavForm = () => ({ label: '', url: '', icon_class: '', display_order: 0, is_visible: true, open_in_new_tab: false });
const navForm = ref(defaultNavForm());

async function fetchNavbarLinks() {
  loadingNavbar.value = true;
  try {
    const { data } = await api.get('dashboard/navbar/');
    navbarLinks.value = data;
  } finally { loadingNavbar.value = false; }
}
function openNavForm(link = null) {
  editingNavLink.value = link; navError.value = '';
  navForm.value = link ? {
    label: link.label, url: link.url, icon_class: link.icon_class || '',
    display_order: link.display_order ?? 0,
    is_visible: link.is_visible, open_in_new_tab: link.open_in_new_tab,
  } : defaultNavForm();
  showNavModal.value = true;
}
function closeNavForm() { showNavModal.value = false; editingNavLink.value = null; }
async function saveNavLink() {
  if (!navForm.value.label || !navForm.value.url) { navError.value = 'Etiqueta y URL son requeridos.'; return; }
  savingNav.value = true; navError.value = '';
  try {
    if (editingNavLink.value) {
      await api.patch(`dashboard/navbar/${editingNavLink.value.uuid}/`, navForm.value);
    } else {
      await api.post('dashboard/navbar/create/', navForm.value);
    }
    toast.success('Enlace guardado.');
    closeNavForm();
    await fetchNavbarLinks();
  } catch (err) {
    navError.value = err?.response?.data?.detail || 'Error al guardar.';
  } finally { savingNav.value = false; }
}
async function deleteNavLink(link) {
  if (!confirm(`Eliminar "${link.label}"?`)) return;
  try {
    await api.delete(`dashboard/navbar/${link.uuid}/delete/`);
    toast.success('Enlace eliminado.');
    await fetchNavbarLinks();
  } catch { toast.error('No se pudo eliminar.'); }
}

// ══ CTA FINAL ══════════════════════════════════════════════════════════════════
const loadingCta = ref(false);
const savingCta  = ref(false);
const ctaError   = ref('');

const defaultCtaForm = () => ({
  eyebrow:           'Empieza hoy',
  title_prefix:      'Impulsa tu empresa con',
  title_highlighted: 'Sintel Technology',
  subtitle:          'Soluciones tecnologicas, equipos y servicios profesionales en un solo lugar.',
  btn_primary_label: 'Solicitar cotizacion',
  btn_primary_url:   '/cotizar',
  btn_ghost_label:   'Explorar catalogo',
  btn_ghost_url:     '/tienda',
});
const ctaForm = ref(defaultCtaForm());

async function fetchFooterCTA() {
  loadingCta.value = true;
  try {
    const { data } = await api.get('dashboard/footer-cta/');
    if (data.uuid) {
      ctaForm.value = {
        eyebrow:           data.eyebrow           || '',
        title_prefix:      data.title_prefix      || '',
        title_highlighted: data.title_highlighted || '',
        subtitle:          data.subtitle          || '',
        btn_primary_label: data.btn_primary_label || '',
        btn_primary_url:   data.btn_primary_url   || '',
        btn_ghost_label:   data.btn_ghost_label   || '',
        btn_ghost_url:     data.btn_ghost_url     || '',
      };
    }
  } finally { loadingCta.value = false; }
}

async function saveCTA() {
  savingCta.value = true; ctaError.value = '';
  try {
    await api.patch('dashboard/footer-cta/update/', ctaForm.value);
    toast.success('CTA actualizado.');
    await fetchFooterCTA();
  } catch (err) {
    ctaError.value = err?.response?.data?.detail || 'Error al guardar.';
  } finally { savingCta.value = false; }
}

// ══ SLIDER DE MARCAS ══════════════════════════════════════════════════════════
const brandItems         = ref([]);
const loadingBrandItems  = ref(false);
const showBrandItemModal = ref(false);
const editingBrandItem   = ref(null);
const savingBrandItem    = ref(false);
const brandItemError     = ref('');
const brandItemFileInput = ref(null);
const brandItemSelectedFile = ref(null);
const brandItemLogoPreview  = ref('');
const brandItemRemoveLogo   = ref(false);
const brandItemDragIndex    = ref(null);

const defaultBrandItemForm = () => ({
  name: '', website: '', display_order: 0, is_active: true, open_new_tab: true,
});
const brandItemForm = ref(defaultBrandItemForm());

async function fetchBrandItems() {
  loadingBrandItems.value = true;
  try {
    const { data } = await api.get('dashboard/brand-slider/');
    brandItems.value = data;
  } finally { loadingBrandItems.value = false; }
}
function openBrandItemForm(item = null) {
  editingBrandItem.value      = item;
  brandItemError.value        = '';
  brandItemSelectedFile.value = null;
  brandItemRemoveLogo.value   = false;
  brandItemLogoPreview.value  = item?.logo || '';
  brandItemForm.value = item ? {
    name: item.name, website: item.website || '',
    display_order: item.display_order ?? 0,
    is_active: item.is_active, open_new_tab: item.open_new_tab,
  } : defaultBrandItemForm();
  showBrandItemModal.value = true;
}
function closeBrandItemForm() { showBrandItemModal.value = false; editingBrandItem.value = null; }
function removeBrandItemLogo() {
  brandItemRemoveLogo.value  = true;
  brandItemSelectedFile.value = null;
  brandItemLogoPreview.value = '';
}
function handleBrandItemLogoSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  brandItemSelectedFile.value = file;
  brandItemLogoPreview.value = URL.createObjectURL(file);
}
async function saveBrandItem() {
  if (!brandItemForm.value.name.trim()) { brandItemError.value = 'El nombre es requerido.'; return; }
  savingBrandItem.value = true; brandItemError.value = '';
  try {
    const fd = new FormData();
    Object.entries(brandItemForm.value).forEach(([k, v]) => fd.append(k, v));
    if (brandItemSelectedFile.value) fd.append('logo', brandItemSelectedFile.value);
    if (brandItemRemoveLogo.value) fd.append('remove_logo', 'true');
    const cfg = { headers: { 'Content-Type': 'multipart/form-data' } };
    if (editingBrandItem.value) {
      await api.patch(`dashboard/brand-slider/${editingBrandItem.value.uuid}/`, fd, cfg);
      toast.success('Logo actualizado.');
    } else {
      await api.post('dashboard/brand-slider/create/', fd, cfg);
      toast.success('Logo creado.');
    }
    closeBrandItemForm();
    await fetchBrandItems();
  } catch (err) {
    brandItemError.value = err?.response?.data?.detail || 'Error al guardar.';
  } finally { savingBrandItem.value = false; }
}
async function deleteBrandItem(item) {
  if (!confirm(`Eliminar logo "${item.name}"?`)) return;
  try {
    await api.delete(`dashboard/brand-slider/${item.uuid}/delete/`);
    toast.success('Logo eliminado.');
    await fetchBrandItems();
  } catch { toast.error('No se pudo eliminar.'); }
}
function handleBrandItemDragStart(index) { brandItemDragIndex.value = index; }
async function handleBrandItemDrop(targetIndex) {
  const fromIndex = brandItemDragIndex.value;
  brandItemDragIndex.value = null;
  if (fromIndex === null || fromIndex === targetIndex) return;
  const reordered = [...brandItems.value];
  const [moved] = reordered.splice(fromIndex, 1);
  reordered.splice(targetIndex, 0, moved);
  brandItems.value = reordered;
  try {
    await api.post('dashboard/brand-slider/reorder/', { items: reordered.map((i) => i.uuid) });
  } catch {
    toast.error('No se pudo guardar el nuevo orden.');
    await fetchBrandItems();
  }
}

const loadingBrandConfig = ref(false);
const savingBrandConfig  = ref(false);
const brandConfigError   = ref('');

const defaultBrandConfigForm = () => ({
  title: 'Marcas y clientes', subtitle: '',
  autoplay: true, speed: 3500, direction: 'left', loop: true, pause_on_hover: true,
  items_desktop: 6, items_tablet: 4, items_mobile: 2,
  background_color: '', padding_top: 'normal', padding_bottom: 'normal',
  is_visible: true,
});
const brandConfigForm = ref(defaultBrandConfigForm());

async function fetchBrandConfig() {
  loadingBrandConfig.value = true;
  try {
    const { data } = await api.get('dashboard/brand-slider/config/');
    brandConfigForm.value = {
      title: data.title || '', subtitle: data.subtitle || '',
      autoplay: data.autoplay, speed: data.speed, direction: data.direction,
      loop: data.loop, pause_on_hover: data.pause_on_hover,
      items_desktop: data.items_desktop, items_tablet: data.items_tablet, items_mobile: data.items_mobile,
      background_color: data.background_color || '',
      padding_top: data.padding_top, padding_bottom: data.padding_bottom,
      is_visible: data.is_visible,
    };
  } finally { loadingBrandConfig.value = false; }
}
async function saveBrandConfig() {
  savingBrandConfig.value = true; brandConfigError.value = '';
  try {
    await api.patch('dashboard/brand-slider/config/update/', brandConfigForm.value);
    toast.success('Configuracion actualizada.');
    await fetchBrandConfig();
  } catch (err) {
    brandConfigError.value = err?.response?.data?.detail || 'Error al guardar.';
  } finally { savingBrandConfig.value = false; }
}

// ══ INIT ═══════════════════════════════════════════════════════════════════════
onMounted(() => {
  fetchModules();
  fetchBanners();
  fetchCards();
  fetchGroupTitles();
  fetchFooter();
  fetchFooterGroups();
  fetchBrand();
  fetchNavbarLinks();
  fetchFooterCTA();
  fetchBrandItems();
  fetchBrandConfig();
});
</script>

<style scoped>
/* ══ SHELL ══════════════════════════════════════════════════════════════════ */
.hcb-shell {
  display: grid;
  grid-template-columns: 220px 1fr 320px;
  height: calc(100vh - 70px);
  overflow: hidden;
  background: #f1f5f9;
  font-size: .875rem;
  margin: -1.5rem;
}

/* ══ SIDEBAR ════════════════════════════════════════════════════════════════ */
.hcb-sidebar {
  background: #0f172a;
  color: #94a3b8;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  flex-shrink: 0;
}
.hcb-logo {
  display: flex; align-items: center; gap: .6rem;
  padding: 1.25rem 1.25rem 1rem;
  color: #fff; font-weight: 800; font-size: .95rem;
  border-bottom: 1px solid rgba(255,255,255,.07);
}
.hcb-logo .bi { font-size: 1.2rem; color: #2563eb; }
.hcb-nav { padding: .75rem .625rem; flex: 1; display: flex; flex-direction: column; gap: .25rem; }
.hcb-nav-btn {
  display: flex; align-items: center; gap: .6rem;
  padding: .625rem .875rem; border-radius: 10px;
  border: none; background: none; color: #94a3b8;
  cursor: pointer; text-align: left; width: 100%;
  font-size: .825rem; font-weight: 500;
  transition: background 180ms, color 180ms;
}
.hcb-nav-btn:hover { background: rgba(255,255,255,.06); color: #e2e8f0; }
.hcb-nav-btn--active { background: #2563eb !important; color: #fff !important; }
.hcb-nav-btn .bi { font-size: 1rem; flex-shrink: 0; }
.hcb-badge {
  margin-left: auto;
  background: rgba(255,255,255,.15); color: #fff;
  font-size: .65rem; font-weight: 700;
  padding: .15rem .45rem; border-radius: 99px;
}
.hcb-badge--gray { background: #e2e8f0; color: #64748b; }
.hcb-sidebar-footer { padding: 1rem 1.25rem; border-top: 1px solid rgba(255,255,255,.07); }
.hcb-preview-btn {
  display: flex; align-items: center; gap: .5rem;
  color: #94a3b8; text-decoration: none; font-size: .8rem;
  transition: color 200ms;
}
.hcb-preview-btn:hover { color: #fff; }

/* ══ EDITOR ═════════════════════════════════════════════════════════════════ */
.hcb-editor {
  overflow-y: auto;
  padding: 1.75rem 2rem;
}
.hcb-section-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  margin-bottom: 1.5rem; gap: 1rem;
}
.hcb-section-title { font-size: 1.25rem; font-weight: 800; color: #0f172a; margin-bottom: .25rem; }
.hcb-section-sub   { color: #64748b; margin: 0; font-size: .825rem; }
.hcb-loading { display: flex; justify-content: center; padding: 3rem; }
.hcb-empty { text-align: center; color: #94a3b8; padding: 2rem; background: #fff; border-radius: 12px; }
.hcb-empty--sm { display: flex; align-items: center; justify-content: center; gap: .75rem; padding: 1.25rem; font-size: .85rem; }
.hcb-hint { font-size: .72rem; color: #94a3b8; }

/* Buttons */
.hcb-btn {
  display: inline-flex; align-items: center; gap: .4rem;
  padding: .5rem 1rem; border-radius: 8px;
  border: 1px solid #e2e8f0; background: #fff; cursor: pointer;
  font-size: .825rem; font-weight: 600; color: #374151;
  transition: all 180ms;
}
.hcb-btn:hover { background: #f8fafc; }
.hcb-btn--primary { background: #2563eb; border-color: #2563eb; color: #fff; }
.hcb-btn--primary:hover { background: #1d4ed8; border-color: #1d4ed8; }
.hcb-icon-btn {
  width: 30px; height: 30px; border-radius: 8px;
  border: 1px solid #e2e8f0; background: #fff;
  display: grid; place-items: center; cursor: pointer; font-size: .8rem;
  transition: all 180ms;
}
.hcb-icon-btn:hover { background: #f1f5f9; }
.hcb-icon-btn--danger:hover { background: #fef2f2; border-color: #ef4444; color: #ef4444; }
.hcb-icon-btn--success:hover { background: #f0fdf4; border-color: #22c55e; color: #22c55e; }
.hcb-icon-btn--sm { width: 26px; height: 26px; font-size: .75rem; }
.hcb-icon-btn--xs { width: 24px; height: 24px; font-size: .7rem; }
.hcb-btn-link { background: none; border: none; cursor: pointer; font-size: .8rem; padding: 0; }

/* Chips */
.hcb-chip {
  display: inline-flex; align-items: center;
  padding: .2rem .55rem; border-radius: 6px;
  background: #f1f5f9; color: #475569;
  font-size: .7rem; font-weight: 600;
}
.hcb-chip--green { background: #dcfce7; color: #16a34a; }
.hcb-chip--gray  { background: #f1f5f9; color: #94a3b8; }
.hcb-chip--xs    { font-size: .65rem; padding: .15rem .45rem; }

/* Modules grid */
.hcb-modules-grid { display: flex; flex-direction: column; gap: .75rem; }
.hcb-module-card {
  display: flex; align-items: center; gap: 1rem;
  background: #fff; border-radius: 12px; padding: 1rem 1.25rem;
  border: 1px solid #e2e8f0; transition: box-shadow 180ms;
}
.hcb-module-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.06); }
.hcb-module-card--hidden { opacity: .55; }
.hcb-module-card__color {
  width: 44px; height: 44px; border-radius: 12px;
  display: grid; place-items: center; flex-shrink: 0;
  color: #fff; font-size: 1.1rem;
}
.hcb-module-card__body { flex: 1; min-width: 0; }
.hcb-module-card__label { font-weight: 700; color: #0f172a; margin-bottom: .35rem; }
.hcb-module-card__meta { display: flex; gap: .4rem; flex-wrap: wrap; }
.hcb-module-card__actions { display: flex; gap: .4rem; }

/* Banners list */
.hcb-banners-list { display: flex; flex-direction: column; gap: .625rem; }
.hcb-banner-row {
  display: flex; align-items: center; gap: 1rem;
  background: #fff; border-radius: 12px; padding: .875rem 1rem;
  border: 1px solid #e2e8f0;
}
.hcb-banner-row--inactive { opacity: .6; }
.hcb-drag-handle { cursor: grab; color: #94a3b8; flex-shrink: 0; }
.hcb-drag-handle:active { cursor: grabbing; }

/* Footer groups grid */
.hcb-fg-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: .75rem; }
.hcb-fg-card {
  display: flex; align-items: center; gap: .75rem;
  background: #fff; border-radius: 12px; padding: .875rem 1rem;
  border: 1px solid #e2e8f0; cursor: pointer; transition: border-color .15s ease;
}
.hcb-fg-card:hover { border-color: #93c5fd; }
.hcb-fg-card--selected { border-color: #2563eb; box-shadow: 0 0 0 1px #2563eb; }
.hcb-fg-card--inactive { opacity: .6; }
.hcb-fg-card__icon {
  width: 40px; height: 40px; border-radius: 8px; flex-shrink: 0;
  background: #eff6ff; color: #2563eb; display: grid; place-items: center; font-size: 1.1rem;
}
.hcb-fg-card__body { flex: 1; min-width: 0; }
.hcb-fg-card__title { font-weight: 600; color: #0f172a; }
.hcb-fg-card__meta { font-size: .75rem; color: #94a3b8; }
.hcb-banner-thumb {
  width: 80px; height: 52px; border-radius: 8px;
  overflow: hidden; flex-shrink: 0; background: #f1f5f9;
  display: grid; place-items: center;
}
.hcb-banner-thumb img { width: 100%; height: 100%; object-fit: cover; }
.hcb-banner-video-icon, .hcb-banner-placeholder { color: #94a3b8; font-size: 1.4rem; }
.hcb-banner-info { flex: 1; min-width: 0; }
.hcb-banner-title { font-weight: 600; color: #0f172a; margin-bottom: .3rem; }
.hcb-banner-meta  { display: flex; gap: .35rem; flex-wrap: wrap; }
.hcb-banner-actions { display: flex; gap: .4rem; }

/* Groups */
.hcb-groups-list { display: flex; flex-direction: column; gap: 1.5rem; }
.hcb-group-block { background: #fff; border-radius: 14px; border: 1px solid #e2e8f0; overflow: hidden; }
.hcb-group-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: .875rem 1.25rem; border-bottom: 1px solid #f1f5f9;
  background: #fafbfc; gap: .75rem;
}
.hcb-group-header__left  { display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; }
.hcb-group-header__right { display: flex; align-items: center; gap: .5rem; }
.hcb-group-name { font-weight: 700; color: #0f172a; }
.hcb-inline-input {
  border: 1px solid #2563eb; border-radius: 6px; padding: .3rem .6rem;
  font-size: .825rem; outline: none; min-width: 160px;
}

/* Cards grid */
.hcb-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: .75rem;
  padding: 1rem;
}
.hcb-card-thumb {
  border: 1px solid #e2e8f0; border-radius: 10px; padding: .75rem;
  display: flex; align-items: flex-start; gap: .6rem;
  background: #fff; transition: box-shadow 180ms;
}
.hcb-card-thumb:hover { box-shadow: 0 2px 10px rgba(0,0,0,.07); }
.hcb-card-thumb__icon {
  width: 34px; height: 34px; border-radius: 8px;
  display: grid; place-items: center; flex-shrink: 0; font-size: .9rem;
}
.hcb-card-thumb__body { flex: 1; min-width: 0; }
.hcb-card-thumb__title { font-weight: 600; font-size: .8rem; color: #0f172a; margin-bottom: .3rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hcb-card-thumb__meta  { display: flex; gap: .3rem; flex-wrap: wrap; }
.hcb-card-thumb__actions { display: flex; flex-direction: column; gap: .3rem; }

/* Card section */
.hcb-card-section { background: #fff; border-radius: 14px; border: 1px solid #e2e8f0; padding: 1.5rem; }
.hcb-subsection-title { font-weight: 700; color: #0f172a; margin-bottom: 1rem; font-size: .9rem; }

/* Links list */
.hcb-links-list { display: flex; flex-direction: column; gap: .5rem; }
.hcb-link-row {
  display: flex; align-items: center; gap: .75rem;
  padding: .625rem .875rem; background: #f8fafc;
  border-radius: 8px; border: 1px solid #e2e8f0;
}
.hcb-link-icon { color: #64748b; font-size: 1rem; flex-shrink: 0; }
.hcb-link-info { flex: 1; display: flex; align-items: center; gap: .4rem; flex-wrap: wrap; }
.hcb-link-title { font-weight: 600; color: #0f172a; }

/* Brand preview */
.hcb-brand-preview {
  display: flex; align-items: center; gap: 1rem;
  background: #f8fafc; border-radius: 12px; padding: 1.5rem;
  border: 1px solid #e2e8f0;
}
.hcb-brand-preview__logo {
  width: 64px; height: 64px; border-radius: 12px;
  overflow: hidden; flex-shrink: 0; background: #e2e8f0;
  display: grid; place-items: center;
}
.hcb-brand-preview__img { width: 100%; height: 100%; object-fit: contain; }
.hcb-brand-preview__placeholder { color: #94a3b8; font-size: 1.75rem; }
.hcb-brand-preview__name { font-weight: 800; font-size: 1.1rem; color: #0f172a; }
.hcb-brand-preview__tagline { color: #64748b; font-size: .85rem; }

/* Forms */
.hcb-form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: .875rem; }
.hcb-field { display: flex; flex-direction: column; gap: .35rem; }
.hcb-field--full { grid-column: 1 / -1; }
.hcb-label { font-size: .75rem; font-weight: 600; color: #374151; }
.hcb-input {
  border: 1px solid #e2e8f0; border-radius: 8px; padding: .5rem .75rem;
  font-size: .875rem; color: #0f172a; background: #fff;
  outline: none; transition: border-color 180ms;
  width: 100%;
}
.hcb-input:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,.12); }
.hcb-select { border: 1px solid #e2e8f0; border-radius: 8px; padding: .5rem .75rem; font-size: .875rem; color: #0f172a; background: #fff; outline: none; width: 100%; }
.hcb-select:focus { border-color: #2563eb; }
.hcb-select-sm { border: 1px solid #e2e8f0; border-radius: 6px; padding: .3rem .5rem; font-size: .75rem; color: #374151; background: #fff; cursor: pointer; }
.hcb-color-input { width: 38px; height: 38px; border-radius: 8px; border: 1px solid #e2e8f0; padding: 2px; cursor: pointer; }
.hcb-upload-area {
  border: 2px dashed #e2e8f0; border-radius: 10px;
  padding: 1.5rem; text-align: center; cursor: pointer;
  display: flex; flex-direction: column; align-items: center; gap: .5rem;
  color: #94a3b8; font-size: .825rem; transition: border-color 200ms, background 200ms;
}
.hcb-upload-area:hover, .hcb-upload-area--dragging {
  border-color: #2563eb; background: rgba(37,99,235,.04);
}
.hcb-upload-area .bi { font-size: 1.5rem; color: #cbd5e1; }
.hcb-upload-hint { font-size: .7rem; color: #cbd5e1; }

/* Media actual con opcion eliminar */
.hcb-media-current {
  border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden;
  background: #f8fafc;
}
.hcb-media-current__img {
  width: 100%; max-height: 160px; object-fit: cover; display: block;
}
.hcb-media-current__actions {
  display: flex; gap: .5rem; padding: .625rem;
  border-top: 1px solid #f1f5f9;
}
.hcb-btn--danger-sm {
  display: inline-flex; align-items: center; gap: .3rem;
  padding: .3rem .7rem; border-radius: 7px; font-size: .75rem; font-weight: 600;
  border: 1px solid #fca5a5; background: #fef2f2; color: #dc2626; cursor: pointer;
  transition: all 180ms;
}
.hcb-btn--danger-sm:hover { background: #fee2e2; border-color: #ef4444; }
.hcb-btn--sm {
  display: inline-flex; align-items: center; gap: .3rem;
  padding: .3rem .7rem; border-radius: 7px; font-size: .75rem; font-weight: 600;
  border: 1px solid #e2e8f0; background: #fff; color: #374151; cursor: pointer;
  transition: all 180ms;
}
.hcb-btn--sm:hover { background: #f8fafc; }

/* ══ PREVIEW ════════════════════════════════════════════════════════════════ */
.hcb-preview-panel {
  background: #fff; border-left: 1px solid #e2e8f0;
  display: flex; flex-direction: column; overflow: hidden;
}
.hcb-preview-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: .875rem 1rem; border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}
.hcb-preview-label { font-weight: 700; font-size: .8rem; color: #374151; }
.hcb-preview-viewport-btns { display: flex; gap: .3rem; }
.hcb-vp-btn {
  width: 28px; height: 28px; border-radius: 6px;
  border: 1px solid #e2e8f0; background: #fff;
  display: grid; place-items: center; cursor: pointer; font-size: .75rem;
  transition: all 180ms;
}
.hcb-vp-btn.active, .hcb-vp-btn:hover { background: #2563eb; border-color: #2563eb; color: #fff; }
.hcb-preview-frame-wrap { flex: 1; overflow-y: auto; padding: 1rem; background: #f8fafc; }
.hcb-preview-frame { background: #fff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; min-height: 200px; padding: 1rem; }
.hcb-preview-frame--tablet { max-width: 768px; margin: 0 auto; }
.hcb-preview-frame--mobile { max-width: 375px; margin: 0 auto; }

/* Preview: el contenido real ahora lo pintan HomeRenderer/CustomerNavbar/
   CustomerFooter (componentes reales, no markup propio) -- solo queda el
   contenedor del frame. El wrapper con position:relative crea un containing
   block para los descendientes position:fixed de CustomerNavbar (standalone
   usa position:relative de todos modos, pero se deja por robustez). */
.hcb-preview-frame--real { position: relative; padding: 0; }

/* ══ MODALES ════════════════════════════════════════════════════════════════ */
/* El chrome del modal (backdrop/header/footer) ahora vive en
   components/base/BaseModal.vue -- aqui solo quedan las clases de contenido
   especifico de cada formulario (hcb-form-grid, hcb-field, hcb-input, etc.) */

/* Banner live preview */
.hcb-banner-live-preview {
  position: relative; border-radius: 12px; overflow: hidden;
  background: #f1f5f9; min-height: 120px;
}
.hcb-blp-img { width: 100%; height: 160px; object-fit: cover; display: block; }
.hcb-blp-placeholder {
  height: 120px; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: .5rem;
  color: #94a3b8; font-size: .85rem;
}
.hcb-blp-placeholder .bi { font-size: 2rem; }
.hcb-blp-overlay {
  position: absolute; bottom: 0; left: 0; right: 0;
  background: linear-gradient(to top, rgba(0,0,0,.65), transparent);
  padding: .875rem 1rem;
}
.hcb-blp-title    { color: #fff; font-weight: 800; font-size: .9rem; }
.hcb-blp-subtitle { color: rgba(255,255,255,.8); font-size: .8rem; margin-top: .2rem; }
.hcb-blp-eyebrow {
  color: rgba(255,255,255,.78); font-size: .65rem; font-weight: 700; letter-spacing: 1.5px;
  text-transform: uppercase; margin-bottom: .3rem;
}
.hcb-blp-cta {
  margin-top: .5rem; background: #2563eb; color: #fff; border: none;
  border-radius: 6px; padding: .3rem .75rem; font-size: .75rem; font-weight: 600; cursor: pointer;
}
.hcb-blp-cta--ghost {
  background: transparent; border: 1px solid rgba(255,255,255,.55); color: rgba(255,255,255,.9);
}

/* Module live preview */
.hcb-module-live-preview {
  display: flex; align-items: center; gap: 1rem;
  border-radius: 12px; padding: 1rem 1.25rem;
}
.hcb-mlp-icon {
  width: 48px; height: 48px; border-radius: 14px;
  display: grid; place-items: center; color: #fff; font-size: 1.25rem; flex-shrink: 0;
}

/* Card form two-col */
.hcb-card-form-col  { overflow-y: auto; }
.hcb-card-preview-col { display: flex; flex-direction: column; }
.hcb-card-live-preview { flex: 1; padding: .5rem; }
</style>
