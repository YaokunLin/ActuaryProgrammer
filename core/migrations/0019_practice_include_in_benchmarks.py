# Generated by Django 3.2.15 on 2022-09-26 16:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_practice_telecom_make_domain_blankable"),
    ]

    operations = [
        migrations.AddField(
            model_name="practice",
            name="include_in_benchmarks",
            field=models.BooleanField(default=False),
        ),
    ]