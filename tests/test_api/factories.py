import factory

from core.models import Practice


class PracticeModelFactory(factory.DjangoModelFactory):
    class Meta:
        model = Practice

    field1 = factory.faker.Faker("name")


PracticeModelFactory.build()
PracticeModelFactory.build_batch()
