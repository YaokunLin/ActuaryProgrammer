# Peerlogic API

## Docker

Make sure to run these commands from the root of the project.

### Initial setup

If you haven't created an .env file go ahead and make one from the example file:
`cp .envexample .env`

Fill in the necessary creds in `.env`.

Make sure Docker is running, then do the following steps:
`docker-compose build api`

After initial build and servers are running, in a separate terminal window run the following:

`docker-compose run api python manage.py migrate`
`docker-compose run api python manage.py createsuperuser`
`docker-compose run api python manage.py loaddata fixtures/django_celery_beat.json`

All done!

### Running/Stopping

Start:
`docker-compose up`

End all processes:
`docker-compose down  --remove-orphans`

## Run it Locally (w/o Docker)

Not really recommended; docker has been more tested.

First time?

```bash
python3 -m venv env
```

On fresh updates, do the following:

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

## Deployment steps for GKE

If editing the peerlogic-api.yaml, do the following steps

```bash
$ kubectl apply -f peerlogic-api.yaml
$ kubectl rollout status deployment.apps/peerlogic-api
deployment "peerlogic-api" successfully rolled out
$ kubectl get pods
```

Helpful links for updating the deployment:

* [Kubernetes Engine](https://cloud.google.com/python/django/kubernetes-engine)
* [Inject Data into an Application](https://kubernetes.io/docs/tasks/inject-data-application/)
* [Updating a Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#updating-a-deployment)

TODO: when just updating source code
