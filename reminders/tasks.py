# import os
# import requests
# from reminders import celery, db, app
# from models.appointment import Appointment
# from sqlalchemy.orm.exc import NoResultFound
# import arrow


# @celery.task()
# def send_sms_reminder(appointment_id):
#     try:
#         appointment = db.session.query(
#             Appointment).filter_by(id=appointment_id).one()
#     except NoResultFound:
#         return

#     time = arrow.get(appointment.time).to(appointment.timezone)

#     body = "Hello {0}. You have an appointment at {1}!".format(
#         appointment.name,
#         time.format('h:mm a')
#     )

#     to = appointment.phone_number
#     url = f"https://core1-phx.peerlogic.com/ns-api/?object=message&action=create&domain=Peerlogic&user=1554&from_num=14805611554&type=sms&destination={to}&message={body}"


#     token_url = "https://core1-phx.peerlogic.com/ns-api/oauth2/token/"

#     token_payload={'format': 'json',
#     'grant_type': 'password',
#     'client_id': '***REMOVED***',
#     'client_secret': '***REMOVED***',
#     'username': '***REMOVED***',
#     'password': '***REMOVED***'}
#     token_response = requests.request("POST", token_url, data=token_payload)

#     print(token_response.json())

#     print(url)
#     headers = {
#   'Authorization': f"Bearer {token_response.json()['access_token']}"
# }
#     response = requests.request("POST", url, headers=headers)
#     print(response)
