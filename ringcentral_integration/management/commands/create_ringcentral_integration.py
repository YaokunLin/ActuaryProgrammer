from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

import requests
from ringcentral import SDK
from core.models import Practice, PracticeTelecom, VoipProvider
from ringcentral_integration.models import RingCentralAPICredentials, RingCentralCallSubscription


class Command(BaseCommand):
    help = "Creates all resources from peerlogic voip provider for a new environment"

    def add_arguments(self, parser):
        parser.add_argument("peerlogic_root_api_url", type=str)
        parser.add_argument("voip_provider_id", type=str)
        parser.add_argument("practice_name", type=str)
        parser.add_argument("practice_voip_domain", type=str)

    def handle(self, *args, **options):
        self.stdout.write(f"Getting voip provider with options['voip_provider_id']='{options['voip_provider_id']}'")
        voip_provider = VoipProvider.objects.get(pk=options["voip_provider_id"])
        self.stdout.write(self.style.SUCCESS(f"Got voip provider with pk='{voip_provider.pk}'"))

        self.stdout.write(f"Getting ringcentral credentials for voip provider'{options['voip_provider_id']}'")
        ringcentral_creds = RingCentralAPICredentials.objects.get(voip_provider_id=options['voip_provider_id'])
        self.stdout.write(self.style.SUCCESS(f"Got ringcentral credentials with pk='{ringcentral_creds.pk}'"))

        with transaction.atomic():
            self.stdout.write(f"Creating practice with name='{options['practice_name']}'")
            practice = Practice.objects.create(name=options["practice_name"], active=True)
            self.stdout.write(self.style.SUCCESS(f"Created practice with pk='{practice.pk}'"))

            self.stdout.write(f"Creating practice telecom with domain='{options['practice_voip_domain']}'")
            practice_telecom = PracticeTelecom.objects.create(voip_provider=voip_provider, domain=options["practice_voip_domain"], practice=practice)
            self.stdout.write(self.style.SUCCESS(f"Created practice telecom with pk='{practice_telecom.pk}'"))

            self.stdout.write(f"Creating ringcentral_call_subscription with practice_telecom='{practice_telecom.pk}'")
            ringcentral_call_subscription = RingCentralCallSubscription.objects.create(practice_telecom=practice_telecom, active=True)
            self.stdout.write(self.style.SUCCESS(f"Created ringcentral_call_subscription with pk='{ringcentral_call_subscription.pk}'"))

            ringcentral_sdk = SDK(ringcentral_creds.client_id, ringcentral_creds.client_secret, ringcentral_creds.api_url)
            platform = ringcentral_sdk.platform()
            self.stdout.write(f"Username '{ringcentral_creds.username}' and Password '{ringcentral_creds.password}'")
            platform.login(ringcentral_creds.username, '', ringcentral_creds.password)

            websocket_url = f"{options['peerlogic_root_api_url']}{ringcentral_call_subscription.call_subscription_uri}"
            event_subscription_payload = {
                "eventFilters":["/restapi/v1.0/account/~/telephony/sessions"],
                "deliveryMode":{"address":websocket_url,
                "transportType":"WebHook"}
            }
            event_subscription_response = platform.post('/restapi/v1.0/subscription', event_subscription_payload)

            # attempt to get response content as json, get the first
            try:
                event_subscription = event_subscription_response.json()[0]
            except requests.exceptions.JSONDecodeError:
                msg = "Problem attempting to retrieve JSON response for event subscription."
                self.stdout.write(self.style.ERROR(msg))
                raise Exception(msg)

            ringcentral_call_subscription.source_id = event_subscription["id"]
            ringcentral_call_subscription.save()
            self.stdout.write(self.style.SUCCESS(f"Created netsapiens_call_subscription with source_id='{ringcentral_call_subscription.source_id}'"))
