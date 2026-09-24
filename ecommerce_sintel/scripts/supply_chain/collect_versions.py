"""
HARDENING F16/C1 -- inventario y verificacion de versiones (imagenes Docker, Ollama y modelos, paquetes Python).

LO EJECUTA EL USUARIO A MANO (regla del proyecto: el asistente no ejecuta pruebas ni escaneos). Solo biblioteca estandar. Solo LECTURA:
`docker image inspect`, la API de Ollama (/api/version, /api/tags) y, opcionalmente, `docker run --rm --entrypoint pip <imagen> freeze`
(crea un contenedor efimero desde la IMAGEN; nunca hace `exec` en contenedores de produccion).

    python scripts/supply_chain/collect_versions.py --ollama http://localhost:11434 --out scripts/supply_chain/_out/manifest.json
    python scripts/supply_chain/collect_versions.py --pip-images ecommerce_sintel_ai_adk:prod --out ...      # + paquetes Python
    python scripts/supply_chain/collect_versions.py --verify ecommerce_sintel/docs/supply_chain/manifest.json   # exit 1 si hay deriva

Que reporta y como se interpreta:
  - images: cada `image:` de docker-compose(.prod).yml con su digest local (RepoDigests/Id) y una advertencia si el tag es flotante
    (`latest`, sin version) o no esta fijado por digest (`@sha256:`).
  - ollama: version del servidor y, por modelo, el DIGEST completo (un `ollama pull` puede cambiar lo que hay detras de un tag).
  - packages: `pip freeze` de las imagenes indicadas.
Para fijar de verdad (plan sec. 20): `image: nombre:tag@sha256:<digest>` en compose; el modelo de produccion se documenta por digest y se
verifica con --verify tras cada `ollama pull`.
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILES = ["docker-compose.yml", "docker-compose.prod.yml"]
FLOATING_TAGS = {"latest", "stable", "main", "master", "lts"}


def sh(*cmd, timeout=120) -> str:
    try:
        return subprocess.run(list(cmd), capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="ignore").stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def compose_images() -> dict:
    found: dict = {}
    for name in COMPOSE_FILES:
        path = ROOT / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            m = re.match(r"^\s+image:\s*([^\s#]+)", line)
            if m:
                found.setdefault(m.group(1), []).append(name)
    return found


def analyze_image(ref: str, files: list[str]) -> dict:
    tag = ref.split(":")[-1] if ":" in ref.split("/")[-1] else ""
    pinned_digest = "@sha256:" in ref
    warnings = []
    if not tag and not pinned_digest:
        warnings.append("sin tag (equivale a latest)")
    if tag in FLOATING_TAGS:
        warnings.append(f"tag flotante ({tag})")
    if not pinned_digest:
        warnings.append("no fijada por digest (@sha256)")
    info = json.loads(sh("docker", "image", "inspect", ref) or "[]")
    local = info[0] if info else {}
    return {"files": sorted(set(files)), "tag": tag or None, "pinned_by_digest": pinned_digest, "warnings": warnings,
            "local_id": local.get("Id"), "repo_digests": local.get("RepoDigests", []), "present_locally": bool(local)}


def ollama_info(base: str) -> dict:
    out: dict = {"base_url": base, "version": None, "models": {}}
    try:
        with urllib.request.urlopen(base.rstrip("/") + "/api/version", timeout=10) as resp:
            out["version"] = json.loads(resp.read().decode()).get("version")
        with urllib.request.urlopen(base.rstrip("/") + "/api/tags", timeout=10) as resp:
            for m in json.loads(resp.read().decode()).get("models", []):
                out["models"][m["name"]] = {"digest": m.get("digest"), "size": m.get("size"), "modified_at": m.get("modified_at")}
    except Exception as exc:  # noqa: BLE001
        out["error"] = type(exc).__name__
    return out


def pip_freeze(image: str) -> dict:
    text = sh("docker", "run", "--rm", "--entrypoint", "pip", image, "freeze", timeout=180)
    return {line.split("==")[0].lower(): line.split("==")[1] for line in text.splitlines() if "==" in line}


def build_manifest(args) -> dict:
    manifest = {"images": {ref: analyze_image(ref, files) for ref, files in sorted(compose_images().items())}}
    if args.ollama:
        manifest["ollama"] = ollama_info(args.ollama)
    if args.pip_images:
        manifest["packages"] = {img: pip_freeze(img) for img in args.pip_images}
    return manifest


def verify(expected: dict, current: dict) -> list[str]:
    problems = []
    for ref, exp in expected.get("images", {}).items():
        cur = current.get("images", {}).get(ref)
        if cur is None:
            problems.append(f"imagen {ref}: ya no aparece en los compose")
        elif exp.get("local_id") and cur.get("local_id") and exp["local_id"] != cur["local_id"]:
            problems.append(f"imagen {ref}: cambio el id local ({exp['local_id'][:19]} -> {cur['local_id'][:19]})")
    exp_o, cur_o = expected.get("ollama"), current.get("ollama")
    if exp_o and cur_o:
        if exp_o.get("version") != cur_o.get("version"):
            problems.append(f"ollama: version {exp_o.get('version')} -> {cur_o.get('version')}")
        for name, meta in exp_o.get("models", {}).items():
            cur_meta = cur_o.get("models", {}).get(name)
            if cur_meta is None:
                problems.append(f"modelo {name}: ya no esta instalado")
            elif meta.get("digest") != cur_meta.get("digest"):
                problems.append(f"modelo {name}: el digest cambio (un pull actualizo el contenido del tag)")
    for image, pkgs in expected.get("packages", {}).items():
        cur_pkgs = current.get("packages", {}).get(image)
        if cur_pkgs is None:
            continue
        for name, version in pkgs.items():
            if cur_pkgs.get(name) != version:
                problems.append(f"paquete {name} en {image}: {version} -> {cur_pkgs.get(name)}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ollama", default="", help="URL de Ollama, p. ej. http://localhost:11434")
    ap.add_argument("--pip-images", nargs="*", default=[], help="imagenes de las que sacar `pip freeze`")
    ap.add_argument("--out", default="")
    ap.add_argument("--verify", default="", help="manifest de referencia: sale con 1 si hay deriva")
    args = ap.parse_args()
    manifest = build_manifest(args)
    text = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    if args.verify:
        problems = verify(json.loads(Path(args.verify).read_text(encoding="utf-8")), manifest)
        for p in problems:
            print("DERIVA:", p)
        print("verificacion:", "FALLA" if problems else "OK")
        return 1 if problems else 0
    for ref, info in manifest["images"].items():
        print(f"{ref:<48} {'OK ' if not info['warnings'] else '!! '}{'; '.join(info['warnings'])}")
    if "ollama" in manifest:
        print("ollama", manifest["ollama"].get("version"), {k: (v['digest'] or '')[:12] for k, v in manifest["ollama"]["models"].items()})
    if not args.out:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
