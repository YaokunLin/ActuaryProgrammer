import os
from typing import Optional
from django.conf import settings
from django.core.management.base import BaseCommand

from google.api_core.exceptions import PermissionDenied
from oauth2_provider.models import (
    get_application_model,
)

from devtools.api_clients.peerlogic_api_client import PeerlogicAPIClient

from calls.models import Call, CallAudioPartial, CallPartial

# TODO: This code doesn't work, figure out why
# from calls.publishers import publish_call_audio_partial_saved

Application = get_application_model()

peerlogic_api_client: Optional[PeerlogicAPIClient] = None


class Command(BaseCommand):
    help = "Reprocesses call audio partials for a given time period."

    def add_arguments(self, parser):
        parser.add_argument(
            "peerlogic_client_base_url", type=str, help="URL to use to POST the publish again - like https://peerlogic-api-dev.wn.r.appspot.com/api"
        )
        parser.add_argument("--start-date", type=str, help="start_date string is <YYYY-MM-DD>")
        parser.add_argument("--end-date", type=str, help="end_date string is <YYYY-MM-DD>")
        parser.add_argument("--call-id", type=str)
        parser.add_argument("--practice-id", type=str)
        parser.add_argument("--no-op", type=str, help="show output but don't reprocess")

    def handle(self, *args, **options):
        peerlogic_client_base_url = options["peerlogic_client_base_url"]
        start_date = options.get("start_date")
        end_date = options.get("end_date")
        call_id = options.get("call_id")
        no_op = options.get("no_op")
        global peerlogic_api_client
        peerlogic_api_client = PeerlogicAPIClient(peerlogic_api_url=peerlogic_client_base_url)
        peerlogic_api_client.login(username=settings.NETSAPIENS_API_USERNAME, password=settings.NETSAPIENS_API_PASSWORD)

        if call_id:
            self.reprocess_audio_for_call(call_id=call_id, no_op=no_op)
            return

        practice_id = options.get("practice_id")

        # TODO: make practice id truly optional for code that follows

        calls = Call.objects.filter(call_start_time__gte=start_date, call_start_time__lte=end_date, practice__id=practice_id)
        call_partials = CallPartial.objects.filter(call__id__in=calls.values("pk"))
        call_audio_partials = CallAudioPartial.objects.filter(call_partial_id__in=call_partials.values("pk")).select_related("call_partial__call")
        print(f"Call count: {calls.count()}")
        print(f"Call Partials count: {call_partials.count()}")
        print(f"Call Audio partials count: {call_audio_partials.count()}")

        for call_audio_partial in call_audio_partials.iterator():
            call_partial_pk = call_audio_partial.call_partial.pk
            call_pk = call_audio_partial.call_partial.call.pk
            self.publish_call_audio_partial_saved(call_id=call_pk, call_partial_id=call_partial_pk, audio_partial_id=call_audio_partial, no_op=no_op)

    def publish_call_audio_partial_saved(self, call_id, call_partial_id, audio_partial_id, no_op: bool):
        global peerlogic_api_client
        try:
            if no_op:
                self.stdout.write(
                    f"No-op, just printing out what we would republish: Call audio partial ready event for: call_id='{call_id}' partial_id='{call_partial_id}' call_audio_partial_id='{audio_partial_id}'"
                )
                return

            # TODO: This code doesn't work, figure out why
            # publish_call_audio_partial_saved(call_id=call_id, partial_id=call_partial_id, audio_partial_id=audio_partial_id)

            self.stdout.write(
                f"Republishing call audio partial ready event for: call_id='{call_id}' partial_id='{call_partial_id}' call_audio_partial_id='{audio_partial_id}'"
            )
            peerlogic_api_client.republish_call_audio_partial(call_id, call_partial_id, audio_partial_id)
            self.stdout.write(
                f"Republished call audio partial ready event for call_id='{call_id}' partial_id='{call_partial_id}' call_audio_partial_id='{audio_partial_id}'"
            )
        except PermissionDenied:
            message = "Must add role 'roles/pubsub.publisher'. Exiting."
            self.stdout.write(message)

    def reprocess_audio_for_call(self, call_id: str, no_op: bool):
        call = Call.objects.get(pk=call_id)
        print(f"Processing 1 call {call.pk}:")
        call_pk = call.pk
        call_partials = CallPartial.objects.filter(call__id=call.pk)
        call_audio_partials = CallAudioPartial.objects.filter(call_partial_id__in=call_partials.values("pk")).select_related("call_partial__call")

        print(f"Call Partials count for call {call.pk}: {call_partials.count()}")
        print(f"Call Audio partials count for call {call.pk}: {call_audio_partials.count()}")

        for call_audio_partial in call_audio_partials.iterator():
            call_partial_pk = call_audio_partial.call_partial.pk
            self.publish_call_audio_partial_saved(call_pk, call_partial_pk, call_audio_partial.pk, no_op)
