"""
Script de auditoría de queries para core.services.selectors.HomeFeedSelector

Uso:
    python manage.py shell
    > exec(open('core/audit_queries.py').read())

Verifica queries N+1 en cada método de HomeFeedSelector.
"""

from django.test.utils import CaptureQueriesContext
from django.db import connection
from core.services.commands import HomeFeedSelector

print("=" * 80)
print("AUDITORÍA DE QUERIES — HomeFeedSelector")
print("=" * 80)

# Test: get_flash_offers
print("\n[1] HomeFeedSelector.get_flash_offers()")
print("-" * 80)
with CaptureQueriesContext(connection) as ctx:
    offers = list(HomeFeedSelector.get_flash_offers())
    
print(f"Total items: {len(offers)}")
print(f"Queries ejecutadas: {len(ctx)}")
print(f"Queries/item ratio: {len(ctx) / max(len(offers), 1):.2f}")

if len(ctx) > 5:
    print("⚠️  ALERTA: Muchas queries, posible N+1")
    for i, q in enumerate(ctx[:5], 1):
        print(f"\nQuery {i}:")
        print(q['sql'][:150])
else:
    print("✅ OK: Queries en rango aceptable")

# Test: get_featured_products
print("\n\n[2] HomeFeedSelector.get_featured_products()")
print("-" * 80)
with CaptureQueriesContext(connection) as ctx:
    products = list(HomeFeedSelector.get_featured_products())
    
print(f"Total items: {len(products)}")
print(f"Queries ejecutadas: {len(ctx)}")
print(f"Queries/item ratio: {len(ctx) / max(len(products), 1):.2f}")

if len(ctx) > 5:
    print("⚠️  ALERTA: Muchas queries, posible N+1")
    for i, q in enumerate(ctx[:5], 1):
        print(f"\nQuery {i}:")
        print(q['sql'][:150])
else:
    print("✅ OK: Queries en rango aceptable")

# Test: get_featured_equipment
print("\n\n[3] HomeFeedSelector.get_featured_equipment()")
print("-" * 80)
with CaptureQueriesContext(connection) as ctx:
    equipment = list(HomeFeedSelector.get_featured_equipment())
    
print(f"Total items: {len(equipment)}")
print(f"Queries ejecutadas: {len(ctx)}")
print(f"Queries/item ratio: {len(ctx) / max(len(equipment), 1):.2f}")

if len(ctx) > 5:
    print("⚠️  ALERTA: Muchas queries, posible N+1")
    for i, q in enumerate(ctx[:5], 1):
        print(f"\nQuery {i}:")
        print(q['sql'][:150])
else:
    print("✅ OK: Queries en rango aceptable")

# Test: get_featured_services
print("\n\n[4] HomeFeedSelector.get_featured_services()")
print("-" * 80)
with CaptureQueriesContext(connection) as ctx:
    services = list(HomeFeedSelector.get_featured_services())
    
print(f"Total items: {len(services)}")
print(f"Queries ejecutadas: {len(ctx)}")
print(f"Queries/item ratio: {len(ctx) / max(len(services), 1):.2f}")

if len(ctx) > 5:
    print("⚠️  ALERTA: Muchas queries, posible N+1")
    for i, q in enumerate(ctx[:5], 1):
        print(f"\nQuery {i}:")
        print(q['sql'][:150])
else:
    print("✅ OK: Queries en rango aceptable")

# Test: get_module_configs
print("\n\n[5] HomeFeedSelector.get_module_configs()")
print("-" * 80)
with CaptureQueriesContext(connection) as ctx:
    modules = HomeFeedSelector.get_module_configs()
    
print(f"Total items: {len(modules)}")
print(f"Queries ejecutadas: {len(ctx)}")

if len(ctx) > 3:
    print("⚠️  ALERTA: Más de 3 queries para módulos")
    for i, q in enumerate(ctx, 1):
        print(f"\nQuery {i}:")
        print(q['sql'][:150])
else:
    print("✅ OK: Queries óptimas")

# Test: build_home_feed (completo)
print("\n\n[INTEGRACIÓN] HomeFeedSelector.build_home_feed()")
print("-" * 80)
with CaptureQueriesContext(connection) as ctx:
    feed = HomeFeedSelector.build_home_feed()
    
print(f"Queries totales para home-feed: {len(ctx)}")
print(f"Objetivo: < 15 queries")

if len(ctx) < 15:
    print(f"✅ OK: {len(ctx)} queries")
else:
    print(f"⚠️  ALERTA: {len(ctx)} queries (objetivo: < 15)")
    print("\nPrimeras 10 queries:")
    for i, q in enumerate(ctx[:10], 1):
        print(f"\n{i}. {q['sql'][:120]}...")

print("\n" + "=" * 80)
print("FIN AUDITORÍA")
print("=" * 80)
