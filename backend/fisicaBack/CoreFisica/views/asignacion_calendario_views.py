from rest_framework import viewsets
from ..models import AsignacionCalendario
from ..serializers import AsignacionCalendarioSerializer

class AsignacionCalendarioViewSet(viewsets.ModelViewSet):
    queryset = AsignacionCalendario.objects.all()
    serializer_class = AsignacionCalendarioSerializer
