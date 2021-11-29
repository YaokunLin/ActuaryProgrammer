#!/bin/bash
PROJECT_ID=$(gcloud config list --format='value(core.project)')
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
DOCKER_REPO="gcr.io/${PROJECT_ID}/peerlogic-api"
CLOUDBUILD_SERVICE_ACCOUNT="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
VAULT_ID="wlmpasbyyncmhpjji3lfc7ra4a"

textred=$(tput setaf 1) # Red
textgreen=$(tput setaf 2) # Green
textylw=$(tput setaf 3) # Yellow
textblue=$(tput setaf 4) # Blue
textpur=$(tput setaf 5) # Purple
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

export DOCKER_REPO
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



echo "${textgreen}Enabling services ${textreset}"
gcloud services enable appengine.googleapis.com
gcloud services enable sql-component.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable redis.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com


# echo "${textgreen}Creating App Engine project ${textreset}"
# gcloud app create

# echo "${textgreen}Creating tiny cloud sql instance:"
# gcloud sql instances create $PROJECT_ID \
# --database-version=POSTGRES_13 \
# --cpu=2 \
# --memory=7680MB \
# --region=us-west4


# echo "${textgreen}Setting the password for the 'postgres' user:"
# gcloud sql users set-password postgres \
# --instance=$PROJECT_ID \
# --password=${POSTGRES_ROOT_PASSWORD}

# echo "${textgreen}Creating peerlogic user:"
# gcloud sql users create peerlogic \
# --instance=$PROJECT_ID \
# --password=${POSTGRES_PEERLOGIC_PASSWORD}


# echo "${textgreen}Creating peerlogic database:"
# gcloud sql databases create peerlogic \
# --instance=$PROJECT_ID


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


# echo "${textgreen}Creating redis instance${textreset}"
# gcloud redis instances create peerlogic-api --size=2 --region=us-west4

# echo "${textblue}Reading redis url${textreset}"
# REDIS_IP_RANGE=$(gcloud redis instances describe peerlogic-api --region=us-west4 --format "value(
# reservedIpRange)")
# REDIS_PORT=$(gcloud redis instances describe peerlogic-api --region=us-west4 --format "value(port)")
# REDIS_IP=${REDIS_IP_RANGE%/*}

# export REDIS_URL="redis://${REDIS_IP}:${REDIS_PORT}/0"



# echo "${textgreen}Reserving static IP address${textreset}"
# gcloud compute addresses create $PROJECT_ID --global
# ADDRESS=$(gcloud compute addresses describe $PROJECT_ID --global --format "value(address)")

# echo "${textgreen}Assigning $DOMAIN_NAME to ADDRESS: $ADDRESS  ${textreset}"


# echo "${textgreen}Create A-record using gcloud${textreset}"
# gcloud dns --project=peerlogic-dns record-sets transaction start \
#     --zone=peerlogic-tech

# gcloud dns --project=peerlogic-dns record-sets transaction add $ADDRESS \
#     --name=${DOMAIN_NAME}. \
#     --ttl=300 \
#     --type=A \
#     --zone=peerlogic-tech

# gcloud dns --project=peerlogic-dns record-sets transaction execute \
#     --zone=peerlogic-tech

# echo "${textgreen}Domain name ${DOMAIN_NAME} is propagating. All set! ${textreset}"

