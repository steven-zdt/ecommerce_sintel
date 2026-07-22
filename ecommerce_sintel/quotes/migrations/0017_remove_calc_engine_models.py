from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('quotes', '0016_subcategory_and_question_fields'),
    ]

    operations = [
        migrations.DeleteModel(name='QuoteRuleAction'),
        migrations.DeleteModel(name='QuoteRuleCondition'),
        migrations.DeleteModel(name='QuoteRule'),
        migrations.DeleteModel(name='QuoteTemplateMaterial'),
    ]
