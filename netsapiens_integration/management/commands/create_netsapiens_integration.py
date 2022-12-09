from typing import Dict, List
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from core.clients.netsapiens_client import NetsapiensAPIClient
from core.models import Organization, Practice, PracticeTelecom, VoipProvider
from netsapiens_integration.models import (
    NetsapiensAPICredentials,
    NetsapiensCallSubscription,
)


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

        self.stdout.write(f"Getting netsapiens credentials with PEERLOGIC_NETSAPIENS_API_CREDENTIALS_ID='{settings.PEERLOGIC_NETSAPIENS_API_CREDENTIALS_ID}'")
        ns_creds = NetsapiensAPICredentials.objects.get(pk=settings.PEERLOGIC_NETSAPIENS_API_CREDENTIALS_ID)
        self.stdout.write(self.style.SUCCESS(f"Got netsapiens credentials with pk='{ns_creds.pk}'"))

        netsapiens_api_client = NetsapiensAPIClient(root_api_url=ns_creds.api_url)
        netsapiens_api_client.login(username=ns_creds.username, password=ns_creds.password, client_id=ns_creds.client_id, client_secret=ns_creds.client_secret)

        practice_voip_domain = options["practice_voip_domain"]
        self.stdout.write(f"Checking domain entered exists in Netsapiens, practice_voip_domain='{practice_voip_domain}'")
        domain_response = netsapiens_api_client.get_domain(practice_voip_domain)
        domains: List[Dict] = domain_response.json()
        self.stdout.write(f"Domain entered exists in Netsapiens, practice_voip_domain='{practice_voip_domain}', domains='{domains}'")

        with transaction.atomic():
            practice_name = options["practice_name"]
            self.stdout.write(f"Creating organization with name='{practice_name}'")
            organization = Organization.objects.create(name=practice_name)
            self.stdout.write(self.style.SUCCESS(f"Created organization with pk='{organization.pk}'"))

            self.stdout.write(f"Creating practice with name='{practice_name}'")
            practice = Practice.objects.create(name=practice_name, active=True, organization=organization)
            self.stdout.write(self.style.SUCCESS(f"Created practice with pk='{practice.pk}'"))

            self.stdout.write(f"Creating practice telecom with domain='{options['practice_voip_domain']}'")
            practice_telecom = PracticeTelecom.objects.create(voip_provider=voip_provider, domain=options["practice_voip_domain"], practice=practice)
            self.stdout.write(self.style.SUCCESS(f"Created practice telecom with pk='{practice_telecom.pk}'"))

            self.stdout.write(f"Creating netsapiens_call_subscription with practice_telecom='{practice_telecom.pk}'")
            netsapiens_call_subscription = NetsapiensCallSubscription.objects.create(practice_telecom=practice_telecom, active=True)
            self.stdout.write(self.style.SUCCESS(f"Created netsapiens_call_subscription with pk='{netsapiens_call_subscription.pk}'"))

            # Call ns-api to create event Subscription - from core1 side
            post_url = f"{options['peerlogic_root_api_url']}{netsapiens_call_subscription.call_subscription_uri}"
            event_subscription_response = netsapiens_api_client.create_event_subscription(domain=options["practice_voip_domain"], post_url=post_url)
            # attempt to get response content as json, get the first
            try:
                event_subscription = event_subscription_response.json()[0]
            except requests.exceptions.JSONDecodeError:
                msg = "Problem attempting to retrieve JSON response for event subscription."
                self.stdout.write(self.style.ERROR(msg))
                raise Exception(msg)

            netsapiens_call_subscription.source_id = event_subscription["id"]
            netsapiens_call_subscription.save()
            self.stdout.write(self.style.SUCCESS(f"Created netsapiens_call_subscription with source_id='{netsapiens_call_subscription.source_id}'"))
