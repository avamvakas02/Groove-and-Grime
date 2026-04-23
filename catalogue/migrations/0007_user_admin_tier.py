from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0006_wishlistitem'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='tier',
            field=models.CharField(
                choices=[
                    ('VISITOR', 'Visitor'),
                    ('PRO', 'Pro'),
                    ('PRO_PLUS', 'Pro+'),
                    ('MANAGER', 'Manager'),
                    ('ADMIN', 'Admin'),
                ],
                default='VISITOR',
                help_text='Determines user access level and exclusive discounts.',
                max_length=10,
            ),
        ),
    ]
