from django.db import migrations


def seed_renting_home_cards(apps, schema_editor):
    HomeCard = apps.get_model('core', 'HomeCard')
    HomeCardGroup = apps.get_model('core', 'HomeCardGroup')

    groups = [
        {
            'name': 'renting_home_solutions',
            'title': 'Soluciones premium de renting',
            'subtitle': 'Cards superiores del marketplace de alquiler.',
            'display_order': 210,
            'columns': 4,
        },
        {
            'name': 'renting_home_use_cases',
            'title': 'Renta tecnologia lista para operar en campo',
            'subtitle': 'Aplicaciones recomendadas',
            'display_order': 220,
            'columns': 6,
        },
        {
            'name': 'renting_home_availability',
            'title': 'Reserva por dias u horas con verificacion automatica',
            'subtitle': 'Disponibilidad inteligente',
            'display_order': 230,
            'columns': 2,
        },
        {
            'name': 'renting_home_process',
            'title': 'Del equipo a la solucion instalada',
            'subtitle': 'Proceso',
            'display_order': 240,
            'columns': 4,
        },
        {
            'name': 'renting_home_brands',
            'title': 'Marcas y ecosistemas compatibles',
            'subtitle': 'Compatibilidad',
            'display_order': 250,
            'columns': 6,
        },
    ]

    for group in groups:
        HomeCardGroup.objects.get_or_create(
            name=group['name'],
            defaults={
                'title': group['title'],
                'subtitle': group['subtitle'],
                'display_order': group['display_order'],
                'is_visible': True,
                'layout_type': 'grid',
                'columns': group['columns'],
            },
        )

    cards = [
        ('renting_home_solutions', 'Seguridad temporal', 'CCTV, control perimetral y monitoreo para eventos, obras y sedes temporales.', 'bi-camera-video', '#0369a1', 1),
        ('renting_home_solutions', 'Conectividad por proyecto', 'Redes, WiFi, switching y enlaces listos para operar durante el periodo contratado.', 'bi-router', '#2563eb', 2),
        ('renting_home_solutions', 'Infraestructura TI', 'Racks, energia, respaldo, computo y equipos empresariales con soporte tecnico.', 'bi-hdd-rack', '#4f46e5', 3),
        ('renting_home_solutions', 'Solucion con operador', 'Equipo, transporte, instalacion, configuracion, capacitacion y operador especializado.', 'bi-person-workspace', '#0f766e', 4),
        ('renting_home_use_cases', 'Eventos', '', 'bi-music-note-beamed', '#3730a3', 1),
        ('renting_home_use_cases', 'Construccion', '', 'bi-cone-striped', '#3730a3', 2),
        ('renting_home_use_cases', 'Hospitales', '', 'bi-hospital', '#3730a3', 3),
        ('renting_home_use_cases', 'Centros comerciales', '', 'bi-shop-window', '#3730a3', 4),
        ('renting_home_use_cases', 'Empresas', '', 'bi-buildings', '#3730a3', 5),
        ('renting_home_use_cases', 'Condominios', '', 'bi-house-gear', '#3730a3', 6),
        ('renting_home_availability', 'Modalidad', 'Horas o dias', 'bi-clock-history', '#0369a1', 1),
        ('renting_home_availability', 'Siguiente fecha', 'Motor de disponibilidad', 'bi-calendar-check', '#0369a1', 2),
        ('renting_home_availability', 'Logistica', 'Entrega y recogida', 'bi-truck', '#0369a1', 3),
        ('renting_home_availability', 'Paquetes', 'Solo equipo a premium', 'bi-box-seam', '#0369a1', 4),
        ('renting_home_process', 'Seleccionar', '', 'bi-check2-square', '#166534', 1),
        ('renting_home_process', 'Reservar', '', 'bi-calendar2-check', '#166534', 2),
        ('renting_home_process', 'Pagar', '', 'bi-credit-card', '#166534', 3),
        ('renting_home_process', 'Entregar', '', 'bi-truck', '#166534', 4),
        ('renting_home_process', 'Instalar', '', 'bi-tools', '#166534', 5),
        ('renting_home_process', 'Usar', '', 'bi-play-circle', '#166534', 6),
        ('renting_home_process', 'Recoger', '', 'bi-arrow-return-left', '#166534', 7),
        ('renting_home_process', 'Cerrar', '', 'bi-clipboard-check', '#166534', 8),
        ('renting_home_brands', 'Hikvision', '', 'bi-hdd-network', '#475569', 1),
        ('renting_home_brands', 'Dahua', '', 'bi-hdd-network', '#475569', 2),
        ('renting_home_brands', 'Ubiquiti', '', 'bi-router', '#475569', 3),
        ('renting_home_brands', 'Cisco', '', 'bi-diagram-3', '#475569', 4),
        ('renting_home_brands', 'Dell', '', 'bi-pc-display', '#475569', 5),
        ('renting_home_brands', 'APC', '', 'bi-lightning-charge', '#475569', 6),
    ]

    for group_name, title, description, icon_class, color, order in cards:
        HomeCard.objects.get_or_create(
            group_name=group_name,
            title=title,
            defaults={
                'description': description,
                'icon_class': icon_class,
                'background_color': color,
                'display_order': order,
                'is_active': True,
                'card_type': 'premium' if group_name == 'renting_home_solutions' else 'compact',
            },
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0018_delete_companycontactinfo_delete_sitebrandconfig'),
    ]

    operations = [
        migrations.RunPython(seed_renting_home_cards, noop_reverse),
    ]
