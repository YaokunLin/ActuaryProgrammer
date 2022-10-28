import factory
import pytest

from core.models import Practice


class PracticeModelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Practice

    field1 = factory.faker.Faker("name") # TODO: use a valid field


PracticeModelFactory.build()
PracticeModelFactory.build_batch()


# pytest fixtures
@pytest.fixture
def Practice():
    def _practices():
        pass
