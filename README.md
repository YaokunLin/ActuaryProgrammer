# Peerlogic API

## Dependencies

# TODO

## Docker

Make sure to run these commands from the root of the project.

### Initial setup

Solvestack Meetup folks - use SOLVESTACK_README.md instead for this section.

Create a new file in the root of the peerlogic-api directory called `.env`.

Paste the contents of this 1Password secret into the `.env` file

See 1Password for a starter
file: [peerlogic-api LOCAL  starter .env file](https://start.1password.com/open/i?a=P3RU52IFYBEH3GKEDF2UBYENBQ&v=wlmpasbyyncmhpjji3lfc7ra4a&i=sxjcghmtefeqvdystb2l6q7k5y&h=my.1password.com)

### Docker commands:

Initialize Postgres and create the peerlogic database, without tables:

```
docker-compose up postgres
```

Apply the structure of the tables to the database.

```
docker-compose up migrate
```

Add the super user with username of `admin` and password of `password`, set by .env file.

```
docker-compose run api python3 manage.py createsuperuser --noinput
```

After initial build and api and postgres are running, start it all up:

`docker-compose up`



<!-- TODO: Generate fixtures to play with locally) -->


All done!

### Running/Stopping

Start:
`docker-compose up`

End all processes:
`docker-compose down --remove-orphans`

### Database and Data Schema Creations

`docker-compose run api python3 manage.py makemigrations --name {name}`

## Run it Locally (w/o Docker)

Not really recommended; docker has been more tested.

### Initializing, Installing, and Migrating:

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

# Postman Collection

There is a Postman Collection that can be used to validate setup and test changes. Import the following: (Peerlogic API
Collection)[https://www.getpostman.com/collections/c1045d02c72c56abd559]

# Deployment

CI/CD is set up for deploying to development with App Engine.

See `deployment/app_engine/DEPLOYMENT.md` for deploying to another environment with App Engine.

# 1Password sign-in

Set up your CLI tool: https://support.1password.com/command-line-getting-started/

Sign in:

https://support.1password.com/command-line/#sign-in-or-out

```bash
op signin [<sign_in_address>](https://peerlogic.1password.com/signin) <email_address> <secret_key>
```

eval $(op signin my)

<!-- For MAC:

```bash
echo "1PASSWORD_SHORTHAND=<youroutputtedtokenhere>" >> ~/.bashrc
``` -->

# Running Management Commands

## Setup Proxy Access to the Environment

Creation of credentials requires us to be local / on the same network as the environment in question since we're using the ORM to update the database itself directly.

1. Download the appropriate credentials file to access the environment via IAM. Place this somewhere that is secure and you won't forget it. You'll need to use this later.

2. Create or activate the google cloud environment

    Either this with the appropriate values at the prompts:

    ```bash
    gcloud init
    ```

    Or this:

    ```bash
    gcloud config configuration activate peerlogic-api-dev
    ```

3. Enter the google cloud environment to access the database with cloud sql proxy

    ```bash
    ./devtools/cloud_sql_proxy.bash
    ```

## Database Access to the Environment

Google Cloud credentials are necessary to access the database. Your environment file must be setup accordingly.

1. Ensure you have a copy of the appropriate deployment's environment. Use Secret Manager of the appropriate environment to download a copy.

2. Backup your local .env

    ```bash
    mv .env .env.local
    ```

3. Rename the environment configuration to .env so you can use it.

    ```bash
    cp .env.dev .env
    ```

4. Update the .env file to use the google credentials file.

    ```bash
    PROJECT_ID=peerlogic-api-dev # put your env here
    GOOGLE_APPLICATION_CREDENTIALS=.credentials/peerlogic-api-dev-9d33d6f6e911.json  # THIS IS JUST AN EXAMPLE, YOURS WILL BE NAMED DIFFERENTLY.
    ```

5. Build the necessary dependencies in a separate terminal window:

   ```bash
   docker-compose -f ./devtools/cloudsql-docker-compose.yml up --build
   ```

## Management Command - Create Netsapiens subscription

1. Follow above instructions under "Running Management Commands" before continuing.

2. Run the creation command:

    ```bash
    docker-compose -f ./devtools/cloudsql-docker-compose.yml run api python3 manage.py create_netsapiens_integration {peerlogic_root_api_url}, {voip_provider_id}, {practice_name}, {practice_voip_domain}
    ```


    NOTE: double check the peerlogic_root_api_url. It's not as easy as just swapping out "dev", "stage", and "prod" as the subdomains themselves are different!

    ```bash
    docker-compose -f ./devtools/cloudsql-docker-compose.yml run api python3 manage.py create_netsapiens_integration https://peerlogic-api-prod.wm.r.appspot.com drFoXEnEwrN28Gowp3CoRN "Thunderbird Dental Studio" dentaldesignstudios_thunderbird
    ```

## Management Command - Create Client Credential Auth User

1. Follow above instructions under "Running Management Commands" before continuing.

2. Create a client credential / application at https://peerlogic-api-{rest-of-appspot-baseurl}/oauth/applications/. Take note of the client ID and Secret on the form and add it to 1Password before clicking Save.
   *NOTE: The moment you click the Save button you will no longer have access to the client secret.*
   *NOTE: For Client type, select Public. Otherwise you will have a bad time.*

3. Run the creation command:

    ```bash
    docker-compose -f ./devtools/cloudsql-docker-compose.yml run api python3 manage.py create_auth0_client_credential_user {name}, {client_id}
    ```

    example:

    ```bash
    docker-compose -f ./devtools/cloudsql-docker-compose.yml run api python3 manage.py create_auth0_client_credential_user auth0 NAWAyL0aOx6mw0kzLXXccSTKiSPJ4JqvuLE33qeX
    ```

    Take note of the id.

4. Set the proper secret in Secret Manager for your environment and redeploy the API.
    In the Secret manager you will need to update AUTH0_MACHINE_CLIENT_ID and AUTH0_MACHINE_USER_ID so the mapping can be used when authenticating with client credentials for admin endpoints, like `/api/users`.

5. [Update the Auth0 Custom Action secrets](https://manage.auth0.com/dashboard/us/dev-ea57un9z/actions/library) for `PEERLOGIC_API_CLIENT_ID` `PEERLOGIC_API_CLIENT_SECRET` for the application.