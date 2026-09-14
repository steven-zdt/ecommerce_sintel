import re
import logging
from typing import Literal
from pydantic import BaseModel, model_validator

logger = logging.getLogger(__name__)

# Reutilizamos los modelos de guardrails.py
from guardrails import ViolationItem, ValidationReport


# ─── Reglas CRITICAL frontend ─────────────────────────────────────────────────

def _rule_no_options_api(code: str, app: str) -> ViolationItem | None:
    # Detecta la firma clásica de Options API: export default { ... data() ... }
    options_api_pattern = re.search(
        r'export\s+default\s*\{[^}]*\b(data|methods|computed|mounted|created|watch)\s*[:(]',
        code, re.DOTALL
    )
    if options_api_pattern:
        return ViolationItem(
            rule_id="VUE_OPTIONS_API",
            severity="CRITICAL",
            description=(
                "Options API detectada (export default { data(), methods: {} }). "
                "SIEMPRE usar Composition API con <script setup>. "
                "Reemplazar con: <script setup> ... const x = ref() ... </script>"
            ),
        )
    return None


def _rule_no_direct_axios(code: str, app: str) -> ViolationItem | None:
    # Detecta import axios directo o uso de fetch() para API calls
    if re.search(r"import\s+axios\s+from\s+['\"]axios['\"]", code):
        return ViolationItem(
            rule_id="VUE_DIRECT_AXIOS",
            severity="CRITICAL",
            description=(
                "Import axios directo detectado. "
                "Usar SIEMPRE: import { useApi } from '@/composables/useApi' → const api = useApi(). "
                "El composable maneja JWT, refresh automatico y base URL."
            ),
        )
    return None


def _rule_dashboard_writes(code: str, app: str) -> ViolationItem | None:
    # Detecta POST/PATCH/DELETE a endpoints que no son dashboard/
    write_patterns = re.findall(
        r"api\.(post|patch|put|delete)\s*\(\s*['\"]([^'\"]+)['\"]",
        code, re.IGNORECASE
    )
    bad_endpoints = []
    for method, endpoint in write_patterns:
        # dashboard/, auth/, cart/ son permitidos como destinos de escritura
        allowed_prefixes = ("dashboard/", "auth/", "cart/", "support/", "users/me")
        if not any(endpoint.startswith(p) for p in allowed_prefixes):
            bad_endpoints.append(f"{method.upper()} '{endpoint}'")

    if bad_endpoints:
        return ViolationItem(
            rule_id="VUE_WRITE_NOT_DASHBOARD",
            severity="CRITICAL",
            description=(
                f"Escritura a endpoint publico detectada: {bad_endpoints[:3]}. "
                "Los ViewSets publicos son ReadOnly (retornan 405 en POST/PATCH/DELETE). "
                "SIEMPRE escribir a dashboard/: api.post('dashboard/products/', payload)"
            ),
        )
    return None


def _rule_no_missing_try_catch(code: str, app: str) -> ViolationItem | None:
    # Detecta llamadas await api. sin bloque try/catch cercano
    api_calls = list(re.finditer(r'await\s+api\.(get|post|patch|delete|put)\s*\(', code))
    if not api_calls:
        return None

    has_try = "try {" in code or "try{" in code
    if not has_try:
        return ViolationItem(
            rule_id="VUE_MISSING_TRY_CATCH",
            severity="CRITICAL",
            description=(
                "Llamadas await api.* sin bloque try/catch. "
                "Toda llamada async debe tener try { ... } catch (err) { toast.error(...) }. "
                "Patron: catch (err) { toast.error(err.response?.data?.detail || 'Error') }"
            ),
        )
    return None


def _rule_id_in_fk_payload(code: str, app: str) -> ViolationItem | None:
    # Detecta patrones como { category: item.id } o { brand: x.id } en payloads de escritura
    payload_id_pattern = re.findall(
        r'\b(category|brand|vendor|service|equipment|product|variant|tax|level)\s*:\s*\w+\.id\b',
        code, re.IGNORECASE
    )
    if payload_id_pattern:
        return ViolationItem(
            rule_id="VUE_ID_IN_FK_PAYLOAD",
            severity="CRITICAL",
            description=(
                f"FK con .id en payload detectado: {payload_id_pattern[:3]}. "
                "Las FK en payloads SIEMPRE deben usar .uuid (no .id). "
                "Ejemplo correcto: { category: category.uuid, brand: brand.uuid }. "
                "El .id (PK entero) SOLO va en la URL: dashboard/products/${item.id}/"
            ),
        )
    return None


