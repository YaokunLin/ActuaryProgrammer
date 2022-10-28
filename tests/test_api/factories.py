import factory

from core.models import Practice


class PracticeModelFactory(factory.DjangoModelFactory):
    class Meta:
        model = Practice

    field1 = factory.faker.Faker("Phone_number")


PracticeModelFactory.build()
PracticeModelFactory.build_batch()
