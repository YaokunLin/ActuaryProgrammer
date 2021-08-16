#!/bin/bash
PROJECT_ID=$(gcloud config list --format='value(core.project)')
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

ENVIRONMENT=$1
ENV_FILE="${ENVIRONMENT}.env"

echo $ENV_FILE

if [ $# -eq 0 ];
then
    echo "please specify the following for environment as an argument: stage | prod"
    exit 1
fi

if [ -f $ENV_FILE ];
then
  echo "loading env file"
  source $ENV_FILE
fi

psql --host 127.0.0.1 --user postgres --password ${POSTGRES_ROOT_PASSWORD} -c "CREATE DATABASE peerlogic;"
psql --host 127.0.0.1 --user postgres --password ${POSTGRES_ROOT_PASSWORD} -c "CREATE USER peerlogic WITH PASSWORD '${POSTGRES_PEERLOGIC_PASSWORD}';"
psql --host 127.0.0.1 --user postgres --password ${POSTGRES_ROOT_PASSWORD} -c "GRANT ALL PRIVILEGES ON DATABASE peerlogic TO peerlogic;"
psql --host 127.0.0.1 --user postgres --password ${POSTGRES_ROOT_PASSWORD}-c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO peerlogic;"
 