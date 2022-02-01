from gcloud.storage.blob import Blob
from typing import Dict, List


class FileToUpload(object):
    def __init__(self, mime_type: str = None, blob: Blob = None):
        self.mime_type = mime_type
        self.blob = blob
        super().__init__()
