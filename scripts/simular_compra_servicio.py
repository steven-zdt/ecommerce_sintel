"""
simular_compra_servicio.py

Simula el flujo completo de un cliente solicitando un servicio tecnico
en Sintel E-Commerce, desde el catalogo (/servicios/) hasta la generacion
y confirmacion de la orden.

FLUJO REAL (equivale a lo que hace el usuario en el navegador):
  PASO 1  Registrar nuevo usuario cliente (o login si ya existe)
  PASO 2  Login + obtener JWT
  PASO 3  GET /api/v1/services/services/     <- catalogo publico
  PASO 4  GET /api/v1/services/services/<uuid>/  <- detalle del servicio
  PASO 5  GET .../quotation/?variant_uuid=X  <- cotizacion previa
  PASO 6  POST /api/v1/orders/service-orders/  <- crear orden de servicio
  PASO 7  POST .../confirm-cod/              <- confirmar pago en sitio
  PASO 8  GET /api/v1/orders/orders/<uuid>/  <- ver orden generada

Uso:
  python scripts/simular_compra_servicio.py
  python scripts/simular_compra_servicio.py --email yo@test.com --password Pass123!
  python scripts/simular_compra_servicio.py --base-url http://localhost:8000 --no-register
  python scripts/simular_compra_servicio.py --service-uuid <uuid> --variant-uuid <uuid>
  python scripts/simular_compra_servicio.py --no-cod   # omite el confirm-cod
  python scripts/simular_compra_servicio.py --verbose  # imprime respuestas completas

Requiere: pip install requests
"""

import argparse
import json
import sys
import uuid as uuid_lib
from datetime import datetime, timezone, timedelta

try:
    import requests
except ImportError:
    print("[ERROR] Instala requests: pip install requests")
    sys.exit(1)


# ─── Configuracion por defecto ────────────────────────────────────────────────

DEFAULT_BASE_URL = "http://localhost:8000"

# Usuario de prueba — se crea automaticamente si no existe
TEST_USER = {
    "email": f"cliente_sim_{uuid_lib.uuid4().hex[:8]}@sintel.co",
    "password": "TestSintel2025!",
    "first_name": "Cliente",
    "last_name": "Simulacion",
    "user_type": "CUSTOMER",
}

# Datos del encargado del servicio (contact_person — obligatorio en service-orders)
CONTACT_PERSON = {
    "full_name": "Juan Carlos Perez",
    "document_type": "CC",
    "document_number": "1098765432",
    "cargo": "Gerente de Operaciones",
    "email": "juan.perez@empresa.co",
    "phone": "3001234567",
    "phone_alt": "6012345678",
    "company": "Empresa Demo SAS",
    "department": "Operaciones",
    "access_notes": "Porteria principal, preguntar por sistemas",
}

VERBOSE = False


# ─── Helpers de UI ───────────────────────────────────────────────────────────

def header(title):
    bar = "=" * 62
    print(f"\n{bar}")
    print(f"  {title}")
    print(bar)


def step(num, desc):
    print(f"\n[PASO {num}] {desc}")
    print("-" * 52)


def ok(msg):
    print(f"  [OK]   {msg}")


def info(msg):
    print(f"  [i]    {msg}")


def warn(msg):
    print(f"  [!]    {msg}")


def fail(msg, data=None):
    print(f"\n  [FAIL] {msg}")
    if data:
        print(json.dumps(data, indent=4, ensure_ascii=False, default=str))
    sys.exit(1)


def dump(label, data):
    if VERBOSE:
        print(f"\n  --- {label} ---")
        print(json.dumps(data, indent=4, ensure_ascii=False, default=str))


def safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return {"_raw": resp.text[:200]} if resp.text else {}


# ─── Cliente HTTP ────────────────────────────────────────────────────────────

class SintelClient:
    def __init__(self, base_url):
        self.base = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _url(self, path):
        return f"{self.base}{path}"

    def set_token(self, token):
        self.session.headers["Authorization"] = f"Bearer {token}"

    def post(self, path, data=None):
        return self.session.post(self._url(path), json=data, timeout=30)

    def get(self, path, params=None):
        return self.session.get(self._url(path), params=params, timeout=30)


# ─── Paso 1: Registrar ───────────────────────────────────────────────────────

