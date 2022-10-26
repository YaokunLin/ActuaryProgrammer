import os
import pytest
import requests


# Setting environment variables
os.environ["LOCAL_URL"] = "http://0.0.0.0:8000/"

# Getting environment variables
LOCAL = os.getenv("LOCAL_URL")


def test_api():
    peerlogic = requests.get(LOCAL)  # TODO: need to add code to configure url
    assert peerlogic.status_code==200


@pytest.fixture
def function_fixture():
    pass

# TODO: Implement
