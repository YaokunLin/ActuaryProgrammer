# Generated by Django 3.2.13 on 2022-06-01 00:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_user_remove_tokens_while_everything_is_delegated_to_netsapiens'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='auth0_id',
            field=models.CharField(blank=True, max_length=120),
        ),
    ]