def paso_1_register(client, user_data):
    step(1, f"Registrar usuario: {user_data['email']}")
    payload = {
        "email":            user_data["email"],
        "password":         user_data["password"],
        "password_confirm": user_data["password"],
        "first_name":       user_data["first_name"],
        "last_name":        user_data["last_name"],
        "user_type":        user_data.get("user_type", "CUSTOMER"),
    }
    resp = client.post("/api/v1/auth/register/", data=payload)
    dump("register response", safe_json(resp))

    if resp.status_code == 201:
        data = resp.json()
        ok(f"Usuario creado: {data.get('email')}")
        info(f"UUID: {data.get('uuid') or data.get('id')}")
        return True

    if resp.status_code == 400 and "email" in resp.text.lower():
        warn("El email ya esta registrado — continuando con login existente")
        return False

    fail(f"Error al registrar (HTTP {resp.status_code})", resp.json())


# ─── Paso 2: Login ───────────────────────────────────────────────────────────

def paso_2_login(client, email, password):
    step(2, f"Login: {email}")
    resp = client.post("/api/v1/auth/login/", data={"email": email, "password": password})
    dump("login response", safe_json(resp))

    if resp.status_code != 200:
        fail(f"Login fallido (HTTP {resp.status_code})", resp.json())

    data = resp.json()
    tokens = data.get("tokens", {})
    access = tokens.get("access") or data.get("access")
    if not access:
        fail("No se recibio access token en la respuesta", data)

    client.set_token(access)
    user = data.get("user", {})
    ok(f"Login exitoso — {user.get('email')}")
    info(f"user_type: {user.get('user_type', '?')}")
    return access


# ─── Paso 3: Listar servicios ────────────────────────────────────────────────

def paso_3_catalogo(client):
    step(3, "GET catalogo de servicios activos  /api/v1/services/services/")
    resp = client.get("/api/v1/services/services/", params={"is_active": "true", "page_size": "10"})
    dump("services list", safe_json(resp))

    if resp.status_code != 200:
        fail(f"Error al listar servicios (HTTP {resp.status_code})", resp.json())

    data = resp.json()
    results = data.get("results", data) if isinstance(data, dict) else data

    if not results:
        warn("No hay servicios activos en la base de datos.")
        warn("Crea uno desde el shell de Django:")
        warn("  docker exec -it ecommerce_sintel_django python manage.py shell")
        warn("  >>> from technical_services.models import *")
        warn("  >>> from users.models import User")
        warn("  >>> u = User.objects.filter(is_superuser=True).first()")
        warn("  >>> cat = ServiceCategory.objects.create(name='Instalacion', slug='instalacion')")
        warn("  >>> svc = TechnicalService.objects.create(vendor=u, category=cat, name='Instalacion Electrica', slug='instalacion-electrica', is_active=True, is_purchasable=True)")
        warn("  >>> ServiceVariant.objects.create(service=svc, sku='INST-001', pricing_strategy='FIXED', fixed_price=150000)")
        fail("Sin servicios — cargar datos de prueba primero")

    ok(f"Se encontraron {data.get('count', len(results))} servicio(s). Mostrando primeros:")
    for i, s in enumerate(results[:5], 1):
        info(f"  {i}. {s.get('name')} — uuid={s.get('uuid')}")

    return results


# ─── Paso 4: Detalle del servicio ────────────────────────────────────────────

def paso_4_detalle(client, service_uuid):
    step(4, f"GET detalle del servicio  /api/v1/services/services/{service_uuid}/")
    resp = client.get(f"/api/v1/services/services/{service_uuid}/")
    dump("service detail", safe_json(resp))

    if resp.status_code != 200:
        fail(f"Error al obtener detalle (HTTP {resp.status_code})", resp.json())

    svc = resp.json()
    ok(f"Servicio: {svc.get('name')}")
    desc = str(svc.get("description", "")).strip()
    if desc:
        info(f"Descripcion: {desc[:90]}")

    # Buscar variantes en el detalle o en endpoint separado
    variants = svc.get("variants", [])
    if not variants:
        info("Detalle sin variants — consultando /api/v1/services/variants/?service=<uuid>")
        r2 = client.get("/api/v1/services/variants/", params={"service": service_uuid})
        if r2.status_code == 200:
            vdata = r2.json()
            variants = vdata.get("results", vdata) if isinstance(vdata, dict) else vdata

    if not variants:
        fail("Este servicio no tiene variantes activas. Elige otro o crea una variante.")

    ok(f"Variantes disponibles ({len(variants)}):")
    for i, v in enumerate(variants, 1):
        price = v.get("fixed_price") or v.get("calculated_price") or "dinamico"
        info(f"  {i}. SKU={v.get('sku')}  precio=${price}  uuid={v.get('uuid')}")

    return svc, variants


