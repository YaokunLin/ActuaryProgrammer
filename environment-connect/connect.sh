#!/bin/bash
#set -x # echo on

# 1. Initialize gcloud configuration: gcloud init a new configuration called peerlogic-api-dev if you haven't already done so before
# 2. Build: docker-compose -f ./environment-connect/cloudsql-docker-compose.yml up --build
# 3. Run: ./environment-connect/connect.sh dev <rest-of-command-for-container> from the root of the peerlogic-api repo.

ENVIRONMENT=$1
shift

echo "$@"

COMMAND=$@

gcloud config configurations activate peerlogic-api-$ENVIRONMENT

docker-compose -f ./environment-connect/cloudsql-docker-compose.yml run api $COMMAND
