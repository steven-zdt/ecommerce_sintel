import uuid
import django.db.models.deletion
from django.db import migrations, models


QUESTION_TYPE_CHOICES = [
    ('TEXT', 'Texto'), ('TEXTAREA', 'Texto largo'), ('NUMBER', 'Numero'),
    ('DECIMAL', 'Decimal'), ('CURRENCY', 'Moneda'), ('BOOLEAN', 'Booleano'),
    ('DATE', 'Fecha'), ('TIME', 'Hora'), ('SELECT', 'Select'),
    ('MULTISELECT', 'Multiselect'), ('RADIO', 'Radio'), ('CHECKBOX', 'Checkbox'),
    ('IMAGE', 'Imagen'), ('FILE', 'Archivo'), ('SIGNATURE', 'Firma'),
    ('GPS', 'GPS'), ('ADDRESS', 'Direccion'), ('EMAIL', 'Email'),
    ('PHONE', 'Telefono'), ('NIT', 'NIT'), ('CC', 'Cedula (CC)'),
    ('COLOR', 'Color'), ('SLIDER', 'Deslizador'), ('TABLE', 'Tabla'),
    ('DYNAMIC_LIST', 'Lista dinamica'), ('AUTOCOMPLETE', 'Autocompletar'),
]


class Migration(migrations.Migration):

    dependencies = [
        ('quotes', '0015_rename_equipment_to_module'),
    ]

    operations = [
        migrations.CreateModel(
            name='QuoteTemplateSubcategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('name', models.CharField(max_length=100)),
                ('slug', models.SlugField(max_length=150)),
                ('description', models.TextField(blank=True, default='')),
                ('icon', models.CharField(blank=True, default='', max_length=50)),
                ('display_order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subcategories', to='quotes.quotetemplatecategory')),
            ],
            options={
                'verbose_name': 'Subcategoria de Plantilla de Cotizacion',
                'verbose_name_plural': 'Subcategorias de Plantillas de Cotizacion',
                'ordering': ['display_order', 'name'],
            },
        ),
        migrations.AddConstraint(
            model_name='quotetemplatesubcategory',
            constraint=models.UniqueConstraint(fields=('category', 'slug'), name='unique_subcategory_slug_per_category'),
        ),
        migrations.AddField(
            model_name='quotetemplate',
            name='subcategory',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='templates', to='quotes.quotetemplatesubcategory'),
        ),
        migrations.AddField(
            model_name='quotetemplate',
            name='code',
            field=models.CharField(blank=True, help_text='Codigo corto interno, ej. CCTV-INST-001.', max_length=50, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='quotetemplate',
            name='version',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='quotetemplate',
            name='is_published',
            field=models.BooleanField(default=False, help_text='Visible en /cotizar. Una plantilla no publicada solo se ve en el panel admin.'),
        ),
        migrations.AddField(
            model_name='quotequestion',
            name='description',
            field=models.TextField(blank=True, default='', help_text='Explicacion larga de la pregunta (distinta del texto de ayuda corto).'),
        ),
        migrations.AddField(
            model_name='quotequestion',
            name='is_visible',
            field=models.BooleanField(default=True, help_text='Se muestra al cliente en /cotizar. Desactivar para ocultarla sin borrarla.'),
        ),
        migrations.AddField(
            model_name='quotequestion',
            name='default_value',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='quotequestion',
            name='unit',
            field=models.CharField(blank=True, default='', help_text="Unidad de medida, ej. 'metros', 'm2'.", max_length=50),
        ),
        migrations.AddField(
            model_name='quotequestion',
            name='group',
            field=models.CharField(blank=True, default='', help_text='Etiqueta de agrupacion visual dentro del modulo.', max_length=150),
        ),
        migrations.AddField(
            model_name='quotequestion',
            name='validation_regex',
            field=models.CharField(blank=True, default='', help_text='Patron opcional de validacion (ej. para NIT/CC/Email).', max_length=255),
        ),
        migrations.AddField(
            model_name='quotequestion',
            name='table_columns',
            field=models.JSONField(blank=True, default=list, help_text="Solo para TABLE: lista de nombres de columna, ej. ['Item', 'Cantidad']."),
        ),
        migrations.AlterField(
            model_name='quotequestion',
            name='question_type',
            field=models.CharField(choices=QUESTION_TYPE_CHOICES, default='TEXT', max_length=20),
        ),
    ]
