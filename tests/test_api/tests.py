import pytest
import requests

from peerlogic.settings import TEST_API_CLIENT_ROOT_URL


def test_api():
    peerlogic = requests.get(TEST_API_CLIENT_ROOT_URL)
    assert peerlogic.status_code == 200
