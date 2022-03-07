from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from calls.models import Call, CallAudioPartial, CallPartial


class Command(BaseCommand):
    help = "See if calls are completed and if calls are not."

    # def add_arguments(self, parser):
    #     parser.add_argument("poll_ids", nargs="+", type=int)

    def handle(self, *args, **options):
        call_qs = Call.objects.all()
        for call in call_qs.iterator(chunk_size=settings.QUERYSET_ITERATION_CHUNK_SIZE):
            call_partial_qs = CallPartial.objects.filter(call=call).values("pk")
            for call_partial in call_partial_qs:
                if not CallAudioPartial.objects.filter("")
            # caps_qs = CallAudioPartial.objects.filter(call_partial_id__in=call_partial_qs).order_by("call_partial__time_interaction_started", "-modified_at")
            # caps_counts = len(caps_qs)
