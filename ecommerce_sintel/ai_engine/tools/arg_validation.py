"""
HARDENING F4/C2 (2026-09-24) -- validacion de argumentos de Tools contra su `args_schema`.

Se ejecuta en el `before_tool_callback` del ADK (que recibe los argumentos CRUDOS del modelo; el propio ADK descarta
en silencio los campos que no estan en la firma, por eso el rechazo de campos desconocidos no se puede hacer dentro
del wrapper de la Tool). Los mensajes de error NUNCA incluyen los valores recibidos (solo nombres de campo y tipos),
para no filtrar PII/secretos a logs ni al modelo.

Reglas: campos desconocidos, requeridos faltantes, tipo, `enum`, `minimum`/`maximum`, `maxLength` (default 4000),
`maxItems` (default 100), formato UUID (`format: uuid`, o nombre `uuid` / terminado en `_uuid`), y numeros finitos.
Tolerancia deliberada: un `number`/`integer` acepta un string numerico (los modelos locales lo mandan asi); un dict
o lista para un numero NO se acepta (el modelo mando `{"amount":...}` en un caso real, ver `_parse_price`).
"""
import math
import re

_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
DEFAULT_MAX_STRING = 4000
DEFAULT_MAX_ITEMS = 100


def _is_uuid_field(name: str, spec: dict) -> bool:
    return spec.get("format") == "uuid" or name == "uuid" or name.endswith("_uuid")


def _as_number(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):
        try:
            return float(v.replace(",", "").strip())
        except ValueError:
            return None
    return None


def _check_value(name: str, value, spec: dict) -> list[str]:
    errors: list[str] = []
    t = spec.get("type")
    types = t if isinstance(t, list) else [t]
    if "null" in types and value is None:
        return errors
    types = [x for x in types if x != "null"]
    if not types or types == [None]:
        return errors
    ok_type = False
    for typ in types:
        if typ == "string" and isinstance(value, str):
            ok_type = True
        elif typ in ("number", "integer") and _as_number(value) is not None:
            num = _as_number(value)
            if typ == "integer" and float(num) != int(num):
                continue
            if not math.isfinite(float(num)):
                errors.append(f"{name}: numero no finito")
                return errors
            if "minimum" in spec and num < spec["minimum"]:
                errors.append(f"{name}: menor que el minimo permitido")
            if "maximum" in spec and num > spec["maximum"]:
                errors.append(f"{name}: mayor que el maximo permitido")
            ok_type = True
        elif typ == "boolean" and isinstance(value, bool):
            ok_type = True
        elif typ == "array" and isinstance(value, list):
            ok_type = True
            if len(value) > spec.get("maxItems", DEFAULT_MAX_ITEMS):
                errors.append(f"{name}: demasiados elementos")
        elif typ == "object" and isinstance(value, dict):
            ok_type = True
    if not ok_type:
        errors.append(f"{name}: tipo invalido (se esperaba {'/'.join(str(x) for x in types)}, llego {type(value).__name__})")
        return errors
    if isinstance(value, str):
        if len(value) > spec.get("maxLength", DEFAULT_MAX_STRING):
            errors.append(f"{name}: texto demasiado largo")
        if _is_uuid_field(name, spec) and value and not _UUID_RE.match(value):
            errors.append(f"{name}: UUID malformado")
    if "enum" in spec and value not in spec["enum"]:
        errors.append(f"{name}: valor fuera de los permitidos")
    return errors


def validate_args(schema: dict, args: dict) -> list[str]:
    """Devuelve la lista de errores (vacia = valido). No modifica ni coacciona `args`."""
    schema = schema or {}
    props: dict = schema.get("properties") or {}
    required = schema.get("required") or []
    errors: list[str] = []
    for name in args:
        if name not in props:
            errors.append(f"campo desconocido: {name}")
    for name in required:
        if args.get(name) in (None, ""):
            errors.append(f"falta el campo requerido: {name}")
    for name, value in args.items():
        spec = props.get(name)
        if spec is None or value is None:
            continue
        errors.extend(_check_value(name, value, spec))
    return errors
