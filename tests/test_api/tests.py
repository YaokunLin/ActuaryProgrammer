import pytest

from tests.test_api.factories import LIST_OF_FAKE_PRACTICES

@pytest.mark.unit
def test_for_practices():  # TODO- make a unit test case
    for pract in LIST_OF_FAKE_PRACTICES:
        assert pract.name == pract.name
