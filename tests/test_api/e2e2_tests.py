import requests


from django.conf.settings import TEST_API_CLIENT_ROOT_URL


def test_api():
    response = requests.get(TEST_API_CLIENT_ROOT_URL)
    assert response.status_code == 200
