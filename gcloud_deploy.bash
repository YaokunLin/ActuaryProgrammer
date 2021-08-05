#!/bin/bash
KUBERNETES_BASE_DIR="./kubernetes/base"
PROJECT_ID=$(gcloud config list --format='value(core.project)')
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
DOCKER_REPO="gcr.io/${PROJECT_ID}/peerlogic-api"
CLOUDBUILD_SERVICE_ACCOUNT="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

if [ -z $VIRTUAL_ENV ];
then
  echo "Error: please activate a virtual environment before running this script"
  exit 1
fi

DJANGO_SECRET_KEY=$(python3 -c 'from django.core.management import utils; print(utils.get_random_secret_key())')

echo $ENV_FILE

if [ $# -eq 0 ];
then
  echo "Error: please specify the following for environment as an argument: stage | prod"
  exit 1
fi

ENVIRONMENT=$1
ENV_FILE="${ENVIRONMENT}.env"
KUBERNETES_OVERLAY_DIR="./kubernetes/overlays/${ENVIRONMENT}"
KUBERNETES_ENV_FILE="${KUBERNETES_OVERLAY_DIR}/${ENVIRONMENT}.env"

export DOCKER_REPO
envsubst < "$KUBERNETES_BASE_DIR/peerlogic-api-deployment.yaml" > "$KUBERNETES_OVERLAY_DIR/peerlogic-api-deployment.yaml"


echo "project_id=\"$PROJECT_ID\"" >> $KUBERNETES_ENV_FILE
echo "environment=\"$ENVIRONMENT\"" >> $KUBERNETES_ENV_FILE


if [ -f $ENV_FILE ];
then
  echo "loading env file"
  source $ENV_FILE
fi



SERVICE_ACCOUNT_ID=${PROJECT_ID}-cloud-sql
SERVICE_ACCOUNT_NAME=${SERVICE_ACCOUNT_ID}@${PROJECT_ID}.iam.gserviceaccount.com

# # enable services
# gcloud services enable sql-component.googleapis.com
# gcloud services enable sqladmin.googleapis.com
# gcloud services enable compute.googleapis.com
# gcloud services enable container.googleapis.com
# gcloud services enable redis.googleapis.com
# gcloud services enable cloudbuild.googleapis.com
# gcloud services enable dns.googleapis.com

# # Cloud SQL
# # Start with a tiny instance. We can ramp it up when we have customers on it.
# gcloud sql instances create ${PROJECT_ID} \
# --database-version=POSTGRES_13 \
# --cpu=2 \
# --memory=7680MB \
# --region=us-west4

# echo "Setting the password for the 'postgres' user:"
# gcloud sql users set-password postgres \
# --instance=${PROJECT_ID} \
# --password=${POSTGRES_ROOT_PASSWORD}

CLOUDSQL_CONNECTION_NAME=$(gcloud sql instances describe ${PROJECT_ID} --format "value(connectionName)")

echo "cloudsql_connection_name=\"${CLOUDSQL_CONNECTION_NAME}\"" >> $KUBERNETES_ENV_FILE

export CLOUDSQL_CONNECTION_NAME
envsubst < "$KUBERNETES_BASE_DIR/cloudsql.yaml" > "$KUBERNETES_OVERLAY_DIR/cloudsql.yaml"



# echo "Start cloud_sql_proxy in a new window and continue to the next script - psql_deploy.bash"

 


# # Service Accounts


# gcloud iam service-accounts create $SERVICE_ACCOUNT_ID \
#     --display-name="${PROJECT_ID}"


# gcloud projects add-iam-policy-binding $PROJECT_ID \
#     --member="serviceAccount:${SERVICE_ACCOUNT_NAME}" \
#     --role="roles/cloudsql.client"

# gcloud projects add-iam-policy-binding $PROJECT_ID \
#       --member="serviceAccount:${CLOUDBUILD_SERVICE_ACCOUNT}" \
#       --role="roles/container.developer"

# gcloud iam service-accounts keys create key-file \
#     --iam-account="${SERVICE_ACCOUNT_NAME}"
# cat key-file | op create document - --title "${ENVIRONMENT} ${SERVICE_ACCOUNT_NAME} - key-file" --vault wlmpasbyyncmhpjji3lfc7ra4a



# gsutil mb gs://${PROJECT_ID}
# gsutil defacl set public-read gs://${PROJECT_ID}

# # Cloudbuild takes care of the rest - collectstatic

# gcloud container clusters create peerlogic-api \
#   --scopes "https://www.googleapis.com/auth/userinfo.email","cloud-platform" \
#   --num-nodes 4 --zone $ZONE \
#   --enable-ip-alias

# gcloud container clusters get-credentials peerlogic-api --zone $ZONE


# # Kubectl secrets




# kubectl create secret generic cloudsql-oauth-credentials --from-file=credentials.json=key-file
# kubectl create secret generic cloudsql --from-literal=POSTGRES_DB=peerlogic \
#     --from-literal=POSTGRES_USER=peerlogic \
#     --from-literal=POSTGRES_PASSWORD=${POSTGRES_PEERLOGIC_PASSWORD}
# kubectl create secret generic django --from-literal=DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
# kubectl create secret generic netsapiens --from-literal=NETSAPIENS_CLIENT_SECRET=${NETSAPIENS_CLIENT_SECRET} \
# --from-literal=NETSAPIENS_API_USERNAME=${NETSAPIENS_API_USERNAME} \
# --from-literal=NETSAPIENS_API_PASSWORD=${NETSAPIENS_API_PASSWORD}

# # Redis
# gcloud redis instances create peerlogic-api --size=2 --region=us-west4
REDIS_IP_RANGE=$(gcloud redis instances describe peerlogic-api --region=us-west4 --format "value(
reservedIpRange)")
REDIS_PORT=$(gcloud redis instances describe peerlogic-api --region=us-west4 --format "value(port)")
REDIS_IP=${REDIS_IP_RANGE%/*}


echo "redis_url=\"redis://${REDIS_IP}:${REDIS_PORT}/0\"" >> $KUBERNETES_ENV_FILE


# # Reserve a static IP
# gcloud compute addresses create $PROJECT_ID --global
# ADDRESS=$(gcloud compute addresses describe $PROJECT_ID --global \
#     |grep 'address:' |  awk -F: '{print $2}')

# echo "Assigning $DOMAIN_NAME to ADDRESS: $ADDRESS"



# # Create A-record using gcloud

# gcloud dns --project=peerlogic-dns record-sets transaction start \
#     --zone=peerlogic-tech

# gcloud dns --project=peerlogic-dns record-sets transaction add $ADDRESS \
#     --name=${DOMAIN_NAME}. \
#     --ttl=300 \
#     --type=A \
#     --zone=peerlogic-tech

# gcloud dns --project=peerlogic-dns record-sets transaction execute \
#     --zone=peerlogic-tech

echo "Domain name ${DOMAIN_NAME} is propagating. All set!"


# gcloud builds submit --project=$PROJECT_ID --config cloudbuild.yaml \
#   --substitutions "_DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY},_POSTGRES_USER=peerlogic,_POSTGRES_DB=peerlogic,_POSTGRES_PASSWORD=${_POSTGRES_PEERLOGIC_PASSWORD},_DOCKER_REPO=${DOCKER_REPO}"


# TODO: eventually apply kustomize substitutions
# kubectl apply -k ./kubernetes/overlays/stage