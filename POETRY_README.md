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

Install the appropriate python version via Pyenv. See pyproject.toml for the latest version (3.7.15 as of 2022-12-01).


```bash
pyenv install 3.7.15
```

Check that this was installed on your system and appears when listed:

```bash
pyenv versions
```

Set this version of python for peerlogic-api. In the root of the directory run:

```bash
pyenv local 3.7.15
```

Now check that we're using this binary and version for peerlogic-api.

```bash
which python
```

You should see `/Users/<name>/.pyenv/shims/python`. Anything else is incorrect and means you need to check your
preceding work.

Check the version of python you are running.

```bash
python --version
```

You should see python set to 3.7.15.

### Install and use Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

If the installation above doesn't work, or if you just want more information about poetry you can visit
[https://python-poetry.org/docs/].

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

>**NEVER MANUALLY CHANGE poetry.lock, and try to avoid manually changing `tool.poetry` sections in pyproject.toml**
> To update, remove and install dependencies, use the poetry CLI [add](https://python-poetry.org/docs/cli/#add)
> and [remove](https://python-poetry.org/docs/cli/#remove)
> If it is a development-only dependency, ensure you use `--dev`!

### Pre-commit Hooks

We have pre-commit hooks which execute inside the poetry environment for consistency.

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
export LDFLAGS="-L/opt/homebrew/opt/openssl@3/lib"
export CPPFLAGS="-I/opt/homebrew/opt/openssl@3/include"
export GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=1
export GRPC_PYTHON_BUILD_SYSTEM_ZLIB=1
```

Some google libs require a rust compiler.

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Psycopg2 requires some other host dependencies:

```bash
brew install postgresql@14
brew install openssl
brew link --force openssl
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
