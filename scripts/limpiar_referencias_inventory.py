"""
limpiar_referencias_inventory.py

Elimina todas las referencias directas a la app `inventory` desde otras apps.
La app inventory ya gestiona su propio estado — otras apps deben comunicarse
con ella a traves de sus endpoints REST (/api/v1/inventory/) o signals, no
mediante imports directos de sus modelos y servicios.

REFERENCIAS DETECTADAS (22 lineas en 13 archivos):
  cart/services/commands.py
  cart/tests.py
  dashboard/api/serializers.py
  dashboard/services/admin_orchestrators.py
  dashboard/tests.py
  orders/services/commands.py
  payment/online/services/commands.py
  payment/shared/commands.py
  shop/api/serializers.py          (2 ocurrencias, inline en metodo)
  shop/management/commands/seed_product_sale_flow.py
  shop/services/selectors.py
  shop/services/summary.py
  technical_services/tests.py

Uso:
  # Ver que cambiaria sin tocar nada (default)
  python scripts/limpiar_referencias_inventory.py --dry-run

  # Aplicar cambios (crea .bak de cada archivo modificado)
  python scripts/limpiar_referencias_inventory.py --apply

  # Aplicar sin backup
  python scripts/limpiar_referencias_inventory.py --apply --no-backup

  # Solo listar archivos afectados
  python scripts/limpiar_referencias_inventory.py --list
"""

import argparse
import re
import shutil
import sys
from pathlib import Path


# ─── Raiz del proyecto Django ─────────────────────────────────────────────────

DJANGO_ROOT = Path(__file__).resolve().parent.parent / "ecommerce_sintel"

# ─── Patron para detectar cualquier referencia a inventory ───────────────────

# Captura lineas que contienen un import de inventory:
#   from inventory.X import Y
#   from inventory.X import (Y, Z)       <- una linea
#   from inventory.X import (            <- apertura multilinea (se detecta por presencia)
#   import inventory.X
# Tanto al nivel de modulo como inline (dentro de funciones con indentacion)
INVENTORY_IMPORT_RE = re.compile(
    r"^(?P<indent>\s*)"
    r"(?P<stmt>"
    r"(?:from\s+inventory(?:\.\w+)*\s+import\s+.*)"
    r"|(?:import\s+inventory(?:\.\w+)*)"
    r")",
    re.MULTILINE,
)

# Marcador que dejamos en lugar de cada import eliminado
MARKER = "# INVENTORY_REMOVED: {original}  # -> usar /api/v1/inventory/ o signal"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _plural(n, word):
    return f"{n} {word}{'s' if n != 1 else ''}"


def find_inventory_refs(django_root: Path) -> dict[Path, list[dict]]:
    """
    Escanea todos los .py fuera de inventory/ y devuelve un dict:
      { archivo: [ {lineno, original, indent}, ... ] }
    """
    hits: dict[Path, list[dict]] = {}

    for py_file in sorted(django_root.rglob("*.py")):
        # Excluir la propia app de inventario y migraciones
        rel = py_file.relative_to(django_root)
        parts = rel.parts
        if parts[0] == "inventory":
            continue
        if "migrations" in parts:
            continue
        if "__pycache__" in parts:
            continue

        text = py_file.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        file_hits = []

        for i, line in enumerate(lines, start=1):
            m = INVENTORY_IMPORT_RE.match(line)
            if m:
                file_hits.append({
                    "lineno":   i,
                    "original": line,
                    "indent":   m.group("indent"),
                    "stmt":     m.group("stmt").strip(),
                })

        if file_hits:
            hits[py_file] = file_hits

    return hits


def apply_removals(
    py_file: Path,
    file_hits: list[dict],
    backup: bool = True,
    dry_run: bool = False,
) -> int:
    """
    Comenta las lineas de import de inventory en py_file.
    Retorna el numero de lineas modificadas.
    """
    text = py_file.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines(keepends=True)

    changed = 0
    for hit in file_hits:
        idx = hit["lineno"] - 1          # 0-based
        original = hit["original"]
        indent = hit["indent"]
        stmt = hit["stmt"]

        # Construir la linea de reemplazo: comentario con marcador
        replacement = (
            f"{indent}# INVENTORY_REMOVED: {stmt}"
            f"  # -> usar /api/v1/inventory/ o signal\n"
        )

        # Manejar imports multilinea con parentesis
        # Si la linea abre un parentesis sin cerrarlo, consumir hasta el cierre
        end_idx = idx
        if "(" in lines[idx] and ")" not in lines[idx]:
            while end_idx < len(lines) - 1 and ")" not in lines[end_idx]:
                end_idx += 1
            # Comentar todas las lineas del bloque multilinea
            block_lines = lines[idx : end_idx + 1]
            commented = [
                f"{indent}# INVENTORY_REMOVED (parte {i+1}): {l.rstrip()}\n"
                for i, l in enumerate(block_lines)
            ]
            if not dry_run:
                lines[idx : end_idx + 1] = commented
            changed += (end_idx - idx + 1)
        else:
            if not dry_run:
                lines[idx] = replacement
            changed += 1

    if not dry_run and changed > 0:
        if backup:
            shutil.copy2(py_file, py_file.with_suffix(".py.bak"))
        py_file.write_text("".join(lines), encoding="utf-8")

    return changed


