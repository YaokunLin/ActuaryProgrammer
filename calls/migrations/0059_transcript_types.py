# Generated by Django 3.2.15 on 2022-10-20 18:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calls', '0058_unique_sentiment_per_call'),
    ]

    operations = [
        migrations.AlterField(
            model_name='callpartial',
            name='time_interaction_started',
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name='calltranscript',
            name='transcript_type',
            field=models.CharField(choices=[('full_text', 'Full Text'), ('channel_1_text', 'Channel 1 Text'), ('channel_2_text', 'Channel 2 Text'), ('speaker_1_text', 'Speaker 1 Text'), ('speaker_2_text', 'Speaker 2 Text')], default='full_text', max_length=80),
        ),
        migrations.AlterField(
            model_name='calltranscriptpartial',
            name='transcript_type',
            field=models.CharField(choices=[('full_text', 'Full Text'), ('channel_1_text', 'Channel 1 Text'), ('channel_2_text', 'Channel 2 Text'), ('speaker_1_text', 'Speaker 1 Text'), ('speaker_2_text', 'Speaker 2 Text')], default='full_text', max_length=80),
        ),
    ]