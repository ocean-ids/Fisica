from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, SAFE_METHODS
from ..models import PatronAsignacion
from ..serializers import PatronAsignacionSerializer


class PatronAsignacionPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.has_perm('CoreFisica.view_patronasignacion')
        elif request.method == 'POST':
            return request.user.has_perm('CoreFisica.add_patronasignacion')
        elif request.method in ('PUT', 'PATCH'):
            return request.user.has_perm('CoreFisica.change_patronasignacion')
        elif request.method == 'DELETE':
            return request.user.has_perm('CoreFisica.delete_patronasignacion')
        return False

class PatronAsignacionListCreateView(generics.ListCreateAPIView):
    queryset = PatronAsignacion.objects.all()
    serializer_class = PatronAsignacionSerializer
    permission_classes = [permissions.IsAuthenticated, PatronAsignacionPermission]

    def create(self, request, *args, **kwargs):
       
        print('DEBUG: POST /api/patrones/ data:', request.data)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print('DEBUG: PatronAsignacion create errors:', serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

class PatronAsignacionRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PatronAsignacion.objects.all()
    serializer_class = PatronAsignacionSerializer
    permission_classes = [permissions.IsAuthenticated, PatronAsignacionPermission]



