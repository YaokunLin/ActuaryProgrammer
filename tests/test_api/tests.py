import os

import pytest
import requests

from peerlogic.settings import LOCAL


# Create you tet cases here
def test_api():
    peerlogic = requests.get(LOCAL)  # TODO: need to add code to configure url
    assert peerlogic.status_code == 200


@pytest.fixture
def function_fixture():
    pass


# TODO: Implement
