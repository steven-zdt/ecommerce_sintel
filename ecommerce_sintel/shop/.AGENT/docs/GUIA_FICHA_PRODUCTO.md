# Guia: Como Redactar la Ficha de un Producto (shop)

Companero de `ARQUITECTURA_COMPLETA_SHOP.md` §13 — ese documento explica el catalogo enriquecido
(modelos, service layer, endpoints); este documento es la guia practica de contenido para quien
carga un producto nuevo.

**Actualizado 2026-08-03 (segunda pasada):** la brecha de modelo frente a `renting` que motivo
esta guia originalmente **ya se cerro** — `shop.Product` tiene ahora los mismos 11 modelos
estructurados que `renting.Equipment` (ProductFeature, ProductIncludedItem/ExcludedItem,
ProductSpecificationGroup/ProductSpecification, ProductRequirement, ProductServiceIncluded/
OptionalService, ProductFAQ, ProductVideo, ProductDocument), con endpoints admin reales
(`/api/v1/dashboard/product-*`, ver §13.2 del doc de arquitectura). **Lo que sigue pendiente es
la UI de admin (frontend)** — hoy esos endpoints solo son alcanzables via API directa (Postman/
`curl`) o `manage.py shell`, no desde `/panel/productos` → `ProductForm.vue`. Esta guia describe
el contenido tanto para cuando se use la UI (una vez exista) como para cargar datos hoy via API.

**Referencia de nivel de detalle esperado:** producto real
"Alquiler de Arco Detector de Metales para Control de Accesos y Eventos" en el modulo de renting
(`/panel/renta`, item "Gestionar Equipo") — verificado en vivo contra produccion.

---

## 1. Que campo llena cada seccion

| Seccion de esta guia | Campo/modelo real |
|---|---|
| Descripcion comercial | `Product.description` (prosa, primer bloque) |
| Descripcion tecnica | `Product.description` (prosa, segundo bloque) |
| Caracteristicas destacadas | `ProductFeature` (fila titulo+valor+icono, NO texto libre) |
| Incluye / No incluye | `ProductIncludedItem` / `ProductExcludedItem` |
| Especificaciones tecnicas | `ProductSpecificationGroup` + `ProductSpecification` (agrupadas) **o** `ProductVariant.attributes` (JSON plano, ver §13.4 del doc de arquitectura) para specs que varian por SKU |
| Requisitos de instalacion/uso | `ProductRequirement` |
| Servicios incluidos/opcionales | `ProductServiceIncluded` / `ProductOptionalService` |
| Documentacion asociada | `ProductDocument` (upload real, tipado Manual/Ficha tecnica/Certificado/etc. — YA NO es un link Markdown dentro de `description`) |
| Preguntas frecuentes | `ProductFAQ` |
| Video | `ProductVideo` (lista, YouTube/Vimeo/MP4) — `Product.video_url` sigue existiendo como campo legacy de un solo video |
| Resumen de tarjeta | `Product.short_description` |
| SEO | `Product.meta_title` / `Product.meta_description` |

**Nota sobre `description`:** con los modelos estructurados arriba, `description` vuelve a su
proposito original (prosa comercial/tecnica en 2 parrafos) — ya NO hace falta meter listas,
tablas de specs ni links a documentos ahi dentro. La plantilla de la seccion 2 de este documento
sigue siendo valida como CONTENIDO, pero cada bloque ahora tiene un lugar estructurado propio.

---

## 2. Plantilla (copiar dentro de `description`)

```markdown
## Descripcion comercial
{2-4 frases, tono de venta, caso de uso principal. Ejemplo de tono de referencia (renting):
"Garantice la maxima seguridad en sus eventos corporativos, conciertos, ferias y congresos..."}

## Descripcion tecnica
{Que es el producto, para que sirve, contexto de uso profesional/domestico, a quien esta dirigido.}

## Componentes e integraciones
- {Componente 1 que trae la caja}
- {Componente 2 que trae la caja}
- {Integracion/compatibilidad: apps moviles, protocolos, estandares (ej. ONVIF, RTSP)}

## Especificaciones tecnicas

**{Grupo 1, ej. "Camara"}**
| Especificacion | Valor |
|---|---|
| {nombre} | {valor} |

**{Grupo 2, ej. "Grabador (DVR/NVR)"}**
| Especificacion | Valor |
|---|---|
| {nombre} | {valor} |

## Documentacion asociada
- [Ficha tecnica]({url})
- [Manual de instalacion]({url})

## Requisitos de instalacion
- {ej. punto electrico cercano, conexion a internet, espacio de montaje}
```

