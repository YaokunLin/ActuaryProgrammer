# Poetry

## Installation (OSX)

Disclaimer: This is a work in progress and we do not have prebuilt wheels for google libs and psycopg2 so there is a bit of extra work involved for now, especially on ARM hardware.

Poetry brings with it lots of benefits for deterministic deploys, etc. For now, we're only leveraging it for local development, but we may in the future update our dockerfile to leverage it therein.

We will still run dependencies (postgres, redis, etc.) locally with docker compose.

You will need to have the following installed. Be sure to follow prompts and put appropriate things on your PATH and in your .zshrc/.zprofile., brew, pyenv, and the appropriate python version (3.7.9 at time of writing) via pyenv installed if you don't already:

### Xcode Command Line Tools

```bash
xcode-select --install
```

### Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Pyenv

```bash
brew install pyenv
```

Appropriate python version via Pyenv (3.7.9 at time of writing)

```bash
pyenv install 3.7.9
```

It may not be possible to install the python version above.

```bash
pyenv install 3.7.12
```

to check installed version of python through pyenv run;

```bash
pyenv versions
```

Before continuing, it is necessary to ensure your python version is correct and use pyenv. Run the following commands in the root of your directory.

```bash
which python
```

This will check if you are running pyenv; you should see `/Users/<name>/.pyenv/shims/python`

```bash
python --version
```

This will check the version of python you are running. You should see python set to 3.7.9 or 3.7.12, respectively; if not, set to one of the two versions. You need to run one of the following commands.

```bash
pyenv local 3.7.12
pyenv local 3.7.9
```

### install and use Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

if the install above does't work, or if you just want more information about poetry you can visit [https://python-poetry.org/docs/]

### using poetry to set up virtual environment

Tell poetry to honor your pyenv version:
```bash
poetry config virtualenvs.prefer-active-python true
```

When using the appropriate version of python you can run the following command which will create a virtual env via poetry for you.

```bash
poetry install
```

(Optional) To get into a shell for this virtual environment, just run:

```bash
poetry shell
```

Once your poetry environment is all set up, you can set your IDE's python interpreter to the virtual environment that Poetry created.
Instructions will vary per IDE.


To run postgres and redis, run the following separately:

```bash
docker-compose up -d redis postgres
```

### Updating dependencies

> :warning: **NEVER MANUALLY CHANGE poetry.lock, and try to avoid manually changing `tool.poetry` sections in pyproject.toml**
To update, remove and install dependencies, use the poetry CLI [add](https://python-poetry.org/docs/cli/#add) and [remove](https://python-poetry.org/docs/cli/#remove)
If it is a development-only dependency, ensure you use `--dev`!

### Pre-commit Hooks

We have pre-commit hooks which execute inside of the poetry environment for consistency. If you'd like to enable them, just run:

```bash
pre-commit install
```

If for any reason you run into issues with these that you can't sort out, getting around them is as easy as:

```bash
pre-commit uninstall
```

### Just-for-now Stuff (especially for ARM Mac users)

Since we don't have prebuilt wheels, you'll have a few extra steps to get up and running.

Ensure the following environment variables are set (~/.zshrc probably):

```bash
export LDFLAGS="-L/opt/homebrew/opt/openssl@1.1/lib"
export CPPFLAGS="-I/opt/homebrew/opt/openssl@1.1/include"
export GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=1
export GRPC_PYTHON_BUILD_SYSTEM_ZLIB=1
```

Some of the google libs require a rust compiler.

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Psycopg2 requires some other host dependencies:

```bash
brew install postgresql
brew install openssl
brew link openssl
```

As always, follow any prompts/instructions from the output of those commands above.

Once of all that is done (and your active shell reflects the changes), you should be all ready `poetry install`!


## Recreating Poetry Environment
In case of an emergency and you need to start fresh, follow these steps

# Stop the current virtualenv if active or alternative use `exit` to exit from a Poetry shell session

```bash
deactivate
```

# Remove all the files of the current environment of the folder we are in

```bash
POETRY_LOCATION=`poetry env info -p`
echo "Poetry is $POETRY_LOCATION"
rm -rf "$POETRY_LOCATION"
```

# Reactivate Poetry shell
```bash
poetry shell
```

# Install everything
```bash
poetry install
```