def _rule_no_invented_imports(code: str, app: str) -> ViolationItem | None:
    # Detecta imports de componentes que no existen en el registry
    FORBIDDEN_COMPONENTS = [
        "Button.vue", "Badge.vue", "Rating.vue", "Modal.vue",
        "Spinner.vue", "Card.vue", "Input.vue", "Table.vue", "Drawer.vue",
        "Tooltip.vue", "Dropdown.vue", "Breadcrumb.vue", "Pagination.vue",
    ]
    found = []
    for comp in FORBIDDEN_COMPONENTS:
        if comp in code:
            found.append(comp)
    if found:
        return ViolationItem(
            rule_id="VUE_INVENTED_IMPORT",
            severity="CRITICAL",
            description=(
                f"Import de componentes inexistentes detectado: {found}. "
                "Solo importar componentes listados en FRONTEND_COMPONENT_REGISTRY.md. "
                "Spinner → <div class='spinner-border text-primary'></div> | "
                "Card → GlassCard | Modal → SintelOffcanvas | Button → <button class='btn btn-primary'>"
            ),
        )
    return None


# ─── Reglas WARNING frontend ──────────────────────────────────────────────────

def _rule_no_search_debounce(code: str, app: str) -> ViolationItem | None:
    has_search_input = bool(re.search(r'@input|v-model.*search|@keyup', code, re.IGNORECASE))
    if not has_search_input:
        return None
    has_debounce = "setTimeout" in code or "debounce" in code.lower()
    if not has_debounce:
        return ViolationItem(
            rule_id="VUE_MISSING_DEBOUNCE",
            severity="WARNING",
            description=(
                "Input de busqueda sin debounce detectado. "
                "Agregar: let timer = null; function onSearch() { clearTimeout(timer); timer = setTimeout(fetch, 400) }"
            ),
        )
    return None


def _rule_no_lazy_route(code: str, app: str) -> ViolationItem | None:
    # Solo aplica si el codigo parece ser un archivo router.js
    if "createRouter" not in code and "routes:" not in code:
        return None
    # Busca imports estaticos de componentes en routes
    static_component = re.search(
        r'component\s*:\s*(?!(?:\(\s*\)\s*=>|\(\s*\)\s*\{))\s*\w+',
        code
    )
    if static_component:
        return ViolationItem(
            rule_id="VUE_NO_LAZY_ROUTE",
            severity="WARNING",
            description=(
                "Componente de ruta sin lazy loading detectado. "
                "Usar: component: () => import('@/modules/shop/ProductList.vue')"
            ),
        )
    return None


def _rule_price_formatting(code: str, app: str) -> ViolationItem | None:
    bad_price = re.search(r'\.(toFixed|toLocaleString)\s*\(|Math\.(round|floor|ceil)\s*\([^)]*price', code)
    if bad_price:
        return ViolationItem(
            rule_id="VUE_BAD_PRICE_FORMAT",
            severity="WARNING",
            description=(
                "Formato de precio con toFixed/Math.round detectado. "
                "Usar SIEMPRE: new Intl.NumberFormat('es-CO').format(num)"
            ),
        )
    return None


# ─── Guardián principal frontend ──────────────────────────────────────────────

FRONTEND_CRITICAL_RULES = [
    _rule_no_options_api,
    _rule_no_direct_axios,
    _rule_dashboard_writes,
    _rule_no_missing_try_catch,
    _rule_id_in_fk_payload,
    _rule_no_invented_imports,
]

FRONTEND_WARNING_RULES = [
    _rule_no_search_debounce,
    _rule_no_lazy_route,
    _rule_price_formatting,
]


class SintelFrontendGuard:
    @classmethod
    def validate(cls, code: str, app_context: str = "") -> ValidationReport:
        violations: list[ViolationItem] = []
        warnings: list[ViolationItem] = []

        for rule_fn in FRONTEND_CRITICAL_RULES:
            try:
                result = rule_fn(code, app_context)
                if result:
                    violations.append(result)
            except Exception as exc:
                logger.warning("[guardrails_frontend] Error en regla %s: %s", rule_fn.__name__, exc)

        for rule_fn in FRONTEND_WARNING_RULES:
            try:
                result = rule_fn(code, app_context)
                if result:
                    warnings.append(result)
            except Exception as exc:
                logger.warning("[guardrails_frontend] Error en warning %s: %s", rule_fn.__name__, exc)

        report = ValidationReport(violations=violations, warnings=warnings)
        logger.info(
            "[guardrails_frontend] app=%s passed=%s violations=%d warnings=%d",
            app_context, report.passed, len(violations), len(warnings),
        )
        return report
