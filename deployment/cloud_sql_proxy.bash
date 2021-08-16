
PROJECT_ID=$(gcloud config list --format='value(core.project)')

gcloud services enable sqladmin.googleapis.com
#CLOUDSQL_CONNECTION_NAME=$(gcloud sql instances describe ${PROJECT_ID} --format "value(connectionName)")

# TODO: remove
CLOUDSQL_CONNECTION_NAME=$(gcloud sql instances describe peerlogic-dev --format "value(connectionName)")


./cloud_sql_proxy -instances=${CLOUDSQL_CONNECTION_NAME}=tcp:5432