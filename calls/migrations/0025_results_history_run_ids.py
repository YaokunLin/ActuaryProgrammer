# Generated by Django 3.2.12 on 2022-04-05 23:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ml', '0001_initial'),
        ('calls', '0024_procedure_updates_and_keyword_lookup'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='calllongestpause',
            name='raw_call_pause_model_run_id',
        ),
        migrations.AddField(
            model_name='calloutcome',
            name='call_outcome_model_run',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resulting_call_outcomes', to='ml.mlmodelresulthistory', verbose_name='ml model run for this call outcome'),
        ),
        migrations.AddField(
            model_name='calloutcomereason',
            name='call_outcome_reason_model_run',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resulting_call_outcome_reasons', to='ml.mlmodelresulthistory', verbose_name='ml model run for this call outcome reason'),
        ),
        migrations.AddField(
            model_name='callpurpose',
            name='call_purpose_model_run',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resulting_call_purposes', to='ml.mlmodelresulthistory', verbose_name='ml model run for this call purpose'),
        ),
        migrations.AddField(
            model_name='callsentiment',
            name='call_sentiment_model_run',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resulting_call_sentiments', to='ml.mlmodelresulthistory', verbose_name='ml model run for this call sentiment'),
        ),
        migrations.AddField(
            model_name='calltranscript',
            name='call_transcript_model_run',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resulting_call_transcripts', to='ml.mlmodelresulthistory', verbose_name='ml model run for this call transcript'),
        ),
        migrations.AddField(
            model_name='calltranscriptfragment',
            name='call_transcript_fragment_model_run',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resulting_call_transcript_fragments', to='ml.mlmodelresulthistory', verbose_name='ml model run for this call transcript fragment'),
        ),
        migrations.AddField(
            model_name='calltranscriptfragmentsentiment',
            name='call_transcript_fragment_sentiment_model_run',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resulting_call_transcript_fragment_sentiments', to='ml.mlmodelresulthistory', verbose_name='ml model run for this call transcript fragment sentiment'),
        ),
    ]