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


from core.cloud_functions import bar

# noqa
from nexhealth_integration.cloud_functions.foo import foo
