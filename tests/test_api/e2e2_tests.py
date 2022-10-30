import requests
from peerlogic.settings import TEST_API_CLIENT_ROOT_URL


response = requests.get(TEST_API_CLIENT_ROOT_URL)

def test_api():
    assert response.status_code == 200


print(response.status_code)