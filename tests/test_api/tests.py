import os

import pytest
import requests

from peerlogic.settings import TEST_API_CLIENT_ROOT_URL


# Create you tet cases here
def test_api():
    peerlogic = requests.get(TEST_API_CLIENT_ROOT_URL)  # TODO: need to add code to configure url
    assert peerlogic.status_code == 200


@pytest.fixture
def function_fixture():
    pass


# TODO: Implement