# ─── Paso 5: Cotizacion previa ───────────────────────────────────────────────

def paso_5_cotizacion(client, service_uuid, variant_uuid, duration=None):
    step(5, "GET cotizacion previa  .../quotation/")
    params = {"variant_uuid": str(variant_uuid)}
    if duration:
        params["duration"] = str(duration)
    resp = client.get(f"/api/v1/services/services/{service_uuid}/quotation/", params=params)
    dump("quotation", safe_json(resp))

    if resp.status_code != 200:
        warn(f"Cotizacion no disponible (HTTP {resp.status_code}) — continuando")
        return None

    q = resp.json()
    ok(f"Precio base:      ${q.get('base_amount', '?')}")
    info(f"Costo mano obra:  ${q.get('labor_cost', '?')}")
    info(f"Costo materiales: ${q.get('material_cost', '?')}")
    info(f"IVA ({q.get('iva_rate', '?')}%):      ${q.get('iva_amount', '?')}")
    ok(f"TOTAL estimado:   ${q.get('total_price', '?')}")
    return q


# ─── Paso 6: Crear orden de servicio (con retry de slot) ─────────────────────

_CAPACITY_KEYWORDS = ("capacidad", "horario", "disponible", "fecha u hora")
_MAX_SLOT_RETRIES  = 20   # cuantos slots intentar antes de rendirse
_SLOT_STEP_HOURS   = 4    # horas a avanzar por reintento (>= estimated_hours del servicio)
_WORK_START_HOUR   = 8    # primera hora laboral (UTC)
_WORK_END_HOUR     = 17   # ultima hora laboral (UTC)


def _next_work_slot(dt: datetime, step_hours: int) -> datetime:
    """Avanza dt por step_hours, saltando fuera del horario laboral."""
    dt = dt + timedelta(hours=step_hours)
    # Si cae fuera del horario laboral, ir al dia siguiente a las 8am
    if dt.hour >= _WORK_END_HOUR or dt.hour < _WORK_START_HOUR:
        dt = (dt + timedelta(days=1)).replace(
            hour=_WORK_START_HOUR, minute=0, second=0, microsecond=0
        )
    return dt


def paso_6_crear_service_order(client, variant_uuid, contact_person, base_dt: datetime):
    step(6, "POST solicitud de servicio  /api/v1/orders/service-orders/")

    candidate = base_dt
    attempt = 0

    while attempt < _MAX_SLOT_RETRIES:
        scheduled_dt = candidate.isoformat()
        payload = {
            "variant_uuid":   str(variant_uuid),
            "quantity":       1,
            "priority":       "medium",
            "description":    "Solicitud de servicio generada por simulacion de compra automatica.",
            "address":        "Calle 100 No. 15-20, Bogota, Cundinamarca",
            "scheduled_at":   scheduled_dt,
            "contact_person": contact_person,
        }

        if attempt == 0:
            dump("service-order payload", payload)

        resp = client.post("/api/v1/orders/service-orders/", data=payload)
        body = safe_json(resp)

        if resp.status_code == 201:
            if attempt > 0:
                info(f"Slot encontrado en el intento {attempt + 1}: {scheduled_dt[:16]} UTC")
            dump("service-order response", body)
            ok("Orden de servicio creada")
            info(f"Order UUID: {body.get('uuid')}")
            info(f"Status:     {body.get('status')}")
            info(f"Total:      ${body.get('total_amount', '?')}")
            return body

        if resp.status_code == 400:
            detail = str(body.get("detail", ""))
            # Si es error de capacidad, avanzar al siguiente slot
            if any(kw in detail.lower() for kw in _CAPACITY_KEYWORDS):
                attempt += 1
                if attempt == 1:
                    info(f"Slot ocupado en {scheduled_dt[:16]}. Buscando slot libre...")
                candidate = _next_work_slot(candidate, _SLOT_STEP_HOURS)
                continue
            # Otro error 400 — no tiene sentido reintentar
            fail(f"Error de validacion (HTTP 400)", body)

        # Cualquier otro error HTTP
        fail(f"Error inesperado (HTTP {resp.status_code})", body)

    fail(
        f"No se encontro slot disponible despues de {_MAX_SLOT_RETRIES} intentos.\n"
        f"  El servicio puede estar completamente lleno en el rango de fechas buscado.\n"
        f"  Intenta con --days-ahead 30 o usa --service-uuid con otro servicio."
    )


