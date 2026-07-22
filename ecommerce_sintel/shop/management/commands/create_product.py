# shop/management/commands/create_product.py
#
# USO:
#   python manage.py create_product
#
# Mapea campo a campo el formulario "Nuevo Producto" de /panel/productos.
# Edita los bloques marcados con  <-- AQUI  y ejecuta el comando.

from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from shop.models import Category, Brand, Product, ProductVariant


# ============================================================
# BLOQUE 1 — DATOS GENERALES
# (Tab "General" del formulario > campos superiores)
# ============================================================

NOMBRE           = ""          # <-- AQUI: Nombre del producto. Ej: "Cable HDMI 4K 2m"    [OBLIGATORIO]
RESUMEN_CORTO    = ""          # <-- AQUI: Frase breve para tarjetas. Max 255 chars         [opcional]
DESCRIPCION      = ""          # <-- AQUI: Descripcion completa del producto                [opcional]
URL_VIDEO        = ""          # <-- AQUI: URL YouTube o Vimeo. Ej: "https://..."           [opcional]

# Condicion del producto — elige uno:
#   "new"          Nuevo
#   "used"         Usado
#   "refurbished"  Reacondicionado
CONDICION        = "new"       # <-- AQUI                                                   [obligatorio]

# Categoria — escribe el nombre EXACTO como aparece en /panel/categorias
CATEGORIA_NOMBRE = ""          # <-- AQUI: Ej: "Electronica", "Herramientas"                [OBLIGATORIO]

# Marca — escribe el nombre EXACTO como aparece en /panel/marcas (o deja "" para sin marca)
MARCA_NOMBRE     = ""          # <-- AQUI: Ej: "Samsung", "Bosch"                           [opcional]

# Visibilidad
ES_ACTIVO        = True        # <-- AQUI: True = visible en tienda / False = oculto
ES_DESTACADO     = False       # <-- AQUI: True = aparece en secciones "Destacados"


# ============================================================
# BLOQUE 2 — PRECIO Y SKU DE LA VARIANTE POR DEFECTO
# (Seccion "Precio y SKU de la variante por defecto" del formulario)
# Solo aplica al crear. Para ajustar precio/stock despues, usa /panel/productos → Editar → Variantes
# ============================================================

PRECIO_BASE      = Decimal("0.00")   # <-- AQUI: Ej: Decimal("149900")   [OBLIGATORIO, > 0]
SKU              = ""                 # <-- AQUI: Ej: "HDMI-4K-2M-001"    [opcional, auto si vacio]

# Variante por defecto — campos adicionales (se configuran en Tab Variantes tras crear)
STOCK_INICIAL    = 0                  # <-- AQUI: Unidades disponibles al crear
PRECIO_OFERTA    = None               # <-- AQUI: Decimal("99900") o None  [opcional]

# Atributos de la variante (clave-valor libre)
# Ej: {"Color": "Negro", "Longitud": "2m"}
ATRIBUTOS        = {}                 # <-- AQUI: dict con los atributos de la variante


# ============================================================
# BLOQUE 3 — SEO
# (Tab "SEO" del formulario)
# ============================================================

META_TITULO      = ""          # <-- AQUI: Titulo optimizado para Google. Max 70 chars      [opcional]
META_DESCRIPCION = ""          # <-- AQUI: Descripcion para buscadores. Max 160 chars       [opcional]


# ============================================================
# BLOQUE 4 — LOGISTICA DE LA VARIANTE
# (Tab Variantes → editar variante → seccion Logistica / Transporte)
# ============================================================

PESO_KG  = None   # <-- AQUI: float o None. Ej: 0.35
LARGO_CM = None   # <-- AQUI: float o None. Ej: 20.0
ANCHO_CM = None   # <-- AQUI: float o None. Ej: 10.0
ALTO_CM  = None   # <-- AQUI: float o None. Ej: 5.0


# ============================================================
# MOTOR — no editar debajo de esta linea
# ============================================================

