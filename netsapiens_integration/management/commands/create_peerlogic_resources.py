from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

import requests

from core.models import Practice, PracticeTelecom, VoipProvider
from netsapiens_integration.models import NetsapiensCallSubscription


def insert_voip_provider_with_pk():
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO public.core_voipprovider (created_at,modified_at,id,company_name,integration_type,created_by_id,modified_by_id,active) VALUES ('2022-02-07 00:00:00.000','2022-02-07 00:00:00.000', %s,'Peerlogic','netsapiens',NULL,NULL,true);",
            [settings.PEERLOGIC_NETSAPIENS_VOIP_PROVIDER_ID],
        )
    try:
        voip_provider = VoipProvider.objects.get(pk=settings.PEERLOGIC_NETSAPIENS_VOIP_PROVIDER_ID)

    except VoipProvider.DoesNotExist:
        raise CommandError()

    return voip_provider


def insert_practice_with_pk():
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO public.core_practice (created_at,modified_at,id,name,industry,created_by_id,modified_by_id,active) VALUES ('2021-12-16 13:48:32.542','2022-02-01 18:15:36.628',%s,'Peerlogic','dentistry_general',NULL,NULL,true);",
            [settings.TEST_NETSAPIENS_PRACTICE_ID],
        )
    try:
        practice = Practice.objects.get(pk=settings.TEST_NETSAPIENS_PRACTICE_ID)

    except Practice.DoesNotExist:
        raise CommandError()

    return practice


def insert_practice_telecom_with_pk(practice):
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO public.core_practicetelecom (created_at,modified_at,id,domain,phone_sms,phone_callback,created_by_id,modified_by_id,practice_id,voip_provider_id) VALUES ('2021-12-16 14:29:30.163','2021-12-16 14:29:30.163',%s,'Peerlogic','','',NULL,NULL,%s,NULL);",
            [settings.TEST_NETSAPIENS_PRACTICE_ID, practice],
        )
    try:
        practice_telecom = PracticeTelecom.objects.get(pk=settings.TEST_NETSAPIENS_PRACTICE_TELECOM_ID)

    except PracticeTelecom.DoesNotExist:
        raise CommandError()

    return practice_telecom


class Command(BaseCommand):
    help = "Creates all resources from peerlogic voip provider for a new environment"

    def handle(self, *args, **options):
        try:
            self.stdout.write(f"Getting voip provider with {settings.PEERLOGIC_NETSAPIENS_VOIP_PROVIDER_ID}")
            voip_provider = VoipProvider.objects.get(pk=settings.PEERLOGIC_NETSAPIENS_VOIP_PROVIDER_ID)
            self.stdout.write(self.style.SUCCESS(f"Got voip provider with {voip_provider.pk}"))
        except VoipProvider.DoesNotExist:
            self.stdout.write(f"Creating voip provider with {settings.PEERLOGIC_NETSAPIENS_VOIP_PROVIDER_ID}")
            insert_voip_provider_with_pk()
            self.stdout.write(self.style.SUCCESS(f"Created voip provider with {settings.PEERLOGIC_NETSAPIENS_VOIP_PROVIDER_ID}"))

        # TODO: do stuff with voip_provider

        try:
            self.stdout.write(f"Getting practice with {settings.TEST_NETSAPIENS_PRACTICE_ID}")
            practice = Practice.objects.get(pk=settings.TEST_NETSAPIENS_PRACTICE_ID)
            self.stdout.write(self.style.SUCCESS(f"Got practice with {practice.pk}"))
        except Practice.DoesNotExist:
            self.stdout.write(f"Creating practice with {settings.TEST_NETSAPIENS_PRACTICE_ID}")
            insert_practice_with_pk()
            self.stdout.write(self.style.SUCCESS(f"Created practice with {settings.TEST_NETSAPIENS_PRACTICE_ID}"))

        try:
            self.stdout.write(f"Getting practice telecom with {settings.TEST_NETSAPIENS_PRACTICE_TELECOM_ID}")
            practice_telecom = PracticeTelecom.objects.get(pk=settings.TEST_NETSAPIENS_PRACTICE_TELECOM_ID)
            self.stdout.write(self.style.SUCCESS(f"Got practice telecom with {practice_telecom.pk}"))
        except PracticeTelecom.DoesNotExist:
            self.stdout.write(f"Creating practice telecom with {settings.TEST_NETSAPIENS_PRACTICE_TELECOM_ID}")
            insert_practice_telecom_with_pk()
            self.stdout.write(self.style.SUCCESS(f"Created practice with {settings.TEST_NETSAPIENS_PRACTICE_TELECOM_ID}"))

        self.stdout.write(f"Getting or creating netsapiens_call_subscription with practice_telecom='{practice_telecom.pk}'")
        netsapiens_call_subscription, netsapiens_call_subscription_created = NetsapiensCallSubscription.objects.get_or_create(
            practice_telecom=practice_telecom,
            defaults={"active": True},
        )
        if netsapiens_call_subscription_created:
            self.stdout.write(self.style.SUCCESS(f"Created netsapiens_call_subscription with id='{netsapiens_call_subscription.pk}'"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Got netsapiens_call_subscription with id='{netsapiens_call_subscription.pk}'"))

        # TODO: create Netsapiens API Credentials

        # TODO: Call ns-api to create event Subscription - from core1 side

        # TODO: patch netsapiens_call_subscription from above with source_id
