# Peerlogic API


## GCloud Setup

Log into Google Kubernetes Engine (GKE):

```bash
gcloud container clusters get-credentials peerlogic-dev-1 --zone "us-west3-c"
gcloud auth configure-docker
```

Log into Google Kubernetes Engine (GKE):

```bash
gcloud container clusters get-credentials peerlogic-dev-1 --zone "us-west3-c"
gcloud auth configure-docker
```
# 1Password sign-in

Set up your CLI tool: https://support.1password.com/command-line-getting-started/

Sign in: 

https://support.1password.com/command-line/#sign-in-or-out

```bash
op signin [<sign_in_address>](https://peerlogic.1password.com/signin) <email_address> <secret_key>
```
eval $(op signin my)

<!-- For MAC:

```bash
echo "1PASSWORD_SHORTHAND=<youroutputtedtokenhere>" >> ~/.bashrc
``` -->

## Docker

Make sure to run these commands from the root of the project.

### Initial setup

If you haven't created an .env file go ahead and make one from the example file:
`cp .envexample .env`

Fill in the necessary creds in `.env`.

Make sure Docker is running, then do the following steps:
`docker-compose build api`

After initial build and servers are running, in a separate terminal window run the following:

`docker-compose run api python3 manage.py migrate`

`docker-compose run api python3 manage.py createsuperuser`

`docker-compose run api python3 manage.py loaddata fixtures/django_celery_beat.json`


All done!

### Running/Stopping

Start:
`docker-compose up`

End all processes:
`docker-compose down  --remove-orphans`

## Run it Locally (w/o Docker)

Not really recommended; docker has been more tested.


### Initializing, Installing, and Migrating:
First time?

```bash
python3 -m venv env
```

On both first time and fresh updates, do the following:

```bash
source env/bin/activate # ./env/Scripts/activate on Windows
pip3 install -r requirements/requirements.txt
python manage.py migrate
```

To start the backend:

```bash
source env/bin/activate # ./env/Scripts/activate on Windows
python3 manage.py runserver
```

# Deployment

GKE ships with kubernetes version 1.19 in gcloud installation, which means it ships with kustomize version 2.0.3 at the time of this writing:

Helpful Docs:
* [Kustomize 2.0.3](https://github.com/kubernetes-sigs/kustomize/tree/v2.0.3/docs)



See REDEPLOYMENT.md for steps on updating development and staging environments with configuration or code changes.

See DEPLOYMENT.md for steps to create a completely new environment from scratch.
