import factory
from faker import Faker

fake = Faker()
fake = fake.first_name()
fakepractice = f"{fake}'s Dental"


class PracticeModelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'core.models.Practice'
    practice_name = fakepractice # TODO: use a valid field


PracticeModelFactory.build()
PracticeModelFactory.build_batch()
