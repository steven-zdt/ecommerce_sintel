"""Casos parametrizados compartidos por los archivos de este paquete (HARDENING F11)."""
import pytest

from eval import redteam as rt


def attack_params(categories=None, kinds=None):
    """pytest.param(categoria, kind, texto) por cada variante; ids legibles y deterministas."""
    params = []
    for category, attacks in rt.ATTACKS.items():
        if categories and category not in categories:
            continue
        for n, attack in enumerate(attacks):
            for m, v in enumerate(rt.all_variants(attack)):
                if kinds and v.kind not in kinds:
                    continue
                params.append(pytest.param(category, v.kind, v.text, id=f"{category}-{n}-{m}-{v.kind}"))
    return params


def leak_params(items, kinds=None):
    """items = [(texto, marcador)] -> pytest.param(kind, texto_mutado, marcador)."""
    params = []
    for n, (text, marker) in enumerate(items):
        for m, v in enumerate(rt.mutate(text)):
            if kinds and v.kind not in kinds:
                continue
            params.append(pytest.param(v.kind, v.text, marker, id=f"{n}-{m}-{v.kind}"))
    return params


def xfail_if_known(text=None, group=None, kind=None):
    """xfail (no estricto) si la variante tiene un hallazgo conocido: de deteccion (por texto) o de la guardia de salida (grupo, kind)."""
    reason = rt.gap_for(text) if text else rt.KNOWN_GAPS.get((group, kind), "")
    if reason:
        pytest.xfail(reason)
