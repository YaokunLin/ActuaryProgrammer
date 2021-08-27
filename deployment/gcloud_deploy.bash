#!/bin/bash
KUBERNETES_BASE_DIR="./kubernetes/base"
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



KUBERNETES_OVERLAY_DIR="./kubernetes/overlays/${PROJECT_ID}"
KUBERNETES_ENV_FILE="${KUBERNETES_OVERLAY_DIR}/.env"

rm -f $KUBERNETES_ENV_FILE
touch $KUBERNETES_ENV_FILE

echo "${textblue}Reading environment and project ID for kube cluster${textreset}"
export ENVIRONMENT
export PROJECT_ID

envsubst < "${KUBERNETES_BASE_DIR}/peerlogic-api-deployment.yaml" > "${KUBERNETES_OVERLAY_DIR}/peerlogic-api-deployment.yaml"


CLOUD_SQL_SERVICE_ACCOUNT_ID=${PROJECT_ID}-cloud-sql
CLOUD_SQL_SERVICE_ACCOUNT_NAME=${CLOUD_SQL_SERVICE_ACCOUNT_ID}@${PROJECT_ID}.iam.gserviceaccount.com



echo "${textgreen}Enabling services ${textreset}"
gcloud services enable sql-component.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable container.googleapis.com
gcloud services enable redis.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable dns.googleapis.com
gcloud services enable secretmanager.googleapis.com


echo "${textgreen}Creating tiny cloud sql instance:"
gcloud sql instances create $PROJECT_ID \
--database-version=POSTGRES_13 \
--cpu=2 \
--memory=7680MB \
--region=us-west4


echo "${textgreen}Setting the password for the 'postgres' user:"
gcloud sql users set-password postgres \
--instance=$PROJECT_ID \
--password=${POSTGRES_ROOT_PASSWORD}

echo "${textgreen}Creating peerlogic user:"
gcloud sql users create peerlogic \
--instance=$PROJECT_ID \
--password=${POSTGRES_PEERLOGIC_PASSWORD}


echo "${textgreen}Creating peerlogic database:"
gcloud sql databases create peerlogic \
--instance=$PROJECT_ID


echo "${textblue}Reading cloud sql connection name for kube cluster${textreset}"
CLOUDSQL_CONNECTION_NAME=$(gcloud sql instances describe $PROJECT_ID --format "value(connectionName)")

export CLOUDSQL_CONNECTION_NAME




echo "${textgreen}Creating cloud sql service account${textreset}"
gcloud iam service-accounts create $CLOUD_SQL_SERVICE_ACCOUNT_ID \
    --display-name="${PROJECT_ID}"


echo "${textgreen}Adding Cloud SQL roles${textreset}"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUD_SQL_SERVICE_ACCOUNT_NAME}" \
    --role="roles/cloudsql.client"


echo "${textgreen}Creating key file for cloud sql service account${textreset}"
gcloud iam service-accounts keys create key-file \
    --iam-account="${CLOUD_SQL_SERVICE_ACCOUNT_NAME}"

echo "${textgreen}Adding Key file to 1Password${textreset}"
cat key-file | op create document - --title "${ENVIRONMENT} ${CLOUD_SQL_SERVICE_ACCOUNT_NAME} - key-file" --vault $VAULT_ID



echo "${textgreen}Adding Cloud Build roles${textreset}"
gcloud projects add-iam-policy-binding $PROJECT_ID \
      --member="serviceAccount:${CLOUDBUILD_SERVICE_ACCOUNT}" \
      --role="roles/container.developer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
      --member="serviceAccount:${CLOUDBUILD_SERVICE_ACCOUNT}" \
      --role="roles/secretmanager.secretAccessor"



echo "${textgreen}Create cloud storage bucket for Django static resources${textreset}"
gsutil mb gs://${PROJECT_ID}
gsutil defacl set public-read gs://${PROJECT_ID}


echo "${textgreen}Create cluster${textreset}"
gcloud container clusters create peerlogic-api \
  --scopes "https://www.googleapis.com/auth/userinfo.email","cloud-platform" \
  --num-nodes 2 --zone $ZONE \
  --enable-ip-alias

gcloud container clusters get-credentials peerlogic-api --zone $ZONE



echo "${textgreen}Creating kubectl secrets${textreset}"
kubectl create secret generic cloudsql-oauth-credentials --from-file=credentials.json=key-file
kubectl create secret generic cloudsql --from-literal=POSTGRES_DB=peerlogic \
    --from-literal=POSTGRES_USER=peerlogic \
    --from-literal=POSTGRES_PASSWORD=${POSTGRES_PEERLOGIC_PASSWORD}
kubectl create secret generic django --from-literal=DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
kubectl create secret generic netsapiens --from-literal=NETSAPIENS_CLIENT_SECRET=${NETSAPIENS_CLIENT_SECRET} \
--from-literal=NETSAPIENS_API_USERNAME=${NETSAPIENS_API_USERNAME} \
--from-literal=NETSAPIENS_API_PASSWORD=${NETSAPIENS_API_PASSWORD}


echo "${textgreen}Creating redis instance${textreset}"
gcloud redis instances create peerlogic-api --size=2 --region=us-west4

echo "${textblue}Reading redis url for kube cluster${textreset}"
REDIS_IP_RANGE=$(gcloud redis instances describe peerlogic-api --region=us-west4 --format "value(
reservedIpRange)")
REDIS_PORT=$(gcloud redis instances describe peerlogic-api --region=us-west4 --format "value(port)")
REDIS_IP=${REDIS_IP_RANGE%/*}

export REDIS_URL="redis://${REDIS_IP}:${REDIS_PORT}/0"



echo "${textgreen}Reserving static IP address${textreset}"
gcloud compute addresses create $PROJECT_ID --global
ADDRESS=$(gcloud compute addresses describe $PROJECT_ID --global --format "value(address)")

echo "${textgreen}Assigning $DOMAIN_NAME to ADDRESS: $ADDRESS  ${textreset}"


echo "${textgreen}Create A-record using gcloud${textreset}"
gcloud dns --project=peerlogic-dns record-sets transaction start \
    --zone=peerlogic-tech

gcloud dns --project=peerlogic-dns record-sets transaction add $ADDRESS \
    --name=${DOMAIN_NAME}. \
    --ttl=300 \
    --type=A \
    --zone=peerlogic-tech

gcloud dns --project=peerlogic-dns record-sets transaction execute \
    --zone=peerlogic-tech

echo "${textgreen}Domain name ${DOMAIN_NAME} is propagating. All set! ${textreset}"


envsubst < "$KUBERNETES_BASE_DIR/cloudsql.yaml" > "$KUBERNETES_OVERLAY_DIR/cloudsql.yaml"
envsubst < "$KUBERNETES_BASE_DIR/configmap.yaml" > "$KUBERNETES_OVERLAY_DIR/configmap.yaml"


# TODO: get cloud build to work someday
# cd ..
# gcloud builds submit --project=$PROJECT_ID --config ./cloudbuild.yaml \
#   --substitutions "_DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY},_POSTGRES_USER=peerlogic,_POSTGRES_DB=peerlogic,_POSTGRES_PASSWORD=${POSTGRES_PEERLOGIC_PASSWORD},_DOCKER_REPO=${DOCKER_REPO}"


echo "${textgreen}Start cloud_sql_proxy.bash in a new window and continue to the next script - psql_deploy.bash ${textreset}"


kustomize build $KUBERNETES_OVERLAY_DIR |\
     kubectl apply -f -