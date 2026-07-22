from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quotes', '0014_quotequestion_allow_other'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='quotequestion',
            name='unique_question_key_per_equipment',
        ),
        migrations.RenameModel(
            old_name='QuoteTemplateEquipment',
            new_name='QuoteTemplateModule',
        ),
        migrations.RenameField(
            model_name='quotequestion',
            old_name='equipment',
            new_name='module',
        ),
        migrations.AlterField(
            model_name='quotequestion',
            name='module',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='questions', to='quotes.quotetemplatemodule'),
        ),
        migrations.AddConstraint(
            model_name='quotequestion',
            constraint=models.UniqueConstraint(fields=('module', 'key'), name='unique_question_key_per_module'),
        ),
        migrations.AddField(
            model_name='quotetemplatemodule',
            name='module_type',
            field=models.CharField(
                choices=[('EQUIPMENT', 'Equipos'), ('MATERIALS', 'Materiales'), ('LABOR', 'Mano de Obra')],
                default='EQUIPMENT', max_length=20,
            ),
        ),
        migrations.AlterModelOptions(
            name='quotetemplatemodule',
            options={
                'ordering': ['module_type', 'display_order', 'id'],
                'verbose_name': 'Modulo de Plantilla',
                'verbose_name_plural': 'Modulos de Plantilla',
            },
        ),
        migrations.AlterField(
            model_name='quotequestion',
            name='key',
            field=models.SlugField(db_index=True, help_text='Identificador unico de la pregunta dentro de su modulo.', max_length=100),
        ),
    ]
