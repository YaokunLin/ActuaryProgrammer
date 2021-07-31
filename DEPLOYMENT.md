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

Collect static:
```bash
python manage.py collectstatic
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


## Update GKE deployment yaml file with the appropriate image name

This is titled peerlogic-api-\<env\>.yaml.

Update the image value for each container spec for the following: peerlogic-api, and peerlogic-celery-beat, and peerlogic-celery-worker wiht your new repo:

`gcr.io/peerlogic-api-prod/peerlogic-api`



# Create Cloud Build for GKE

[Enable Cloudbuild API](https://console.cloud.google.com/marketplace/product/google/cloudbuild.googleapis.com)

Enable Kubernetes Engine - Kubernetes Engine Developer in the [Settings page for GKE](https://console.cloud.google.com/cloud-build/settings/service-account).

Test your build before creating a trigger:

```bash
gcloud builds submit --project=project-id --config build-config
```

Where:

* project-id is the ID for your project.
* build-config is the name of your build configuration file.



## Configure HTTPS Ingress


### Reserve a static IP

```bash
gcloud compute addresses create YOURPROJECTID --global
gcloud compute addresses describe YOURPROJECTID --global
```

Create the managed certificate manifest in your peerlogic-api-\<env\>.yaml and reference it in your ingress resource.

Look up the IP address of the load balancer created in the previous step. Use the following command to get the IP address of the load balancer:

```bash
kubectl get ingress
```
The output is similar to the following:

```bash
NAME            CLASS    HOSTS   ADDRESS                 PORTS   AGE
basic-ingress   <none>   *       should-match-above-ip   80      54s
```


The load balancer's IP address is listed in the ADDRESS column. If you are using a reserved static IP address that will be the load balancer's address.

If the address is not listed, wait for the Ingress to finish setting up.

### Visiting your reserved static IP address
To verify that the load balancer is configured correctly, you can either use a web browser to visit the IP address or use curl:


curl http://203.0.113.32/

Note: You might get HTTP 404 and HTTP 500 errors for a few minutes if you used Ingress resource to configure a load balancer. It takes time for configuration changes to propagate to regions across the globe.

### Configuring your domain name records
Configure the DNS records for your domains to point to the IP address of the load balancer. 

To have browsers querying your domain name, such as example.com, or subdomain name, such as blog.example.com, point to the static IP address you reserved, you must update the DNS (Domain Name Server) records of your domain name.

You must create an A (Address) type DNS record for your domain or subdomain name and have its value configured with the reserved IP address.

DNS records of your domain are managed by your nameserver. Our nameserver is a DNS service called Cloud DNS, located in the peerlogic-dns project.

Follow Cloud DNS Quickstart guide to configure DNS A record for your domain name with the reserved IP address of your application. Go to Cloud DNS and create a record set in peerlogic-tech pointing api-\<env\>.peerlogic.tech to the static IP.

Note: You must wait for the DNS records you configured to propagate before continuing.

### Visiting your domain name
To verify that your domain name's DNS A records resolve to the IP address you reserved, visit your domain name.

Note: It can take a few hours for DNS records to propagate. This time might depend on your nameservers, local internet service provider (ISP), and many other factors.
To make a DNS query for your domain name's A record, run the host command:


host example.com
Output:

example.com has address 203.0.113.32
At this point, you can point your web browser to your domain name and visit your website!

### Babysit the Google-managed Certificate
Wait for the Google-managed certificate to be provisioned. This may take up to 60 minutes. You can check on the status of the certificate with the following command:

```bash
kubectl describe managedcertificate CERTIFICATE_NAME
```

Once a certificate is successfully provisioned, the value of the Status.CertificateStatus field will be Active. The following example shows the output of kubectl describe after the certificate is successfully provisioned:


Name:         CERTIFICATE_NAME
Namespace:    default
Labels:       <none>
Annotations:  <none>
API Version:  networking.gke.io/v1
Kind:         ManagedCertificate
(...)
Spec:
  Domains:
    DOMAIN_NAME1
    DOMAIN_NAME2
Status:
  CertificateStatus: Active
(...)


Verify that SSL is working by visiting your domains using the https:// prefix. Your browser will indicate that the connection is secure and you can view the certificate details.

