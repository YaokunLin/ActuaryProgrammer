# Generated by Django 3.2.12 on 2022-04-06 21:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('care', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='procedure',
            name='keyword',
        ),
    ]