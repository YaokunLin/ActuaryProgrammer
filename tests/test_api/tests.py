import pytest
import requests

# Create your tests here.
local_url = 'http://0.0.0.0:8000/'
peerlogic = requests.get(local_url)  # TODO: need to add code to configure url

def test_api():
    assert peerlogic.status_code==200

@pytest.fixture
def function_fixture():
    pass


# TODO: Implement
