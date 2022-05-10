from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.exceptions import APIException


class InternalServerError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = _("Internal Server Error")
    default_code = "internal_server_error"


class ServiceUnavailableError(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = _("Service unavailable. Try again later.")
    default_code = "service_unavailable_error"
