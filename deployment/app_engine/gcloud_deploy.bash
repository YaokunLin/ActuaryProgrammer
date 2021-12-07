#!/bin/bash
set -x #echo on

# First, gcloud init
# Then, run as ./deployment/app_engine/gcloud_deploy.bash from the root of the peerlogic-api repo.

PROJECT_ID=$(gcloud config list --format='value(core.project)')
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CLOUDBUILD_SERVICE_ACCOUNT="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
APP_ENGINE_SERVICE_ACCOUNT="${PROJECT_ID}@appspot.gserviceaccount.com"
VAULT_ID="wlmpasbyyncmhpjji3lfc7ra4a"
REGION=$(gcloud config list --format='value(compute.region)')
ZONE=$(gcloud config list --format='value(compute.zone)')
SUBNET="peerlogic-dev-us-west1-subnet-private"
HOST_PROJECT_ID="peerlogic-vpc-host-dev"

textred=$(tput setaf 1) # Red
textgreen=$(tput setaf 2) # Green
textylw=$(tput setaf 3) # Yellow
textblue=$(tput setaf 4) # Blue
textpurple=$(tput setaf 5) # Purple
textcyn=$(tput setaf 6) # Cyan
textwht=$(tput setaf 7) # White
textreset=$(tput sgr0) # Text reset.

# TODO: check if python 3 is installed as 'python3' first, otherwise use 'python'
# TODO: check op (1Password) is installed before continuing
# TODO: check project name before continuing

if [ -z $VIRTUAL_ENV ];
then
  echo "${textred}Error: please activate a virtual environment before running this script"
  exit 1
fi

DJANGO_SECRET_KEY=$(python3 -c 'from django.core.management import utils; print(utils.get_random_secret_key())')

eval $(op signin my)

ENV_FILE="${PROJECT_ID}.env"




if [ -f $ENV_FILE ];
then
  echo "${textgreen}loading env file $ENV_FILE ${textreset}"
  source $ENV_FILE
fi

echo "${textblue}Reading environment and project ID${textreset}"
export ENVIRONMENT
export PROJECT_ID



CLOUD_SQL_SERVICE_ACCOUNT_ID=${PROJECT_ID}-cloud-sql
CLOUD_SQL_SERVICE_ACCOUNT_NAME=${CLOUD_SQL_SERVICE_ACCOUNT_ID}@${PROJECT_ID}.iam.gserviceaccount.com

gcloud components update


echo "${textgreen}Enabling services ${textreset}"
gcloud services enable appengine.googleapis.com
gcloud services enable sql-component.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable redis.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable vpcaccess.googleapis.com

echo "${textgreen}Creating App Engine project ${textreset}"
gcloud app create

echo "${textgreen}Creating tiny cloud sql instance: ${textreset}"
gcloud sql instances create $PROJECT_ID \
--database-version=POSTGRES_13 \
--cpu=2 \
--memory=7680MB \
--region=us-west4


echo "${textgreen}Setting the password for the 'postgres' user: ${textreset}"
gcloud sql users set-password postgres \
--instance=$PROJECT_ID \
--password=${POSTGRES_ROOT_PASSWORD}


echo "${textgreen}Creating peerlogic database: ${textreset}"
gcloud sql databases create peerlogic \
--instance=$PROJECT_ID


echo "${textblue}Reading cloud sql connection name${textreset}"
CLOUDSQL_CONNECTION_NAME=$(gcloud sql instances describe $PROJECT_ID --format "value(connectionName)")

export CLOUDSQL_CONNECTION_NAME




echo "${textgreen}Creating cloud sql service account${textreset}"
gcloud iam service-accounts create $CLOUD_SQL_SERVICE_ACCOUNT_ID \
    --display-name="${PROJECT_ID}"


echo "${textgreen}Adding Cloud SQL roles${textreset}"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUD_SQL_SERVICE_ACCOUNT_NAME}" \
    --role="roles/cloudsql.client"

echo "${textgreen}Adding Cloudbuild roles${textreset}"
gcloud projects add-iam-policy-binding $PROJECT_ID \
      --member="serviceAccount:${CLOUDBUILD_SERVICE_ACCOUNT}" \
      --role="roles/secretmanager.secretAccessor"
gcloud projects add-iam-policy-binding $PROJECT_ID \
      --member="serviceAccount:${CLOUDBUILD_SERVICE_ACCOUNT}" \
      --role="roles/appengine.serviceAdmin"
gcloud projects add-iam-policy-binding $PROJECT_ID \
      --member="serviceAccount:${CLOUDBUILD_SERVICE_ACCOUNT}" \
      --role="roles/iam.serviceAccountUser"

echo "${textgreen}Adding App engine roles${textreset}"
gcloud secrets add-iam-policy-binding peerlogic-api-env \
    --member="serviceAccount:${APP_ENGINE_SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"

echo "${textgreen}Creating redis instance${textreset}"
gcloud redis instances create peerlogic-api --size=2 --region=us-west4

echo "${textblue}Reading redis url${textreset}"
REDIS_IP_RANGE=$(gcloud redis instances describe peerlogic-api --region=us-west4 --format "value(
reservedIpRange)")
REDIS_PORT=$(gcloud redis instances describe peerlogic-api --region=us-west4 --format "value(port)")
REDIS_IP=${REDIS_IP_RANGE%/*}

export REDIS_URL="redis://${REDIS_IP}:${REDIS_PORT}/0"

# example connector name: peerlogic-api-dev-redis-to-shared-vpc-connector


# TODO: connect redis
# gcloud redis instances describe peerlogic-api --region=us-west4
# gcloud compute networks vpc-access connectors create redis-to-shared-vpc-connector \
# --region="${REGION}" \
# --subnet="${SUBNET}" \
# --subnet-project="${HOST_PROJECT_ID}" \
# --min-instances=2 \
# --max-instances=10 \
# --machine-type=e2-micro

# gcloud compute networks vpc-access connectors describe redis-to-shared-vpc-connector \
# --region $REGION


echo "${textgreen}Creating cloud build trigger using branch name app-engine to start${textreset}"
gcloud beta builds triggers create app-engine \
--repo=peerlogic-api \
--branch-pattern=^app-engine$ \
--build-config=deployment/app_engine/cloudbuild.yaml \
--service-account="${CLOUDBUILD_SERVICE_ACCOUNT}"

# TODO: Add substitutions

# TODO: custom domain mapping


echo "${textpurple} TO FINISH:"
echo "1. Place a  ${PROJECT_ID}.env into deployment/ directory,"
echo "2. Be sure to escape certain key value pairs in the ${PROJECT_ID}.env that have special characters in them"
echo "3. Make sure to run cloud_sql_proxy.bash in one terminal and in a separate terminal, run ./deployment/psql_deploy.bash to finish up the process.${textreset}"