import ast
import re
import logging
from typing import Literal
from pydantic import BaseModel, model_validator

logger = logging.getLogger(__name__)


class ViolationItem(BaseModel):
    rule_id: str
    severity: Literal["CRITICAL", "WARNING"]
    description: str
    line_hint: str = ""


class ValidationReport(BaseModel):
    passed: bool = True
    violations: list[ViolationItem] = []
    warnings: list[ViolationItem] = []

    @model_validator(mode="after")
    def compute_passed(self) -> "ValidationReport":
        has_critical = any(v.severity == "CRITICAL" for v in self.violations)
        self.passed = not has_critical
        return self


# ─── Reglas CRITICAL ─────────────────────────────────────────────────────────

def _rule_no_float_money(code: str, app: str) -> ViolationItem | None:
    pattern = r'(price|amount|total|discount|subtotal|rate|fee|balance)\s*[=:]\s*\d+\.\d+'
    matches = re.findall(pattern, code, re.IGNORECASE)
    if not matches:
        return None
    bad = [m for m in matches if not any(
        prefix in code[max(0, code.find(m) - 20):code.find(m)]
        for prefix in ("Decimal(", "decimal.Decimal(")
    )]
    if bad:
        return ViolationItem(
            rule_id="FLOAT_MONEY",
            severity="CRITICAL",
            description=(
                "Valor monetario como float literal detectado. "
                f"Campos afectados: {bad[:3]}. Usar Decimal('X.XX') siempre."
            ),
            line_hint=str(bad[0]),
        )
    return None


def _rule_no_physical_delete(code: str, app: str) -> ViolationItem | None:
    # Management commands y scripts de seed usan .delete() de forma legitima
    # (limpiar fixtures, vaciar carritos, etc.) — no son logica de negocio.
    if "BaseCommand" in code or "class Command" in code:
        return None

    lines = [l for l in code.split("\n") if not l.strip().startswith("#")]
    clean = "\n".join(lines)
    matches = re.findall(r'\.\s*delete\s*\(\s*\)', clean)
    if not matches:
        return None

    # Permitir borrado de CartItem en queryset (cart.items / CartItem.objects)
    # Es una tabla de sesion, no una entidad de negocio con soft-delete obligatorio.
    allowed_contexts = ("cart.items", "CartItem.objects", "items.all()")
    dangerous = []
    for match_pos in [m.start() for m in re.finditer(r'\.\s*delete\s*\(\s*\)', clean)]:
        snippet = clean[max(0, match_pos - 60):match_pos]
        if not any(ctx in snippet for ctx in allowed_contexts):
            dangerous.append(clean[max(0, match_pos - 30):match_pos + 10].strip())

    if dangerous:
        return ViolationItem(
            rule_id="PHYSICAL_DELETE",
            severity="CRITICAL",
            description=(
                "Borrado fisico detectado (.delete()). "
                "Usar soft-delete: obj.is_active=False; obj.is_deleted=True; obj.save(update_fields=[...]). "
                f"Contextos detectados: {dangerous[:2]}"
            ),
        )
    return None


def _rule_no_emojis(code: str, app: str) -> ViolationItem | None:
    emoji_re = re.compile(
        r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
        r"\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF"
        r"\U00002702-\U000027B0\U000024C2-\U0001F251"
        r"\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F"
        r"\U0001FA70-\U0001FAFF]+",
        flags=re.UNICODE,
    )
    matches = emoji_re.findall(code)
    if matches:
        return ViolationItem(
            rule_id="EMOJI_IN_PY",
            severity="CRITICAL",
            description=(
                f"Emoji detectado en archivo Python: {matches[:3]}. "
                "Causa SyntaxError / 500 en el entorno de produccion."
            ),
        )
    return None


def _rule_wrong_admin_permission(code: str, app: str) -> ViolationItem | None:
    bad_import = re.search(
        r'from\s+rest_framework\.permissions\s+import[^\n]*IsAdminUser', code
    )
    if bad_import:
        return ViolationItem(
            rule_id="WRONG_ADMIN_PERMISSION_IMPORT",
            severity="CRITICAL",
            description=(
                "Import incorrecto: 'from rest_framework.permissions import IsAdminUser'. "
                "Usar: 'from users.api.permissions import IsAdminUser'. "
                "El IsAdminUser de DRF solo verifica is_staff, no is_superuser."
            ),
        )
    if 'is_staff' in code and 'is_superuser' not in code:
        context_match = re.search(r'.{0,80}is_staff.{0,80}', code)
        snippet = context_match.group(0).strip() if context_match else ""
        if 'def has_permission' in code or 'permission_classes' in code:
            return ViolationItem(
                rule_id="INCOMPLETE_ADMIN_CHECK",
                severity="CRITICAL",
                description=(
                    "Verificacion de is_staff sin is_superuser en logica de permisos. "
                    "El rol admin requiere is_staff=True AND is_superuser=True."
                ),
                line_hint=snippet,
            )
    return None


def _rule_notify_outside_on_commit(code: str, app: str) -> ViolationItem | None:
    has_notify = "dispatch_notification" in code or "ws_notify" in code
    if not has_notify:
        return None
    if "on_commit" not in code:
        return ViolationItem(
            rule_id="NOTIFY_OUTSIDE_ON_COMMIT",
            severity="CRITICAL",
            description=(
                "dispatch_notification / ws_notify detectado fuera de transaction.on_commit. "
                "Patron correcto: transaction.on_commit(lambda: NotificationCommands.dispatch_notification(...))"
            ),
        )
    return None


