"""Guard global de la suite de tests (C-04 de la auditoria).

Fuerza que los tests corran contra PostgreSQL, no SQLite. SQLite no aplica
bloqueo de fila real para select_for_update(), asi que los tests de
concurrencia (Orders::create_from_cart, Cart, Renting::confirm_payment)
pasarian por la razon equivocada -- no porque el lock funcione, sino porque
SQLite serializa de otra forma. Sin este guard, `pytest` sin DB_HOST cae a
SQLite silenciosamente y esos tests dejan de probar lo que dicen probar.
"""
from django.conf import settings


def pytest_configure(config):
    engine = settings.DATABASES.get('default', {}).get('ENGINE', '')
    if 'postgresql' not in engine:
        import pytest
        pytest.exit(
            "Los tests deben correr contra PostgreSQL, no '%s'. "
            "Define DB_HOST (p.ej. dentro del contenedor Docker) antes de pytest." % engine,
            returncode=1,
        )
