import pytest

from tests.test_api.factories import LIST_OF_FAKE_PRACTICES


def test_for_active_practices():  # TODO- make a unit test case
    for pract in LIST_OF_FAKE_PRACTICES:
        assert pract.name == pract.name
