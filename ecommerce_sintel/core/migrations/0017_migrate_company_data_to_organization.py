from django.db import migrations


def copy_data_forward(apps, schema_editor):
    """
    Copia el registro activo de SiteBrandConfig/CompanyContactInfo y las filas
    de FooterLink(category='social') hacia organization. Las filas sociales de
    FooterLink se eliminan aqui (ya migradas); SiteBrandConfig/CompanyContactInfo
    se eliminan como modelos completos en la siguiente migracion.
    """
    SiteBrandConfig = apps.get_model('core', 'SiteBrandConfig')
    CompanyContactInfo = apps.get_model('core', 'CompanyContactInfo')
    FooterLink = apps.get_model('core', 'FooterLink')

    Company = apps.get_model('organization', 'Company')
    Branding = apps.get_model('organization', 'Branding')
    ContactInfo = apps.get_model('organization', 'ContactInfo')
    SocialLink = apps.get_model('organization', 'SocialLink')

    brand = SiteBrandConfig.objects.filter(is_active=True, is_deleted=False).first()
    if brand:
        Company.objects.create(trade_name=brand.site_name, is_active=True)
        Branding.objects.create(logo=brand.logo, tagline=brand.tagline, is_active=True)

    contact = CompanyContactInfo.objects.filter(is_active=True, is_deleted=False).first()
    if contact:
        ContactInfo.objects.create(
            phone=contact.phone,
            email=contact.email,
            address=contact.address,
            working_hours=contact.working_hours,
            is_active=True,
        )

    social_links = FooterLink.objects.filter(category='social', is_deleted=False)
    for link in social_links:
        SocialLink.objects.create(
            platform=link.title,
            url=link.url,
            icon_class=link.icon_class,
            display_order=link.display_order,
            is_active=link.is_active,
        )
    social_links.delete()


def copy_data_backward(apps, schema_editor):
    """
    No-op deliberado: revertir esta migracion no reconstruye el estado de core.
    Los modelos SiteBrandConfig/CompanyContactInfo se eliminan por completo en
    la migracion siguiente (0018) -- para un rollback real hay que restaurar
    desde backup de BD, no desde esta migracion.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_alter_companycontactinfo_address_and_more'),
        ('organization', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(copy_data_forward, copy_data_backward),
    ]
