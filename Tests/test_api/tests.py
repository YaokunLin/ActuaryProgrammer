import requests
from django.test import TestCase

# Create your tests here.
peerlogr = requests.post('https://peerlogic-api-dev.wn.r.appspot.com')

def test_api():
    assert peerlogr.status_code == 200

print(peerlogr.status_code)
