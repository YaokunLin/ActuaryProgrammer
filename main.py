"""
Cloud function entrypoints

All we should do here is import entrypoints we wish to expose
"""
import logging
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "peerlogic.settings")

django.setup()
log = logging.getLogger(__name__)


# noqa
# TODO Kyle: from cloud_functions.foo.entrypoint import foo
def foo(event, context) -> None:
    log.info(f"Started foo! Event: {event}, Context: {context}")
    log.info("Completed foo!")
