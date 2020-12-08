import requests
from django.conf import settings


from peerlogic.celery import app
from core.models import User, Client
from reminders.models import Cadence


@app.task()
def send_sms_reminders():
    appointments = None
    appointments = []
    for cadence in Cadence.objects.all():
        appointments = requests.request(
            "GET", f"{cadence.client.rest_base_url}/appointments?date=today"
        ).json()
        if len(appointments) > 0:
            for a in appointments:
                a["client"] = cadence.client
                a["cadence"] = cadence

    print(appointments)
    for appointment in appointments:
        rest_base_url = appointment["client"].rest_base_url
        start_hour = appointment["start_hour"]
        start_minute = appointment["start_minute"]
        start_minute = f"0{start_minute}" if int(start_minute) < 10 else start_minute
        patient_guid = appointment["patient_guid"]
        domain = appointment["client"].group.name
        user = appointment["cadence"].user_sending_reminder
        django_user = User.objects.get(
            pk=appointment["cadence"].user_sending_reminder.id
        )
        sms_number = django_user.sms_number
        user = django_user.telecom_user
        patient = requests.request(
            "GET", f"{rest_base_url}/patients/{patient_guid}"
        ).json()

        patient_name = patient["first_name"].rstrip().title()
        body = f"Hello {patient_name}. You have an appointment at {start_hour}:{start_minute}. Ready to see you soon!"

        to = patient["mobile_phone"].strip()
        url = f"{settings.NS_BASE_URL}/?object=message&action=create&domain={domain}&user={user}&from_num={sms_number}&type=sms&destination={to}&message={body}"
        print(url)

        token_url = f"{settings.NS_BASE_URL}/oauth2/token/"

        token_payload = {
            "format": "json",
            "grant_type": "password",
            "client_id": settings.NS_CLIENT_ID,
            "client_secret": settings.NS_CLIENT_SECRET,
            "username": settings.NS_API_USER,
            "password": settings.NS_API_PASSWORD,
        }
        token_response = requests.request("POST", token_url, data=token_payload)

        print(token_response.json())

        print(url)
        headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}
        response = requests.request("POST", url, headers=headers)
        print(response)
