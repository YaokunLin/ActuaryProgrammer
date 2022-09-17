Install ngrok 

ngrok http 8000

Grab the Forwarding URL

Use that in the RingCentral Create Subscription request
https://developers.ringcentral.com/api-reference/Subscriptions/createSubscription

Set the ngrok url as the `address`, set the transportType to `WebHook` and set the eventFilters to `/restapi/v1.0/account/~/telephony/sessions`

Example: https://8472-104-60-198-180.ngrok.io/api/integrations/ringcentral/webhook