# ─── Modos de operacion ───────────────────────────────────────────────────────

def cmd_list(hits: dict):
    print(f"\n{'='*60}")
    print(f"  REFERENCIAS A inventory DETECTADAS EN OTRAS APPS")
    print(f"{'='*60}\n")
    total = 0
    for path, file_hits in hits.items():
        rel = path.relative_to(DJANGO_ROOT)
        print(f"  {rel}  ({_plural(len(file_hits), 'linea')})")
        for h in file_hits:
            print(f"    L{h['lineno']:>4}  {h['stmt']}")
        total += len(file_hits)
        print()
    print(f"  Total: {_plural(total, 'referencia')} en {_plural(len(hits), 'archivo')}\n")


def cmd_dry_run(hits: dict):
    print(f"\n{'='*60}")
    print(f"  DRY-RUN — cambios que se aplicarian (ninguno se guarda)")
    print(f"{'='*60}\n")
    total_lines = 0
    for path, file_hits in hits.items():
        rel = path.relative_to(DJANGO_ROOT)
        print(f"  [{rel}]")
        for h in file_hits:
            print(f"    - L{h['lineno']:>4}  ELIMINAR: {h['stmt']}")
            print(f"           -> # INVENTORY_REMOVED: {h['stmt']}  # -> /api/v1/inventory/")
        total_lines += len(file_hits)
        print()
    print(f"  Resumen: {_plural(total_lines, 'linea')} comentadas en {_plural(len(hits), 'archivo')}")
    print(f"\n  Para aplicar: python scripts/limpiar_referencias_inventory.py --apply\n")


def cmd_apply(hits: dict, backup: bool):
    print(f"\n{'='*60}")
    print(f"  APLICANDO ELIMINACION DE REFERENCIAS A inventory")
    print(f"{'='*60}\n")

    total_lines = 0
    files_changed = 0

    for path, file_hits in hits.items():
        rel = path.relative_to(DJANGO_ROOT)
        n = apply_removals(path, file_hits, backup=backup, dry_run=False)
        total_lines += n
        files_changed += 1
        bak = " (backup: .py.bak)" if backup else ""
        print(f"  [OK]  {rel}{bak}  — {_plural(n, 'linea')} comentada")

    print(f"\n  Resumen: {_plural(total_lines, 'linea')} comentadas en {_plural(files_changed, 'archivo')}")

    if backup:
        print(f"\n  Backups creados como <archivo>.py.bak — para revertir:")
        print(f"    python scripts/limpiar_referencias_inventory.py --revert")

    print(f"\n  SIGUIENTE PASO:")
    print(f"  Los symbols eliminados (InventorySelector, StockRecord, etc.) aun")
    print(f"  aparecen en el codigo. Busca los marcadores con:")
    print(f"    grep -rn 'INVENTORY_REMOVED' ecommerce_sintel/ --include='*.py'")
    print(f"  Y tambien los usages que quedaron sin importar:")
    print(f"    grep -rn 'InventorySelector\\|InventoryCommands\\|StockRecord\\|StockAdjustmentDTO' \\")
    print(f"      ecommerce_sintel/ --include='*.py' | grep -v '^ecommerce_sintel/inventory/'")
    print()


def cmd_revert(django_root: Path):
    print(f"\n{'='*60}")
    print(f"  REVERTIR — restaurar .py.bak")
    print(f"{'='*60}\n")
    reverted = 0
    for bak in sorted(django_root.rglob("*.py.bak")):
        original = bak.with_suffix("")  # quita .bak
        shutil.copy2(bak, original)
        bak.unlink()
        print(f"  [OK]  {original.relative_to(django_root)}")
        reverted += 1
    if reverted == 0:
        print(f"  No se encontraron archivos .py.bak para revertir.")
    else:
        print(f"\n  {_plural(reverted, 'archivo')} revertido.")
    print()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Elimina imports directos de la app inventory en otras apps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--dry-run", action="store_true", default=True,
        help="(default) Mostrar cambios sin aplicar",
    )
    group.add_argument(
        "--apply", action="store_true",
        help="Aplicar cambios (comenta las lineas de import)",
    )
    group.add_argument(
        "--list", action="store_true",
        help="Solo listar archivos y lineas afectadas",
    )
    group.add_argument(
        "--revert", action="store_true",
        help="Restaurar archivos desde .py.bak (deshace --apply)",
    )
    parser.add_argument(
        "--no-backup", action="store_true",
        help="Con --apply: no crear archivos .py.bak",
    )
    parser.add_argument(
        "--root", default=str(DJANGO_ROOT),
        help=f"Raiz del proyecto Django (default: {DJANGO_ROOT})",
    )
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"[ERROR] Directorio no encontrado: {root}")
        sys.exit(1)

    if args.revert:
        cmd_revert(root)
        return

    hits = find_inventory_refs(root)
    if not hits:
        print("\n  No se encontraron referencias a inventory en otras apps. Nada que hacer.\n")
        return

    if args.list:
        cmd_list(hits)
    elif args.apply:
        cmd_apply(hits, backup=not args.no_backup)
    else:
        # dry-run (default)
        cmd_dry_run(hits)


if __name__ == "__main__":
    main()
