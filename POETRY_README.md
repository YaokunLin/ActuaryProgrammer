# Poetry

### Installation (OSX)
Disclaimer: This is a work in progress and we do not have prebuilt wheels for google libs and psycopg2 so there is a bit of extra work involved for now, especially on ARM hardware

Poetry brings with it lots of benefits for deterministic deploys, etc. For now, we're only leveraging it for local development, but we may in the future update our dockerfile to leverage it therein.

We will still run dependencies (postgres, redis, etc.) locally with docker compose.

You will need to have the following installed. Be sure to follow prompts and put appropriate things on your PATH and in your .zshrc/.zprofile., brew, pyenv, and the appropriate python version (3.7.9 at time of writing) via pyenv installed if you don't already:

Xcode Command Line Tools
```
xcode-select --install
```

Homebrew
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Pyenv
```
brew install pyenv
```

Appropriate python version via Pyenv (3.7.9 at time of writing)
```
pyenv install 3.7.9
```

Poetry
```
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
```

After that you can run the following command which will create a virtual env via poetry for you.
```
poetry install
```

(Optional) To get into a shell for this virtual environment, just run:
```
poetry shell
```

Once your poetry environment is all set up, you can set your IDE's python interpreter to the virtual environment that Poetry created.
Instructions will vary per IDE.

### Updating dependencies
> :warning: **NEVER MANUALLY CHANGE poetry.lock, and try to avoid manually changing `tool.poetry` sections in pyproject.toml**

To update, remove and install dependencies, use the poetry CLI [add](https://python-poetry.org/docs/cli/#add) and [remove](https://python-poetry.org/docs/cli/#remove)
If it is a development-only dependency, ensure you use `--dev`!


### ARM Mac Stuff

Since we don't have prebuilt wheels, you'll have a few extra steps to get up and running.

Ensure the following environment variables are set (~/.zshrc probably):
```
export LDFLAGS="-L/opt/homebrew/opt/openssl@1.1/lib"
export CPPFLAGS="-I/opt/homebrew/opt/openssl@1.1/include"
export GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=1
export GRPC_PYTHON_BUILD_SYSTEM_ZLIB=1
```

Some of the google libs require a rust compiler.
```
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Psycopg2 requires some other host dependencies:
```
brew install postgresql
brew install openssl
brew link openssl
```

After all that is done (and your active shell reflects the changes), you should be all set to `poetry install`