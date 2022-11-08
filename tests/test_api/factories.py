import factory
import shortuuid
from faker import Faker

from core.models import Practice

fake = Faker()


class PracticeModelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Practice

    id = shortuuid.uuid()
    name = f"{fake.first_name()}'s Dental"
    industry = "Dental"
    active = fake.boolean(chance_of_getting_true=80)


build = PracticeModelFactory.build_batch(3)
