import json
import requests
import requests.compat  
from typing import (
    Dict
)

from django.conf import settings


class TwilioCnameClient(requests.Request):


    # Authorization: Basic <credentials>

    # E.164 International Standard (https://en.wikipedia.org/wiki/E.164)
    # National Formatting (012) 345-6789

    def __init__(self, twilio_base_url, username, password):
        self._twilio_base_url = twilio_base_url
        self._username = username  # key_sid
        self._password = password  # key_secret


    def lookup_phone_number(self, phone_number: str) -> Dict:
        # Example from API docs 
        #   curl -X GET 'https://lookups.twilio.com/v1/PhoneNumbers/3105555555' \
        #   -u ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX:your_auth_token

        url_for_phone_lookup = requests.compat.urljoin(self._twilio_base_url, phone_number)

        response = requests.get(url_for_phone_lookup, auth=(self._username, self._password))  # use tuple for basic auth
        try:
            response.raise_for_status()
        except requests.exceptions.ConnectionError as err:
            # eg, no internet
            pass
        except requests.exceptions.HTTPError as err:
            # eg, url, server and other errors
            raise SystemExit(err)
        
        phone_number_lookup_data = response.json()
        return json.loads(phone_number_lookup_data)
        

def is_valid_username(username: str) -> bool:
    """The only requirement is that usernames not contain a colon since that's a separator"""
    return ":" not in username
