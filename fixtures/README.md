# Fixtures

## Load Fixtures

```bash
docker-compose run --rm  api python3 manage.py loaddata -i fixtures/core.json fixtures/netsapiens_integration.json fixtures/netsapiens_integration_event_extracts.json fixtures/netsapiens_integration_cdr2_extracts.json
docker-compose run --rm  api python3 manage.py loaddata -i fixtures/calls_ctps.json fixtures/calls_caps.json
docker-compose run --rm  api python3 manage.py loaddata -i fixtures/calls_calltranscript.json fixtures/calls_callaudio.json
```

## Generate more Fixtures when needed

Requirements:
* First, you must be a devops admin to generate these because there is a lot that could go wrong if you are pointed at the wrong environment.
* Second, see Running Management Commands on the root README.md to connect with the production database.

How to generate more fixtures:

```bash
docker-compose run --rm  api python3 manage.py loaddata -i fixtures/core.json
docker-compose -f ./devtools/cloudsql-docker-compose.yml run --rm  api python3 manage.py dumpdata --indent 2 netsapiens_integration.NetsapiensAPICredentials -o .credentials/netsapiens_integration_api_credentials.json
docker-compose -f ./devtools/cloudsql-docker-compose.yml run --rm  api python3 manage.py dumpdata --indent 2 netsapiens_integration.NetsapiensCallSubscription -o fixtures/netsapiens_integration.json
docker-compose -f ./devtools/cloudsql-docker-compose.yml run --rm  api python3 manage.py dump_object netsapiens_integration.NetsapiensCallSubscriptionEventExtract GUFpaWwv3HEoWxRdkFrxwB 77ioYZWqUZT6xQqLzJhuAU bM2bGvuzeGG4aJ6esswqCx TztfY2RtavnF3TJcRTcE8n NEihQUCNDHv4EtTS4VoEnc 4Sg38hjfF93Lyk9JK28tCK 5X4pw5GmwRKFUG8UUQnWPS CdPWAadQzziE4DF7Wnzys2 GQmZjtHQzp5nvf4puHYZwU dFXGDZatVJtinNt7CMoh7A imz9uja3Lh8k3U5SajR96m dSWcM59yBd8qs7uKsBfvQL > fixtures/netsapiens_integration_event_extracts.json
# remove all system warnings from file before continuing
docker-compose -f ./devtools/cloudsql-docker-compose.yml run --rm  api python3 manage.py dump_object netsapiens_integration.NetsapiensCdr2Extract MkrpWrbzfkhxsehqppHURq > fixtures/netsapiens_integration_cdr2_extracts.json
# remove all system warnings before continuing
/devtools/cloudsql-docker-compose.yml run --rm  api python3 manage.py dump_object calls.CallAudioPartial JHx3BbihjXuZaBQp6BVkYd > fixtures/calls_caps.json
# remove all system warnings before continuing
/devtools/cloudsql-docker-compose.yml run --rm  api python3 manage.py dump_object calls.CallTranscriptPartial WttwSMbBdqmjdUkZKfs6EV buzJhDKf8cqGxHPk59yEtN R3LputDNYXWkV9zLYsZnfN > fixtures/calls_ctps.json
# remove all system warnings before continuing
docker-compose -f ./devtools/cloudsql-docker-compose.yml run --rm  api python3 manage.py dump_object calls.CallAudio mCHXcnfKxvGXFx7dpEmq9A > fixtures/calls_callaudio.json
# remove all system warnings before continuing
./devtools/cloudsql-docker-compose.yml run --rm  api python3 manage.py dump_object calls.CallTranscript WbtxpYUXqupNfNApktyy2D 9DwQJmcBnGoPRR6rimkdSM MhdCXmPQDu2e7wU7KWHLuW > fixtures/calls_calltranscript.json
# remove all system warnings before continuing
```