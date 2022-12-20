import json
from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from traceback import format_exc
from typing import Any, Callable, Dict, Generator, List, Optional
from urllib.parse import urlencode, urljoin

import requests

from nexhealth_integration.models import APIRequest
from nexhealth_integration.utils import NexHealthLogAdapter

log = NexHealthLogAdapter(getLogger(__name__))


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

    def __init__(self, root_api_url: str, api_token: str, nh_institution_id: int, nh_location_id: int, subdomain: str, max_per_page: int = 300) -> None:
        self._session = requests.Session()
        self._session.headers = {
            "Authorization": api_token,
            "Accept": "application/vnd.Nexhealth+json; version=2",
            "Content-Type": "application/json",
        }
        self._root_api_url = f"{root_api_url.rstrip('/')}/"
        self._nh_location_id = nh_location_id
        self._nh_institution_id = nh_institution_id
        self._subdomain = subdomain
        self._max_per_page = max_per_page

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
            params["location_id"] = self._nh_location_id
            params["subdomain"] = self._subdomain

        full_url = url
        if params:
            params = sorted([(k, v) for k, v in params.items()])
            full_url = f"{url}?{urlencode(params)}"

        request_record = APIRequest.objects.create(
            client_nh_institution_id=self._nh_institution_id,
            client_nh_location_id=self._nh_location_id,
            request_body=json.dumps(data) if data else "",
            request_headers=headers,
            request_method=method,
            request_nh_id=nh_id,
            request_nh_location_id=self._nh_location_id if include_location_and_subdomain_params else None,
            request_nh_resource=nh_resource,
            request_nh_subdomain=self._subdomain if include_location_and_subdomain_params else None,
            request_path=url_path,
            request_query_parameters=params,
            request_url=full_url,
            request_status=APIRequest.Status.created,
        )
        log.info(f"Initiating APIRequest ({request_record.id}): {method} {url_path}")
        try:
            response = self._session.request(method, url, params=params, data=data, headers=headers)
            log.info(
                f"Received response for APIRequest ({request_record.id}): {method} {url_path} - {response.status_code} - {response.elapsed.total_seconds()} sec"
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
            log.exception(f"Error updating APIRequest ({request_record.id}) from response!")

    # --- Begin public methods ---
    # --- Detail ---
    def get_location(self) -> APIRequest:
        """
        NexHealth Reference: https://docs.nexhealth.com/reference/getlocationsid
        """
        nh_resource = "locations"
        url_path = f"/{nh_resource}/{self._nh_location_id}"
        return self._request("GET", url_path, nh_resource, nh_id=self._nh_location_id, include_location_and_subdomain_params=False)

    def get_institution(self) -> APIRequest:
        """
        NexHealth Reference: https://docs.nexhealth.com/reference/getinstitutionsid
        """
        nh_resource = "institutions"
        url_path = f"/{nh_resource}/{self._nh_institution_id}"
        return self._request("GET", url_path, nh_resource, nh_id=self._nh_institution_id, include_location_and_subdomain_params=False)

    # --- List ---
    def iterate_list_requests(self, api_client_method: Callable, **kwargs: Any) -> Generator[APIRequest, None, None]:
        """
        For list endpoints, this method will yield APIRequest objects per page until all results are returned
        """

        def _should_keep_requesting(api_request: APIRequest, page: int, per_page: int) -> bool:
            total_count = api_request.response_nh_count

            if not api_request.response_nh_code:
                return False

            if not total_count:
                return False

            if per_page * page >= total_count:
                return False

            return True

        page = 1
        per_page = kwargs.get("per_page", self._max_per_page)
        kwargs["per_page"] = per_page

        while True:
            kwargs["page"] = page
            api_request = api_client_method(**kwargs)
            yield api_request
            if not _should_keep_requesting(api_request, page, per_page):
                break
            page += 1

    def list_patients(
        self,
        page: int = 1,
        per_page: Optional[int] = None,
        sort: str = "created_at",
        new_patients: Optional[bool] = None,
        non_patients: Optional[bool] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        include_different_location_patients: bool = False,
        include_upcoming_appts: bool = False,
        include_charges: bool = True,
        include_payments: bool = True,
        include_adjustments: bool = True,
        include_procedures: bool = False,
        include_insurance_coverages: bool = True,
        updated_since: Optional[datetime] = None,
    ) -> APIRequest:
        """
        NexHealth Reference: https://docs.nexhealth.com/reference/getpatients
        """
        nh_resource = "patients"
        url_path = f"/{nh_resource}"
        params = {
            "page": page,
            "per_page": per_page if per_page is not None else self._max_per_page,
            "location_strict": not include_different_location_patients,
            "sort": sort,
        }
        if new_patients is not None:
            params["new_patient"] = new_patients
        if non_patients is not None:
            params["non_patient"] = non_patients
        if name is not None:
            params["name"] = name
        if email is not None:
            params["email"] = email
        if phone_number is not None:
            params["phone_number"] = phone_number
        if updated_since is not None:
            params["updated_since"] = updated_since.isoformat()

        include = []
        if include_upcoming_appts:
            include.append("upcoming_appts")
        if include_charges:
            include.append("charges")
        if include_procedures:
            include.append("procedures")
        if include_payments:
            include.append("payments")
        if include_adjustments:
            include.append("adjustments")
        if include_insurance_coverages:
            include.append("insurance_coverages")
        if include:
            params["include[]"] = include
        return self._request("GET", url_path, nh_resource, params=params)

    def list_appointments(
        self,
        start_time: datetime,
        end_time: datetime,
        page: int = 1,
        appointment_type_id: Optional[int] = None,
        include_booking_details: bool = True,
        include_descriptors: bool = True,
        include_patients: bool = False,  # patient_id will still be included
        include_procedures: bool = True,
        is_cancelled: Optional[bool] = None,
        patient_id: Optional[int] = None,
        per_page: Optional[int] = None,
        updated_since: Optional[datetime] = None,
    ) -> APIRequest:
        """
        NexHealth Reference: https://docs.nexhealth.com/reference/getappointments
        """
        nh_resource = "appointments"
        url_path = f"/{nh_resource}"
        params = {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "page": page,
            "per_page": per_page if per_page is not None else self._max_per_page,
        }
        if updated_since is not None:
            params["updated_since"] = updated_since.isoformat()
        if is_cancelled is not None:
            params["cancelled"] = is_cancelled
        if patient_id is not None:
            params["patient_id"] = patient_id
        if appointment_type_id is not None:
            params["appointment_type_id"] = appointment_type_id
        include = []
        if include_patients:
            include.append("patient")
        if include_booking_details:
            include.append("booking_details")
        if include_procedures:
            include.append("procedures")
        if include_descriptors:
            include.append("descriptors")
        if include:
            params["include[]"] = include
        return self._request("GET", url_path, nh_resource, params=params)

    def list_providers(
        self,
        page: int = 1,
        per_page: Optional[int] = None,
        updated_since: Optional[datetime] = None,
        foreign_id: Optional[str] = None,
        requestable: Optional[bool] = None,
        inactive: Optional[bool] = None,
        include_locations: bool = False,
        include_availabilities: bool = True,
    ) -> APIRequest:
        """
        NexHealth Reference: https://docs.nexhealth.com/reference/getproviders
        """
        nh_resource = "providers"
        url_path = f"/{nh_resource}"
        params = {
            "page": page,
            "per_page": per_page if per_page is not None else self._max_per_page,
        }
        if updated_since is not None:
            params["updated_since"] = updated_since.isoformat()
        if foreign_id is not None:
            params["foreign_id"] = foreign_id
        if requestable is not None:
            params["requestable"] = requestable
        if inactive is not None:
            params["inactive"] = inactive
        include = []
        if include_locations:
            include.append("locations")
        if include_availabilities:
            include.append("availabilities")
        if include:
            params["include[]"] = include
        return self._request("GET", url_path, nh_resource, params=params)

    def list_insurance_plans(
        self,
        page: int = 1,
        per_page: Optional[int] = None,
        payer_id: Optional[str] = None,
        group_num: Optional[str] = None,
        include_patient_coverages: bool = False,
    ):
        """
        NexHealth Reference: https://sandbox.nexhealth.com/insurance_plans
        """
        nh_resource = "insurance_plans"
        url_path = f"/{nh_resource}"
        params = {
            "page": page,
            "per_page": per_page if per_page is not None else self._max_per_page,
            "subdomain": self._subdomain,
        }
        if payer_id is not None:
            params["payer_id"] = payer_id
        if group_num is not None:
            params["group_num"] = group_num
        if include_patient_coverages:
            params["include[]"] = ["patient_coverages"]

        return self._request("GET", url_path, nh_resource, params=params, include_location_and_subdomain_params=False)
