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
from nexhealth_integration.cloud_functions.ingest_practice import (
    nexhealth_ingest_practice,
)
