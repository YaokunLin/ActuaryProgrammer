# Generated by Django 3.2.12 on 2022-03-30 21:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inbox', '0004_remove_source_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='smsmessage',
            name='message_status',
            field=models.CharField(blank=True, choices=[('bandwidth_message_delivered', 'Bandwidth Message Delivered'), ('bandwidth_message_failed', 'Bandwidth Message Failed'), ('bandwidth_message_received', 'Bandwidth Message Received'), ('bandwidth_message_sending', 'Bandwidth Message Sending'), ('message_sent_to_bandwidth', 'Message Sent To Bandwidth'), ('message_init', 'Message Init')], max_length=255),
        ),
    ]