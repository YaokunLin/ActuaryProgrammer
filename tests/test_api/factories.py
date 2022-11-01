import factory
from faker import Faker
from core.models import Practice

fake = Faker()
fake_Practice = Practice(fake.random_int(1000, 2000), f"{fake.first_name()}'s Dential",
industry = "Dential", active = fake.boolean(chance_of_getting_true=80))
class PracticeModelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Practice
        django_get_or_create = fake_Practice # TODO: use a valid field

LIST_OF_FAKE_PRACTICES = []

LIST_OF_FAKE_PRACTICES.append(fake_Practice)
