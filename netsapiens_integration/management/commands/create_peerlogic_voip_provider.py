from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from core.models import VoipProvider

def insert_with_pk():
    with connection.cursor() as cursor:
        cursor.execute("INSERT INTO public.core_voipprovider (created_at,modified_at,id,company_name,integration_type,created_by_id,modified_by_id,active) VALUES ('2022-02-07 00:00:00.000','2022-02-07 00:00:00.000', %s,'Peerlogic','netsapiens',NULL,NULL,true);", [settings.PEERLOGIC_VOIP_PROVIDER_ID])
    try:
        voip_provider = VoipProvider.objects.get(pk=settings.PEERLOGIC_VOIP_PROVIDER_ID)

    except VoipProvider.DoesNotExist:
        raise CommandError()

    return voip_provider

class Command(BaseCommand):
    help = 'Creates all resources from peerlogic voip provider for a new environment'

    def handle(self, *args, **options):
        try:
            self.stdout.write(f"Getting voip provider with {settings.PEERLOGIC_VOIP_PROVIDER_ID}")
            voip_provider = VoipProvider.objects.get(pk=settings.PEERLOGIC_VOIP_PROVIDER_ID)
            self.stdout.write(self.style.SUCCESS(f"Got voip provider with {settings.PEERLOGIC_VOIP_PROVIDER_ID}"))
        except VoipProvider.DoesNotExist:
            self.stdout.write(f"Creating voip provider with {settings.PEERLOGIC_VOIP_PROVIDER_ID}")
            insert_with_pk()
            self.stdout.write(self.style.SUCCESS(f"Created voip provider with {settings.PEERLOGIC_VOIP_PROVIDER_ID}"))

        # TODO: do stuff with voip_provider
