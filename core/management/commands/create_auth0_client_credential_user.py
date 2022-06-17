from django.conf import settings
from django.core.management.base import BaseCommand


from oauth2_provider.models import (
    get_application_model,
)
from core.models import User

Application = get_application_model()


class Command(BaseCommand):
    help = "Creates user from client credential for a new environment so that the machine or service can do admin actions like creating users."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)
        parser.add_argument("client_id", type=str)

    def handle(self, *args, **options):
        self.stdout.write(f"Getting client credential application with options['client_id']='{options['client_id']}'")
        application = Application.objects.get(client_id=options["client_id"])
        self.stdout.write(self.style.SUCCESS(f"Got application with client_id='{application.client_id}'"))

        self.stdout.write(f"Creating application django user with username='{options['username']}'")
        application_user = User.objects.create(name=options["username"])
        self.stdout.write(self.style.SUCCESS(f"Created application django user with pk='{application_user.pk}'"))

        if settings.DB_HOST == "host.docker.internal":
            self.stdout.write(
                self.style.WARNING(f"Double-check this project ID is correct and then proceed to the proper project for Secret Manager: {settings.PROJECT_ID}")
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Command-Click this Secret Manager link: https://console.cloud.google.com/security/secret-manager/secret/peerlogic-api-env/versions?project={settings.PROJECT_ID}"
                )
            )
            self.stdout.write(self.style.SUCCESS(f"Add the following lines to Secret Manager peerlogic-api-env in project {settings.PROJECT_ID}:"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Add the following lines to your .env file:"))

        self.stdout.write(f"AUTH0_MACHINE_CLIENT_ID={application.client_id}")
        self.stdout.write(f"AUTH0_MACHINE_USER_ID={application_user.pk}")
