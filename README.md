# Peerlogic API

## Docs
- [Getting started running the app locally with Poetry](docs/POETRY_README.md)
- [Cloud Functions](docs/CLOUD_FUNCTION_README.md)
- [SolveStack](docs/SOLVESTACK_README.md)

## Docker

Make sure to run these commands from the root of the project.

### Initial setup

Solvestack Meetup folks - use SOLVESTACK_README.md instead for this section.

Create a new file in the root of the peerlogic-api directory called `.env`.

Paste the contents of this 1Password secret into the `.env` file

See 1Password for a starter
file: [peerlogic-api LOCAL  starter .env file](https://start.1password.com/open/i?a=P3RU52IFYBEH3GKEDF2UBYENBQ&v=wlmpasbyyncmhpjji3lfc7ra4a&i=2swwri27d5bztnkq223yypxdvy&h=my.1password.com)

### Docker commands

Run the following to initialize Postgres and create the peerlogic database, without tables:

```bash
docker-compose up -d postgres
```

Apply the structure of the tables to the database.

```bash
docker-compose up migrate
```

Add the super user with username of `admin` and password of `password`, set by .env file. This can be done at any time / multiple times if needed.

.env file defaults:

```bash
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_PASSWORD=password
```

```bash
docker-compose run api python3 manage.py createsuperuser --noinput
```

After initial build and api and postgres are running, start it all up:

`docker-compose up`

Now it's time to [load data into your local database](fixtures/README.md)

Auth0 Association:

Find your user with @peerlogic.com in the Auth0 User [Local or Development environment user management dashboard](https://manage.auth0.com/dashboard/us/dev-ea57un9z/users)

Grab your Auth0 user id (copy the entire thing including the `auth0|` prefix).

Other environments:

* [Stage](https://manage.auth0.com/dashboard/us/stage-peerlogic/users)
* [Production](https://manage.auth0.com/dashboard/us/peerlogic/users)
![alt text](docs/auth_setup_1.png "Find your user in the list")

Then, associate your Auth0 User by navigating to the [admin](http://localhost:8000/admin/core/user/). Use your credentials of admin and password set above.

In the DJANGO admin if you're not listed, Add a new user and give your information.

Otherwise, click on your User's ID to edit your information.

* Ensure is_staff or is_superuser is set to True.
* add or update your Auth0 user id copied above into your Django / Peerlogic API user.

Save it.

All done!

### Running/Stopping

Start:
`docker-compose up`

End all processes:
`docker-compose down --remove-orphans`

### Database and Data Schema Creations

`docker-compose run api python3 manage.py makemigrations --name {name}`

### Initializing, Installing, and Migrating

First time?

```bash
python3 -m venv env
```

On both first time and fresh updates, do the following:

```bash
source env/bin/activate # ./env/Scripts/activate on Windows
pip3 install -r requirements/requirements.txt
python manage.py migrate
```

To start the backend:

```bash
source env/bin/activate # ./env/Scripts/activate on Windows
python3 manage.py runserver
```

## Postman Collection

There is a Postman Collection that can be used to validate setup and test changes. Import the following: (Peerlogic API
Collection)[https://www.getpostman.com/collections/c1045d02c72c56abd559]

## Deployment

CI/CD is set up for deploying to development with App Engine.

See `deployment/app_engine/DEPLOYMENT.md` for deploying to another environment with App Engine.

## 1Password sign-in

Set up your CLI tool: [https://support.1password.com/command-line-getting-started/]

Sign in:

[https://support.1password.com/command-line/#sign-in-or-out]

```bash
op signin [<sign_in_address>](https://peerlogic.1password.com/signin) <email_address> <secret_key>
```

eval $(op signin my)

<!-- For MAC:
```bash
echo "1PASSWORD_SHORTHAND=<youroutputtedtokenhere>" >> ~/.bashrc
``` -->

## Running Against Other Environments / Running Management Commands Against Other Environments

### Setup Proxy Access to the Environment

Creation of credentials requires us to be local / on the same network as the environment in question since we're using the ORM to update the database itself directly.

1. Download the appropriate credentials file to access the environment via IAM. Place this file into the ./credentials directory. For accessing the local dev environment, use the [local credentials](https://start.1password.com/open/i?a=P3RU52IFYBEH3GKEDF2UBYENBQ&v=wlmpasbyyncmhpjji3lfc7ra4a&i=hwym3nsqbjfhrjskkfjmvcnq4a&h=my.1password.com). If there is another environment you are trying to access, you'll need to generate an appropriate credentials file for that environment.

2. [install Gcloud](https://cloud.google.com/sdk/docs/install) then Create a google cloud environment.

    Enter this with the appropriate values at the prompts:

    ```bash
    gcloud init
    ```

    When it asks to pick a configuration, select `[2] Create a new configuration`.

    Name it `peerlogic-api-dev`, `peerlogic-api-stage` or `peerlogic-api-prod` depending on which project you choose. Select us-west4a as the Compute Region/Zone.

3. Enter the google cloud environment to access the database with [cloud sql proxy](https://cloud.google.com/sql/docs/mysql/connect-instance-auth-proxy#macos-64-bit)

    ```bash
    ./devtools/cloud_sql_proxy.bash
    ```

### Database Access to the Environment

Google Cloud credentials are necessary to access the database. Your environment file must be setup accordingly.

1. Ensure you have a copy of the appropriate deployment's environment. Use Secret Manager of the appropriate environment to download a copy.

2. In the ./environment-connect/ directory place the downloaded .env file with its environment shorthand as a suffix; such as ./environment-connect/.env.dev for example.

3. Update the .env file to use the google credentials file.

    ```bash
    PROJECT_ID=peerlogic-api-dev # put your env here
    GOOGLE_APPLICATION_CREDENTIALS=.credentials/peerlogic-api-dev-9d33d6f6e911.json  # THIS IS JUST AN EXAMPLE, YOURS WILL BE NAMED DIFFERENTLY.
    ```

4. Change the value in ./environment-connect/cloudsql-docker-compose.yml env_file to point at your `.env.dev`.

5. Build the necessary dependencies in a separate terminal window:

   ```bash
   docker-compose -f ./environment-connect/cloudsql-docker-compose.yml up --build
   ```

6. You can now connect as a server via ./environment-connect/connect.sh dev up, and remember to still run the ./devtools/cloud_sql_proxy.bash as explained in the previous section.

    In fact, you can run any docker commands after `./environment-connect/connect.sh dev`!

7. Allow some amount of time for the API to connect to the remote database. We've seen problems with the gunicorn workers timing out and dying.

    Error seen from clients trying to connect to peerlogic-api:

    ```bash
    "raise ConnectionError(err, request=request) requests.exceptions.ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))"
    ```

    Error seen from peerlogic-api side:

    ```bash
    api_1  | [2022-08-20 22:01:53 +0000] [7] [CRITICAL] WORKER TIMEOUT (pid:20)
    api_1  | [2022-08-20 22:01:53 +0000] [20] [INFO] Worker exiting (pid: 20)
    api_1  | [2022-08-20 22:01:53 +0000] [25] [INFO] Booting worker with pid: 25
    ```

### Management Command - Create Netsapiens subscription

1. Follow above instructions under "Running Management Commands" before continuing.

2. Run the creation command:

    ```bash
    ./environment-connect/connect.sh dev run api python3 manage.py create_netsapiens_integration {peerlogic_root_api_url}, {voip_provider_id}, {practice_name}, {practice_voip_domain}
    ```

    NOTE: double check the peerlogic_root_api_url - make sure you're using one of the following:
    * Dev: https://api.dev.peerlogic.com
    * Stage: https://api.stage.peerlogic.com
    * Prod: https://api.prod.peerlogic.com

    NOT the appspot domains! Deprecated.

    ```bash
    ./environment-connect/connect.sh dev run api python3 manage.py create_netsapiens_integration https://api.prod.peerlogic.com drFoXEnEwrN28Gowp3CoRN "ThunderbirdDentalStudio" dentaldesignstudios_thunderbird
    ```

    If you need spaces in the name, you must change them in the admin for each of the outputted Organization and Practice ids. Say, "ThunderbirdDentalStudio" to "Thunderbird Dental Studio"

### Management Command - Create Client Credential Auth User

1. Follow above instructions under "Running Management Commands" before continuing.

2. Create a client credential / application at [https://peerlogic-api-{rest-of-appspot-baseurl}/oauth/applications/].

    2.a. Take note of the client ID and Secret on the form and add it to 1Password before clicking Save.

    2.b. Client type is "Confidential". Authorization grant type is "Client credentials". Algorithm is "No OIDC Support".
   *NOTE: The moment you click the Save button you will no longer have access to the client secret.*
   *NOTE: For Client type, select Public. Otherwise you will have a bad time.*

3. Run the creation command:

    ```bash
    ./environment-connect/connect.sh dev run api python3 manage.py create_auth0_client_credential_user {name} {client_id}
    ```

    example:

    ```bash
    ./environment-connect/connect.sh dev run api python3 manage.py create_auth0_client_credential_user auth0 NAWAyL0aOx6mw0kzLXXccSTKiSPJ4JqvuLE33qeX
    ```

    Take note of the id.

4. Set the proper secret in Secret Manager for your environment and redeploy the API.
    In the Secret manager you will need to update AUTH0_MACHINE_CLIENT_ID and AUTH0_MACHINE_USER_ID so the mapping can be used when authenticating with client credentials for admin endpoints, like `/api/users`.

5. [Update the Auth0 Custom Action secrets](https://manage.auth0.com/dashboard/us/dev-ea57un9z/actions/library) for `PEERLOGIC_API_CLIENT_ID` `PEERLOGIC_API_CLIENT_SECRET` for the application.

## Troubleshooting

1. Problems with login / authentication endpoint / connecting to Netsapiens.

    Error:

    ```bash
    requests.exceptions.ConnectionError: HTTPSConnectionPool(host=‘core1-phx.peerlogic.com’, port=443): Max retries exceeded with url: /ns-api/oauth2/token/ (Caused by NewConnectionError(‘<urllib3.connection.HTTPSConnection object at 0x7f0f89abedd0>: Failed to establish a new connection: [Errno 110] Connection timed out’))
    ```

    Potential solutions:

    1. Restart Docker.
    2. Update Docker.
    3. Restart your computer.

### Running Test Cases

In pyproject.toml under `tool.pytest.ini_options` you will find `addopts = "-vv -x --lf --cov"`
These are pytest commands that we want to execute when running pytest.

1. `-x`: Will stop running tests once one fails
2. `-vv`: Will display more detail about the failed assertion
3. `--lf`: Runs from the last failed test when running pytest
4. `--cov`: outputs a percentage of covered tests.

We are using the pytest framework for unit and integration tets. In the root of your directory run:

```bash
pytest
```

Running `pytest` in the root of your directory will run the test cases written in `tests/test_api/tests.py` or any other file that starts with "test".