`short_description` (campo separado, no va en el Markdown de arriba): 1 sola frase, resumen de la
seccion "Descripcion comercial" — este es el texto que aparece en la tarjeta del catalogo.

---

## 3. Ejemplo completo desarrollado

Basado en un kit CCTV real del catalogo actual de shop (categoria "CCTV", marca Hikvision),
reescrito siguiendo la plantilla de arriba — **ilustrativo**, no aplicado automaticamente al
producto real (requeriria editarlo desde el panel admin, decision de quien administra el catalogo).

> **`short_description`:**
> Kit de videovigilancia Full HD 1080p con 4 camaras, DVR e instalacion incluida — seguridad 24/7
> lista para funcionar.

> **`description`:**
>
> ## Descripcion comercial
> No dejes tu seguridad al azar. Con este Kit de Seguridad Integral Hikvision obtienes vigilancia
> de alta definicion las 24 horas del dia, con tecnologia de punta e instalacion profesional lista
> para funcionar — sin sorpresas ni gastos ocultos. Ideal para negocios, bodegas y hogares que
> necesitan monitoreo confiable desde el primer dia.
>
> ## Descripcion tecnica
> Sistema de videovigilancia analogico HD (TurboHD) de 4 canales, pensado para instalacion
> permanente en interior y exterior. Combina camaras domo resistentes a intemperie con un grabador
> digital (DVR) que permite ver el video en vivo y grabaciones pasadas desde el celular o el
> computador, en cualquier lugar con conexion a internet.
>
> ## Componentes e integraciones
> - 4x camaras domo Hikvision 1080p, vision nocturna IR hasta 20m
> - 1x DVR Hikvision TurboHD de 4 canales
> - 1x disco duro para grabacion continua (preinstalado)
> - Cableado coaxial + conectores, listos para instalar
> - 1x fuente de alimentacion distribuida (4 salidas)
> - Compatible con la app movil Hik-Connect (iOS/Android) para monitoreo remoto
>
> ## Especificaciones tecnicas
>
> **Camaras**
> | Especificacion | Valor |
> |---|---|
> | Resolucion | 1080p (2MP) |
> | Alcance infrarrojo | 20 metros |
> | Proteccion contra intemperie | IP67 |
> | Angulo de vision | 103 grados |
>
> **Grabador (DVR)**
> | Especificacion | Valor |
> |---|---|
> | Canales | 4 |
> | Formato de video | TurboHD (analogico) |
> | Salida | HDMI + VGA |
> | Acceso remoto | App Hik-Connect, P2P sin IP publica |
>
> ## Documentacion asociada
> - [Ficha tecnica de la camara DS-2CE70DF3T-MF (sitio Hikvision)](https://www.hikvision.com/)
> - [Manual del DVR TurboHD (sitio Hikvision)](https://www.hikvision.com/)
>
> ## Requisitos de instalacion
> - Punto electrico cerca de la ubicacion del DVR
> - Conexion a internet (router con salida a la red local) para el acceso remoto
> - Superficie firme para el montaje de camaras (pared o techo)

`attributes` sugerido para la variante principal (convencion de claves, ver §13.3 del doc de
arquitectura):

```json
{
  "resolucion": "1080p",
  "canales": "4",
  "alcance_ir": "20m",
  "proteccion": "IP67",
  "app_movil": "Hik-Connect"
}
```

---

## 4. Checklist rapido antes de publicar

- [ ] `short_description` con una frase de venta clara (aparece en la tarjeta del catalogo)
- [ ] `description` con las 4-6 secciones de la plantilla (comercial, tecnica, componentes,
      especificaciones, documentacion si aplica, requisitos si aplica)
- [ ] Especificaciones agrupadas por categoria logica (no una lista plana sin orden)
- [ ] `meta_title`/`meta_description` llenos (SEO — 70/160 caracteres aprox.)
- [ ] Al menos 1 imagen marcada `is_primary=True`
- [ ] Si el producto tiene manual/ficha tecnica del fabricante, enlazado en "Documentacion asociada"
