# Generated by Django 5.0.6 on 2024-11-12 11:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pushNotification', '0002_fcmtoken_timezone'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fcmtoken',
            name='timezone',
            field=models.CharField(default='America/Los_Angeles', max_length=250),
        ),
    ]