# ─── Paso 7: Confirmar pago COD ──────────────────────────────────────────────

def paso_7_confirmar_cod(client, order_uuid):
    step(7, f"POST confirmar pago en sitio  .../service-orders/{order_uuid}/confirm-cod/")
    resp = client.post(f"/api/v1/orders/service-orders/{order_uuid}/confirm-cod/")
    dump("confirm-cod response", safe_json(resp))

    if resp.status_code == 200:
        ok(resp.json().get("detail", "Confirmado"))
        return True

    if resp.status_code == 400:
        warn(f"No se pudo confirmar COD: {resp.json()}")
        return False

    warn(f"confirm-cod retorno HTTP {resp.status_code}")
    return False


# ─── Paso 8: Ver orden generada ──────────────────────────────────────────────

def paso_8_ver_orden(client, order_uuid):
    step(8, f"GET orden generada  /api/v1/orders/service-orders/{order_uuid}/")
    resp = client.get(f"/api/v1/orders/service-orders/{order_uuid}/")
    dump("order detail", safe_json(resp))

    if resp.status_code != 200:
        warn(f"service-orders/{order_uuid}/ retorno HTTP {resp.status_code} — intentando orders/")
        resp = client.get(f"/api/v1/orders/orders/{order_uuid}/")
        if resp.status_code != 200:
            warn(f"No se pudo recuperar la orden (HTTP {resp.status_code})")
            return None

    return safe_json(resp)


# ─── Mostrar resultado ───────────────────────────────────────────────────────

