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
