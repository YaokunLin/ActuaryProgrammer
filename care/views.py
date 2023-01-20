from django.db.models import Q
from django.db.models.functions import Upper
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from care.models import Patient, Procedure
from care.serializers import ExistingPatientsSerializer, ProcedureSerializer


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
    appointment_created_before = serializer.validated_data["appointment_created_before"]
    practice = serializer.validated_data["practice"]
    phone_number = serializer.validated_data["phone_number"]
    name_last = serializer.validated_data.get("name_last")

    phone_number = phone_number.as_e164  # Numbers are stored e.164, so must format to query

    # Check the whole system to see if ANY patient records exist with this number
    all_patients_qs = Patient.objects.filter(
        Q(phone_number=phone_number) | Q(phone_mobile=phone_number) | Q(phone_home=phone_number) | Q(phone_work=phone_number) | Q(phone_fax=phone_number)
    )
    if name_last:
        all_patients_qs = all_patients_qs.alias(name_last_upper=Upper("name_last")).filter(name_last_upper=name_last.upper())
    is_patient_in_system = all_patients_qs.exists()

    # Check patients bound to the given practice more specifically
    patients = practice.patients.prefetch_related("appointments").filter(
        Q(phone_number=phone_number) | Q(phone_mobile=phone_number) | Q(phone_home=phone_number) | Q(phone_work=phone_number) | Q(phone_fax=phone_number)
    )

    # If a last name is given, do a case-insensitive filter on that
    if name_last:
        patients = patients.alias(name_last_upper=Upper("name_last")).filter(name_last_upper=name_last.upper())

    # Figure out whether any matching patients have completed appointments before
    has_completed_appointments_at_practice = False
    for patient in patients:
        appointments = patient.appointments.filter(pms_created_at__lt=appointment_created_before).order_by("-pms_created_at").all()
        latest_appointment = appointments.first()
        # appointment.is_new_patient being set to false (not NULL) means that a patient has completed appointments before according to the PMS
        if latest_appointment and latest_appointment.is_new_patient is False:
            has_completed_appointments_at_practice = True
            break

        # For all appointments in descending created_at order, if the appointment has been completed, set has_completed_appointments_at_practice and stop looping
        for appointment in appointments:
            if appointment.status == appointment.Status.COMPLETED or appointment.appointment_end_at < now:
                has_completed_appointments_at_practice = True
                break

        if has_completed_appointments_at_practice:
            break

    # is_patient_at_practice: bool whether any patients match for the given name/number at the practice, regardless of completed appointment
    # has_completed_appointments_at_practice: bool whether any of the matching patients are "existing" insofar as they've completed an appointment
    # is_patient_in_system: bool whether any patient record exists with a matching number in the whole system
    return Response(
        {
            "is_patient_at_practice": patients.exists(),
            "has_completed_appointments_at_practice": has_completed_appointments_at_practice,
            "is_patient_in_system": is_patient_in_system,
        },
        status=HTTP_200_OK,
    )
