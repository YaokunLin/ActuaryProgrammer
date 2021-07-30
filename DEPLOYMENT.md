# Creating a new environment

## Create a new project

1. Google Cloud Platform provides a list of instructions for creating a project here: [GCP's Instructions for Creating a Project](https://cloud.google.com/resource-manager/docs/creating-managing-projects) The following list are notes that correspond to specific steps in the process listed in the link.

Name the project peerlogic-api-<environment>, such as peerlogic-api-dev and peerlogic-api-demo. In the *Location* field, Place it into the corresponding folder location (non-production/development-environment/rest-apis, etc.) This is how we are organizing environment resources.

2. Please note that there can be a time lag between the time that you create a project and when it actually appears in the list of available projects for your organization. For example, your project may appear in the list of your recent projects in your account yet a colleague may be logged into their account and not see it in the project list.

3. Make sure that the admin for your organization enables billing for the project.

4. Enable the Cloud SQL, and Compute Engine APIs.

## Set up gcloud

Run the following command and select the following:

* your new project from the list
* select your login or log in for the first time
* select `us-west4-a` as your default region. If you don't see it listed, type `list` to find it.

```bash
gcloud init
```

## Create a Postgres Cloud SQL instance

Start with a tiny instance. We can ramp it up when we have customers on it.

```bash
gcloud sql instances create peerlogic-envname \
--database-version=POSTGRES_13 \
--cpu=2 \
--memory=7680MB \
--region=us-west4
```

Set the password for the `postgres` user:

Password for different environments gets the title "Peerlogic \<Environment\> Postgres User" in 1Password.


```bash
gcloud sql users set-password postgres \
--instance=peerlogic-prod \
--password=PASSWORD
```

Test the password by running the cloud_sql_proxy:

```bash
gcloud sql instances describe peerlogic-envname | grep connection
```

After installing the cloud_sql_proxy, add it to your PATH. Then run the following in a new terminal window.
```bash
cloud_sql_proxy -instances="[YOUR_INSTANCE_CONNECTION_NAME]"=tcp:5432
```

In another terminal window, install postgres and then run the following command:

```bash
psql --host 127.0.0.1 --user postgres --password
```

Enter the password you just set.

Create a *new* `peerlogic` user and database separate from the `postgres`. Password for this user goes into 1Password as Peerlogic \<Environment\> peerlogic user.

```
CREATE DATABASE peerlogic;
CREATE USER peerlogic WITH PASSWORD '[PEERLOGIC_POSTGRES_PASSWORD]';
GRANT ALL PRIVILEGES ON DATABASE peerlogic TO peerlogic;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO peerlogic;
```



## Create a service account

[Follow the docs](https://cloud.google.com/python/django/kubernetes-engine#creating_a_service_account)

Name the service account the following:
peerlogic-api-\<environment\>-cloud-sql

Give it the "Cloud SQL > Cloud SQL Client" Role.

Put the new JSON key file into 1Password as "\<service-account-name> - \<filename\>".

## Create and upload static resources

```
gsutil mb gs://[PROJECT_ID]
gsutil defacl set public-read  gs://[PROJECT_ID]
```

Create a virtual environment if you don't have one yet and activate it. Then install the dependencies.

```bash
python3 -m venv env
source env/bin/activate
pip3 install -r requirements/requirements.txt
```

Upload the collected static resources to the bucket in the static directory:

```bash
gsutil -m rsync -r ./static gs://[PROJECT_ID]/static
```

## Create GKE Cluster

```bash
gcloud container clusters create peerlogic-api \
  --scopes "https://www.googleapis.com/auth/userinfo.email","cloud-platform" \
  --num-nodes 4 --zone "us-west4-a" \
  --enable-ip-alias
```

After the cluster is created, use the kubectl command-line tool, which is integrated with the gcloud tool, to interact with your GKE cluster. Because gcloud and kubectl are separate tools, make sure kubectl is configured to interact with the right cluster.

```bash
gcloud container clusters get-credentials peerlogic-api --zone "us-west4-a"
```

## Create a new GKE deployment yaml for the new environment

Copy peerlogic-api-prod.yaml and name it peerlogic-api-\<env\>.yaml. We will be editing this document's environment variables and commands along the way with our IP addresses and urls.

Update the cloudsql-proxy command in your corresponding GKE deployment yaml file to use the right connection name obtained from the gcloud command:

```bash
gcloud beta sql instances describe peerlogic-prod | grep connectionName
```

## Set up Cloud SQL Connection in GKE

https://cloud.google.com/python/django/kubernetes-engine#set_up_cloud_sql



You need several secrets to enable your GKE app to connect with your Cloud SQL instance. One is required for instance-level access (connection), while the other two are required for database access. For more information about the two levels of access control, see Instance access control.

To create the secret for instance-level access, provide the location ([PATH_TO_CREDENTIAL_FILE]) of the JSON service account key you downloaded when you created your service account (see Creating a service account):


```bash
kubectl create secret generic cloudsql-oauth-credentials --from-file=credentials.json=[PATH_TO_CREDENTIAL_FILE]
```


To create the secrets for database access, use the SQL [PASSWORD] defined in above in step 2 of Initializing your Cloud SQL instance:


```bash
kubectl create secret generic cloudsql --from-literal=POSTGRES_DB=peerlogic \ --from-literal=POSTGRES_USER=peerlogic \
--from-literal=POSTGRES_PASSWORD=[PASSWORD]
```

Retrieve the public Docker image for the Cloud SQL proxy.

```bash
docker pull b.gcr.io/cloudsql-docker/gce-proxy
```



## Create Secret Keys in Kubernetes

Generate a secret key by activating your virtual environment and running the following python:

```python
from django.core.management import utils
print(utils.get_random_secret_key())
```
Copy-paste this value into your next command:

```bash
kubectl create secret generic django --from-literal=DJANGO_SECRET_KEY='YOURGENERATEDKEYHERE'
```

Obtain the username and password for the [Peerlogic Netsapiens API user](https://start.1password.com/open/i?a=P3RU52IFYBEH3GKEDF2UBYENBQ&v=wlmpasbyyncmhpjji3lfc7ra4a&i=4snjuintsvcurafofmf53twjtm&h=my.1password.com). Have an admin set up a new client ID and secret for this application in core1.

Netsapiens Secrets:
```bash
kubectl create secret generic netsapiens --from-literal=NETSAPIENS_CLIENT_SECRET='CLIENTSECRET' \
--from-literal=NETSAPIENS_API_USERNAME='USERNAME' \
--from-literal=NETSAPIENS_API_PASSWORD='PASSWORD'
```


## Create Redis Store

https://cloud.google.com/memorystore/docs/redis/connect-redis-instance-gke

Enter the following command to create a 2 GiB Basic Tier Redis instance in the us-west4 region:
```bash
gcloud redis instances create peerlogic-api-redis --size=2 --region=us-west4
```
Enable `redis.googleapis.com` when asked.

After the instance is created, enter the describe command to get the IP address and port of the instance:


```bash
gcloud redis instances describe peerlogic-api-redis --region=us-west4
```
If successful, gcloud returns something similar to the following:

```bash
authorizedNetwork: projects/my-project/global/networks/default
createTime: '2018-04-09T21:47:56.824081Z'
currentLocationId: us-west4-a
host: 10.0.0.27
locationId: us-west4-a
memorySizeGb: 2
name: projects/my-project/locations/us-west4/instances/myinstance
networkThroughputGbps: 2
port: 6379
redisVersion: REDIS_4_0
reservedIpRange: 10.0.0.24/29
state: READY
tier: BASIC
```
Take note of the zone, IP address, and port of the Redis instance.

## Connect the Redis Store to GKE

Update the values in the appropriate peerlogic-api-\<env\>.yaml to point at the `redis://\<ipadress\>:6379/0` for the CELERY_BROKER_URL and CELERY_RESULT_BACKEND.


## Create Docker Repository

Instructions:

[Enable Artifact Repository](https://console.cloud.google.com/marketplace/product/google/artifactregistry.googleapis.com)

```bash
gcloud artifacts repositories create peerlogic --repository-format=docker \
--location=us-west4 --description="Peerlogic repo"
```
Verify it created successfully.

```bash
gcloud artifacts repositories list
```

## Build using Dockerfile

[Enable Cloudbuild API](https://console.cloud.google.com/marketplace/product/google/cloudbuild.googleapis.com)

Cloud Build allows you to build a Docker image using a Dockerfile. You don't require a separate Cloud Build config file.

To build using a Dockerfile:

1. Get your Cloud project ID by running the following command:

```bash
gcloud config get-value project
```

2. Make sure you are on the `main` branch. Then run the following command from the directory containing Dockerfile, where project-id is your Cloud project ID:

```bash
gcloud builds submit --tag us-west4-docker.pkg.dev/project-id/peerlogic/peerlogic-api:latest
```

Note: If your project ID contains a colon, replace the colon with a forward slash.
After the build is complete, you will see an output similar to the following:

```text
DONE
------------------------------------------------------------------------------------------------------------------------------------
ID                                    CREATE_TIME                DURATION  SOURCE   IMAGES     STATUS
545cb89c-f7a4-4652-8f63-579ac974be2e  2020-11-05T18:16:04+00:00  16S       gs://peerlogic-api-prod_cloudbuild/source/1604600163.528729-b70741b0f2d0449d8635aa22893258fe.tgz  us-west4-docker.pkg.dev/peerlogic/peerlogic-api:latest  SUCCESS
```

You've just built a Docker image named peerlogic-api using a Dockerfile and pushed the image to Artifact Registry.

Navigate to your Cloud Build History and watch the job there. Click on the Build Artifacts tab, and you'll see the docker image, like so: us-west4-docker.pkg.dev/peerlogic-api-prod/peerlogic/peerlogic-api. You can click the icon to open the docker image information in a new tab, and you'll see the latest tag there.

## Grant permissions

Enable the following services/APIs:
* Cloud Build
* Cloud Run
* Artifact Registry
* Compute Engine

Run the following bash commands to assign the Cloud Run Admin and IAM Service Account User permissions.



Open a terminal window.

Set environment variables to store your project ID and project number:

```bash
PROJECT_ID=$(gcloud config list --format='value(core.project)')
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
```

Grant the Cloud Run Admin role to the Cloud Build service account:

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com \
    --role=roles/run.admin
```

Grant the IAM Service Account User role to the Cloud Build service account for the Cloud Run runtime service account:

```bash
gcloud iam service-accounts add-iam-policy-binding \
    $PROJECT_NUMBER-compute@developer.gserviceaccount.com \
    --member=serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com \
    --role=roles/iam.serviceAccountUser
```

## Deploy a prebuilt image

You can configure Cloud Build to deploy a prebuilt image that is stored in Artifact Registry to Cloud Run.

To deploy a prebuilt image:


The cloudbuild.yaml file is the Cloud Build config file. It contains instructions for Cloud Build to deploy the image named `us-west4-docker.pkg.dev/peerlogic-api-prod/peerlogic/peerlogic-api:latest` on the Cloud Run service named cloudrunservice.

Deploy the image by running the following command:

```bash
gcloud builds submit --config cloudbuild.yaml
```

When the build is complete, you will see an output similar to the following:

```
DONE
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

ID                                    CREATE_TIME                DURATION  SOURCE                                                                                            IMAGES  STATUS
784653b2-f00e-4c4b-9f5f-96a5f115bef4  2020-01-23T14:53:13+00:00  23S       gs://cloudrunqs-project_cloudbuild/source/1579791193.217726-ea20e1c787fb4784b19fb1273d032df2.tgz  -       SUCCESS
```

You've just deployed the image peerlogic-api to Cloud Run.

## Update GKE deployment yaml file with the appropriate image name

This is titled peerlogic-api-\<env\>.yaml.

Update the image value for each container spec for the following: peerlogic-api, and peerlogic-celery-beat, and peerlogic-celery-worker wiht your new repo:

`us-west4-docker.pkg.dev/peerlogic-api-prod/peerlogic/peerlogic-api`



