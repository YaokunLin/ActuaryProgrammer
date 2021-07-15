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



### TODO: Set up MySQL



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

## Deployment steps for GKE

Install GCP Dependencies to your local machine:
* [gcloud SDK](https://cloud.google.com/sdk/docs/quickstart)

If on Mac and you get the `zsh compinit: insecure directories, run compaudit for list.
Ignore insecure directories and continue [y] or abort compinit [n]? kcompinit:` error upon creating new terminal windows, then run

```bash
compaudit | xargs chmod g-w
```

### Updating Source Code

Create a new image and push it to the Container Repository in GCP.

```bash
docker build . -t gcr.io/peerlogic-api/peerlogic-api:latest
docker push gcr.io/peerlogic-api/peerlogic-api:latest
 ```

Then, find the deployment you want to deploy the new image to:

```bash
kubectl get deployments
```

Put the deployment name into the right spot and run the following commands:

```bash
kubectl set image deployments/<deploymentname> peerlogic-api=gcr.io/peerlogic-api/peerlogic-api:latest
kubectl set image deployments/<deploymentname> peerlogic-celery-worker=gcr.io/peerlogic-api/peerlogic-api:latest
kubectl set image deployments/<deploymentname> peerlogic-celery-beat=gcr.io/peerlogic-api/peerlogic-api:latest
kubectl apply -f peerlogic-api.yaml
```

This will set off a rolling update.

Check on the status of this with these commands:

```bash
kubectl rollout status deployment.apps/peerlogic-api
kubectl get pods
```

### Updating the Deployment


If your changes include changes to the peerlogic-api.yaml, do the following steps

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

#### TODO: when just updating source code



### Connect to the GCP Cloud SQL postgres DB

https://cloud.google.com/sql/docs/postgres/sql-proxy

#### Install cloudsql-proxy


Download cloud_sql_proxy to your home directory:

https://cloud.google.com/sql/docs/postgres/quickstart-proxy-test




https://codelabs.developers.google.com/codelabs/cloud-sql-connectivity-gce-private/#4


```bash
gcloud sql instances describe peerlogic-dev | grep connectionName
```



