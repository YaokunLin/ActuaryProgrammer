import factory
import shortuuid
from faker import Faker

from core.models import Practice

fake = Faker()
fake_Practice = Practice(shortuuid.uuid(), f"{fake.first_name()}'s Dental", industry="Dental", active=fake.boolean(chance_of_getting_true=80))


class PracticeModelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Practice
        django_get_or_create = fake_Practice


build = PracticeModelFactory.build_batch(3)

LIST_OF_FAKE_PRACTICES = []

LIST_OF_FAKE_PRACTICES.append(fake_Practice)
