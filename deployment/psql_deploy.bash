#!/bin/bash
PROJECT_ID=$(gcloud config list --format='value(core.project)')
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

ENV_FILE="deployment/${PROJECT_ID}.env"

echo $ENV_FILE


textred=$(tput setaf 1) # Red
textgreen=$(tput setaf 2) # Green
textylw=$(tput setaf 3) # Yellow
textblue=$(tput setaf 4) # Blue
textpur=$(tput setaf 5) # Purple
textcyn=$(tput setaf 6) # Cyan
textwht=$(tput setaf 7) # White
textreset=$(tput sgr0) # Text reset.


if [ -f $ENV_FILE ];
then
  echo "${textblue}Loading env file $ENV_FILE ${textreset}"
  source $ENV_FILE
fi


echo "${textblue}Granting privileges to peerlogic user $ENV_FILE ${textreset}"
PGPASSWORD=${POSTGRES_ROOT_PASSWORD} psql --host 127.0.0.1 --user postgres -c "GRANT ALL PRIVILEGES ON DATABASE peerlogic TO peerlogic;"
PGPASSWORD=${POSTGRES_ROOT_PASSWORD} psql --host 127.0.0.1 --user postgres -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO peerlogic;"
 