import factory
from faker import Faker
from core.models import Practice

fake = Faker()
fake = fake.first_name()
fakepractice = f"{fake}'s Dental"


class PracticeModelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Practice
    practice_name = fakepractice # TODO: use a valid field


PracticeModelFactory.build()
PracticeModelFactory.build_batch()
