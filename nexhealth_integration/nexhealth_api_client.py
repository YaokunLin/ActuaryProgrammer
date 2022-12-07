import json
from dataclasses import dataclass
from logging import getLogger
from traceback import format_exc
from typing import Dict, List, Optional
from urllib.parse import urlencode, urljoin

import requests

from nexhealth_integration.models import APIRequest

log = getLogger(__name__)


class NexHealthAPIClient:
    """
    This is a heavy-handed and opinionated client which exposes only a few endpoints.

    All requests made through this client are persisted to the database.

    Each NexHealthAPIClient instance is designed to interface with a single location.
    """

    @dataclass
    class _NexHealthAPIResponse:
        code: Optional[bool] = None
        description: Optional[List[str]] = None
        error: Optional[List[str]] = None
        count: Optional[int] = None
        data: Optional[Dict] = None

    def __init__(self, root_api_url: str, api_token: str, location_id: int, subdomain: str) -> None:
        self._session = requests.Session()
        self._session.headers = {
            "Authorization": api_token,
            "Accept": "application/vnd.Nexhealth+json; version=2",
            "Content-Type": "application/json",
        }
        self._root_api_url = root_api_url
        self._location_id = location_id
        self._subdomain = subdomain

    def _request(
        self,
        method: str,
        url_path: str,
        nh_resource: str,
        nh_id: Optional[int] = None,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        include_location_and_subdomain_params: bool = True,
    ) -> APIRequest:
        url = urljoin(self._root_api_url, url_path)
        if include_location_and_subdomain_params:
            if params is None:
                params = {}
            params["location_id"] = self._location_id
            params["subdomain"] = self._subdomain

        full_url = url
        if params:
            params = sorted([(k, v) for k, v in params.items()])
            full_url = f"{url}?{urlencode(params)}"

        request_record = APIRequest.objects.create(
            request_body=json.dumps(data) if data else "",
            request_headers=headers,
            request_method=method,
            request_nh_id=nh_id,
            request_nh_location_id=self._location_id if include_location_and_subdomain_params else None,
            request_nh_resource=nh_resource,
            request_nh_subdomain=self._subdomain if include_location_and_subdomain_params else None,
            request_path=url_path,
            request_query_parameters=params,
            request_url=full_url,
            request_status=APIRequest.Status.created,
        )
        log.info(f"[NexHealth] Initiating APIRequest ({request_record.id}): {method} {url_path}")
        try:
            response = self._session.request(method, url, params=params, data=data, headers=headers)
            log.info(
                f"[NexHealth] Received response for APIRequest ({request_record.id}): {method} {url_path} - {response.status_code} in {response.elapsed.total_seconds()} sec"
            )
            self._process_api_response(request_record, response)
        except Exception:  # noqa
            request_record.request_status = request_record.Status.error
            request_record.request_error_details = format_exc()
        finally:
            request_record.save()
            return request_record

    def _process_api_response(self, request_record: APIRequest, response: requests.models.Response) -> None:
        try:
            request_record.request_status = request_record.Status.completed
            request_record.response_time_sec = response.elapsed.total_seconds()
            request_record.response_status = response.status_code
            request_record.response_headers = dict(response.headers) if response.headers else None
            request_record.response_body = response.text
            response_obj = self._NexHealthAPIResponse(**response.json())
            request_record.response_nh_code = response_obj.code
            request_record.response_nh_count = response_obj.count
            request_record.response_nh_data = response_obj.data
            request_record.response_nh_description = response_obj.description
            request_record.response_nh_error = response_obj.error
        except Exception:  # noqa
            log.exception("[NexHealth] Error updating APIRequest ({request_record.id}) from response!")

    # --- Begin public methods ---
    def get_location(self) -> APIRequest:
        nh_resource = "locations"
        url_path = f"/{nh_resource}/{self._location_id}"
        return self._request("GET", url_path, nh_resource, nh_id=self._location_id, include_location_and_subdomain_params=False)

    def get_institution(self, nh_id: int) -> APIRequest:
        nh_resource = "institutions"
        url_path = f"/{nh_resource}/{nh_id}"
        return self._request("GET", url_path, nh_resource, nh_id=nh_id, include_location_and_subdomain_params=False)

    def get_patients(self, per_page: int = 300) -> APIRequest:
        nh_resource = "patients"
        url_path = f"/{nh_resource}"
        params = {"per_page": per_page}
        return self._request("GET", url_path, nh_resource, params=params)
