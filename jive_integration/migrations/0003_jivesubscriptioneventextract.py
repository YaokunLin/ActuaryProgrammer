# Generated by Django 3.2.15 on 2022-10-05 00:52

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import django_userforeignkey.models.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('jive_integration', '0002_auto_20220926_1516'),
    ]

    operations = [
        migrations.CreateModel(
            name='JiveSubscriptionEventExtract',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('modified_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('id', django_extensions.db.fields.ShortUUIDField(blank=True, editable=False, primary_key=True, serialize=False)),
                ('peerlogic_call_id', models.CharField(blank=True, db_index=True, default='', max_length=22)),
                ('peerlogic_call_partial_id', models.CharField(blank=True, db_index=True, default='', max_length=22)),
                ('jive_extract', models.JSONField()),
                ('jive_type', models.CharField(db_index=True, max_length=128)),
                ('sub_id', models.CharField(db_index=True, max_length=36)),
                ('old_id', models.CharField(db_index=True, max_length=36)),
                ('new_id', models.CharField(db_index=True, max_length=36)),
                ('entity_id', models.CharField(db_index=True, max_length=128)),
                ('data_leg_id', models.CharField(db_index=True, max_length=36)),
                ('data_created', models.DateTimeField()),
                ('data_participant', models.CharField(max_length=128)),
                ('data_callee_name', models.CharField(max_length=128)),
                ('data_callee_number', models.CharField(max_length=128)),
                ('data_caller_name', models.CharField(max_length=128)),
                ('data_caller_number', models.CharField(max_length=128)),
                ('data_direction', models.CharField(max_length=128)),
                ('data_state', models.CharField(max_length=128)),
                ('data_ani', models.CharField(max_length=128)),
                ('data_recordings_extract', models.JSONField()),
                ('data_is_click_to_call', models.BooleanField()),
                ('data_originator_id', models.CharField(max_length=36)),
                ('data_originator_organization_id', models.CharField(max_length=36)),
                ('created_by', django_userforeignkey.models.fields.UserForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='jivesubscriptioneventextract_created', to=settings.AUTH_USER_MODEL, verbose_name='The user that is automatically assigned')),
                ('modified_by', django_userforeignkey.models.fields.UserForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='jivesubscriptioneventextract_modified', to=settings.AUTH_USER_MODEL, verbose_name='The user that is automatically assigned')),
            ],
            options={
                'get_latest_by': 'modified_at',
                'abstract': False,
            },
        ),
    ]