class Command(BaseCommand):
    help = "Crea un producto con variante por defecto via ORM (script marco)"

    def handle(self, *args, **options):
        User = get_user_model()

        # Validaciones minimas antes de tocar la BD
        if not NOMBRE.strip():
            raise CommandError("NOMBRE es obligatorio. Edita el BLOQUE 1.")
        if not CATEGORIA_NOMBRE.strip():
            raise CommandError("CATEGORIA_NOMBRE es obligatorio. Edita el BLOQUE 1.")
        if PRECIO_BASE <= Decimal("0"):
            raise CommandError("PRECIO_BASE debe ser mayor que 0. Edita el BLOQUE 2.")

        # Vendor — siempre el superusuario principal (regla del proyecto)
        vendor = User.objects.filter(is_superuser=True).first()
        if not vendor:
            raise CommandError("No existe ningun superusuario. Crea uno con createsuperuser.")

        # Categoria
        try:
            categoria = Category.objects.get(name__iexact=CATEGORIA_NOMBRE.strip(), is_active=True)
        except Category.DoesNotExist:
            raise CommandError(
                f"Categoria '{CATEGORIA_NOMBRE}' no encontrada o inactiva. "
                "Verifica el nombre exacto en /panel/categorias."
            )

        # Marca (opcional)
        marca = None
        if MARCA_NOMBRE.strip():
            try:
                marca = Brand.objects.get(name__iexact=MARCA_NOMBRE.strip(), is_active=True)
            except Brand.DoesNotExist:
                raise CommandError(
                    f"Marca '{MARCA_NOMBRE}' no encontrada o inactiva. "
                    "Verifica el nombre exacto en /panel/marcas."
                )

        # Validar SKU si fue definido
        sku_final = SKU.strip() if SKU.strip() else None
        if sku_final and ProductVariant.objects.filter(sku=sku_final).exists():
            raise CommandError(f"El SKU '{sku_final}' ya esta en uso. Elige otro.")

        # Crear Producto
        producto = Product.objects.create(
            vendor=vendor,
            name=NOMBRE.strip(),
            short_description=RESUMEN_CORTO.strip() or None,
            description=DESCRIPCION.strip(),
            video_url=URL_VIDEO.strip() or None,
            condition=CONDICION,
            category=categoria,
            brand=marca,
            is_active=ES_ACTIVO,
            is_featured=ES_DESTACADO,
            meta_title=META_TITULO.strip(),
            meta_description=META_DESCRIPCION.strip(),
        )

        # Crear Variante por defecto
        import uuid as _uuid
        sku_definitivo = sku_final or f"{producto.slug[:20].upper()}-{_uuid.uuid4().hex[:6].upper()}"

        variante = ProductVariant.objects.create(
            product=producto,
            sku=sku_definitivo,
            price=PRECIO_BASE,
            discounted_price=PRECIO_OFERTA,
            is_default=True,
            attributes=ATRIBUTOS,
            weight=PESO_KG,
            length=LARGO_CM,
            width=ANCHO_CM,
            height=ALTO_CM,
        )

        # Resultado
        self.stdout.write(self.style.SUCCESS("\n========================================"))
        self.stdout.write(self.style.SUCCESS("  PRODUCTO CREADO EXITOSAMENTE"))
        self.stdout.write(self.style.SUCCESS("========================================"))
        self.stdout.write(f"  Nombre    : {producto.name}")
        self.stdout.write(f"  UUID      : {producto.uuid}")
        self.stdout.write(f"  Slug      : {producto.slug}")
        self.stdout.write(f"  Categoria : {categoria.name}")
        self.stdout.write(f"  Marca     : {marca.name if marca else '(sin marca)'}")
        self.stdout.write(f"  Condicion : {CONDICION}")
        self.stdout.write(f"  Activo    : {ES_ACTIVO}  |  Destacado: {ES_DESTACADO}")
        self.stdout.write("  ---")
        self.stdout.write(f"  Variante  : {variante.sku}")
        self.stdout.write(f"  Precio    : ${PRECIO_BASE:,.0f}")
        if PRECIO_OFERTA:
            self.stdout.write(f"  Oferta    : ${PRECIO_OFERTA:,.0f}")
        if ATRIBUTOS:
            self.stdout.write(f"  Atributos : {ATRIBUTOS}")
        if any([PESO_KG, LARGO_CM]):
            self.stdout.write(f"  Logistica : {PESO_KG}kg | {LARGO_CM}x{ANCHO_CM}x{ALTO_CM} cm")
        self.stdout.write("  ---")
        self.stdout.write(f"  Panel     : /panel/productos  (busca '{producto.name}')")
        self.stdout.write(f"  Tienda    : /tienda/producto/{producto.uuid}")
        self.stdout.write(self.style.SUCCESS("========================================\n"))
