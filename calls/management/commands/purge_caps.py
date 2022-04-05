from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from calls.models import CallAudioPartial, CallPartial


class Command(BaseCommand):
    help = "Purges all previous call audio partials that have an uploaded cap for a given call partial."

    # def add_arguments(self, parser):
    #     parser.add_argument("poll_ids", nargs="+", type=int)

    def handle(self, *args, **options):
        cap_retrievals_in_progress_qs = CallAudioPartial.objects.exclude(status="uploaded").order_by("call_partial__time_interaction_started", "-modified_at")
        caps_to_delete = None
        caps_to_delete = list()
        caps_passing = list()
        for cap in cap_retrievals_in_progress_qs.iterator(chunk_size=settings.QUERYSET_ITERATION_CHUNK_SIZE):
            cp = None
            print(cap.id)
            cp = CallPartial.objects.get(pk=cap.call_partial_id)
            print(cp.id)
            uploaded = CallAudioPartial.objects.filter(status="uploaded", call_partial=cp)
            if len(uploaded) > 0:
                print(f"CAP {cap} ready for deletion, has uploaded call partial '{cp}'")
                caps_to_delete.append(cap)
                # cap.delete()
                # self.stdout.write(self.style.SUCCESS(f"Successfully purged call audio partial '{cap}'"))
            else:
                caps_passing.append(cap)
                print(f"pass")
                print(f"-")
                print(f"--")
                print(f"---")

            print(f"Deletion count: '{len(caps_to_delete)}'")
            print(f"Passing over count: '{len(caps_passing)}'")

        cap_uploadeds_qs = CallAudioPartial.objects.filter(status="uploaded").order_by("call_partial__time_interaction_started", "modified_at")

        for cap in cap_uploadeds_qs.iterator(chunk_size=settings.QUERYSET_ITERATION_CHUNK_SIZE):
            cp = None
            print(cap.id)
            cp = CallPartial.objects.get(pk=cap.call_partial_id)
            print(cp.id)
            uploaded = CallAudioPartial.objects.filter(status="uploaded", call_partial=cp)
            if len(uploaded) > 1:
                print(f"CAP {cap} ready for deletion, has uploaded call partial '{cp}'")
                caps_to_delete.append(cap)
                # cap.delete()
                # self.stdout.write(self.style.SUCCESS(f"Successfully purged call audio partial '{cap}'"))
            else:
                caps_passing.append(cap)
                print(f"pass")
                print(f"-")
                print(f"--")
                print(f"---")

            print(f"Deletion count: '{len(caps_to_delete)}'")
            print(f"Passing over count: '{len(caps_passing)}'")

        self.stdout.write(self.style.NOTICE(f"CAPs deleted count: {len(caps_to_delete)}"))
