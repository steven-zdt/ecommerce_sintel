"""
HARDENING F15 -- escaner de secretos (stdlib). NUNCA imprime valores: solo archivo, linea, tipo y una huella truncada (sha256[:8]) para
poder comparar hallazgos entre corridas sin exponer el secreto. LO EJECUTA EL USUARIO A MANO (regla: el asistente no ejecuta pruebas).

    python scripts/security/scan_secrets.py --staged          # antes de un commit (lo usa .githooks/pre-commit)
    python scripts/security/scan_secrets.py --tree            # archivos rastreados de HEAD
    python scripts/security/scan_secrets.py --history         # TODO el historial (lento en repos grandes)

Sale con codigo 1 si encuentra algo que no este en la lista de falsos positivos. Falsos positivos conocidos: valores de placeholder
(CHANGE_ME, example, <...>), variables de CI declaradas "solo-CI", y referencias a variables de entorno.
"""
import argparse
import hashlib
import re
import subprocess
import sys

PATTERNS = {
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "openai_style_key": re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "google_api_key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),
    "credential_assignment": re.compile(
        r"""(?i)\b([A-Z0-9_]*(?:password|passwd|secret|token|api_?key|private_?key)[A-Z0-9_]*)["']?\s*[:=]\s*["']?([A-Za-z0-9/+_.=-]{16,})"""),
}
PLACEHOLDER = re.compile(r"(?i)change|cambi|generar|your|xxx|<|example|replace|placeholder|ci-only|never-use|dummy|test|os\.environ|getenv|config\(|\$\{")
SKIP_PATH = re.compile(r"(?i)(^|/)(node_modules|\.git|staticfiles|.*\.lock|package-lock\.json|.*\.min\.js)(/|$)")
TEST_PATH = re.compile(r"(?i)(^|/)(tests?|__tests__)/|(^|/)test_[^/]*\.py$|(^|/)tests\.py$|\.spec\.")  # secretos FALSOS de prueba (JWT/claves de ejemplo)
SKIP_TEXT_EXT = re.compile(r"(?i)\.(png|jpe?g|gif|webp|ico|pdf|woff2?|ttf|zip|gz|mp4|svg)$")


def sh(*cmd) -> str:
    return subprocess.run(list(cmd), capture_output=True, text=True, encoding="utf-8", errors="ignore").stdout


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:8]


def scan_text(path: str, text: str, where: str = "") -> list[dict]:
    findings = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if len(line) > 2000:
            continue
        for kind, pattern in PATTERNS.items():
            m = pattern.search(line)
            if not m:
                continue
            if TEST_PATH.search(path) and kind in ("jwt", "openai_style_key", "credential_assignment"):
                continue
            value = m.group(2) if kind == "credential_assignment" else m.group(0)
            if kind == "credential_assignment" and PLACEHOLDER.search(value + " " + line):
                continue
            findings.append({"where": where, "path": path, "line": lineno, "type": kind, "fingerprint": fingerprint(value),
                             "length": len(value)})
    return findings


def scan_staged() -> list[dict]:
    out = []
    for path in sh("git", "diff", "--cached", "--name-only", "--diff-filter=ACM").splitlines():
        if SKIP_PATH.search(path) or SKIP_TEXT_EXT.search(path):
            continue
        out.extend(scan_text(path, sh("git", "show", f":{path}"), "staged"))
    return out


def scan_tree() -> list[dict]:
    out = []
    for path in sh("git", "ls-files").splitlines():
        if SKIP_PATH.search(path) or SKIP_TEXT_EXT.search(path):
            continue
        out.extend(scan_text(path, sh("git", "show", f"HEAD:{path}"), "HEAD"))
    return out


def scan_history() -> list[dict]:
    seen, out = set(), []
    for commit in sh("git", "rev-list", "--all").split():
        for path in sh("git", "ls-tree", "-r", "--name-only", commit).splitlines():
            if SKIP_PATH.search(path) or SKIP_TEXT_EXT.search(path):
                continue
            blob = sh("git", "rev-parse", f"{commit}:{path}").strip()
            if blob in seen:
                continue
            seen.add(blob)
            out.extend(scan_text(path, sh("git", "cat-file", "-p", blob), commit[:8]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--staged", action="store_true")
    group.add_argument("--tree", action="store_true")
    group.add_argument("--history", action="store_true")
    args = ap.parse_args()
    findings = scan_staged() if args.staged else scan_tree() if args.tree else scan_history()
    grouped: dict = {}
    for f in findings:
        grouped.setdefault((f["path"], f["type"], f["fingerprint"]), []).append(f)
    for (path, kind, fp), items in sorted(grouped.items()):
        first = items[0]
        print(f"{kind:<22} {path}:{first['line']} (len={first['length']}, huella={fp}, apariciones={len(items)}, ej.commit={first['where']})")
    print(f"\n{len(grouped)} hallazgos unicos.")
    return 1 if grouped else 0


if __name__ == "__main__":
    sys.exit(main())
