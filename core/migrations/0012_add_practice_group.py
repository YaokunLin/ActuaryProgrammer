# Generated by Django 3.2.15 on 2022-08-29 18:46

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import django_userforeignkey.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_alter_user_password'),
    ]

    operations = [
        migrations.CreateModel(
            name='PracticeGroup',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('modified_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('id', django_extensions.db.fields.ShortUUIDField(blank=True, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=150, verbose_name='name')),
                ('created_by', django_userforeignkey.models.fields.UserForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='practicegroup_created', to=settings.AUTH_USER_MODEL, verbose_name='The user that is automatically assigned')),
                ('modified_by', django_userforeignkey.models.fields.UserForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='practicegroup_modified', to=settings.AUTH_USER_MODEL, verbose_name='The user that is automatically assigned')),
            ],
            options={
                'get_latest_by': 'modified_at',
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='practice',
            name='practice_group',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, to='core.practicegroup'),
        ),
    ]