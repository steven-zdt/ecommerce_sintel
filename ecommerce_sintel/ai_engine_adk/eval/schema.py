"""
HARDENING F10 -- esquema del golden dataset (una linea JSON por caso, un archivo por categoria A-L).

Campos: id, category (A-L), tier (l1 = deterministico sin LLM | live = contra el ADK real en DEV), env (adk | django: donde
corre el evaluador), kind (que evaluador), input, expected, severity (critical | high | medium), source (por que existe el caso)
y known_gap (true = falla HOY por un hallazgo conocido; no cuenta contra las metricas, se lista aparte).
"""
import json
from pathlib import Path

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"

CATEGORIES = {
    "A": "intent_routing", "B": "rag_retrieval", "C": "answer_generation", "D": "grounding",
    "E": "tool_selection", "F": "tool_arguments", "G": "authorization", "H": "prompt_injection",
    "I": "memory_isolation", "J": "output_safety", "K": "latency", "L": "resilience",
}
TIERS = {"l1", "live"}
ENVS = {"adk", "django"}
SEVERITIES = {"critical", "high", "medium"}
REQUIRED = ("id", "category", "tier", "kind", "input", "expected", "severity", "source")
MIN_CASES_PER_CATEGORY = 5


def validate_case(case: dict) -> list[str]:
    errors = [f"falta {k}" for k in REQUIRED if k not in case]
    if errors:
        return errors
    if case["category"] not in CATEGORIES:
        errors.append(f"categoria invalida: {case['category']}")
    if not str(case["id"]).startswith(case["category"] + "-"):
        errors.append("el id debe empezar con '<categoria>-'")
    if case["tier"] not in TIERS:
        errors.append(f"tier invalido: {case['tier']}")
    if case.get("env", "adk") not in ENVS:
        errors.append(f"env invalido: {case.get('env')}")
    if case["severity"] not in SEVERITIES:
        errors.append(f"severity invalida: {case['severity']}")
    if not isinstance(case["input"], dict) or not isinstance(case["expected"], dict):
        errors.append("input y expected deben ser objetos")
    return errors


def load_dataset(directory: Path | None = None) -> list[dict]:
    """Carga todos los *.jsonl; lanza ValueError con TODOS los problemas (formato, ids duplicados) si los hay."""
    directory = directory or GOLDEN_DIR
    cases, problems, seen = [], [], set()
    for path in sorted(directory.glob("*.jsonl")):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            try:
                case = json.loads(line)
            except ValueError as exc:
                problems.append(f"{path.name}:{n}: JSON invalido ({exc})")
                continue
            errs = validate_case(case)
            if not errs and case["id"] in seen:
                errs = [f"id duplicado {case['id']}"]
            seen.add(case.get("id"))
            problems.extend(f"{path.name}:{n}: {e}" for e in errs)
            cases.append(case)
    if problems:
        raise ValueError("golden dataset invalido:\n" + "\n".join(problems))
    return cases
