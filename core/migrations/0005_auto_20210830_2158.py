# Generated by Django 3.2.6 on 2021-08-30 21:58

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("core", "0004_auto_20201211_0432"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="sms_number",
        ),
        migrations.CreateModel(
            name="GroupTelecom",
            fields=[
                ("id", django_extensions.db.fields.ShortUUIDField(blank=True, editable=False, primary_key=True, serialize=False)),
                ("sms_number", phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, region=None)),
                ("group", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to="auth.group")),
            ],
        ),
    ]