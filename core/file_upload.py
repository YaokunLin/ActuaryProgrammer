from gcloud.storage.blob import Blob
from typing import Dict, List


class FileToUpload(object):
    def __init__(self, mime_type: str = None, blob: Blob = None, errors: List[Dict] = None) -> None:
        if errors == None:
            errors = []
        self.mime_type = mime_type
        self.blob = blob
        self.errors = errors
        super().__init__()
