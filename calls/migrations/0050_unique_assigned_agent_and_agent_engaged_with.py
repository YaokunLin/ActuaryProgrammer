# Generated by Django 3.2.15 on 2022-09-23 00:09
import logging

import django.db.models.deletion
from django.db import migrations, models

# Get an instance of a logger
log = logging.getLogger(__name__)


def deduplicate_agentengagedwith(apps, schema_editor):
    """
    We can't import the model directly as it may be a newer version than this migration expects. We use the historical version.
    """
    Call = apps.get_model("calls", "Call")
    calls = Call.objects.iterator()

    aews_removed = []
    for call in calls:
        if not hasattr(call, "engaged_in_calls"):
            log.info(f"Ignoring call that has no engaged_in_calls: {call.id}")
            continue

        aews = [aew for aew in call.engaged_in_calls.order_by("-modified_at")]
        aews_to_remove = aews[1:]  # take all older ones
        for aew in aews_to_remove:
            aew_id = aew.id
            log.info(f"Deleting duplicate agent engaged with with id='{aew_id}' type={aew.non_agent_engagement_persona_type}")
            aew.delete()
            aews_removed.append(aew_id)

    log.info(f"Deleted duplicate agent engaged with records with ids: {aews_removed}")


def reduplicate_agentengagedwith(apps, schema_editor):
    """Impossible to do unless we're storing the duplicates in a temporary table."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("calls", "0049_sip_extensions_for_call"),
    ]

    operations = [
        migrations.RunPython(deduplicate_agentengagedwith, reduplicate_agentengagedwith),
        migrations.AlterField(
            model_name="agentassignedcall",
            name="call",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name="assigned_agent", to="calls.call", unique=True, verbose_name="Call assigned to agent"
            ),
        ),
        migrations.AlterField(
            model_name="agentengagedwith",
            name="call",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name="engaged_in_calls", to="calls.call", unique=True, verbose_name="The call engaged with"
            ),
        ),
    ]