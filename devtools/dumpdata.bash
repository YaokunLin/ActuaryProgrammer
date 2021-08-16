#!/bin/bash

# run this from the root of the directory, like ./devtools/dumpdata.bash

APPS=( "core" "django_celery_beat" "reminders" )
 
for i in "${APPS[@]}"
do
    echo "Generating fixtures for ${i}"
    docker-compose -f cloudsql-docker-compose.yml run api python3 manage.py dumpdata ${i} --indent 2 -o fixtures/${i}.json
done