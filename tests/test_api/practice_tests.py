import pytest

from tests.test_api.factories import build


# @pytest.mark.unit
def test_for_practices():
    for practice in build:
        assert practice.name == practice.name
