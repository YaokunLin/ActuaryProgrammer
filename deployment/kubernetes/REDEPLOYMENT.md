# Deployment steps for GKE

## Set up gcloud

Run the following command and select the following:

* your new project from the list
* select your login or log in for the first time
* select `us-west4-a` as your default region. If you don't see it listed, type `list` to find it.

```bash
gcloud init
```

## Connect to the GKE Cluster

Use the kubectl command-line tool, which is integrated with the gcloud tool, to interact with your GKE cluster. Because gcloud and kubectl are separate tools, make sure kubectl is configured to interact with the right cluster.

```bash
gcloud container clusters get-credentials peerlogic-api --zone "us-west4-a"
```

## Troubleshooting

If on Mac and you get the `zsh compinit: insecure directories, run compaudit for list.
Ignore insecure directories and continue [y] or abort compinit [n]? kcompinit:` error upon creating new terminal windows, then run

```bash
compaudit | xargs chmod g-w
```

## Updating Source Code

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

### Updating an Existing Deployment


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