def _rule_wompi_missing_signature(code: str, app: str) -> ViolationItem | None:
    if app != "wompi":
        return None
    is_webhook_view = "webhook" in code.lower() or "event" in code.lower()
    if is_webhook_view and "WOMPI_EVENTS_SECRET" not in code and "_verify_wompi_event_signature" not in code:
        return ViolationItem(
            rule_id="WOMPI_MISSING_SIGNATURE_CHECK",
            severity="CRITICAL",
            description=(
                "Endpoint Wompi sin validacion de firma SHA256. "
                "Llamar a _verify_wompi_event_signature(payload) o verificar WOMPI_EVENTS_SECRET "
                "usando hmac.compare_digest antes de procesar cualquier evento."
            ),
        )
    return None


def _rule_viewset_direct_db_write(code: str, app: str) -> ViolationItem | None:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    WRITE_METHODS = {"create", "save", "bulk_create", "update", "get_or_create", "update_or_create"}
    VIEWSET_BASE_NAMES = {"ViewSet", "APIView", "ModelViewSet", "GenericViewSet", "ReadOnlyModelViewSet"}

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        base_names = set()
        for b in node.bases:
            if isinstance(b, ast.Name):
                base_names.add(b.id)
            elif isinstance(b, ast.Attribute):
                base_names.add(b.attr)
        if not base_names.intersection(VIEWSET_BASE_NAMES):
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                if child.func.attr in WRITE_METHODS:
                    return ViolationItem(
                        rule_id="VIEWSET_DIRECT_DB_WRITE",
                        severity="CRITICAL",
                        description=(
                            f"ViewSet '{node.name}' llama directamente a .{child.func.attr}(). "
                            "Los ViewSets solo orquestan: delegar mutaciones a un Command "
                            "en services/commands.py."
                        ),
                    )
    return None


# ─── Reglas WARNING ──────────────────────────────────────────────────────────

def _rule_missing_transaction_atomic(code: str, app: str) -> ViolationItem | None:
    if "Commands" not in code:
        return None
    has_def = bool(re.search(r'\bdef\s+\w+', code))
    if has_def and "transaction.atomic" not in code and "@atomic" not in code:
        return ViolationItem(
            rule_id="MISSING_TRANSACTION_ATOMIC",
            severity="WARNING",
            description=(
                "Clase Commands sin @transaction.atomic en sus metodos de mutacion. "
                "Todos los Commands que escriben en BD deben ser atomicos."
            ),
        )
    return None


def _rule_missing_select_for_update(code: str, app: str) -> ViolationItem | None:
    touches_stock = any(kw in code for kw in ("StockRecord", "stock_record", ".stock", "balance_after"))
    if touches_stock and "select_for_update" not in code:
        return ViolationItem(
            rule_id="MISSING_SELECT_FOR_UPDATE",
            severity="WARNING",
            description=(
                "Operacion sobre stock sin select_for_update(). "
                "Riesgo de race condition bajo carga concurrente alta. "
                "Usar: StockRecord.objects.select_for_update().get(...)"
            ),
        )
    return None


def _rule_selector_side_effects(code: str, app: str) -> ViolationItem | None:
    if "Selector" not in code:
        return None
    write_signals = any(kw in code for kw in (".save(", ".create(", ".delete(", ".update(", "bulk_create"))
    if write_signals:
        return ViolationItem(
            rule_id="SELECTOR_HAS_SIDE_EFFECTS",
            severity="WARNING",
            description=(
                "Un Selector contiene operaciones de escritura. "
                "Los Selectors son de solo lectura. Mover mutaciones a un Command."
            ),
        )
    return None


# ─── Guardián principal ───────────────────────────────────────────────────────

CRITICAL_RULES = [
    _rule_no_float_money,
    _rule_no_physical_delete,
    _rule_no_emojis,
    _rule_wrong_admin_permission,
    _rule_notify_outside_on_commit,
    _rule_wompi_missing_signature,
    _rule_viewset_direct_db_write,
]

WARNING_RULES = [
    _rule_missing_transaction_atomic,
    _rule_missing_select_for_update,
    _rule_selector_side_effects,
]


class SintelArchitectureGuard:
    @classmethod
    def validate(cls, code: str, app_context: str = "") -> ValidationReport:
        violations: list[ViolationItem] = []
        warnings: list[ViolationItem] = []

        for rule_fn in CRITICAL_RULES:
            try:
                result = rule_fn(code, app_context)
                if result:
                    violations.append(result)
            except Exception as exc:
                logger.warning("[guardrails] Error en regla %s: %s", rule_fn.__name__, exc)

        for rule_fn in WARNING_RULES:
            try:
                result = rule_fn(code, app_context)
                if result:
                    warnings.append(result)
            except Exception as exc:
                logger.warning("[guardrails] Error en regla warning %s: %s", rule_fn.__name__, exc)

        report = ValidationReport(violations=violations, warnings=warnings)
        logger.info(
            "[guardrails] app=%s passed=%s violations=%d warnings=%d",
            app_context, report.passed, len(violations), len(warnings),
        )
        return report
