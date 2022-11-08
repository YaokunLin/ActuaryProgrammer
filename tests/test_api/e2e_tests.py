import requests

from peerlogic.settings import TEST_API_CLIENT_ROOT_URL

response = requests.get(f"{TEST_API_CLIENT_ROOT_URL}/admin")


def test_api():
    assert response.status_code == 200
