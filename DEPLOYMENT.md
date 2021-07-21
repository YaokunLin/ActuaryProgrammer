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
gcloud sql instances create peerlogic --tier=db-f1-micro --region=us-west4
```



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
You've just built a Docker image named peerlogic-api using a Dockerfile and pushed the image to Artifact Registry.
```

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



