# Generated by Django 3.2.11 on 2022-01-27 23:05

from django.conf import settings
from django.db import migrations
import django.db.models.deletion
import django_userforeignkey.models.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('netsapiens_integration', '0008_rename_from_calls_sub_to_call_subs_in_all_places'),
    ]

    operations = [
        migrations.RenameField(
            model_name='netsapienscallsubscriptionseventextract',
            old_name='netsapiens_subscription_client',
            new_name='netsapiens_call_subscription',
        ),
        migrations.RenameField(
            model_name='netsapienscdr2extract',
            old_name='netsapiens_subscription_client',
            new_name='netsapiens_call_subscription',
        ),
        migrations.AlterField(
            model_name='netsapienscallsubscriptions',
            name='created_by',
            field=django_userforeignkey.models.fields.UserForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='netsapienscallsubscriptions_created', to=settings.AUTH_USER_MODEL, verbose_name='The user that is automatically assigned'),
        ),
        migrations.AlterField(
            model_name='netsapienscallsubscriptions',
            name='modified_by',
            field=django_userforeignkey.models.fields.UserForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='netsapienscallsubscriptions_modified', to=settings.AUTH_USER_MODEL, verbose_name='The user that is automatically assigned'),
        ),
        migrations.AlterField(
            model_name='netsapienscallsubscriptionseventextract',
            name='created_by',
            field=django_userforeignkey.models.fields.UserForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='netsapienscallsubscriptionseventextract_created', to=settings.AUTH_USER_MODEL, verbose_name='The user that is automatically assigned'),
        ),
        migrations.AlterField(
            model_name='netsapienscallsubscriptionseventextract',
            name='modified_by',
            field=django_userforeignkey.models.fields.UserForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='netsapienscallsubscriptionseventextract_modified', to=settings.AUTH_USER_MODEL, verbose_name='The user that is automatically assigned'),
        ),
    ]