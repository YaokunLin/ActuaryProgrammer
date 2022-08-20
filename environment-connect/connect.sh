#!/bin/bash
#set -x # echo on

# 1. Initialize gcloud configuration: gcloud init a new configuration called peerlogic-api-dev if you haven't already done so before
# 2. Change env_file in ./environment-connect/cloudsql-docker-compose.yml to point at .env.<env>, i.e. .env.stage
# 2. Build: docker-compose -f ./environment-connect/cloudsql-docker-compose.yml up --build
# 3. Run: ./environment-connect/connect.sh dev <rest-of-command-for-container> from the root of the peerlogic-api repo.

ENVIRONMENT=$1
shift

echo "$@"

COMMAND=$@

OUTPUT_FILENAME=$(echo $COMMAND| tr -dc '[:alnum:]\n\r' | tr '[:upper:]' '[:lower:]')

gcloud config configurations activate peerlogic-api-$ENVIRONMENT

# TODO: supply env-file, haven't gotten it to work yet. See above step 2
docker-compose -f ./environment-connect/cloudsql-docker-compose.yml $COMMAND 2>&1 | tee ./environment-connect/logs/$OUTPUT_FILENAME.txt
