# Poetry

### Installation (OSX)
Disclaimer: This is a work in progress and we do not have prebuilt wheels for google libs and psycopg2 so there is a bit of extra work involved for now, especially on M1 hardware

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

To update and install dependencies, use the poetry CLI [add](https://python-poetry.org/docs/cli/#add), [update](https://python-poetry.org/docs/cli/#update),
and [remove](https://python-poetry.org/docs/cli/#remove)
If it is a development-only dependency, ensure you use `--dev`!
