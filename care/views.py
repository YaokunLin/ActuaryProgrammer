from django.db.models import Q
from django.db.models.functions import Upper
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from care.models import Procedure
from care.serializers import ExistingPatientsSerializer, ProcedureSerializer
from core.models import Appointment, Patient, Practice


class ProcedureViewset(viewsets.ModelViewSet):
    queryset = Procedure.objects.all().order_by("-modified_at")
    serializer_class = ProcedureSerializer
    filter_fields = ["ada_code", "procedure_price_average"]


@api_view(["GET"])
@permission_classes([IsAdminUser])
def get_existing_patients(request: Request) -> Response:
    """
    Given a practice ID, phone number and other optional data, return whether patients exist in the system matching that info
    """
    now = timezone.now()
    serializer = ExistingPatientsSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    practice = serializer.validated_data["practice"]
    phone_number = serializer.validated_data["phone_number"]
    name_last = serializer.validated_data.get("name_last")

    phone_number = phone_number.as_e164  # Numbers are stored e.164, so must format to query

    patients = practice.patients.prefetch_related("appointments").filter(
        Q(phone_number=phone_number) | Q(phone_mobile=phone_number) | Q(phone_home=phone_number) | Q(phone_work=phone_number) | Q(phone_fax=phone_number)
    )

    if patients and name_last:
        patients = patients.alias(name_last_upper=Upper("name_last")).filter(name_last_upper=name_last.upper())

    matches_existing_patient = False
    for patient in patients:
        appointments = patient.appointments.order_by("-created_at").all()
        latest_appointment = appointments.first()
        # appointment.is_new_patient being set to false (not NULL) means that a patient has completed appointments before according to the PMS
        if latest_appointment and latest_appointment.is_new_patient is False:
            matches_existing_patient = True
            break

        for appointment in appointments:
            if appointment.status == appointment.Status.COMPLETED or appointment.appointment_end_at < now:
                matches_existing_patient = True
                break

        if matches_existing_patient:
            break

    data = {"total_matches": patients.count(), "matches_existing_patient": matches_existing_patient}
    return Response(data, status=HTTP_200_OK)