def mostrar_resultado(order, base_url):
    header("ORDEN DE SERVICIO GENERADA")

    print(f"  UUID:              {order.get('uuid')}")
    print(f"  Status:            {order.get('status')}")
    print(f"  Total:             ${order.get('total_amount', '?')}")
    print(f"  Creada:            {order.get('created_at', '')[:19]}")

    items = order.get("items", [])
    if items:
        print(f"\n  Items ({len(items)}):")
        for it in items:
            print(f"    - {it.get('item_name')}  |  SKU={it.get('sku')}  |  "
                  f"x{it.get('quantity')}  |  ${it.get('price')}")

    detail = order.get("service_detail", {}) or {}
    if detail:
        print(f"\n  Detalle del servicio:")
        print(f"    Prioridad:    {detail.get('priority')}")
        print(f"    Descripcion:  {str(detail.get('description', ''))[:80]}")
        print(f"    Direccion:    {detail.get('address')}")
        print(f"    Fecha/hora:   {str(detail.get('scheduled_at', ''))[:16]}")
        print(f"    Tecnico:      {detail.get('technician') or '(pendiente asignacion)'}")
        cp = detail.get("contact_person") or {}
        if cp:
            print(f"\n  Encargado del servicio:")
            print(f"    {cp.get('full_name')} — {cp.get('cargo')}")
            print(f"    Doc: {cp.get('document_type')} {cp.get('document_number')}")
            print(f"    Tel: {cp.get('phone')}  |  Email: {cp.get('email')}")

    timeline = order.get("timeline", [])
    if timeline:
        print(f"\n  Timeline ({len(timeline)} eventos):")
        for ev in timeline:
            print(f"    [{ev.get('created_at', '')[:16]}] {ev.get('status')} — {ev.get('notes', '')}")

    print(f"\n  Ver en panel admin:")
    print(f"    {base_url}/api/v1/orders/service-orders/{order.get('uuid')}/")
    print()


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    global VERBOSE

    parser = argparse.ArgumentParser(
        description="Simula solicitud de servicio tecnico — Sintel E-Commerce",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL,
                        help="URL base del backend Django (default: http://localhost:8000)")
    parser.add_argument("--email", default=None,
                        help="Email del cliente. Omitir = crear usuario nuevo automaticamente")
    parser.add_argument("--password", default=TEST_USER["password"],
                        help=f"Password (default: {TEST_USER['password']})")
    parser.add_argument("--no-register", action="store_true",
                        help="Omitir registro — solo hace login con el email/password dados")
    parser.add_argument("--service-uuid", default=None,
                        help="UUID del servicio especifico. Omitir = usar el primero disponible")
    parser.add_argument("--variant-uuid", default=None,
                        help="UUID de la variante especifica. Omitir = usar la primera disponible")
    parser.add_argument("--no-cod", action="store_true",
                        help="Omitir el paso de confirmacion COD (la orden queda en pending)")
    parser.add_argument("--days-ahead", type=int, default=7,
                        help="Dias en el futuro para agendar el servicio (default: 7)")
    parser.add_argument("--verbose", action="store_true",
                        help="Imprimir respuestas JSON completas de cada paso")
    args = parser.parse_args()

    VERBOSE = args.verbose

    header(f"SIMULACION DE COMPRA DE SERVICIO  —  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    info(f"Backend: {args.base_url}")
    info(f"Metodo de pago: {'COD (contra entrega)' if not args.no_cod else 'Ninguno — orden queda en pending'}")

    client = SintelClient(args.base_url)

    # Verificar backend activo
    try:
        health = client.get("/api/v1/health/")
        if health.status_code == 200:
            ok("Backend activo (health check OK)")
        else:
            warn(f"Health retorno HTTP {health.status_code} — verificar Django")
    except requests.exceptions.ConnectionError:
        fail(
            f"No se puede conectar a {args.base_url}\n"
            f"  Verificar que Django este corriendo:\n"
            f"  docker compose up -d sintel_django"
        )

    # Determinar credenciales
    email = args.email or TEST_USER["email"]
    password = args.password

    # Paso 1: Registro
    if not args.no_register:
        user_data = {**TEST_USER, "email": email, "password": password}
        paso_1_register(client, user_data)
    else:
        step(1, f"Registro omitido (--no-register)")
        info(f"Usando credenciales existentes: {email}")

    # Paso 2: Login
    paso_2_login(client, email, password)

    # Paso 3: Catalogo
    if args.variant_uuid and args.service_uuid:
        step(3, "Catalogo omitido (--service-uuid y --variant-uuid especificados)")
        service_uuid = args.service_uuid
        variant_uuid = args.variant_uuid
        info(f"Servicio UUID:  {service_uuid}")
        info(f"Variante UUID:  {variant_uuid}")
    else:
        services = paso_3_catalogo(client)
        service_uuid = args.service_uuid or services[0]["uuid"]

        # Paso 4: Detalle
        _, variants = paso_4_detalle(client, service_uuid)
        variant_uuid = args.variant_uuid or variants[0]["uuid"]
        info(f"Variante seleccionada: {variant_uuid}")

        # Paso 5: Cotizacion
        paso_5_cotizacion(client, service_uuid, variant_uuid)

    # Punto de inicio para busqueda de slot: days_ahead dias en el futuro a las 8am UTC.
    # El paso 6 avanza automaticamente si el slot esta ocupado (retry hasta 20 veces).
    base_dt = (
        datetime.now(tz=timezone.utc) + timedelta(days=args.days_ahead)
    ).replace(hour=_WORK_START_HOUR, minute=0, second=0, microsecond=0)
    info(f"\nBuscando slot desde: {base_dt.isoformat()[:16]} UTC")

    # Paso 6: Crear orden de servicio (busca slot libre automaticamente)
    order = paso_6_crear_service_order(client, variant_uuid, CONTACT_PERSON, base_dt)
    order_uuid = order["uuid"]

    # Paso 7: Confirmar COD (opcional)
    if not args.no_cod:
        confirmado = paso_7_confirmar_cod(client, order_uuid)
        if confirmado:
            ok("Servicio agendado y pago COD registrado")
    else:
        step(7, "Confirmacion COD omitida (--no-cod)")
        warn("La orden queda en status='pending'")

    # Paso 8: Ver orden final
    orden_final = paso_8_ver_orden(client, order_uuid)
    if orden_final:
        mostrar_resultado(orden_final, args.base_url)
    else:
        warn("No se pudo recuperar la orden completa — verificar manualmente")

    header("SIMULACION COMPLETADA")
    ok("El flujo de solicitud de servicio tecnico funciona correctamente.")
    info(f"Orden UUID: {order_uuid}")
    if not args.no_cod:
        info("El servicio queda en estado 'processing' o 'pending' segun logica de payment.")
    info(f"Explorar en Swagger: {args.base_url}/api/docs/")


if __name__ == "__main__":
    main()
