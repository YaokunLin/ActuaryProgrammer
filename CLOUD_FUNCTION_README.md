# Cloud Functions

## Overview

We leverage [Cloud Functions](https://cloud.google.com/functions) in this project to perform
asynchronous, potentially long-lived operations with or without robust retry, and triggered
ad hoc, on a schedule or in response to some event ([Pub/Sub](https://cloud.google.com/pubsub), [Cloud Storage Triggers](https://cloud.google.com/functions/docs/calling/storage), or [Cloud Function Webhook Targets](https://cloud.google.com/run/docs/triggering/webhooks)). For this specific project, more often than not these Cloud Functions will be
performing operations against our [RDBMS](https://cloud.google.com/sql/docs/postgres) using the [Django ORM](https://docs.djangoproject.com/en/4.1/topics/db/queries/).

> **THIS GUIDE IS NOT EXHAUSTIVE**
>
> For now, this guide is just going to cover setup for a Cloud Function triggered by Pub/Sub
> with a deadletter topic also setup. For other setups, you'll need to read some docs and
> extrapolate.

## Helpful Links
- [Cloud Functions](https://cloud.google.com/functions)
- [Pub/Sub](https://cloud.google.com/pubsub)
- [GitHub Actions Cloud Function Deploy](https://github.com/google-github-actions/deploy-cloud-functions)

## Implementation / Anatomy

#### [Entrypoint](main.py)

Cloud Function entrypoints are python functions with a specific signature in a specific file[^1].
Because of this, we must have a single [main.py](main.py) file for the entire project which has
the following responsibilities:
1. Setup the Django environment so that we can use the ORM. This includes loading of general configuration.
2. Import and expose entrypoints to Cloud Functions which are defined in their respective app directories.

This file should only be importing code from elsewhere. No functions should be defined here.

#### [GitHub Action Configuration](main.py)

This is a spicy [YAML](https://yaml.org/) file that configures the [GitHub Action](https://github.com/features/actions) (CI)
for all of our cloud functions.

This file is broken down into jobs and those jobs are broken down into steps:
1. Job runs to initialize variables for use in later jobs
2. Jobs run concurrently for each Cloud Function
   - This is the section that will be modified as you add/remove Cloud Functions
   - These jobs take about 3-5 minutes each and (again) run concurrently. Each job:
      - Checks out the code
      - Authenticates to GCP
      - Copies [requirements.txt](requirements/requirements.txt) to root directory[^1]
      - Deploys the Cloud Function and configures the [Subscription](https://cloud.google.com/pubsub/docs/create-subscription)
      - Configuration for the Cloud Function can be changed when necessary (e.g. memory, timeout, etc.)[^2]
3. Job runs to announce success or failure to Slack

#### Actual Logic
The actual logic for Cloud Functions can live in any of the app directories in this project.

Generally, our code should have the following structure:
```
peerlogic-api/
  .github/
  main.py
  app_name/
    cloud_functions/
      function_name.py
```

The function defined must have the following signature and must info log start and complete:
```py
import logging
from typing import Dict

from peerlogic.decorators import try_catch_log

log = logging.getLogger(__name__)


@try_catch_log
def function_name(event: Dict, context: Dict) -> None:
    log.info(f"Started function_name! Event: {event}, Context: {context}")
    # ... Logic goes here
    log.info("Completed function_name!")
```

## Monitoring

> **UNDER CONSTRUCTION**
>
> More to come...

## Example of Adding a Cloud Function

Let's add a new Cloud Function to the [NexHealth Integration app](nexhealth_integration/)!

Our function will be called "bar". This function will do is:
1. Info log that the function is starting up
2. Count the number of practices in the system and info log that value
3. Info log that the function is finished

We will trigger our function on a Pub/Sub topic, which we are also naming "bar".
Following our best practices, this topic will be backed by a deadletter topic.

To get messages into our Pub/Sub topic, we will create an admin-only API endpoint.

> For simplicity, we're going to be adding on our new function based on the existing configuration for
> another function, which is called "foo". For now, this is the quickest way to spin up a new cloud function:
> copy configuration from an existing function in the project.

> **UNDER CONSTRUCTION**
>
> More to come...

[^1]: https://cloud.google.com/functions/docs/writing#directory-structure-python
[^2]: https://github.com/google-github-actions/deploy-cloud-functions
